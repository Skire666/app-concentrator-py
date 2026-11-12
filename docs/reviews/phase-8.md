# Phase 8 review report

First issue (2026-11-12). Branch `phase-8-release`, 8 commits on top of `main` (`a249e66`). The branch is
not pushed and nothing is tagged. The owner decisions of the plan review are in ADR-044.

Owner answer (2026-11-12): "Suit tes recommandations". The items "decided during the build" are approved and
the open questions below take their defaults (ADR-044 amendment).

## Summary

- **Release 1.0.0.** The version comes from `pyproject.toml` and goes into a Windows version resource.
  `scripts/build.py --release` writes `dist/Concentrator-1.0.0-win64.zip` (32.6 MB after the review and the
  move to miniaudio, ADR-045). Unused Qt and Python parts are removed and Qt Multimedia is gone, taking the
  bundle from 153 MB to 70.7 MB; the frozen self-check still passes.
- **Measured performance.** All four targets are met with 1,000 tasks: startup 1.3 s, save 0.25 s on the
  writer thread, task table 44 ms, search ≤ 12 ms (details below). `scripts/bench_app.py` measures them in
  a temporary profile, and the startup time is also logged at every start.
- **Frozen schema version 1 with a migration path.** A reference file must read and write back byte for
  byte. A migration chain of dict-to-dict steps runs before validation; a test-only v1 → v2 migration
  proves it. A version 2 file is refused and left untouched.
- **Keyboard and screen readers.**
  - Alt letters on every dialog caption and button, on the Settings page and on the module bar, unique per
    window in English and French.
  - Every reachable control is named for screen readers.
  - Tab follows the reading order on every dialog and page. Three pages had widgets out of order, and the
    list dialog went from Name to Description before Priority.
- **Audits.**
  - Message boxes rendered user text as HTML; this is fixed.
  - No user text is logged at INFO or above.
  - Only the storage adapters and the log setup write files.
  - Every error code has a test.
  - An exception in a Qt slot reaches the log and the error dialog.
  - 42 error messages now say what to do.

## Spec coverage

| Requirement | Status | Notes |
|---|---|---|
| Coverage thresholds met with margin; untested error codes covered | done | 98.4 % overall; every error code appears in a test (new architecture test) |
| Error messages read by the human | ready for you | `docs/reviews/phase-8-messages.md`: all 84 messages, the 42 revised ones marked |
| No task text, path or URL logged at INFO or above | done | sentinel test over every task, list, focus and link use case and a damaged file read (owner 2: data file and application paths stay) |
| HTML escaping in every rich-text widget | done, with a fix | message boxes now plain text; UI audit of every label, tooltip and model tooltip |
| Links opened as-is; data file written only through the atomic writer | done | architecture test lists the only modules that write files |
| Forced exception in a slot → error dialog and log | done | UI test with the real hooks and `UnexpectedErrorPresenter` |
| Performance table | done | all targets met, see below; history of 10 events instead of 20 (build 2) |
| Display scaling 100 to 200 %, light and dark themes | manual | see the manual test script; colors already come from palette roles only |
| Full keyboard use, mnemonics, shortcuts, accessible names | done | ADR-044 build 7 to 10; shortcuts listed in `USAGE.md` are all covered by tests |
| Minimum window size respected | manual | unchanged since phase 0 (`ui.min_width_px`, `ui.min_height_px`) |
| Freeze schema 1, migration framework, test-only v1 → v2 | done | ADR-044 build 1 |
| File of a newer app refused and never overwritten | done | already refused since phase 1; new test checks load, probe and the folder |
| `build.py --release`, version resource, zip | done | ADR-044 build 12 |
| Smoke test on an account without Python | manual | script below |
| SmartScreen documented; no signing or installer | done | `USAGE.md` and `README.md`; review question 1 |
| `README.md`, `USAGE.md`, `CONTRIBUTING.md`, `CHANGELOG.md` | done | screenshots to capture (owner 4) |
| Tag `v1.0.0` | yours | after the review, with `phase-8-accepted` |

## Deviations and decisions

All are recorded in ADR-044. Items "decided during the build" to approve:

