<?php

declare(strict_types=1);

require_once '/var/www/safegloss/src/bootstrap.php';

try {
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        handle_post();
    }
    render_page((string) ($_GET['page'] ?? 'home'));
} catch (Throwable $exception) {
    render_error_page($exception);
}

function handle_post(): never
{
    require_csrf();
    $action = (string) ($_POST['action'] ?? '');

    match ($action) {
        'login' => login_action(),
        'logout' => logout_action(),
        'register' => register_action(),
        'save_story' => save_story_action(),
        'save_glossary' => save_glossary_action(),
        'save_quiz' => save_quiz_action(),
        'save_roster' => save_roster_action(),
        'save_lesson' => save_lesson_action(),
        'start_reading' => start_reading_action(),
        'finish_reading' => finish_reading_action(),
        'submit_quiz' => submit_quiz_action(),
        default => throw new RuntimeException('Unknown form action.'),
    };
}

function render_page(string $page): void
{
    match ($page) {
        'home' => home_page(),
        'login' => login_page(),
        'register' => register_page(),
        'dashboard' => dashboard_page(),
        'my_lessons' => my_lessons_page(),
        'lesson_intro' => lesson_intro_page(),
        'lesson_read' => lesson_read_page(),
        'lesson_quiz' => lesson_quiz_page(),
        'my_scores' => my_scores_page(),
        'stories' => stories_page(),
        'glosses' => glosses_page(),
        'quizzes' => quizzes_page(),
        'rosters' => rosters_page(),
        'lessons_manage' => lessons_manage_page(),
        'gradebook' => gradebook_page(),
        'system_log' => system_log_page(),
        'score_log' => score_log_page(),
        'mail_log' => mail_log_page(),
        default => not_found_page(),
    };
}

function home_page(): void
{
    $user = current_user();
    if ($user !== null) {
        redirect_to('dashboard');
    }
    render_header('Research reading and glossary platform', 'home');
    ?>
    <section class="hero">
        <p class="eyebrow">Living 2014 research application replication</p>
        <p>SafeGloss delivers reading lessons with optional vocabulary annotations while recording the interaction measures needed for glossary research.</p>
        <div class="button-row">
            <a class="button" href="/index.php?page=login">Login</a>
            <a class="button button-secondary" href="/index.php?page=register">Register with a site code</a>
        </div>
    </section>
    <section class="feature-grid" aria-label="Application roles">
        <article><h2>Students</h2><p>Read assigned passages, use optional glosses, complete comprehension assessments, and review scores.</p></article>
        <article><h2>Instructors</h2><p>Build stories, glossaries, quizzes, rosters, and sequenced lessons.</p></article>
        <article><h2>Researchers</h2><p>Audit treatment assignment, timestamped interaction logs, scores, and captured session reports.</p></article>
    </section>
    <?php
    render_footer();
}

function login_page(): void
{
    if (current_user() !== null) {
        redirect_to('dashboard');
    }
    render_header('Login', 'login');
    ?>
    <form method="post" class="form-card narrow-form">
        <?php csrf_field(); ?>
        <input type="hidden" name="action" value="login">
        <label>SafeGloss username
            <input name="username" required autocomplete="username" maxlength="80">
        </label>
        <label>Password
            <input type="password" name="password" required autocomplete="current-password">
        </label>
        <button class="button" type="submit">Login</button>
    </form>
    <?php
    render_footer();
}

function register_page(): void
{
    if (current_user() !== null) {
        redirect_to('dashboard');
    }
    render_header('Registering for an account', 'register');
    ?>
    <p class="lede">Use the four-digit site code supplied by your instructor or researcher.</p>
    <form method="post" class="form-card registration-form">
        <?php csrf_field(); ?>
        <input type="hidden" name="action" value="register">
        <div class="form-grid">
            <label>SafeGloss username <span aria-hidden="true">*</span>
                <input name="username" required minlength="3" maxlength="80" autocomplete="username">
            </label>
            <label>Native language <span aria-hidden="true">*</span>
                <input name="native_language" required maxlength="80">
            </label>
            <label>Password <span aria-hidden="true">*</span>
                <input type="password" name="password" required minlength="12" autocomplete="new-password">
            </label>
            <label>Confirm password <span aria-hidden="true">*</span>
                <input type="password" name="password_confirm" required autocomplete="new-password">
            </label>
            <label>Email address <span aria-hidden="true">*</span>
                <input type="email" name="email" required maxlength="254" autocomplete="email">
            </label>
            <label>Confirm email address <span aria-hidden="true">*</span>
                <input type="email" name="email_confirm" required maxlength="254">
            </label>
        </div>
        <fieldset>
            <legend>How do you rate your skill level with information technology?</legend>
            <div class="rating-row">
                <?php for ($rating = 1; $rating <= 10; $rating++): ?>
                    <label><input type="radio" name="technology_proficiency" value="<?= $rating ?>" required> <?= $rating ?></label>
                <?php endfor; ?>
            </div>
        </fieldset>
        <fieldset>
            <legend>How do you rate your skill level with dictionaries, glosses, or similar language-support tools?</legend>
            <div class="rating-row">
                <?php for ($rating = 1; $rating <= 10; $rating++): ?>
                    <label><input type="radio" name="glossary_proficiency" value="<?= $rating ?>" required> <?= $rating ?></label>
                <?php endfor; ?>
            </div>
        </fieldset>
        <div class="form-grid">
            <label>Role <span aria-hidden="true">*</span>
                <select name="role" required>
                    <option value="student">Student</option>
                    <option value="instructor">Instructor</option>
                </select>
            </label>
            <label>4-digit site code <span aria-hidden="true">*</span>
                <input name="site_code" required inputmode="numeric" pattern="[0-9]{4}" maxlength="4">
            </label>
        </div>
        <label class="checkbox-label">
            <input type="checkbox" name="consent" value="yes" required>
            I have read and understand the applicable study information and consent materials supplied by the researcher.
        </label>
        <button class="button" type="submit">Submit</button>
    </form>
    <?php
    render_footer();
}

