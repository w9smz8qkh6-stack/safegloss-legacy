<?php

declare(strict_types=1);

function join_code_digest(string $code): string
{
    return hash_hmac('sha256', trim($code), app_config('key'));
}

function treatment_mode_for_label(string $label, string $labelAMode): string
{
    if (!in_array($label, ['A', 'B'], true)) {
        throw new InvalidArgumentException('Treatment label must be A or B.');
    }
    if (!in_array($labelAMode, ['contiguous', 'margin'], true)) {
        throw new InvalidArgumentException('Label A mode must be contiguous or margin.');
    }
    return $label === 'A'
        ? $labelAMode
        : ($labelAMode === 'contiguous' ? 'margin' : 'contiguous');
}

function choose_treatment_label(array $existingLabels, ?int $randomBit = null): string
{
    $last = end($existingLabels);
    if ($last === 'A') {
        return 'B';
    }
    if ($last === 'B') {
        return 'A';
    }
    $randomBit ??= random_int(0, 1);
    return $randomBit === 0 ? 'A' : 'B';
}

function find_site_by_join_code(PDO $pdo, string $code, bool $lock = false): ?array
{
    $sql = 'SELECT * FROM sites WHERE join_code_digest = ? AND is_active = TRUE';
    if ($lock) {
        $sql .= ' FOR UPDATE';
    }
    $statement = $pdo->prepare($sql);
    $statement->execute([join_code_digest($code)]);
    $site = $statement->fetch();
    return $site ?: null;
}

function assignment_for_site(PDO $pdo, array $site): array
{
    if ($site['assignment_strategy'] === 'post_experiment_balanced') {
        $statement = $pdo->prepare(
            "SELECT u.treatment_label, COUNT(DISTINCT a.id) qualified_count
             FROM users u
             LEFT JOIN lesson_attempts a ON a.student_id = u.id AND a.status = 'completed'
             LEFT JOIN system_events e ON e.attempt_id = a.id AND e.action = 'gloss_open'
             WHERE u.site_id = ? AND u.role = 'student' AND e.id IS NOT NULL
             GROUP BY u.treatment_label"
        );
        $statement->execute([$site['id']]);
        $counts = ['A' => 0, 'B' => 0];
        foreach ($statement->fetchAll() as $row) {
            if (isset($counts[$row['treatment_label']])) {
                $counts[$row['treatment_label']] = (int) $row['qualified_count'];
            }
        }
        if ($counts['A'] !== $counts['B']) {
            $label = $counts['A'] < $counts['B'] ? 'A' : 'B';
            return [$label, treatment_mode_for_label($label, $site['label_a_mode'])];
        }
    }

    $statement = $pdo->prepare(
        "SELECT treatment_label FROM users
         WHERE site_id = ? AND role = 'student' AND treatment_label IS NOT NULL
         ORDER BY id"
    );
    $statement->execute([$site['id']]);
    $labels = array_column($statement->fetchAll(), 'treatment_label');
    $label = choose_treatment_label($labels);
    return [$label, treatment_mode_for_label($label, $site['label_a_mode'])];
}

function record_event(
    PDO $pdo,
    array $user,
    string $action,
    ?array $attempt = null,
    ?string $term = null,
    array $context = [],
    ?string $clientEventId = null,
    ?string $clientRecordedAt = null
): void {
    $statement = $pdo->prepare(
        'INSERT INTO system_events
        (attempt_id, user_id, site_id, lesson_id, treatment_label, treatment_mode,
         action, term_text, client_event_id, client_recorded_at, context_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
    );
    $statement->execute([
        $attempt['id'] ?? null,
        $user['id'],
        $user['site_id'] ?? null,
        $attempt['lesson_id'] ?? null,
        $attempt['treatment_label'] ?? $user['treatment_label'] ?? null,
        $attempt['treatment_mode'] ?? $user['treatment_mode'] ?? null,
        $action,
        $term,
        $clientEventId,
        $clientRecordedAt,
        json_encode($context, JSON_THROW_ON_ERROR),
    ]);
}

function owned_attempt(array $user, int $attemptId): array
{
    $statement = db()->prepare('SELECT * FROM lesson_attempts WHERE id = ? AND student_id = ?');
    $statement->execute([$attemptId, $user['id']]);
    $attempt = $statement->fetch();
    if (!$attempt) {
        http_response_code(404);
        throw new RuntimeException('Lesson attempt not found.');
    }
    return $attempt;
}

function paired_gloss_durations(array $events): array
{
    $openEvents = [];
    $pairs = [];

    foreach ($events as $event) {
        $term = (string) ($event['term_text'] ?? '');
        $action = (string) ($event['action'] ?? '');
        $timestamp = $event['server_recorded_at'] ?? null;
        if ($term === '' || !is_string($timestamp)) {
            continue;
        }
        if ($action === 'gloss_open') {
            $openEvents[$term][] = $timestamp;
            continue;
        }
        if ($action !== 'gloss_close' || empty($openEvents[$term])) {
            continue;
        }

        $openedAt = array_shift($openEvents[$term]);
        $opened = new DateTimeImmutable($openedAt, new DateTimeZone('UTC'));
        $closed = new DateTimeImmutable($timestamp, new DateTimeZone('UTC'));
        $seconds = (float) $closed->format('U.u') - (float) $opened->format('U.u');
        if ($seconds >= 0) {
            $pairs[] = [
                'term' => $term,
                'opened_at' => $openedAt,
                'closed_at' => $timestamp,
                'duration_seconds' => $seconds,
            ];
        }
    }

    return $pairs;
}

function score_answers(array $questions, array $submittedAnswers): array
{
    $details = [];
    $correct = 0;

    foreach ($questions as $question) {
        $questionId = (int) $question['id'];
        $selected = isset($submittedAnswers[$questionId])
            ? (int) $submittedAnswers[$questionId]
            : null;
        $correctChoiceId = null;
        foreach ($question['choices'] as $choice) {
            if ((bool) $choice['is_correct']) {
                $correctChoiceId = (int) $choice['id'];
                break;
            }
        }
        $isCorrect = $selected !== null && $selected === $correctChoiceId;
        $correct += $isCorrect ? 1 : 0;
        $details[] = [
            'question_id' => $questionId,
            'selected_choice_id' => $selected,
            'is_correct' => $isCorrect,
        ];
    }

    $total = count($questions);
    return [
        'correct' => $correct,
        'total' => $total,
        'percent' => $total > 0 ? round(($correct / $total) * 100, 3) : 0.0,
        'details' => $details,
    ];
}

function duration_seconds(?string $start, ?string $end): ?float
{
    if ($start === null || $end === null) {
        return null;
    }
    $startTime = new DateTimeImmutable($start, new DateTimeZone('UTC'));
    $endTime = new DateTimeImmutable($end, new DateTimeZone('UTC'));
    return max(0.0, (float) $endTime->format('U.u') - (float) $startTime->format('U.u'));
}