1. Schema 1 is frozen by `tests/data/schema-v1.toml`. The migration chain lives in
   `infrastructure/persistence/migrations/`, and no new error code was added.
2. Measurements: the startup time counts from process creation (interpreter and imports included). The
   benchmark tasks hold 10 history events, the cap set at phase 7, instead of the 20 of the spec table.
3. Message boxes show plain text (a real bug: a list named `<b>Work</b>` was shown bold in the delete
   question).
4. to 6. Tests for log privacy, file writers and error codes.
7. to 9. Mnemonics in the catalogs, checked per window; accessible names taken from the snapshots. Widgets
   created by a render get their Tab place through `insert_before`, which handles a Qt 6 behavior:
   `setTabOrder` puts the second widget after every descendant of the first, and ignores widgets that
   take no focus.
10. **Tab leaves the multi-line fields** (task text, list description): a tab character can no longer be
    typed there (review question 3).
11. 42 messages revised; field-level storage lines rely on the recovery dialog for what to do.
12. Release zip and bundle trimming, checked with the PE import tables.

Spec text changed: the smoke test now says "taskbar flash" instead of "notification" (owner 7). `AGENTS.md`
now covers the plain-text rule, the keyboard rules, the mnemonic convention, the frozen schema and the new
build commands.

Process note: commit `36c1a1b` was first made while `ruff check` failed. I had piped the gate output, which
hid its exit code. I fixed the lint error, ran the gates again (green), and amended that local commit
before the next step. No commit on the branch has a failing gate. Since then I commit only on a 0 exit code.

## Gates

`uv run python scripts/check.py` on the last commit:

| Gate | Result |
|---|---|
| `ruff format` | passed |
| `ruff check` | passed |
| `basedpyright` (strict) | 0 errors, 0 warnings, 0 notes |
| `furryp check concentrator` | all checks passed |
| `pytest --cov` | 3192 passed, 0 failed, 0 skipped |
| `coverage_gate.py` | passed |

`uv run python scripts/build.py --release` succeeded: 50.9 MB of Qt parts removed, 102.1 MB left, the
self-check passed (MP3 decoding, SVG icons, data round trip), and the zip is 46.0 MB. After the review
(option A, ADR-044 amendment 3): 60.5 MB removed, 92.5 MB left, a 42.5 MB zip, startup 1.35 to 1.42 s, and
the self-check also checks SHA-256. The file properties
of `Concentrator.exe` show Concentrator 1.0.0, skire666.

## Coverage per layer

Branch coverage (statements + branches):

| Layer | Coverage | Threshold |
|---|---|---|
| domain | 99.81 % | 80 % |
| application | 99.00 % | 75 % |
| presentation | 99.02 % | 70 % |
| infrastructure | 98.23 % | — |
| ui | 97.99 % | — |
| bootstrap | 92.42 % | — |
| overall | 98.39 % | 70 % |

## Performance

Measured on this PC with `uv run python scripts/bench_app.py --startup --exe dist/Concentrator/Concentrator.exe`.
The data file holds 1,000 open tasks in one list, each with 10 history events (959 kB). The shipped ini and
catalogs are used. Times are the best of 5 runs; startup runs are listed one by one.

| Scenario | Target | Measured |
|---|---|---|
| Startup to window shown, 1,000 tasks | ≤ 2 s | 1.32 to 1.34 s (frozen exe); 1.39 to 1.52 s with `python -m concentrator` |
| Save of the same file | off the UI thread, ≤ 1 s | 0.25 s on the writer thread (encode, atomic write, `.bak`) |
| Task table snapshot, 1,000 rows | ≤ 100 ms | 44 ms |
| Typing in the search box, 1,000 tasks | ≤ 50 ms per filter | 12 ms for the first search (texts folded once), then ≤ 2 ms |

Notes:
- Reading the file at startup takes 0.32 s, within the startup time.
- The startup runs are offscreen. On your screen, the Journal shows the real value at each start:
  `Startup took … ms (process start to main window shown)`.
- The search applies 150 ms after the last key (`todo.search_debounce_ms`).

## Manual test script

The GUI cannot be inspected from here, so I have not run any of these steps.

