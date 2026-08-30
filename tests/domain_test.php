<?php

declare(strict_types=1);

require_once '/var/www/safegloss/src/domain.php';

function assert_same(mixed $expected, mixed $actual, string $message): void
{
    if ($expected !== $actual) {
        fwrite(STDERR, sprintf(
            "FAIL: %s\nExpected: %s\nActual:   %s\n",
            $message,
            var_export($expected, true),
            var_export($actual, true)
        ));
        exit(1);
    }
}

assert_same('margin', treatment_mode_for_label('A', 'margin'), 'Chapter 3 profile maps A to margin.');
assert_same('contiguous', treatment_mode_for_label('B', 'margin'), 'Chapter 3 profile maps B to contiguous.');
assert_same('contiguous', treatment_mode_for_label('A', 'contiguous'), 'Table 3 profile maps A to contiguous.');
assert_same('margin', treatment_mode_for_label('B', 'contiguous'), 'Table 3 profile maps B to margin.');

assert_same('A', choose_treatment_label([], 0), 'An empty site can begin with A.');
assert_same('B', choose_treatment_label([], 1), 'An empty site can begin with B.');
assert_same('B', choose_treatment_label(['A']), 'Assignment alternates after A.');
assert_same('A', choose_treatment_label(['A', 'B']), 'Assignment alternates after B.');

$score = score_answers(
    [
        ['id' => 10, 'choices' => [['id' => 100, 'is_correct' => true], ['id' => 101, 'is_correct' => false]]],
        ['id' => 20, 'choices' => [['id' => 200, 'is_correct' => false], ['id' => 201, 'is_correct' => true]]],
    ],
    [10 => 100, 20 => 200]
);
assert_same(1, $score['correct'], 'Scoring counts correct answers.');
assert_same(2, $score['total'], 'Scoring counts all questions.');
assert_same(50.0, $score['percent'], 'Scoring calculates the percentage.');
assert_same(false, $score['details'][1]['is_correct'], 'Scoring records incorrect answers.');

assert_same(
    1.25,
    duration_seconds('2026-01-01 12:00:00.250000', '2026-01-01 12:00:01.500000'),
    'Duration calculations preserve microseconds.'
);
assert_same(
    0.0,
    duration_seconds('2026-01-01 12:00:02.000000', '2026-01-01 12:00:01.000000'),
    'Negative durations are clamped to zero.'
);

$pairs = paired_gloss_durations([
    ['action' => 'gloss_close', 'term_text' => 'orphan', 'server_recorded_at' => '2026-01-01 12:00:00.000000'],
    ['action' => 'gloss_open', 'term_text' => 'near', 'server_recorded_at' => '2026-01-01 12:00:00.250000'],
    ['action' => 'gloss_open', 'term_text' => 'near', 'server_recorded_at' => '2026-01-01 12:00:02.000000'],
    ['action' => 'gloss_close', 'term_text' => 'near', 'server_recorded_at' => '2026-01-01 12:00:01.750000'],
    ['action' => 'gloss_close', 'term_text' => 'near', 'server_recorded_at' => '2026-01-01 12:00:03.000000'],
]);
assert_same(2, count($pairs), 'Gloss events are paired in FIFO order per term.');
assert_same(1.5, $pairs[0]['duration_seconds'], 'First gloss duration is calculated correctly.');
assert_same(1.0, $pairs[1]['duration_seconds'], 'Second gloss duration is calculated correctly.');

fwrite(STDOUT, "Domain tests passed.\n");
