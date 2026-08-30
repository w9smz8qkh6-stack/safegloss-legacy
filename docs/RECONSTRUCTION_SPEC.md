# SafeGloss 2014 reconstruction specification

## Status and source discipline

This document translates the application description in Brendan O. Downey's
2014 dissertation into a reconstruction target. The primary evidence is Chapter
1, pages 4-8; Chapter 3, pages 48-75; Chapter 5, pages 88-94; Figures 1-26; and
the SafeGloss.org orientation appendix, pages 118-124.

The dissertation describes behavior and shows the interface but does not contain
the original source code, complete database schema, every validation rule, or
the XML schemas. This is therefore a documented reconstruction, not a claim that
the original code was recovered.

Terms used below:

- **Documented**: stated or shown in the dissertation.
- **Inferred**: necessary to make documented behavior operate, but not specified
  at implementation level.
- **Safety adaptation**: a present-day control that does not intentionally alter
  the research behavior.

## Purpose

The application is a portable, database-driven research platform for delivering
reading lessons with optional vocabulary annotations, assigning alternate gloss
presentation treatments, and recording comprehension and interaction measures.
It was intended to support replication and modification by other researchers.

The implementation was a commercially hosted LAMP Web application: Linux,
Apache, MySQL, and PHP. It was accessed in a browser rather than installed as a
native application.

## Roles and access

### Student

Documented capabilities:

- Self-register with a supplied username and four-digit site code.
- Choose a password and provide and confirm an email address.
- Record native language and 1-10 self-ratings for information-technology skill
  and glossary/dictionary skill.
- Acknowledge role-specific informed consent.
- View assigned lessons and previously earned scores.
- Complete the fixed lesson sequence and review which responses were correct or
  incorrect without being shown the correct answers.

### Instructor

The dissertation calls this role **instructor**, not teacher. Documented
capabilities:

- View counts for the instructor's lessons, rosters, students, glosses, and
  quizzes.
- Manage stories, glosses, quizzes, lessons, the site, rosters, and gradebook.
- Assign lessons to the site's full roster or a custom subset.
- Author rich-text story, gloss, and quiz content, including multimedia.
- Import and export glossary and lesson content as XML.

### Researcher

Documented capabilities:

- View system-wide counts of lessons, rosters, students, glosses, quizzes, and
  sites.
- Inspect score and system logs.
- Filter log records by site and treatment group.
- Audit session-level data also sent by email after quiz submission.

Researcher account provisioning is not documented. Creating it through a local
setup command is an inferred safety adaptation; it must not be available through
public registration.

## Registration and treatment assignment

Registration stores the form responses and assigned treatment in the user's
database record. Within each site, the first participant is assigned A or B at
random and subsequent registrants alternate from the previous assignment so the
groups remain balanced.

Chapter 5 reports a post-experiment correction intended to balance not only
registrations but completed participants and participants who clicked at least
one gloss. The replica must preserve the study-time algorithm as the historical
default and expose the post-experiment algorithm as an explicitly labeled
alternative for new replications. The assignment algorithm used for a study
must be stored with the study/site record.

### Unresolved A/B label conflict

Chapter 3 says Group A displayed the gloss in the right margin and Group B next
to the clicked word. Table 3 labels Treatment A as contiguous and Treatment B as
non-contiguous. These statements conflict.

The application must therefore store the semantic treatment mode
(`contiguous` or `margin`) independently from any display label (`A` or `B`). A
site configuration may select the label mapping. Exports must include both
fields. The replica must not silently encode either contradictory mapping as a
universal historical fact.

## Content model

### Sites and rosters

- A site represents a participating class or cohort and has a join code.
- Registration with the same site code adds students to that site's roster.
- Instructors can create custom rosters from subsets of the site's students.
- Lessons can be assigned to one or more rosters.

### Stories

- An instructor creates a story by typing or pasting rich HTML text.
- The editor reports a word count and stores attribution text separately.
- Bolded words or phrases become gloss targets.
- In the student view, targets appear blue and open a gloss rather than navigate.

The historical editor was CKEditor with reduced controls plus special-character
and Adobe Flash controls. The replica should retain the rich-text workflow and
visual result. Flash execution is excluded as an unsafe obsolete capability;
historical Flash references may be represented as inert archival metadata.

### Glosses