1. **Display scaling.** Run the steps below at 100 %, 125 %, 150 % and 200 % (Settings > Display > Scale,
   then restart Concentrator).
   - Check every page and every dialog (timer, favorite, hourly chime, task, list, first launch, Data file
     problem): no clipped or overlapping text, timer digits sharp, module bar icons crisp.
   - Resize the window to its minimum size: nothing overlaps.
2. **Themes.** Repeat at 100 % with Windows in light mode, then in dark mode (Settings > Personalization >
   Colors). These must stay readable:
   - an overdue task, bold and highlighted, in the table and in the focus queue;
   - a due-today task (bold);
   - an invalid field (border);
   - the ringing caption;
   - the Journal error rows;
   - the "Second launch not blocked" warning.
3. **Keyboard.** In English, then in French:
   - In each dialog, hold Alt: one letter is underlined on every caption and on Save and Cancel. Press
     Alt and each letter: the focus goes to that field, and Save or Cancel act. Check the same on the
     Settings page, and on the module bar (Alt+F, Alt+J, Alt+E in English; Alt+F, Alt+J, Alt+R in French).
   - Press Tab and Shift+Tab through each dialog and page: the focus moves top to bottom and left to
     right. On the Focus page it goes through zone 1, then zone 2: timer, focus queue fields and entries,
     favorites, then Add and the hourly chime. In the task text, Tab moves to the List field.
   - Optional: start Narrator (Ctrl+Win+Enter) and Tab through the task dialog: each field is read with
     its caption.
4. **Markup.** Create a list named `<b>Work</b>`, then delete it: the question shows the name as typed,
   not in bold.
5. **Release smoke test** on a Windows 11 account without Python:
   - Unzip `Concentrator-1.0.0-win64.zip` and run `Concentrator.exe` (SmartScreen: More info > Run anyway).
   - Check the file properties of the exe (Details tab): product Concentrator, version 1.0.0.
   - Create the data file at the default location.
   - Start a 10-second timer: the alarm sounds. Start another one and put another application in front:
     the taskbar button flashes when it rings.
   - Create two lists and three tasks (one repeating, one with a path line), queue one task, and click
     the path.
   - Close and restart: everything is there. Settings > About shows version 1.0.0.
6. **Update from the previous build.** With the phase 7 build, or your everyday data file, close it, then
   open the same data file with the 1.0.0 build: lists, tasks, favorites, chime, focus queue and settings
   are intact. Make a change; the file is saved with `app_version = '1.0.0'` and `schema_version = 1`.
7. **Error messages.** Read `docs/reviews/phase-8-messages.md` in both languages.
8. **Startup time.** Open your largest data file, then look for `Startup took` in the Journal.
9. **Screenshots.** Capture `docs/images/focus-page.png`, `journal-page.png` and `settings-page.png` at
   100 % for the README (light mode, a few lists and tasks, nothing personal).

## Open questions

1. **Code signing or installer for 1.0.0?** (spec review question 1). Default: no. The zip and the
   documented SmartScreen step are enough for a personal application; signing needs a paid certificate.
2. **Features from the "not planned" notes to schedule for 1.1?** (spec review question 2). Default: none
   for now; decide after using 1.0.0 for a while. Candidates noted in earlier phases are restoring a
   running countdown after Concentrator restarts (phase 2, "not planned") and a "Clear completed" button
   for the focus queue (phase 7, ADR-043).
3. **Tab in the multi-line fields** now moves to the next field instead of typing a tab character.
   Default: keep (no keyboard trap, standard in forms).
4. **History events in the benchmark:** 10 per task (the phase 7 cap) instead of 20. Default: keep; the
   file of the spec target would only be larger if the cap were raised.
5. **Mnemonic letters.** I chose them to be unique per window, preferring word initials. The less usual
   ones are English "S&ettings" on the module bar (Save uses S on that page), "La&nguage", "First chime
   &at", and French "Arrêter a&utomatiquement après". Default: keep; any letter can be changed in the
   catalogs, and the catalog test checks uniqueness.
6. **CHANGELOG date.** 1.0.0 is dated 2026-11-12. Default: set it to the day of the `v1.0.0` tag if that
   is later.
