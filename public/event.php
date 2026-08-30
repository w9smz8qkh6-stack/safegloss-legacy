<?php

declare(strict_types=1);

require_once '/var/www/safegloss/src/bootstrap.php';

header('Content-Type: application/json; charset=utf-8');

try {
    if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
        http_response_code(405);
        throw new RuntimeException('POST required.');
    }
    require_csrf();
    $user = require_user('student');
    $attempt = owned_attempt($user, (int) ($_POST['attempt_id'] ?? 0));
    if ($attempt['status'] !== 'reading') {
        http_response_code(409);
        throw new RuntimeException('The reading session is not active.');
    }
    $action = (string) ($_POST['event_action'] ?? '');
    if (!in_array($action, ['gloss_open', 'gloss_close'], true)) {
        throw new RuntimeException('Unsupported reading event.');
    }
    $clientRecordedAt = (string) ($_POST['client_recorded_at'] ?? '');
    try {
        $parsedClientTime = new DateTimeImmutable($clientRecordedAt);
        $mysqlClientTime = $parsedClientTime->setTimezone(new DateTimeZone('UTC'))->format('Y-m-d H:i:s.u');
    } catch (Throwable) {
        $mysqlClientTime = null;
    }
    $term = trim((string) ($_POST['term'] ?? ''));
    $clientEventId = trim((string) ($_POST['client_event_id'] ?? ''));
    if ($term === '' || mb_strlen($term) > 255) {
        throw new RuntimeException('A valid gloss term is required.');
    }
    if (!preg_match('/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i', $clientEventId)) {
        throw new RuntimeException('A valid version 4 event identifier is required.');
    }
    record_event(
        db(), $user, $action, $attempt, $term,
        ['client_timezone_offset' => (int) ($_POST['client_timezone_offset'] ?? 0)],
        $clientEventId, $mysqlClientTime ?: null
    );
    echo json_encode(['ok' => true], JSON_THROW_ON_ERROR);
} catch (Throwable $exception) {
    if (http_response_code() < 400) { http_response_code(400); }
    echo json_encode(['ok' => false, 'error' => app_config('env') === 'development' ? $exception->getMessage() : 'Event rejected.'], JSON_THROW_ON_ERROR);
}