function login_action(): never
{
    $username = trim((string) ($_POST['username'] ?? ''));
    $statement = db()->prepare('SELECT * FROM users WHERE username = ? AND is_active = TRUE');
    $statement->execute([$username]);
    $user = $statement->fetch();
    if (!$user || !password_verify((string) ($_POST['password'] ?? ''), $user['password_hash'])) {
        flash('error', 'The username or password was not recognized.');
        redirect_to('login');
    }
    session_regenerate_id(true);
    $_SESSION['user_id'] = (int) $user['id'];
    db()->prepare('UPDATE users SET last_login_at = CURRENT_TIMESTAMP(6) WHERE id = ?')->execute([$user['id']]);
    record_event(db(), $user, 'user_login');
    redirect_to('dashboard');
}

function logout_action(): never
{
    $user = current_user();
    if ($user !== null) {
        record_event(db(), $user, 'user_logout');
    }
    $_SESSION = [];
    if (ini_get('session.use_cookies')) {
        $params = session_get_cookie_params();
        setcookie(session_name(), '', time() - 42000, $params['path'], '', $params['secure'], $params['httponly']);
    }
    session_destroy();
    redirect_to('home');
}

function register_action(): never
{
    $username = trim((string) ($_POST['username'] ?? ''));
    $email = trim((string) ($_POST['email'] ?? ''));
    $password = (string) ($_POST['password'] ?? '');
    $role = (string) ($_POST['role'] ?? '');
    $technology = filter_var($_POST['technology_proficiency'] ?? null, FILTER_VALIDATE_INT);
    $glossary = filter_var($_POST['glossary_proficiency'] ?? null, FILTER_VALIDATE_INT);
    if (!preg_match('/^[A-Za-z0-9_.-]{3,80}$/', $username)) {
        throw new RuntimeException('Username must contain 3-80 letters, numbers, periods, underscores, or hyphens.');
    }
    if (!filter_var($email, FILTER_VALIDATE_EMAIL) || !hash_equals($email, (string) ($_POST['email_confirm'] ?? ''))) {
        throw new RuntimeException('Email addresses must be valid and match.');
    }
    if (strlen($password) < 12 || !hash_equals($password, (string) ($_POST['password_confirm'] ?? ''))) {
        throw new RuntimeException('Passwords must contain at least 12 characters and match.');
    }
    if (!in_array($role, ['student', 'instructor'], true)) {
        throw new RuntimeException('Invalid registration role.');
    }
    if ($technology < 1 || $technology > 10 || $glossary < 1 || $glossary > 10) {
        throw new RuntimeException('Both proficiency responses must be between 1 and 10.');
    }
    if (($_POST['consent'] ?? '') !== 'yes') {
        throw new RuntimeException('Consent acknowledgement is required.');
    }

    $pdo = db();
    $pdo->beginTransaction();
    try {
        $site = find_site_by_join_code($pdo, (string) ($_POST['site_code'] ?? ''), true);
        if ($site === null) {
            throw new RuntimeException('The site code was not recognized.');
        }
        [$label, $mode] = $role === 'student' ? assignment_for_site($pdo, $site) : [null, null];
        $statement = $pdo->prepare(
            'INSERT INTO users
             (site_id, username, email, password_hash, role, native_language,
              technology_proficiency, glossary_proficiency, treatment_label,
              treatment_mode, consented_at)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP(6))'
        );
        $statement->execute([
            $site['id'], $username, $email, password_hash($password, PASSWORD_DEFAULT), $role,
            trim((string) ($_POST['native_language'] ?? '')), $technology, $glossary, $label, $mode,
        ]);
        $userId = (int) $pdo->lastInsertId();
        if ($role === 'student') {
            $roster = $pdo->prepare('SELECT id FROM rosters WHERE site_id = ? AND is_site_roster = TRUE');
            $roster->execute([$site['id']]);
            $rosterId = $roster->fetchColumn();
            if (!$rosterId) {
                $pdo->prepare('INSERT INTO rosters (site_id, name, is_site_roster) VALUES (?, ?, TRUE)')
                    ->execute([$site['id'], $site['name'] . ' site roster']);
                $rosterId = $pdo->lastInsertId();
            }
            $pdo->prepare('INSERT INTO roster_memberships (roster_id, student_id) VALUES (?, ?)')
                ->execute([$rosterId, $userId]);
        }
        $userStatement = $pdo->prepare('SELECT * FROM users WHERE id = ?');
        $userStatement->execute([$userId]);
        record_event($pdo, $userStatement->fetch(), 'account_created', null, null, ['role' => $role]);
        $pdo->commit();
    } catch (Throwable $exception) {
        $pdo->rollBack();
        if ($exception instanceof PDOException && $exception->getCode() === '23000') {
            throw new RuntimeException('That username is already in use.');
        }
        throw $exception;
    }

    flash('success', 'Your account was created. Please log in.');
    redirect_to('login');
}

function dashboard_page(): void
{
    $user = require_user();
    render_header('Home', 'dashboard', $user);
    if ($user['role'] === 'student') {
        $counts = student_counts((int) $user['id']);
        render_count_table(['Lessons' => $counts['lessons'], 'Glossaries' => $counts['glossaries'], 'Quizzes' => $counts['quizzes']]);
    } elseif ($user['role'] === 'instructor') {
        $counts = instructor_counts((int) $user['id'], (int) $user['site_id']);
        render_count_table(['Lessons' => $counts['lessons'], 'Rosters' => $counts['rosters'], 'Students' => $counts['students'], 'Glosses' => $counts['glossaries'], 'Quizzes' => $counts['quizzes']]);
    } else {
        $counts = researcher_counts();
        render_count_table(['Lessons' => $counts['lessons'], 'Rosters' => $counts['rosters'], 'Students' => $counts['students'], 'Glosses' => $counts['glossaries'], 'Quizzes' => $counts['quizzes'], 'Sites' => $counts['sites']]);
    }
    render_footer();
}

function render_count_table(array $counts): void
{
    echo '<table class="count-table"><tbody>';
    foreach ($counts as $label => $count) {
        echo '<tr><th scope="row">' . h($label) . '</th><td>' . h($count) . '</td></tr>';
    }
    echo '</tbody></table>';
}

function student_counts(int $studentId): array
{
    $statement = db()->prepare(
        'SELECT COUNT(DISTINCT l.id) lessons, COUNT(DISTINCT l.glossary_id) glossaries, COUNT(DISTINCT l.quiz_id) quizzes
         FROM lessons l JOIN lesson_rosters lr ON lr.lesson_id = l.id
         JOIN roster_memberships rm ON rm.roster_id = lr.roster_id
         WHERE rm.student_id = ? AND l.is_active = TRUE'
    );
    $statement->execute([$studentId]);
    return $statement->fetch();
}

