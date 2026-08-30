<?php

declare(strict_types=1);

function nav_items(?array $user): array
{
    if ($user === null) {
        return [
            'home' => 'Home',
            'login' => 'Login',
            'register' => 'Register',
        ];
    }
    if ($user['role'] === 'student') {
        return [
            'dashboard' => 'Home',
            'my_lessons' => 'My Lessons',
            'my_scores' => 'My Scores',
        ];
    }
    if ($user['role'] === 'instructor') {
        return [
            'dashboard' => 'Home',
            'stories' => 'Stories',
            'glosses' => 'Glosses',
            'quizzes' => 'Quizzes',
            'lessons_manage' => 'Lessons',
            'rosters' => 'Site',
            'gradebook' => 'Gradebook',
        ];
    }
    return [
        'dashboard' => 'Home',
        'system_log' => 'System Log',
        'score_log' => 'Score Log',
        'mail_log' => 'Mail Log',
    ];
}

function render_header(string $title, string $activePage, ?array $user = null): void
{
    $fullTitle = $title === '' ? 'SafeGloss' : $title . ' - SafeGloss';
    ?>
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title><?= h($fullTitle) ?></title>
    <link rel="stylesheet" href="/assets/safegloss.css">
    <script src="/assets/safegloss.js" defer></script>
</head>
<body data-page="<?= h($activePage) ?>">
<a class="skip-link" href="#main-content">Skip to main content</a>
<div class="site-shell">
    <header class="brand-bar">
        <a class="brand" href="/index.php">
            <span class="brand-mark" aria-hidden="true">SS</span>
            <span class="brand-name">SafeGloss</span>
            <span class="brand-tagline">glossary management system</span>
        </a>
        <?php if ($user !== null): ?>
            <div class="session-links">
                <span>Signed in as <?= h($user['username']) ?></span>
                <form method="post" action="/index.php" class="inline-form">
                    <input type="hidden" name="csrf_token" value="<?= h(csrf_token()) ?>">
                    <input type="hidden" name="action" value="logout">
                    <button class="link-button" type="submit">Logout</button>
                </form>
            </div>
        <?php endif; ?>
    </header>
    <nav class="primary-nav" aria-label="Primary">
        <?php foreach (nav_items($user) as $page => $label): ?>
            <a href="/index.php?page=<?= h($page) ?>"<?= $page === $activePage ? ' aria-current="page"' : '' ?>><?= h($label) ?></a>
        <?php endforeach; ?>
    </nav>
    <main id="main-content" tabindex="-1">
        <?php foreach (take_flashes() as $message): ?>
            <div class="notice notice-<?= h($message['kind']) ?>" role="status"><?= h($message['message']) ?></div>
        <?php endforeach; ?>
        <h1><?= h($title) ?></h1>
    <?php
}

function render_footer(): void
{
    ?>
    </main>
    <footer>
        <span>SafeGloss research application reconstruction</span>
        <span>Original study platform described in 2014</span>
    </footer>
</div>
</body>
</html>
    <?php
}

function csrf_field(): void
{
    ?><input type="hidden" name="csrf_token" value="<?= h(csrf_token()) ?>"><?php
}

function render_error_page(Throwable $exception): void
{
    $status = http_response_code();
    if ($status < 400) {
        http_response_code(500);
        $status = 500;
    }
    $user = null;
    try {
        $user = current_user();
    } catch (Throwable) {
        // The error page must also work when the database is unavailable.
    }
    render_header('Unable to complete request', 'error', $user);
    echo '<div class="notice notice-error" role="alert">';
    echo h(app_config('env') === 'development' ? $exception->getMessage() : 'The request could not be completed.');
    echo '</div><p>Status: ' . h($status) . '</p>';
    render_footer();
}