- A gloss belongs to or is selected for a story.
- Each entry contains a target word or phrase and rich annotation content.
- Entries may have language-specific equivalents/translations.
- Gloss XML import/export was compatible with the Adobe Captivate 6 glossary
  widget.

The exact Captivate XML schema is not reproduced in the dissertation. Support
must remain marked inferred until an original sample or authoritative schema is
located.

### Quizzes

- An instructor creates a multiple-choice quiz.
- Prompts may contain images or other multimedia.
- One response is marked correct.
- Answer options are randomized when presented.
- Quiz scoring is automatic.

### Lessons

- A lesson aggregates a title/introduction, story, glossary, quiz, and roster
  assignments.
- Lessons may be saved without a roster, but the interface warns the instructor.
- Lesson XML import/export supports sharing between instructors.
- The exact lesson XML schema is not documented and must be labeled inferred.

## Student lesson sequence

1. The student chooses a lesson from **My Lessons**.
2. An introduction states the purpose, instructions, or time limits.
3. Continuing loads the reading and records `reading_start`.
4. Clicking a gloss target opens either a near-text or right-margin tooltip,
   based on the student's treatment. Opening and closing are separately timed.
5. Continuing records `reading_end` and opens the comprehension quiz. The
   student cannot return to the passage while taking the quiz.
6. Finishing scores the quiz, records completion, shows the score, and returns
   the student to the home screen.
7. **My Scores** shows the lesson components, completion time, score, and a
   detail view identifying correct and incorrect responses without revealing
   the correct answers.

## Instrumentation

The database log records timestamped lesson-related actions with the user, site,
treatment, action description, and contextual item such as the glossed word.
Documented actions include:

- account creation and login;
- lesson/reading load and reading start;
- gloss open and gloss close;
- reading end;
- quiz completion; and
- lesson administration activity visible to the researcher.

Timestamps were recorded to microsecond precision. The replica must use an
absolute UTC event timestamp with microseconds and must also retain session,
lesson, user, site, semantic treatment, treatment label, and structured event
context. Client-generated interaction times must be accepted only with a
server-received timestamp and validation metadata so exports distinguish the
two clocks.

Derived session measures:

- comprehension score as percentage correct;
- reading duration: `reading_end - reading_start`, in seconds;
- gloss click count;
- each gloss duration: `gloss_close - gloss_open`;
- total glossing time: sum of closed gloss durations, in seconds; and
- technology and glossary self-efficacy ratings from registration.

An integrated mail function composed and transmitted a session report to the
researcher after every quiz submission. The report contained participant/site
details, proficiency ratings, treatment, score, lesson identifiers, reading
timestamps and duration, each gloss open/close/duration, click count, and total
glossing time.

For safety, reconstructed mail must default to a non-delivering capture or log
transport. SMTP delivery is an explicit deployment configuration. A failed mail
delivery must not discard or roll back the database record.

## Interface character

The figures show a compact desktop-oriented interface with:

- a pale blue gradient header and footer;
- a small SafeGloss/"glossary management system" wordmark;
- uppercase horizontal tabs;
- green active tabs and action buttons;
- narrow centered content;
- simple striped tables; and
- modal/lightbox score detail.

The replica should reproduce this character and information architecture. It
may add responsive behavior, keyboard focus, semantic markup, and accessible
labels as safety/accessibility adaptations. The dissertation itself required
W3C accessibility conformance.

## Reproducibility and capacity

The documented target included portability, extensibility, import/export,
professional presentation, W3C accessibility, protection against unauthorized
account/database/script access, and support for approximately 50-60 concurrent
users.

A clean checkout must provide:

- a supported PHP runtime served by Apache;
- MySQL-compatible schema creation and migrations;
- a local non-delivering mail capture path;
- synthetic or clearly licensed demonstration content;
- deterministic setup instructions; and
- automated checks for treatment assignment, access control, event pairing,
  derived measures, answer randomization, and scoring.

## Explicit non-goals

The following features in the current Django repository are not established as
part of the 2014 system:

- AI story, glossary, or quiz generation;
- external book discovery;
- reading-level generators and rule libraries;
- continuous/card/movie mode selection;
- courses and units above lessons;
- standards and learning-objective catalogs;
- background acquisition jobs;
- Google OAuth and product analytics services; and
- PWA/offline behavior.

They belong elsewhere unless a historical source is later found.