function instructor_counts(int $instructorId, int $siteId): array
{
    $queries = [
        'lessons' => ['SELECT COUNT(*) FROM lessons WHERE instructor_id = ?', $instructorId],
        'rosters' => ['SELECT COUNT(*) FROM rosters WHERE site_id = ?', $siteId],
        'students' => ["SELECT COUNT(*) FROM users WHERE site_id = ? AND role = 'student'", $siteId],
        'glossaries' => ['SELECT COUNT(*) FROM glossaries WHERE instructor_id = ?', $instructorId],
        'quizzes' => ['SELECT COUNT(*) FROM quizzes WHERE instructor_id = ?', $instructorId],
    ];
    $counts = [];
    foreach ($queries as $name => [$sql, $value]) {
        $statement = db()->prepare($sql);
        $statement->execute([$value]);
        $counts[$name] = (int) $statement->fetchColumn();
    }
    return $counts;
}

function researcher_counts(): array
{
    $tables = ['lessons', 'rosters', 'glossaries', 'quizzes', 'sites'];
    $counts = [];
    foreach ($tables as $table) {
        $counts[$table] = (int) db()->query("SELECT COUNT(*) FROM {$table}")->fetchColumn();
    }
    $counts['students'] = (int) db()->query("SELECT COUNT(*) FROM users WHERE role = 'student'")->fetchColumn();
    return $counts;
}

function stories_page(): void
{
    $user = require_user('instructor');
    $statement = db()->prepare('SELECT * FROM stories WHERE instructor_id = ? ORDER BY created_at DESC');
    $statement->execute([$user['id']]);
    render_header('Stories', 'stories', $user);
    render_manager_table($statement->fetchAll(), ['title' => 'Story', 'updated_at' => 'Last updated']);
    ?>
    <details class="manager-form"><summary>Add story</summary>
        <form method="post" class="form-card">
            <?php csrf_field(); ?><input type="hidden" name="action" value="save_story">
            <label>Story title<input name="title" required maxlength="255"></label>
            <label>Story text <span class="help">Use &lt;strong&gt; around words that should open a gloss.</span>
                <textarea name="body_html" rows="14" required></textarea>
            </label>
            <label>Attribution text<textarea name="attribution_html" rows="3"></textarea></label>
            <button class="button" type="submit">Add story</button>
        </form>
    </details>
    <?php render_footer();
}

function save_story_action(): never
{
    $user = require_user('instructor');
    $title = trim((string) ($_POST['title'] ?? ''));
    if ($title === '') {
        throw new RuntimeException('A story title is required.');
    }
    db()->prepare('INSERT INTO stories (instructor_id, title, body_html, attribution_html) VALUES (?, ?, ?, ?)')
        ->execute([$user['id'], $title, sanitize_rich_html((string) $_POST['body_html']), sanitize_rich_html((string) ($_POST['attribution_html'] ?? ''))]);
    record_event(db(), $user, 'story_created', null, null, ['story_id' => (int) db()->lastInsertId()]);
    flash('success', 'Story added.');
    redirect_to('stories');
}

function glosses_page(): void
{
    $user = require_user('instructor');
    $statement = db()->prepare(
        'SELECT g.*, COUNT(t.id) term_count FROM glossaries g
         LEFT JOIN glossary_terms t ON t.glossary_id = g.id
         WHERE g.instructor_id = ? GROUP BY g.id ORDER BY g.created_at DESC'
    );
    $statement->execute([$user['id']]);
    render_header('Glosses', 'glosses', $user);
    render_manager_table($statement->fetchAll(), ['name' => 'Glossary', 'term_count' => 'Words']);
    ?>
    <details class="manager-form"><summary>Add glossary</summary>
        <form method="post" class="form-card">
            <?php csrf_field(); ?><input type="hidden" name="action" value="save_glossary">
            <label>Glossary name<input name="name" required maxlength="255"></label>
            <label>Words and definitions <span class="help">One per line: word | definition. Definitions may use the safe story markup.</span>
                <textarea name="terms" rows="12" required></textarea>
            </label>
            <button class="button" type="submit">Add glossary</button>
        </form>
    </details>
    <?php render_footer();
}

function save_glossary_action(): never
{
    $user = require_user('instructor');
    $name = trim((string) ($_POST['name'] ?? ''));
    $lines = preg_split('/\R/u', (string) ($_POST['terms'] ?? ''), -1, PREG_SPLIT_NO_EMPTY);
    if ($name === '' || !$lines) {
        throw new RuntimeException('A name and at least one word are required.');
    }
    $pdo = db();
    $pdo->beginTransaction();
    try {
        $pdo->prepare('INSERT INTO glossaries (instructor_id, name) VALUES (?, ?)')->execute([$user['id'], $name]);
        $glossaryId = (int) $pdo->lastInsertId();
        $termStatement = $pdo->prepare('INSERT INTO glossary_terms (glossary_id, term_text, definition_html) VALUES (?, ?, ?)');
        foreach ($lines as $line) {
            $parts = array_map('trim', explode('|', $line, 2));
            if (count($parts) !== 2 || $parts[0] === '' || $parts[1] === '') {
                throw new RuntimeException('Each glossary line must contain "word | definition".');
            }
            $termStatement->execute([$glossaryId, $parts[0], sanitize_rich_html($parts[1])]);
        }
        record_event($pdo, $user, 'glossary_created', null, null, ['glossary_id' => $glossaryId]);
        $pdo->commit();
    } catch (Throwable $exception) {
        $pdo->rollBack();
        throw $exception;
    }
    flash('success', 'Glossary added.');
    redirect_to('glosses');
}

