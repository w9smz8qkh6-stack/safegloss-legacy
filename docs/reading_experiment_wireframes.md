# Reading Experiment Platform – UI Wireframes (Text)

Below are ASCII-style wireframes for key screens in the Reading Experiment Platform.

---

## 1. Student – “My Lessons” (desktop)

+--------------------------------------------------------------------------------+
| [Logo]  Reading Experiments                             User ▾ | Logout        |
+--------------------------------------------------------------------------------+
|                                                                                |
|  My Lessons                                                                    |
|  --------------------------------------------------------------------------    |
|  [Filter: All ▾]  [Status: In progress ▾]          [ Search box         ]      |
|                                                                                |
|  ┌──────────────────────────────────────────────────────────────────────┐      |
|  | Lesson Card                                                          |      |
|  |----------------------------------------------------------------------|      |
|  | [Title]  “The Journey North”                                         |      |
|  | [Subtitle] Site: ISA – Grade 7                                      |
|  | [Meta] Reading level: B1   •   Modes: Text, Cards, Movie            |
|  | [Progress bar: ████████░░░  60%]     Status: In Progress             |
|  | [Button: Resume]       [Icon: Results] [Icon: Details]              |
|  └──────────────────────────────────────────────────────────────────────┘      |
|                                                                                |
|  ┌──────────────────────────────────────────────────────────────────────┐      |
|  | Lesson Card                                                          |      |
|  |----------------------------------------------------------------------|      |
|  | [Title]  “Volcanoes and Plate Tectonics”                             |      |
|  | [Meta] Reading level: Grade 6–7 • Modes: Text, Cards                 |
|  | [Progress bar: ░░░░░░░░░░  0%]   Status: Not started                 |
|  | [Button: Start]                                                      |
|  └──────────────────────────────────────────────────────────────────────┘      |
|                                                                                |
+--------------------------------------------------------------------------------+
|  © 2025 Reading Experiment Platform                                            |
+--------------------------------------------------------------------------------+


---

## 2. Student – Lesson Reader (header + mode switcher)

+--------------------------------------------------------------------------------+
| [Logo]  Reading Experiments                             Bren ▾ | Logout        |
+--------------------------------------------------------------------------------+
| [Breadcrumb: My Lessons > The Journey North]                                   |
|                                                                                |
|  ┌──────────────────────────────────────────────────────────────────────────┐  |
|  | [Lesson Title] The Journey North                                        |  |
|  | [Sub] Reading level: B1 • Approx. time: 10 minutes                      |  |
|  |                                                                          |  |
|  |  Modes: [ Text ]  [ Cards ]  [ Movie ]                                  |  |
|  |         (Text active, others outlined)                                  |  |
|  └──────────────────────────────────────────────────────────────────────────┘  |
|                                                                                |
|  ┌──────────────────────────────────────────────────────────────────────────┐  |
|  |                                                                          |  |
|  |  [ Reader Container - mode-specific content injected here asynchronously ] |
|  |                                                                          |  |
|  |  (Content for continuous text mode, see next frame)                      |  |
|  |                                                                          |  |
|  └──────────────────────────────────────────────────────────────────────────┘  |
|                                                                                |
|  [Button: Go to Quiz]                            [Timer / Progress optional]   |
+--------------------------------------------------------------------------------+


---

## 3. Student – Reader: Continuous Text Mode

Inside Reader Container:

┌──────────────────────────────────────────────────────────────────────────────┐
| [Toolbar Row]                                                                |
|   [A-] [A+]    [Theme: Light ▾]    [Info: i]                                 |
|-------------------------------------------------------------------------------|
|                                                                              |
|  [Scrollable text column – centered, max-width ~700px]                       |
|                                                                              |
|   In the far north, the sky glowed with bands of green and purple.          |
|   As Lina stepped out of the cabin, the air felt sharper, the snow          |
|   beneath her boots squeaking with each step.                               |
|                                                                              |
|   “We have to hurry,” said her uncle. “The [   aurora   ] danced longer     |
|    than usual tonight.”                                                     |
|                                                                              |
|   ...                                                                       |
|                                                                              |
|   (Gloss terms are underlined spans like [aurora] with data-term-id attrs.) |
|                                                                              |
└──────────────────────────────────────────────────────────────────────────────┘

Gloss Tooltip / Bottom Sheet pops on click (mobile as sheet):

┌────────── Gloss Detail (bottom sheet) ──────────────────────┐
| aurora                                                      |
|-------------------------------------------------------------|
| Definition:                                                 |
|   A natural light display in the Earth's sky, mostly seen   |
|   in high-latitude regions.                                |
| Translation: cực quang (vi)                                |
| [Close]                                                     |
└─────────────────────────────────────────────────────────────┘


---

## 4. Student – Reader: Card Mode (segment slideshow)

