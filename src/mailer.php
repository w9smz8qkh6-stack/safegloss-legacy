<?php

declare(strict_types=1);

function build_session_report(PDO $pdo, int $attemptId): array
{
    $statement = $pdo->prepare(
        "SELECT a.*, u.username, u.technology_proficiency, u.glossary_proficiency,
                s.name site_name, l.title lesson_title, q.correct_count, q.question_count
         FROM lesson_attempts a
         JOIN users u ON u.id = a.student_id
         JOIN sites s ON s.id = u.site_id
         JOIN lessons l ON l.id = a.lesson_id
         JOIN quiz_submissions q ON q.attempt_id = a.id
         WHERE a.id = ?"
    );
    $statement->execute([$attemptId]);
    $attempt = $statement->fetch();
    if (!$attempt) {
        throw new RuntimeException('Cannot build a report for an unknown attempt.');
    }

    $eventStatement = $pdo->prepare(
        "SELECT action, term_text, server_recorded_at
         FROM system_events WHERE attempt_id = ?
         ORDER BY server_recorded_at, id"
    );
    $eventStatement->execute([$attemptId]);
    $pairs = paired_gloss_durations($eventStatement->fetchAll());
    $totalGloss = array_sum(array_column($pairs, 'duration_seconds'));
    $readingDuration = duration_seconds($attempt['reading_started_at'], $attempt['reading_ended_at']);

    $lines = [
        'SafeGloss Session Report',
        str_repeat('=', 24),
        'Participant: ' . $attempt['username'],
        'Site: ' . $attempt['site_name'],
        'Technology proficiency: ' . ($attempt['technology_proficiency'] ?? 'not recorded'),
        'Glossary proficiency: ' . ($attempt['glossary_proficiency'] ?? 'not recorded'),
        'Treatment label: ' . $attempt['treatment_label'],
        'Treatment mode: ' . $attempt['treatment_mode'],
        'Comprehension score: ' . $attempt['score_percent'] . '%',
        'Lesson: ' . $attempt['lesson_title'] . ' (ID ' . $attempt['lesson_id'] . ')',
        'Reading start: ' . $attempt['reading_started_at'],
        'Reading end: ' . $attempt['reading_ended_at'],
        'Reading duration seconds: ' . ($readingDuration === null ? 'unavailable' : number_format($readingDuration, 6, '.', '')),
        'Gloss opens paired with closes: ' . count($pairs),
    ];
    foreach ($pairs as $pair) {
        $lines[] = sprintf(
            '- %s | %s -> %s | %.6f seconds',
            $pair['term'],
            $pair['opened_at'],
            $pair['closed_at'],
            $pair['duration_seconds']
        );
    }
    $lines[] = 'Total glossing seconds: ' . number_format($totalGloss, 6, '.', '');

    return [
        'subject' => 'SafeGloss session report (' . $attempt['id'] . ')',
        'body' => implode("\n", $lines) . "\n",
    ];
}

function queue_session_report(PDO $pdo, int $attemptId): void
{
    $report = build_session_report($pdo, $attemptId);
    $transport = app_config('mail_transport');
    if (!in_array($transport, ['database', 'smtp'], true)) {
        throw new RuntimeException('MAIL_TRANSPORT must be database or smtp.');
    }

    $status = 'captured';
    $error = null;
    $sentAt = null;
    if ($transport === 'smtp') {
        try {
            smtp_send(
                app_config('report_to'),
                app_config('mail_from'),
                $report['subject'],
                $report['body']
            );
            $status = 'sent';
            $sentAt = (new DateTimeImmutable('now', new DateTimeZone('UTC')))
                ->format('Y-m-d H:i:s.u');
        } catch (Throwable $exception) {
            $status = 'failed';
            $error = substr($exception->getMessage(), 0, 500);
        }
    }

    $statement = $pdo->prepare(
        'INSERT INTO mail_outbox
         (recipient, sender, subject, body_text, transport, status, error_message, sent_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
    );
    $statement->execute([
        app_config('report_to'),
        app_config('mail_from'),
        $report['subject'],
        $report['body'],
        $transport,
        $status,
        $error,
        $sentAt,
    ]);
}

function smtp_send(string $recipient, string $sender, string $subject, string $body): void
{
    $host = app_config('smtp_host');
    $port = (int) app_config('smtp_port');
    $encryption = app_config('smtp_encryption');
    if ($host === '' || !in_array($encryption, ['starttls', 'tls'], true)) {
        throw new RuntimeException('SMTP requires a host and verified TLS transport.');
    }

    $remote = ($encryption === 'tls' ? 'tls://' : 'tcp://') . $host . ':' . $port;
    $context = stream_context_create([
        'ssl' => [
            'verify_peer' => true,
            'verify_peer_name' => true,
            'peer_name' => $host,
        ],
    ]);
    $socket = @stream_socket_client($remote, $errorNumber, $errorMessage, 10, STREAM_CLIENT_CONNECT, $context);
    if (!is_resource($socket)) {
        throw new RuntimeException("SMTP connection failed: {$errorMessage} ({$errorNumber})");
    }
    stream_set_timeout($socket, 10);

    $read = static function () use ($socket): string {
        $response = '';
        do {
            $line = fgets($socket, 2048);
            if ($line === false) {
                throw new RuntimeException('SMTP server closed the connection unexpectedly.');
            }
            $response .= $line;
        } while (isset($line[3]) && $line[3] === '-');
        return $response;
    };
    $command = static function (string $line, array $expected) use ($socket, $read): string {
        fwrite($socket, $line . "\r\n");
        $response = $read();
        $code = (int) substr($response, 0, 3);
        if (!in_array($code, $expected, true)) {
            throw new RuntimeException('SMTP command rejected with status ' . $code . '.');
        }
        return $response;
    };

    $greeting = $read();
    if ((int) substr($greeting, 0, 3) !== 220) {
        throw new RuntimeException('SMTP server did not provide a ready greeting.');
    }
    $command('EHLO safegloss.local', [250]);
    if ($encryption === 'starttls') {
        $command('STARTTLS', [220]);
        if (!stream_socket_enable_crypto($socket, true, STREAM_CRYPTO_METHOD_TLS_CLIENT)) {
            throw new RuntimeException('SMTP TLS negotiation failed.');
        }
        $command('EHLO safegloss.local', [250]);
    }

    $username = app_config('smtp_username');
    if ($username !== '') {
        $command('AUTH LOGIN', [334]);
        $command(base64_encode($username), [334]);
        $command(base64_encode(app_config('smtp_password')), [235]);
    }

    $command('MAIL FROM:<' . $sender . '>', [250]);
    $command('RCPT TO:<' . $recipient . '>', [250, 251]);
    $command('DATA', [354]);
    $headers = [
        'From: ' . $sender,
        'To: ' . $recipient,
        'Subject: ' . $subject,
        'Date: ' . gmdate(DATE_RFC2822),
        'Message-ID: <' . bin2hex(random_bytes(12)) . '@safegloss.local>',
        'MIME-Version: 1.0',
        'Content-Type: text/plain; charset=UTF-8',
        'Content-Transfer-Encoding: 8bit',
    ];
    $message = implode("\r\n", $headers) . "\r\n\r\n" . str_replace("\n.", "\n..", str_replace("\r\n", "\n", $body));
    fwrite($socket, str_replace("\n", "\r\n", $message) . "\r\n.\r\n");
    $response = $read();
    if ((int) substr($response, 0, 3) !== 250) {
        throw new RuntimeException('SMTP server did not accept the message.');
    }
    $command('QUIT', [221]);
    fclose($socket);
}
