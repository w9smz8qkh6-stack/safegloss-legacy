<?php

declare(strict_types=1);

const APP_ROOT = __DIR__ . '/..';

function env_value(string $name, ?string $default = null): ?string
{
    $value = getenv($name);
    return $value === false ? $default : $value;
}

function app_config(string $name): string
{
    static $config = null;

    if ($config === null) {
        $config = [
            'env' => env_value('APP_ENV', 'production'),
            'key' => env_value('APP_KEY', ''),
            'url' => rtrim((string) env_value('APP_URL', ''), '/'),
            'db_host' => env_value('DB_HOST', '127.0.0.1'),
            'db_port' => env_value('DB_PORT', '3306'),
            'db_name' => env_value('DB_NAME', 'safegloss_legacy'),
            'db_user' => env_value('DB_USER', 'safegloss'),
            'db_password' => env_value('DB_PASSWORD', ''),
            'mail_transport' => env_value('MAIL_TRANSPORT', 'database'),
            'mail_from' => env_value('MAIL_FROM', 'webmaster@safegloss.invalid'),
            'report_to' => env_value('RESEARCH_REPORT_TO', 'researcher@safegloss.invalid'),
            'smtp_host' => env_value('SMTP_HOST', ''),
            'smtp_port' => env_value('SMTP_PORT', '587'),
            'smtp_encryption' => env_value('SMTP_ENCRYPTION', 'starttls'),
            'smtp_username' => env_value('SMTP_USERNAME', ''),
            'smtp_password' => env_value('SMTP_PASSWORD', ''),
        ];

        if ($config['key'] === '') {
            throw new RuntimeException('APP_KEY is required.');
        }
        if ($config['env'] === 'production' && strlen($config['key']) < 32) {
            throw new RuntimeException('APP_KEY must contain at least 32 characters in production.');
        }
    }

    if (!array_key_exists($name, $config)) {
        throw new InvalidArgumentException("Unknown configuration key: {$name}");
    }

    return (string) $config[$name];
}

function db(): PDO
{
    static $pdo = null;

    if ($pdo === null) {
        $dsn = sprintf(
            'mysql:host=%s;port=%s;dbname=%s;charset=utf8mb4',
            app_config('db_host'),
            app_config('db_port'),
            app_config('db_name')
        );
        $pdo = new PDO($dsn, app_config('db_user'), app_config('db_password'), [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false,
        ]);
        $pdo->exec("SET time_zone = '+00:00'");
    }

    return $pdo;
}

function is_https(): bool
{
    return (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off')
        || ($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https';
}

function start_secure_session(): void
{
    if (PHP_SAPI === 'cli' || session_status() === PHP_SESSION_ACTIVE) {
        return;
    }

    session_name('safegloss_legacy');
    session_set_cookie_params([
        'lifetime' => 0,
        'path' => '/',
        'secure' => is_https(),
        'httponly' => true,
        'samesite' => 'Lax',
    ]);
    session_start();
}

function send_security_headers(): void
{
    if (PHP_SAPI === 'cli' || headers_sent()) {
        return;
    }

    header('X-Content-Type-Options: nosniff');
    header('X-Frame-Options: DENY');
    header('Referrer-Policy: same-origin');
    header('Permissions-Policy: camera=(), microphone=(), geolocation=()');
    header("Content-Security-Policy: default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'");
}

function h(mixed $value): string
{
    return htmlspecialchars((string) $value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function sanitize_rich_html(string $html): string
{
    $allowedTags = ['p', 'br', 'strong', 'b', 'em', 'i', 'u', 'ul', 'ol', 'li', 'blockquote', 'a', 'img', 'span'];
    $allowedAttributes = [
        'a' => ['href', 'title'],
        'img' => ['src', 'alt', 'width', 'height'],
        'span' => ['lang'],
    ];

    $document = new DOMDocument('1.0', 'UTF-8');
    libxml_use_internal_errors(true);
    $document->loadHTML(
        '<!doctype html><html><body><div id="safegloss-root">' . $html . '</div></body></html>',
        LIBXML_HTML_NOIMPLIED | LIBXML_HTML_NODEFDTD
    );
    libxml_clear_errors();

    $root = $document->getElementById('safegloss-root');
    if (!$root instanceof DOMElement) {
        return '';
    }

    $cleanNode = function (DOMNode $node) use (&$cleanNode, $document, $allowedTags, $allowedAttributes): void {
        foreach (iterator_to_array($node->childNodes) as $child) {
            if (!$child instanceof DOMElement) {
                continue;
            }

            $tag = strtolower($child->tagName);
            if (!in_array($tag, $allowedTags, true)) {
                $cleanNode($child);
                $fragment = $document->createDocumentFragment();
                while ($child->firstChild !== null) {
                    $fragment->appendChild($child->firstChild);
                }
                $node->replaceChild($fragment, $child);
                continue;
            }

            foreach (iterator_to_array($child->attributes) as $attribute) {
                $allowed = $allowedAttributes[$tag] ?? [];
                if (!in_array(strtolower($attribute->name), $allowed, true)) {
                    $child->removeAttributeNode($attribute);
                }
            }

            foreach (['href', 'src'] as $urlAttribute) {
                if (!$child->hasAttribute($urlAttribute)) {
                    continue;
                }
                $url = trim($child->getAttribute($urlAttribute));
                if (!preg_match('/^(https?:|mailto:|\/)/i', $url)) {
                    $child->removeAttribute($urlAttribute);
                }
            }

            if ($tag === 'a') {
                $child->setAttribute('rel', 'noopener noreferrer');
            }
            $cleanNode($child);
        }
    };

    $cleanNode($root);
    $output = '';
    foreach ($root->childNodes as $child) {
        $output .= $document->saveHTML($child);
    }
    return $output;
}

function csrf_token(): string
{
    start_secure_session();
    if (empty($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }
    return (string) $_SESSION['csrf_token'];
}

function require_csrf(): void
{
    $submitted = (string) ($_POST['csrf_token'] ?? '');
    if (!hash_equals(csrf_token(), $submitted)) {
        http_response_code(419);
        throw new RuntimeException('Your form session expired. Please return and try again.');
    }
}

function flash(string $kind, string $message): void
{
    start_secure_session();
    $_SESSION['flash'][] = ['kind' => $kind, 'message' => $message];
}

function take_flashes(): array
{
    start_secure_session();
    $messages = $_SESSION['flash'] ?? [];
    unset($_SESSION['flash']);
    return is_array($messages) ? $messages : [];
}

function redirect_to(string $page, array $parameters = []): never
{
    $query = http_build_query(['page' => $page] + $parameters);
    header('Location: /index.php?' . $query, true, 303);
    exit;
}

function current_user(): ?array
{
    start_secure_session();
    $userId = filter_var($_SESSION['user_id'] ?? null, FILTER_VALIDATE_INT);
    if (!$userId) {
        return null;
    }

    $statement = db()->prepare('SELECT * FROM users WHERE id = ? AND is_active = TRUE');
    $statement->execute([$userId]);
    $user = $statement->fetch();
    return $user ?: null;
}

function require_user(?string $role = null): array
{
    $user = current_user();
    if ($user === null) {
        flash('error', 'Please log in to continue.');
        redirect_to('login');
    }
    if ($role !== null && $user['role'] !== $role) {
        http_response_code(403);
        throw new RuntimeException('You do not have access to this page.');
    }
    return $user;
}

require_once __DIR__ . '/domain.php';
require_once __DIR__ . '/mailer.php';
require_once __DIR__ . '/ui.php';

start_secure_session();
send_security_headers();
