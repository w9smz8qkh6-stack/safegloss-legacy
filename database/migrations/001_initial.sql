SET NAMES utf8mb4;
SET time_zone = '+00:00';

CREATE TABLE sites (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    join_code_digest CHAR(64) NOT NULL UNIQUE,
    assignment_strategy ENUM('historical_alternating', 'post_experiment_balanced')
        NOT NULL DEFAULT 'historical_alternating',
    label_a_mode ENUM('contiguous', 'margin') NOT NULL DEFAULT 'margin',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB;

CREATE TABLE users (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    site_id BIGINT UNSIGNED NULL,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(254) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('student', 'instructor', 'researcher') NOT NULL,
    native_language VARCHAR(80) NULL,
    technology_proficiency TINYINT UNSIGNED NULL,
    glossary_proficiency TINYINT UNSIGNED NULL,
    treatment_label ENUM('A', 'B') NULL,
    treatment_mode ENUM('contiguous', 'margin') NULL,
    consented_at DATETIME(6) NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    last_login_at DATETIME(6) NULL,
    CONSTRAINT fk_users_site FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE SET NULL,
    CONSTRAINT chk_technology_proficiency CHECK (technology_proficiency BETWEEN 1 AND 10),
    CONSTRAINT chk_glossary_proficiency CHECK (glossary_proficiency BETWEEN 1 AND 10),
    INDEX idx_users_site_role (site_id, role),
    INDEX idx_users_email (email)
) ENGINE=InnoDB;

CREATE TABLE rosters (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    site_id BIGINT UNSIGNED NOT NULL,
    instructor_id BIGINT UNSIGNED NULL,
    name VARCHAR(200) NOT NULL,
    is_site_roster BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_rosters_site FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE,
    CONSTRAINT fk_rosters_instructor FOREIGN KEY (instructor_id) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE KEY uq_site_roster_name (site_id, name)
) ENGINE=InnoDB;

CREATE TABLE roster_memberships (
    roster_id BIGINT UNSIGNED NOT NULL,
    student_id BIGINT UNSIGNED NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (roster_id, student_id),
    CONSTRAINT fk_membership_roster FOREIGN KEY (roster_id) REFERENCES rosters(id) ON DELETE CASCADE,
    CONSTRAINT fk_membership_student FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE stories (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    instructor_id BIGINT UNSIGNED NOT NULL,
    title VARCHAR(255) NOT NULL,
    body_html MEDIUMTEXT NOT NULL,
    attribution_html TEXT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_stories_instructor FOREIGN KEY (instructor_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_stories_instructor (instructor_id)
) ENGINE=InnoDB;

CREATE TABLE glossaries (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    instructor_id BIGINT UNSIGNED NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_glossaries_instructor FOREIGN KEY (instructor_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE glossary_terms (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    glossary_id BIGINT UNSIGNED NOT NULL,
    term_text VARCHAR(255) NOT NULL,
    definition_html TEXT NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_terms_glossary FOREIGN KEY (glossary_id) REFERENCES glossaries(id) ON DELETE CASCADE,
    UNIQUE KEY uq_glossary_term (glossary_id, term_text)
) ENGINE=InnoDB;

CREATE TABLE glossary_equivalents (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    term_id BIGINT UNSIGNED NOT NULL,
    language_code VARCHAR(16) NOT NULL,
    equivalent_text VARCHAR(255) NOT NULL,
    CONSTRAINT fk_equivalents_term FOREIGN KEY (term_id) REFERENCES glossary_terms(id) ON DELETE CASCADE,
    UNIQUE KEY uq_term_language (term_id, language_code)
) ENGINE=InnoDB;

CREATE TABLE story_gloss_targets (
    story_id BIGINT UNSIGNED NOT NULL,
    term_id BIGINT UNSIGNED NOT NULL,
    target_text VARCHAR(255) NOT NULL,
    PRIMARY KEY (story_id, term_id, target_text),
    CONSTRAINT fk_targets_story FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE,
    CONSTRAINT fk_targets_term FOREIGN KEY (term_id) REFERENCES glossary_terms(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE quizzes (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    instructor_id BIGINT UNSIGNED NOT NULL,
    title VARCHAR(255) NOT NULL,
    instructions_html TEXT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_quizzes_instructor FOREIGN KEY (instructor_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE quiz_questions (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    quiz_id BIGINT UNSIGNED NOT NULL,
    prompt_html TEXT NOT NULL,
    position SMALLINT UNSIGNED NOT NULL,
    CONSTRAINT fk_questions_quiz FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE,
    UNIQUE KEY uq_quiz_position (quiz_id, position)
) ENGINE=InnoDB;

CREATE TABLE quiz_choices (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    question_id BIGINT UNSIGNED NOT NULL,
    choice_html TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL DEFAULT FALSE,
    position SMALLINT UNSIGNED NOT NULL,
    CONSTRAINT fk_choices_question FOREIGN KEY (question_id) REFERENCES quiz_questions(id) ON DELETE CASCADE,
    UNIQUE KEY uq_question_position (question_id, position)
) ENGINE=InnoDB;

CREATE TABLE lessons (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    instructor_id BIGINT UNSIGNED NOT NULL,
    site_id BIGINT UNSIGNED NOT NULL,
    story_id BIGINT UNSIGNED NOT NULL,
    glossary_id BIGINT UNSIGNED NOT NULL,
    quiz_id BIGINT UNSIGNED NOT NULL,
    title VARCHAR(255) NOT NULL,
    introduction_html TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_lessons_instructor FOREIGN KEY (instructor_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_lessons_site FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE,
    CONSTRAINT fk_lessons_story FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE RESTRICT,
    CONSTRAINT fk_lessons_glossary FOREIGN KEY (glossary_id) REFERENCES glossaries(id) ON DELETE RESTRICT,
    CONSTRAINT fk_lessons_quiz FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE lesson_rosters (
    lesson_id BIGINT UNSIGNED NOT NULL,
    roster_id BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (lesson_id, roster_id),
    CONSTRAINT fk_lesson_rosters_lesson FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE,
    CONSTRAINT fk_lesson_rosters_roster FOREIGN KEY (roster_id) REFERENCES rosters(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE lesson_attempts (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    lesson_id BIGINT UNSIGNED NOT NULL,
    student_id BIGINT UNSIGNED NOT NULL,
    treatment_label ENUM('A', 'B') NOT NULL,
    treatment_mode ENUM('contiguous', 'margin') NOT NULL,
    status ENUM('introduced', 'reading', 'quiz', 'completed') NOT NULL DEFAULT 'introduced',
    reading_started_at DATETIME(6) NULL,
    reading_ended_at DATETIME(6) NULL,
    quiz_started_at DATETIME(6) NULL,
    quiz_submitted_at DATETIME(6) NULL,
    score_percent DECIMAL(6,3) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_attempts_lesson FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE,
    CONSTRAINT fk_attempts_student FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_attempts_student_lesson (student_id, lesson_id),
    INDEX idx_attempts_status (status)
) ENGINE=InnoDB;

CREATE TABLE system_events (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    attempt_id BIGINT UNSIGNED NULL,
    user_id BIGINT UNSIGNED NOT NULL,
    site_id BIGINT UNSIGNED NULL,
    lesson_id BIGINT UNSIGNED NULL,
    treatment_label ENUM('A', 'B') NULL,
    treatment_mode ENUM('contiguous', 'margin') NULL,
    action VARCHAR(80) NOT NULL,
    term_text VARCHAR(255) NULL,
    client_event_id CHAR(36) NULL,
    client_recorded_at DATETIME(6) NULL,
    server_recorded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    context_json JSON NOT NULL,
    CONSTRAINT fk_events_attempt FOREIGN KEY (attempt_id) REFERENCES lesson_attempts(id) ON DELETE SET NULL,
    CONSTRAINT fk_events_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_events_site FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE SET NULL,
    CONSTRAINT fk_events_lesson FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE SET NULL,
    UNIQUE KEY uq_client_event (attempt_id, client_event_id),
    INDEX idx_events_filter (site_id, treatment_mode, server_recorded_at),
    INDEX idx_events_attempt_action (attempt_id, action, server_recorded_at)
) ENGINE=InnoDB;

CREATE TABLE quiz_submissions (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    attempt_id BIGINT UNSIGNED NOT NULL UNIQUE,
    correct_count SMALLINT UNSIGNED NOT NULL,
    question_count SMALLINT UNSIGNED NOT NULL,
    score_percent DECIMAL(6,3) NOT NULL,
    submitted_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_submissions_attempt FOREIGN KEY (attempt_id) REFERENCES lesson_attempts(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE quiz_answers (
    submission_id BIGINT UNSIGNED NOT NULL,
    question_id BIGINT UNSIGNED NOT NULL,
    selected_choice_id BIGINT UNSIGNED NULL,
    is_correct BOOLEAN NOT NULL,
    PRIMARY KEY (submission_id, question_id),
    CONSTRAINT fk_answers_submission FOREIGN KEY (submission_id) REFERENCES quiz_submissions(id) ON DELETE CASCADE,
    CONSTRAINT fk_answers_question FOREIGN KEY (question_id) REFERENCES quiz_questions(id) ON DELETE CASCADE,
    CONSTRAINT fk_answers_choice FOREIGN KEY (selected_choice_id) REFERENCES quiz_choices(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE mail_outbox (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    recipient VARCHAR(254) NOT NULL,
    sender VARCHAR(254) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    body_text MEDIUMTEXT NOT NULL,
    transport ENUM('database', 'smtp') NOT NULL,
    status ENUM('captured', 'sent', 'failed') NOT NULL,
    error_message VARCHAR(500) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    sent_at DATETIME(6) NULL,
    INDEX idx_outbox_status (status, created_at)
) ENGINE=InnoDB;