function quizzes_page(): void
{
    $user = require_user('instructor');
    $statement = db()->prepare(
        'SELECT q.*, COUNT(qq.id) question_count FROM quizzes q
         LEFT JOIN quiz_questions qq ON qq.quiz_id = q.id
         WHERE q.instructor_id = ? GROUP BY q.id ORDER BY q.created_at DESC'
    );
    $statement->execute([$user['id']]);
    render_header('Quizzes', 'quizzes', $user);
    render_manager_table($statement->fetchAll(), ['title' => 'Quiz', 'question_count' => 'Questions']);
    ?>
    <details class="manager-form"><summary>Add quiz</summary>
        <form method="post" class="form-card">
            <?php csrf_field(); ?><input type="hidden" name="action" value="save_quiz">
            <label>Quiz title<input name="title" required maxlength="255"></label>
            <label>Instructions<textarea name="instructions_html" rows="3">Choose the correct answer for each question.</textarea></label>
            <label>Questions <span class="help">One per line: prompt | correct answer | wrong answer | wrong answer</span>
                <textarea name="questions" rows="12" required></textarea>
            </label>
            <button class="button" type="submit">Add quiz</button>
        </form>
    </details>
    <?php render_footer();
}

function save_quiz_action(): never
{
    $user = require_user('instructor');
    $title = trim((string) ($_POST['title'] ?? ''));
    $lines = preg_split('/\R/u', (string) ($_POST['questions'] ?? ''), -1, PREG_SPLIT_NO_EMPTY);
    if ($title === '' || !$lines) {
        throw new RuntimeException('A title and at least one question are required.');
    }
    $pdo = db();
    $pdo->beginTransaction();
    try {
        $pdo->prepare('INSERT INTO quizzes (instructor_id, title, instructions_html) VALUES (?, ?, ?)')
            ->execute([$user['id'], $title, sanitize_rich_html((string) ($_POST['instructions_html'] ?? ''))]);
        $quizId = (int) $pdo->lastInsertId();
        $questionStatement = $pdo->prepare('INSERT INTO quiz_questions (quiz_id, prompt_html, position) VALUES (?, ?, ?)');
        $choiceStatement = $pdo->prepare('INSERT INTO quiz_choices (question_id, choice_html, is_correct, position) VALUES (?, ?, ?, ?)');
        foreach (array_values($lines) as $questionPosition => $line) {
            $parts = array_map('trim', explode('|', $line));
            if (count($parts) < 4 || in_array('', $parts, true)) {
                throw new RuntimeException('Each quiz line needs a prompt, one correct answer, and at least two wrong answers.');
            }
            $prompt = array_shift($parts);
            $questionStatement->execute([$quizId, sanitize_rich_html($prompt), $questionPosition + 1]);
            $questionId = (int) $pdo->lastInsertId();
            foreach (array_values($parts) as $choicePosition => $choice) {
                $choiceStatement->execute([
                    $questionId,
                    sanitize_rich_html($choice),
                    $choicePosition === 0 ? 1 : 0,
                    $choicePosition + 1,
                ]);
            }
        }
        record_event($pdo, $user, 'quiz_created', null, null, ['quiz_id' => $quizId]);
        $pdo->commit();
    } catch (Throwable $exception) {
        $pdo->rollBack();
        throw $exception;
    }
    flash('success', 'Quiz added.');
    redirect_to('quizzes');
}

function rosters_page(): void
{
    $user = require_user('instructor');
    $rosters = db()->prepare(
        'SELECT r.*, COUNT(rm.student_id) student_count FROM rosters r
         LEFT JOIN roster_memberships rm ON rm.roster_id = r.id
         WHERE r.site_id = ? GROUP BY r.id ORDER BY r.is_site_roster DESC, r.name'
    );
    $rosters->execute([$user['site_id']]);
    $students = db()->prepare("SELECT id, username FROM users WHERE site_id = ? AND role = 'student' ORDER BY username");
    $students->execute([$user['site_id']]);
    render_header('Roster manager', 'rosters', $user);
    render_manager_table($rosters->fetchAll(), ['name' => 'Roster', 'student_count' => 'Students']);
    ?>
    <details class="manager-form"><summary>Add custom roster</summary>
        <form method="post" class="form-card">
            <?php csrf_field(); ?><input type="hidden" name="action" value="save_roster">
            <label>Roster name<input name="name" required maxlength="200"></label>
            <fieldset><legend>Students</legend><div class="check-list">
                <?php foreach ($students->fetchAll() as $student): ?>
                    <label><input type="checkbox" name="student_ids[]" value="<?= h($student['id']) ?>"> <?= h($student['username']) ?></label>
                <?php endforeach; ?>
            </div></fieldset>
            <button class="button" type="submit">Add roster</button>
        </form>
    </details>
    <?php render_footer();
}

function save_roster_action(): never
{
    $user = require_user('instructor');
    $name = trim((string) ($_POST['name'] ?? ''));
    if ($name === '') {
        throw new RuntimeException('Roster name is required.');
    }
    $studentIds = array_values(array_filter(array_map('intval', (array) ($_POST['student_ids'] ?? []))));
    $pdo = db();
    $pdo->beginTransaction();
    try {
        $pdo->prepare('INSERT INTO rosters (site_id, instructor_id, name) VALUES (?, ?, ?)')
            ->execute([$user['site_id'], $user['id'], $name]);
        $rosterId = (int) $pdo->lastInsertId();
        $membership = $pdo->prepare(
            "INSERT INTO roster_memberships (roster_id, student_id)
             SELECT ?, id FROM users WHERE id = ? AND site_id = ? AND role = 'student'"
        );
        foreach ($studentIds as $studentId) {
            $membership->execute([$rosterId, $studentId, $user['site_id']]);
        }
        record_event($pdo, $user, 'roster_created', null, null, ['roster_id' => $rosterId]);
        $pdo->commit();
    } catch (Throwable $exception) {
        $pdo->rollBack();
        throw $exception;
    }
    flash('success', 'Roster added.');
    redirect_to('rosters');
}