Inside Reader Container:

┌──────────────────────────────────────────────────────────────────────────────┐
| [Top Bar] Card 3 of 12                               25% [Progress Bar ▓░]  |
|-------------------------------------------------------------------------------|
|                                                                              |
|  ┌──────────────────────────────────────────────────────────────────────┐    |
|  | [Segment Title] Scene 3 – The Cabin                                  |    |
|  |----------------------------------------------------------------------|    |
|  | [Optional Image thumbnail – full-width banner or aspect ratio 16:9]  |    |
|  |  ┌───────────────────────────────────────────────────────────────┐   |    |
|  |  |                                                               |   |    |
|  |  |                      [ Cabin in Snow Image ]                  |   |    |
|  |  |                                                               |   |    |
|  |  └───────────────────────────────────────────────────────────────┘   |    |
|  |                                                                      |    |
|  |  Text of this segment only:                                          |    |
|  |                                                                      |    |
|  |  Lina pushed the door open slowly. The cabin was warmer than she     |    |
|  |  expected, the woodstove crackling softly. A map of the region       |    |
|  |  hung on the wall, with a small [   compass   ] pinned next to it.   |    |
|  |                                                                      |    |
|  └──────────────────────────────────────────────────────────────────────┘    |
|                                                                              |
|  [◀ Previous]                     [Play Slideshow ▷]              [Next ▶]   |
└──────────────────────────────────────────────────────────────────────────────┘


---

## 5. Student – Reader: Movie Mode

Inside Reader Container:

┌──────────────────────────────────────────────────────────────────────────────┐
|  [Movie Mode Toolbar]                                                       |
|   Scene 3 of 12   •   “The Cabin”                                          |
|-------------------------------------------------------------------------------|
|  ┌───────────────────────────────────────┬────────────────────────────────┐ |
|  |                                       |                                | |
|  |   [Visual Panel]                      |  [Text Panel]                  | |
|  |   ┌───────────────────────────────┐   |                                | |
|  |   |                               |   |  Lina pushed the door open    | |
|  |   |      [ Image / Video ]       |   |  slowly. The cabin was warmer  | |
|  |   |                               |   |  than she expected, the        | |
|  |   └───────────────────────────────┘   |  woodstove crackling softly.   | |
|  |                                       |  A map of the region hung on   | |
|  |   [If audio narration:              ] |  the wall, with a small        | |
|  |   [Audio scrubber (if separate)    ] |  [ compass ] pinned next to it.| |
|  |                                       |                                | |
|  └───────────────────────────────────────┴────────────────────────────────┘ |
|                                                                              |
|  [◀ Prev Scene]  [⏯ Play/Pause]  [Next Scene ▶]                              |
|                                                                              |
|  [Timeline: ────────●────────────]    0:15 / 2:40                            |
└──────────────────────────────────────────────────────────────────────────────┘

Mobile variant:

┌──────────────────────────────────────────────────────────────┐
| Scene 3 / 12 – The Cabin                                     |
|--------------------------------------------------------------|
| [Visual Panel – full width video/image]                      |
| [Text Panel – below, scrollable if needed]                   |
| [Controls row: ◀  ⏯  ▶ ]    [Progress bar]  [00:15 / 02:40]  |
└──────────────────────────────────────────────────────────────┘


---

## 6. Student – Quiz View

+--------------------------------------------------------------------------------+
| [Logo] Reading Experiments                             Bren ▾ | Logout         |
+--------------------------------------------------------------------------------+
| [Breadcrumb: My Lessons > The Journey North > Quiz]                          |
|                                                                                |
|  ┌──────────────────────────────────────────────────────────────────────────┐  |
|  |  Quiz: The Journey North – Comprehension Check                          |  |
|  |  Questions: 10   •   Time limit: 15 minutes   [Time left: 14:23]        |  |
|  └──────────────────────────────────────────────────────────────────────────┘  |
|                                                                                |
|  ┌──────────────────────────────────────────────────────────────────────────┐  |
|  |  Q3 of 10                                                                |  |
|  |-------------------------------------------------------------------------|  |
|  |  Why does Lina need to hurry at the beginning of the story?            |  |
|  |                                                                         |  |
|  |  ( ) Because the aurora is fading and they must travel while it lasts  |  |
|  |  ( ) Because the sun is setting and it will be too dark to see         |  |
|  |  ( ) Because the cabin is too cold to stay inside                      |  |
|  |  ( ) Because her uncle is late for an important meeting                |  |
|  |                                                                         |  |
|  |  [Previous]                                [Save & Next]               |  |
|  └──────────────────────────────────────────────────────────────────────────┘  |
|                                                                                |
|  [Button: Submit Quiz]                                                        |
+--------------------------------------------------------------------------------+


---

## 7. Instructor – Dashboard

