<?php

declare(strict_types=1);

require_once '/var/www/safegloss/src/bootstrap.php';

function usage(): never
{
    fwrite(STDERR, "Usage:\n  php setup.php site <name> <4-digit-code> <chapter3|table3>\n  php setup.php user <researcher|instructor> <username> <email> [4-digit-site-code]\n");
    exit(2);
}

function prompt_password(): string
{
    fwrite(STDOUT, 'Password: ');
    shell_exec('stty -echo');
    $password = trim((string) fgets(STDIN));
    shell_exec('stty echo');
    fwrite(STDOUT, "\n");
    if (strlen($password) < 12) {
        throw new RuntimeException('Password must contain at least 12 characters.');
    }
    return $password;
}

try {
    $command = $argv[1] ?? null;
    if ($command === 'site' && count($argv) === 5) {
        [$script, $_command, $name, $code, $profile] = $argv;
        if (!preg_match('/^[0-9]{4}$/', $code) || !in_array($profile, ['chapter3', 'table3'], true)) {
            usage();
        }
        $labelAMode = $profile === 'chapter3' ? 'margin' : 'contiguous';
        db()->prepare('INSERT INTO sites (name, join_code_digest, label_a_mode) VALUES (?, ?, ?)')
            ->execute([$name, join_code_digest($code), $labelAMode]);
        $siteId = (int) db()->lastInsertId();
        db()->prepare('INSERT INTO rosters (site_id, name, is_site_roster) VALUES (?, ?, TRUE)')
            ->execute([$siteId, $name . ' site roster']);
        fwrite(STDOUT, "Created site {$name} with {$profile} treatment-label profile.\n");
        exit(0);
    }
    if ($command === 'user' && in_array(count($argv), [5, 6], true)) {
        $role = $argv[2];
        $username = $argv[3];
        $email = $argv[4];
        if (!in_array($role, ['researcher', 'instructor'], true) || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
            usage();
        }
        $siteId = null;
        if ($role === 'instructor') {
            if (!isset($argv[5])) { usage(); }
            $site = find_site_by_join_code(db(), $argv[5]);
            if ($site === null) { throw new RuntimeException('Site code not found.'); }
            $siteId = $site['id'];
        }
        $password = prompt_password();
        db()->prepare('INSERT INTO users (site_id, username, email, password_hash, role) VALUES (?, ?, ?, ?, ?)')
            ->execute([$siteId, $username, $email, password_hash($password, PASSWORD_DEFAULT), $role]);
        fwrite(STDOUT, "Created {$role} account {$username}.\n");
        exit(0);
    }
    usage();
} catch (Throwable $exception) {
    fwrite(STDERR, 'Setup failed: ' . $exception->getMessage() . "\n");
    exit(1);
}