function lessons_manage_page(): void
{
    $user = require_user('instructor');
    $pdo = db();
    $lessons = $pdo->prepare(
        'SELECT l.*, s.title story_title, q.title quiz_title FROM lessons l
         JOIN stories s ON s.id = l.story_id JOIN quizzes q ON q.id = l.quiz_id
         WHERE l.instructor_id = ? ORDER BY l.created_at DESC'
    );
    $lessons->execute([$user['id']]);
    $resources = [];
    foreach (['stories', 'glossaries', 'quizzes'] as $table) {
        $label = $table === 'glossaries' ? 'name' : 'title';
        $statement = $pdo->prepare("SELECT id, {$label} label FROM {$table} WHERE instructor_id = ? ORDER BY {$label}");
        $statement->execute([$user['id']]);
        $resources[$table] = $statement->fetchAll();
    }
    $rosters = $pdo->prepare('SELECT id, name FROM rosters WHERE site_id = ? ORDER BY is_site_roster DESC, name');
    $rosters->execute([$user['site_id']]);
    render_header('Lesson manager', 'lessons_manage', $user);
    render_manager_table($lessons->fetchAll(), ['title' => 'Lesson', 'story_title' => 'Reading', 'quiz_title' => 'Quiz']);
    ?>
    <details class="manager-form"><summary>Add lesson</summary>
        <form method="post" class="form-card">
            <?php csrf_field(); ?><input type="hidden" name="action" value="save_lesson">
            <label>Lesson title<input name="title" required maxlength="255"></label>
            <label>Introduction<textarea name="introduction_html" rows="5" required></textarea></label>
            <div class="form-grid">
                <?php foreach ([
                    'stories' => ['label' => 'Story', 'field' => 'story_id'],
                    'glossaries' => ['label' => 'Glossary', 'field' => 'glossary_id'],
                    'quizzes' => ['label' => 'Quiz', 'field' => 'quiz_id'],
                ] as $key => $resourceType): ?>
                    <label><?= h($resourceType['label']) ?><select name="<?= h($resourceType['field']) ?>" required>
                        <option value="">Choose...</option>
                        <?php foreach ($resources[$key] as $resource): ?><option value="<?= h($resource['id']) ?>"><?= h($resource['label']) ?></option><?php endforeach; ?>
                    </select></label>
                <?php endforeach; ?>
            </div>
            <fieldset><legend>Assign to rosters</legend><div class="check-list">
                <?php foreach ($rosters->fetchAll() as $roster): ?>
                    <label><input type="checkbox" name="roster_ids[]" value="<?= h($roster['id']) ?>"> <?= h($roster['name']) ?></label>
                <?php endforeach; ?>
            </div></fieldset>
            <button class="button" type="submit">Add lesson</button>
        </form>
    </details>
    <?php render_footer();
}

function save_lesson_action(): never
{
    $user = require_user('instructor');
    $title = trim((string) ($_POST['title'] ?? ''));
    $storyId = (int) ($_POST['story_id'] ?? 0);
    $glossaryId = (int) ($_POST['glossary_id'] ?? 0);
    $quizId = (int) ($_POST['quiz_id'] ?? 0);
    if ($title === '' || min($storyId, $glossaryId, $quizId) < 1) {
        throw new RuntimeException('Title, story, glossary, and quiz are required.');
    }
    $pdo = db();
    $owned = $pdo->prepare(
        'SELECT
          (SELECT COUNT(*) FROM stories WHERE id = ? AND instructor_id = ?) +
          (SELECT COUNT(*) FROM glossaries WHERE id = ? AND instructor_id = ?) +
          (SELECT COUNT(*) FROM quizzes WHERE id = ? AND instructor_id = ?)'
    );
    $owned->execute([$storyId, $user['id'], $glossaryId, $user['id'], $quizId, $user['id']]);
    if ((int) $owned->fetchColumn() !== 3) {
        throw new RuntimeException('One or more selected lesson components are unavailable.');
    }
    $rosterIds = array_values(array_filter(array_map('intval', (array) ($_POST['roster_ids'] ?? []))));
    $pdo->beginTransaction();
    try {
        $pdo->prepare(
            'INSERT INTO lessons (instructor_id, site_id, story_id, glossary_id, quiz_id, title, introduction_html)
             VALUES (?, ?, ?, ?, ?, ?, ?)'
        )->execute([$user['id'], $user['site_id'], $storyId, $glossaryId, $quizId, $title, sanitize_rich_html((string) $_POST['introduction_html'])]);
        $lessonId = (int) $pdo->lastInsertId();
        $assign = $pdo->prepare(
            'INSERT INTO lesson_rosters (lesson_id, roster_id)
             SELECT ?, id FROM rosters WHERE id = ? AND site_id = ?'
        );
        foreach ($rosterIds as $rosterId) {
            $assign->execute([$lessonId, $rosterId, $user['site_id']]);
        }
        record_event($pdo, $user, 'lesson_created', null, null, ['lesson_id' => $lessonId]);
        $pdo->commit();
    } catch (Throwable $exception) {
        $pdo->rollBack();
        throw $exception;
    }
    flash('success', $rosterIds ? 'Lesson added.' : 'Lesson saved without a roster assignment.');
    redirect_to('lessons_manage');
}

function render_manager_table(array $rows, array $columns): void
{
    if (!$rows) {
        echo '<p class="empty-state">No items have been added yet.</p>';
        return;
    }
    echo '<div class="table-scroll"><table><thead><tr>';
    foreach ($columns as $label) {
        echo '<th scope="col">' . h($label) . '</th>';
    }
    echo '</tr></thead><tbody>';
    foreach ($rows as $row) {
        echo '<tr>';
        foreach ($columns as $key => $_label) {
            echo '<td>' . h($row[$key] ?? '') . '</td>';
        }
        echo '</tr>';
    }
    echo '</tbody></table></div>';
}

function my_lessons_page(): void
{
    $user = require_user('student');
    $statement = db()->prepare(
        'SELECT DISTINCT l.id, l.title,
           (SELECT status FROM lesson_attempts a WHERE a.lesson_id = l.id AND a.student_id = ? ORDER BY a.id DESC LIMIT 1) latest_status
         FROM lessons l JOIN lesson_rosters lr ON lr.lesson_id = l.id
         JOIN roster_memberships rm ON rm.roster_id = lr.roster_id
         WHERE rm.student_id = ? AND l.is_active = TRUE ORDER BY l.title'
    );
    $statement->execute([$user['id'], $user['id']]);
    render_header('My Lessons', 'my_lessons', $user);
    $lessons = $statement->fetchAll();
    if (!$lessons) {
        echo '<p class="empty-state">No lessons are assigned to you.</p>';
    } else {
        echo '<table><thead><tr><th scope="col">Title</th><th scope="col">Status</th></tr></thead><tbody>';
        foreach ($lessons as $lesson) {
            echo '<tr><td><a href="/index.php?page=lesson_intro&amp;lesson_id=' . h($lesson['id']) . '">' . h($lesson['title']) . '</a></td><td>' . h($lesson['latest_status'] ?? 'not started') . '</td></tr>';
        }
        echo '</tbody></table>';
    }
    render_footer();
}