+--------------------------------------------------------------------------------+
| [Logo] Reading Experiments                              Instructor: Bren ▾    |
+--------------------------------------------------------------------------------+
|  [Nav]  Stories  |  Glossaries  |  Lessons  |  Quizzes  |  Experiments       |
+--------------------------------------------------------------------------------+
|                                                                                |
|  ┌───────────────────────────────────────────────┐  ┌──────────────────────┐  |
|  | Stories                                      |  | Quick Actions        |  |
|  |----------------------------------------------|  |----------------------|  |
|  | Total: 12  •  Recently edited                |  | [+] New Story        |  |
|  |                                              |  | [+] New Lesson       |  |
|  | - The Journey North                  [Edit]  |  | [+] New Quiz         |  |
|  | - Volcanoes & Plate Tectonics        [Edit]  |  | [+] New Experiment   |  |
|  | - ...                                      |  |                      |  |
|  └───────────────────────────────────────────────┘  └──────────────────────┘  |
|                                                                                |
|  ┌───────────────────────────────────────────────┐  ┌──────────────────────┐  |
|  | Upcoming Lessons                             |  | Experiments (status) |  |
|  |----------------------------------------------|  |----------------------|  |
|  | - “The Journey North”  • Grade 7 • Active    |  | tooltip_placement_v1 |
|  | - “Volcanoes…”        • Grade 6 • Draft     |  |   Running (A/B/C)    |  |
|  └───────────────────────────────────────────────┘  └──────────────────────┘  |
|                                                                                |
+--------------------------------------------------------------------------------+


---

## 8. Instructor – Story Editor (Segments & Media)

+--------------------------------------------------------------------------------+
| [Story: The Journey North]                        [Save] [Preview] [More ▾]   |
+--------------------------------------------------------------------------------+
| Tabs: [ Details ]  [ Content ]  [ Segments & Media ]  [ Glossary ]  [ AI Tools]|
+--------------------------------------------------------------------------------+

[Segments & Media Tab]

┌──────────────────────────────────────────────────────────────────────────────┐
|  Auto-Segmentation: [By paragraph ▾]  [Run]    [Add Segment]                 |
|-------------------------------------------------------------------------------|
|  Segment List (sortable, accordion style):                                   |
|                                                                              |
|  ┌──────────────────────────────────────────────────────────────────────┐    |
|  | [Drag ▤]  #1  Scene: The Sky                                       ▾ |    |
|  |----------------------------------------------------------------------|    |
|  | Text preview: "In the far north, the sky glowed with bands..."      |    |
|  | Media:  [Image: sky_north.jpg] [Audio: none] [Video: none]          |    |
|  | [Edit Text] [Edit Media]                                            |    |
|  └──────────────────────────────────────────────────────────────────────┘    |
|                                                                              |
|  ┌──────────────────────────────────────────────────────────────────────┐    |
|  | [Drag ▤]  #2  Scene: The Cabin                                      ▾ |    |
|  |----------------------------------------------------------------------|    |
|  | Text preview: "Lina pushed the door open slowly..."                  |    |
|  | Media:  [Image: cabin.png] [Audio: cabin_narration.mp3]             |    |
|  | [Edit Text] [Edit Media]                                            |    |
|  └──────────────────────────────────────────────────────────────────────┘    |
|                                                                              |
└──────────────────────────────────────────────────────────────────────────────┘


Edit Media modal:

┌────────────────── Edit Media for Segment #2 – The Cabin ─────────────────┐
| [Image]                                                                   |
|   Current: cabin.png   [Change] [Remove]                                  |
|   Alt text: [__________________________________]                          |
|                                                                           |
| [Audio Narration]                                                         |
|   Current: cabin_narration.mp3   [Change] [Remove]                        |
|   [Generate Audio from Text]                                             |
|                                                                           |
| [Video Clip]                                                              |
|   None  [Upload] / [Embed URL]                                           |
|                                                                           |
| [Save] [Cancel]                                                           |
└───────────────────────────────────────────────────────────────────────────┘


---

## 9. Instructor – Glossary Suggestions

+--------------------------------------------------------------------------------+
| [Story: The Journey North]                                         [Back]     |
+--------------------------------------------------------------------------------+
| Tabs: Details | Content | Segments & Media | [Glossary] | AI Tools             |
+--------------------------------------------------------------------------------+

Story Summary:  Words: 820  •  Level: B1   •  Native Lang: Vietnamese (vi)

┌──────────────────────────────────────────────────────────────────────────────┐
|  Active Terms                                                               |
|-------------------------------------------------------------------------------|
|  Term          | Translation  | Difficulty | Gloss Type     | Actions        |
|-------------------------------------------------------------------------------|
| aurora         | cực quang    | ★★★★☆      | definition     | [Edit] [X]     |
| compass        | la bàn       | ★★☆☆☆      | translation    | [Edit] [X]     |
| ...                                                                             |
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
|  AI Suggestions   [Generate more ▷]                                          |
|-------------------------------------------------------------------------------|
|  ┌──────────────────────────────────────────────────────────────────────┐    |
|  | Term: expedition           Difficulty: ★★★★☆                         |    |
|  | Reason: Advanced academic word; key to understanding the journey.   |    |
|  | Definition: A journey undertaken by a group of people ...           |    |
|  | Translation (vi): chuyến thám hiểm                                  |    |
|  | [Accept] [Reject] [Edit]                                            |    |
|  └──────────────────────────────────────────────────────────────────────┘    |
|                                                                              |
|  ┌──────────────────────────────────────────────────────────────────────┐    |
|  | Term: crackling             Difficulty: ★★☆☆☆                         |    |
|  | ...                                                              |    |
|  | [Accept] [Reject] [Edit]                                            |    |
|  └──────────────────────────────────────────────────────────────────────┘    |
└──────────────────────────────────────────────────────────────────────────────┘


---

## 10. Instructor – Lesson Builder Wizard

Step 1:

+--------------------------------------------------------------------------------+
| Create Lesson                                                                  |
+--------------------------------------------------------------------------------+
| Step 1 of 5: Basic Info                                                        |
|-------------------------------------------------------------------------------|
| [Title]       [______________________________________________]               |
| [Site]        [ ISA – Grade 7 ▾ ]                                             |
| [Intro text]  [ WYSIWYG editor...                                     ]       |
|                                                                               |
| [Next ▷]                                                  [Cancel]           |
+--------------------------------------------------------------------------------+


Step 2: Select Story

┌──────────────────────────────────────────────────────────────────────────────┐
| Step 2 of 5: Select Story                                                   |
|-------------------------------------------------------------------------------|
| [Search stories...]                                                         |
|                                                                              |
| ( ) The Journey North          [Level: B1]  [Owner: Bren]                   |
| ( ) Volcanoes & Plate Tectonics [Level: Grade 6–7]                          |
| ( ) ...                                                                    |
|                                                                              |
| [◁ Back]                          [Next ▷]                                   |
└──────────────────────────────────────────────────────────────────────────────┘


Step 4: Reading Modes & Experiment

┌──────────────────────────────────────────────────────────────────────────────┐
| Step 4 of 5: Reading Modes & Experiment                                     |
|-------------------------------------------------------------------------------|
| [x] Continuous text mode                                                     |
| [x] Card slideshow mode                                                      |
| [x] Movie mode                                                               |
|                                                                              |
| Default mode: [ Movie ▾ ]                                                   |
| [ ] Lock mode (students cannot switch)                                      |
|                                                                              |
| Experiment:                                                                  |
|   [ tooltip_placement_v1 ▾ ]   Status: Running                               |
|                                                                              |
| [◁ Back]                          [Next ▷]                                   |
└──────────────────────────────────────────────────────────────────────────────┘


---

## 11. Researcher – Experiment Dashboard

+--------------------------------------------------------------------------------+
| Experiments                                                                   |
+--------------------------------------------------------------------------------+
| [ + New Experiment ]   [ Filter by Status ▾ ] [ Search experiments ... ]      |
+--------------------------------------------------------------------------------+
|  ┌─────────────────────────────────────────────────────────────────────────┐   |
|  | tooltip_placement_v1                                                  |   |
|  |------------------------------------------------------------------------|   |
|  | Status: Running   •  Variants: 3 (A,B,C)                               |   |
|  | Parameters (A): default_mode=text, tooltip_position=inline_bubble      |   |
|  | [View Analytics] [Edit Variants] [Pause]                               |   |
|  └─────────────────────────────────────────────────────────────────────────┘   |
|                                                                              |
|  ┌─────────────────────────────────────────────────────────────────────────┐   |
|  | reading_mode_comparison_v1                                             |   |
|  |------------------------------------------------------------------------|   |
|  | Status: Draft   •  Variants: 2                                         |   |
|  | [View Analytics] [Edit Variants] [Start]                               |   |
|  └─────────────────────────────────────────────────────────────────────────┘   |
+--------------------------------------------------------------------------------+


View Analytics (per experiment):

┌───────────────── tooltip_placement_v1 – Analytics ─────────────────────────┐
| [Filters: Site ▾  Roster ▾  Level ▾  Date range ▾ ]                        |
|----------------------------------------------------------------------------|
| [Chart: Average Reading Time by Variant]                                   |
| [Chart: Mean Score by Variant]                                             |
| [Chart: Gloss Clicks per 1000 words]                                      |
|----------------------------------------------------------------------------|
| [Download CSV]                                                             |
└────────────────────────────────────────────────────────────────────────────┘