function authorized_lesson(array $user, int $lessonId): array
{
    $statement = db()->prepare(
        'SELECT DISTINCT l.*, s.body_html, s.attribution_html, q.instructions_html
         FROM lessons l JOIN stories s ON s.id = l.story_id JOIN quizzes q ON q.id = l.quiz_id
         JOIN lesson_rosters lr ON lr.lesson_id = l.id
         JOIN roster_memberships rm ON rm.roster_id = lr.roster_id
         WHERE l.id = ? AND rm.student_id = ? AND l.is_active = TRUE'
    );
    $statement->execute([$lessonId, $user['id']]);
    $lesson = $statement->fetch();
    if (!$lesson) {
        http_response_code(404);
        throw new RuntimeException('Lesson not found.');
    }
    return $lesson;
}

function active_attempt(array $user, int $lessonId, bool $create = false): ?array
{
    $statement = db()->prepare(
        "SELECT * FROM lesson_attempts WHERE lesson_id = ? AND student_id = ? AND status <> 'completed' ORDER BY id DESC LIMIT 1"
    );
    $statement->execute([$lessonId, $user['id']]);
    $attempt = $statement->fetch();
    if ($attempt || !$create) {
        return $attempt ?: null;
    }
    db()->prepare(
        'INSERT INTO lesson_attempts (lesson_id, student_id, treatment_label, treatment_mode)
         VALUES (?, ?, ?, ?)'
    )->execute([$lessonId, $user['id'], $user['treatment_label'], $user['treatment_mode']]);
    $statement->execute([$lessonId, $user['id']]);
    return $statement->fetch() ?: null;
}

function lesson_intro_page(): void
{
    $user = require_user('student');
    $lesson = authorized_lesson($user, (int) ($_GET['lesson_id'] ?? 0));
    $attempt = active_attempt($user, (int) $lesson['id'], true);
    record_event(db(), $user, 'lesson_introduction_viewed', $attempt);
    render_header($lesson['title'], 'my_lessons', $user);
    echo '<section class="lesson-introduction">' . $lesson['introduction_html'] . '</section>';
    ?>
    <form method="post" class="continue-form">
        <?php csrf_field(); ?><input type="hidden" name="action" value="start_reading">
        <input type="hidden" name="attempt_id" value="<?= h($attempt['id']) ?>">
        <button class="button" type="submit">Continue</button>
    </form>
    <?php render_footer();
}

function start_reading_action(): never
{
    $user = require_user('student');
    $attempt = owned_attempt($user, (int) ($_POST['attempt_id'] ?? 0));
    if ($attempt['status'] === 'introduced') {
        db()->prepare("UPDATE lesson_attempts SET status = 'reading', reading_started_at = CURRENT_TIMESTAMP(6) WHERE id = ?")
            ->execute([$attempt['id']]);
        $attempt = owned_attempt($user, (int) $attempt['id']);
        record_event(db(), $user, 'reading_start', $attempt);
    }
    redirect_to('lesson_read', ['attempt_id' => $attempt['id']]);
}

function lesson_read_page(): void
{
    $user = require_user('student');
    $attempt = owned_attempt($user, (int) ($_GET['attempt_id'] ?? 0));
    if ($attempt['status'] !== 'reading') {
        redirect_to($attempt['status'] === 'quiz' ? 'lesson_quiz' : 'my_lessons', ['attempt_id' => $attempt['id']]);
    }
    $lesson = authorized_lesson($user, (int) $attempt['lesson_id']);
    $terms = db()->prepare('SELECT id, term_text, definition_html FROM glossary_terms WHERE glossary_id = ? ORDER BY CHAR_LENGTH(term_text) DESC');
    $terms->execute([$lesson['glossary_id']]);
    render_header($lesson['title'], 'my_lessons', $user);
    ?>
    <div class="reading-layout treatment-<?= h($attempt['treatment_mode']) ?>" data-attempt-id="<?= h($attempt['id']) ?>" data-csrf-token="<?= h(csrf_token()) ?>">
        <article class="reading-passage"><?= render_glossed_story($lesson['body_html'], $terms->fetchAll()) ?>
            <?php if ($lesson['attribution_html']): ?><aside class="attribution"><?= $lesson['attribution_html'] ?></aside><?php endif; ?>
        </article>
        <aside class="gloss-margin" aria-live="polite" aria-label="Glossary definition"><p>Select a blue word to view its definition.</p></aside>
    </div>
    <form method="post" class="continue-form" data-confirm-reading-finished>
        <?php csrf_field(); ?><input type="hidden" name="action" value="finish_reading">
        <input type="hidden" name="attempt_id" value="<?= h($attempt['id']) ?>">
        <button class="button" type="submit">Continue</button>
    </form>
    <?php render_footer();
}

function render_glossed_story(string $html, array $terms): string
{
    $byText = [];
    foreach ($terms as $term) {
        $byText[mb_strtolower(trim($term['term_text']))] = $term;
    }
    $document = new DOMDocument('1.0', 'UTF-8');
    libxml_use_internal_errors(true);
    $document->loadHTML('<div id="story-root">' . $html . '</div>', LIBXML_HTML_NOIMPLIED | LIBXML_HTML_NODEFDTD);
    libxml_clear_errors();
    $root = $document->getElementById('story-root');
    if (!$root instanceof DOMElement) {
        return $html;
    }
    foreach (iterator_to_array($root->getElementsByTagName('strong')) as $strong) {
        $key = mb_strtolower(trim($strong->textContent));
        if (!isset($byText[$key])) {
            continue;
        }
        $term = $byText[$key];
        $button = $document->createElement('button');
        $button->setAttribute('type', 'button');
        $button->setAttribute('class', 'gloss-target');
        $button->setAttribute('data-term', $term['term_text']);
        $button->setAttribute('data-definition', base64_encode($term['definition_html']));
        $button->setAttribute('aria-expanded', 'false');
        $button->appendChild($document->createTextNode($strong->textContent));
        $strong->parentNode?->replaceChild($button, $strong);
    }
    $output = '';
    foreach ($root->childNodes as $child) {
        $output .= $document->saveHTML($child);
    }
    return $output;
}

function finish_reading_action(): never
{
    $user = require_user('student');
    $attempt = owned_attempt($user, (int) ($_POST['attempt_id'] ?? 0));
    if ($attempt['status'] === 'reading') {
        db()->prepare(
            "UPDATE lesson_attempts SET status = 'quiz', reading_ended_at = CURRENT_TIMESTAMP(6), quiz_started_at = CURRENT_TIMESTAMP(6) WHERE id = ?"
        )->execute([$attempt['id']]);
        $attempt = owned_attempt($user, (int) $attempt['id']);
        record_event(db(), $user, 'reading_end', $attempt);
        record_event(db(), $user, 'quiz_start', $attempt);
    }
    redirect_to('lesson_quiz', ['attempt_id' => $attempt['id']]);
}

function quiz_questions(int $quizId): array
{
    $questionsStatement = db()->prepare('SELECT * FROM quiz_questions WHERE quiz_id = ? ORDER BY position');
    $questionsStatement->execute([$quizId]);
    $questions = $questionsStatement->fetchAll();
    $choicesStatement = db()->prepare('SELECT * FROM quiz_choices WHERE question_id = ? ORDER BY position');
    foreach ($questions as &$question) {
        $choicesStatement->execute([$question['id']]);
        $question['choices'] = $choicesStatement->fetchAll();
    }
    unset($question);
    return $questions;
}

function lesson_quiz_page(): void
{
    $user = require_user('student');
    $attempt = owned_attempt($user, (int) ($_GET['attempt_id'] ?? 0));
    if ($attempt['status'] !== 'quiz') {
        redirect_to('my_lessons');
    }
    $lesson = authorized_lesson($user, (int) $attempt['lesson_id']);
    $questions = quiz_questions((int) $lesson['quiz_id']);
    render_header('Quiz', 'my_lessons', $user);
    echo '<section class="quiz-instructions">' . $lesson['instructions_html'] . '</section>';
    ?>
    <form method="post" class="quiz-form">
        <?php csrf_field(); ?><input type="hidden" name="action" value="submit_quiz">
        <input type="hidden" name="attempt_id" value="<?= h($attempt['id']) ?>">
        <?php foreach ($questions as $index => $question): ?>
            <fieldset class="question-card"><legend><?= h($index + 1) ?>. <?= $question['prompt_html'] ?></legend>
                <?php $choices = $question['choices']; shuffle($choices); ?>
                <?php foreach ($choices as $choice): ?>
                    <label><input type="radio" name="answers[<?= h($question['id']) ?>]" value="<?= h($choice['id']) ?>" required> <?= $choice['choice_html'] ?></label>
                <?php endforeach; ?>
            </fieldset>
        <?php endforeach; ?>
        <button class="button" type="submit">Finish</button>
    </form>
    <?php render_footer();
}

function submit_quiz_action(): never
{
    $user = require_user('student');
    $attempt = owned_attempt($user, (int) ($_POST['attempt_id'] ?? 0));
    if ($attempt['status'] !== 'quiz') {
        throw new RuntimeException('This quiz is not available for submission.');
    }
    $lesson = authorized_lesson($user, (int) $attempt['lesson_id']);
    $questions = quiz_questions((int) $lesson['quiz_id']);
    $score = score_answers($questions, (array) ($_POST['answers'] ?? []));
    $pdo = db();
    $pdo->beginTransaction();
    try {
        $pdo->prepare(
            'INSERT INTO quiz_submissions (attempt_id, correct_count, question_count, score_percent) VALUES (?, ?, ?, ?)'
        )->execute([$attempt['id'], $score['correct'], $score['total'], $score['percent']]);
        $submissionId = (int) $pdo->lastInsertId();
        $answerStatement = $pdo->prepare(
            'INSERT INTO quiz_answers (submission_id, question_id, selected_choice_id, is_correct) VALUES (?, ?, ?, ?)'
        );
        foreach ($score['details'] as $detail) {
            $answerStatement->execute([
                $submissionId,
                $detail['question_id'],
                $detail['selected_choice_id'],
                $detail['is_correct'] ? 1 : 0,
            ]);
        }
        $pdo->prepare(
            "UPDATE lesson_attempts SET status = 'completed', quiz_submitted_at = CURRENT_TIMESTAMP(6), score_percent = ? WHERE id = ?"
        )->execute([$score['percent'], $attempt['id']]);
        $attempt = owned_attempt($user, (int) $attempt['id']);
        record_event($pdo, $user, 'quiz_finished', $attempt, null, ['score_percent' => $score['percent']]);
        $pdo->commit();
    } catch (Throwable $exception) {
        $pdo->rollBack();
        throw $exception;
    }
    queue_session_report($pdo, (int) $attempt['id']);
    flash('success', 'Quiz completed. Your score is ' . $score['percent'] . '%.');
    redirect_to('my_scores');
}

function my_scores_page(): void
{
    $user = require_user('student');
    $statement = db()->prepare(
        "SELECT a.id, l.title, a.quiz_submitted_at, a.score_percent
         FROM lesson_attempts a JOIN lessons l ON l.id = a.lesson_id
         WHERE a.student_id = ? AND a.status = 'completed' ORDER BY a.quiz_submitted_at DESC"
    );
    $statement->execute([$user['id']]);
    render_header('My Scores', 'my_scores', $user);
    $scores = $statement->fetchAll();
    if (!$scores) {
        echo '<p class="empty-state">You have not completed a lesson yet.</p>';
    } else {
        echo '<table><thead><tr><th scope="col">Lesson</th><th scope="col">Completed</th><th scope="col">Score</th><th scope="col">Detail</th></tr></thead><tbody>';
        foreach ($scores as $score) {
            echo '<tr><td>' . h($score['title']) . '</td><td>' . h($score['quiz_submitted_at']) . '</td><td>' . h($score['score_percent']) . '%</td><td><a href="/index.php?page=my_scores&amp;attempt_id=' . h($score['id']) . '#score-detail">View</a></td></tr>';
        }
        echo '</tbody></table>';
    }
    $detailId = (int) ($_GET['attempt_id'] ?? 0);
    if ($detailId > 0) {
        $detail = db()->prepare(
            'SELECT qq.position, qq.prompt_html, qa.is_correct FROM quiz_answers qa
             JOIN quiz_submissions qs ON qs.id = qa.submission_id
             JOIN lesson_attempts a ON a.id = qs.attempt_id
             JOIN quiz_questions qq ON qq.id = qa.question_id
             WHERE a.id = ? AND a.student_id = ? ORDER BY qq.position'
        );
        $detail->execute([$detailId, $user['id']]);
        echo '<section id="score-detail" class="score-detail"><h2>Score detail</h2><table><thead><tr><th>Question</th><th>Result</th></tr></thead><tbody>';
        foreach ($detail->fetchAll() as $row) {
            echo '<tr><td>' . h($row['position']) . '. ' . $row['prompt_html'] . '</td><td>' . ((bool) $row['is_correct'] ? 'Correct' : 'Incorrect') . '</td></tr>';
        }
        echo '</tbody></table><p class="help">Correct answers are not displayed.</p></section>';
    }
    render_footer();
}

function gradebook_page(): void
{
    $user = require_user('instructor');
    $statement = db()->prepare(
        "SELECT u.username, l.title, a.quiz_submitted_at, a.score_percent
         FROM lesson_attempts a JOIN users u ON u.id = a.student_id JOIN lessons l ON l.id = a.lesson_id
         WHERE l.instructor_id = ? AND a.status = 'completed' ORDER BY a.quiz_submitted_at DESC"
    );
    $statement->execute([$user['id']]);
    render_header('Gradebook', 'gradebook', $user);
    render_manager_table($statement->fetchAll(), ['username' => 'Student', 'title' => 'Lesson', 'quiz_submitted_at' => 'Completed', 'score_percent' => 'Score %']);
    render_footer();
}

function system_log_page(): void
{
    $user = require_user('researcher');
    $siteId = (int) ($_GET['site_id'] ?? 0);
    $mode = (string) ($_GET['mode'] ?? '');
    $where = [];
    $parameters = [];
    if ($siteId > 0) { $where[] = 'e.site_id = ?'; $parameters[] = $siteId; }
    if (in_array($mode, ['contiguous', 'margin'], true)) { $where[] = 'e.treatment_mode = ?'; $parameters[] = $mode; }
    $sql = 'SELECT e.*, u.username, s.name site_name, l.title lesson_title FROM system_events e
            JOIN users u ON u.id = e.user_id LEFT JOIN sites s ON s.id = e.site_id LEFT JOIN lessons l ON l.id = e.lesson_id';
    if ($where) { $sql .= ' WHERE ' . implode(' AND ', $where); }
    $sql .= ' ORDER BY e.server_recorded_at DESC, e.id DESC LIMIT 500';
    $statement = db()->prepare($sql); $statement->execute($parameters);
    $sites = db()->query('SELECT id, name FROM sites ORDER BY name')->fetchAll();
    render_header('System Log', 'system_log', $user);
    ?>
    <form method="get" class="filter-bar"><input type="hidden" name="page" value="system_log">
        <label>Site<select name="site_id"><option value="">All sites</option><?php foreach ($sites as $site): ?><option value="<?= h($site['id']) ?>"<?= $siteId === (int) $site['id'] ? ' selected' : '' ?>><?= h($site['name']) ?></option><?php endforeach; ?></select></label>
        <label>Treatment<select name="mode"><option value="">All treatments</option><option value="contiguous"<?= $mode === 'contiguous' ? ' selected' : '' ?>>Contiguous (near)</option><option value="margin"<?= $mode === 'margin' ? ' selected' : '' ?>>Non-contiguous (margin)</option></select></label>
        <button class="button" type="submit">Filter</button>
    </form>
    <div class="table-scroll"><table><thead><tr><th>Serial</th><th>Time (UTC)</th><th>User</th><th>Label</th><th>Mode</th><th>Action</th><th>Word</th><th>Reading</th><th>Site</th></tr></thead><tbody>
    <?php foreach ($statement->fetchAll() as $event): ?><tr><td><?= h($event['id']) ?></td><td><?= h($event['server_recorded_at']) ?></td><td><?= h($event['username']) ?></td><td><?= h($event['treatment_label'] ?? 'N/A') ?></td><td><?= h($event['treatment_mode'] ?? 'N/A') ?></td><td><?= h($event['action']) ?></td><td><?= h($event['term_text'] ?? 'N/A') ?></td><td><?= h($event['lesson_title'] ?? 'N/A') ?></td><td><?= h($event['site_name'] ?? 'N/A') ?></td></tr><?php endforeach; ?>
    </tbody></table></div>
    <?php render_footer();
}

function score_log_page(): void
{
    $user = require_user('researcher');
    $statement = db()->query(
        "SELECT a.id, u.username, s.name site_name, a.treatment_label, a.treatment_mode,
                l.title lesson_title, a.reading_started_at, a.reading_ended_at,
                TIMESTAMPDIFF(MICROSECOND, a.reading_started_at, a.reading_ended_at) / 1000000 reading_seconds,
                a.score_percent, a.quiz_submitted_at,
                SUM(e.action = 'gloss_open') gloss_clicks
         FROM lesson_attempts a JOIN users u ON u.id = a.student_id JOIN sites s ON s.id = u.site_id
         JOIN lessons l ON l.id = a.lesson_id LEFT JOIN system_events e ON e.attempt_id = a.id
         WHERE a.status = 'completed' GROUP BY a.id ORDER BY a.quiz_submitted_at DESC LIMIT 500"
    );
    render_header('Score Log', 'score_log', $user);
    render_manager_table($statement->fetchAll(), [
        'id' => 'Session', 'username' => 'Participant', 'site_name' => 'Site', 'treatment_label' => 'Label',
        'treatment_mode' => 'Mode', 'lesson_title' => 'Lesson', 'reading_seconds' => 'Read seconds',
        'gloss_clicks' => 'Gloss clicks', 'score_percent' => 'Score %',
    ]);
    render_footer();
}

function mail_log_page(): void
{
    $user = require_user('researcher');
    $statement = db()->query('SELECT id, created_at, recipient, subject, transport, status, error_message FROM mail_outbox ORDER BY id DESC LIMIT 500');
    render_header('Mail Log', 'mail_log', $user);
    render_manager_table($statement->fetchAll(), ['id' => 'Report', 'created_at' => 'Created', 'recipient' => 'Recipient', 'subject' => 'Subject', 'transport' => 'Transport', 'status' => 'Status', 'error_message' => 'Error']);
    render_footer();
}

function not_found_page(): void
{
    http_response_code(404);
    render_header('Page not found', 'none', current_user());
    echo '<p>The requested page does not exist.</p>';
    render_footer();
}
