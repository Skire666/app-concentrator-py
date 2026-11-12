# Phase 8 code review: findings and fixes

Branch `phase-8-release`, before the `phase-8-accepted` tag; not pushed. The review covered `main..17867d7`
(the 9 commits of the phase) and looked for defects, not style. It reported 9 findings; 8 are fixed and 1
is not kept.

Findings 1, 2, 3, 5, 6 and 9 were reproduced with a failing unit, integration or UI test before the fix.
Finding 7 is a cost issue and finding 4 concerns the benchmark script, so neither has a failing test. The
decisions are in amendment 2 of ADR-044.

## Findings and fixes

| # | Severity | Finding | Fix |
|---|---|---|---|
| 1 | medium | A favorite label is the user's text, but its button showed it with Qt's mnemonic rule. "R&D" read "RD" with D underlined, and Alt+D started that favorite. A label like "&Journal" took the letter of a module button, and Qt then ignores both. | The presets panel shows the label through `without_mnemonic` ("R&&D"); the accessible name is "R&D". |
| 2 | medium (future) | The migration chain left a version older than its first step unchanged, and the schema validation accepted it because it only checks `schema_version >= 1`. Once version 3 exists with only a 2 → 3 step, a version 1 file would be read as version 3 and later saved with version 3 content labeled 1. Reproduced with a test chain. | `MigrationChain.accepts(version)`; the codec refuses such a file with `STORAGE_FIELD_INVALID_VALUE` on `schema_version`, with a WARNING. Version 0 gets the same code as before. |
| 3 | low | "Startup took N ms" also counted the time the user spent in the first-launch, recovery or unguarded-instance dialogs, so a first start read like a 40 s startup. | `StartupFlowPresenter.asked_the_user`; after a dialog the log reads "Main window shown N ms after the process started, startup dialogs included". The benchmark reads only the "Startup took" line. |
| 4 | low (tooling) | `bench_app.py` timed `save()` without checking its outcome, so a failing save would have been reported as a fast one. | A failed save stops the benchmark with its error codes. The measured saves succeed: the published numbers stand. |
| 5 | low | The focus queue scroll area was an empty Tab stop after the rows, and the Settings page scroll area was one before the fields. | Both scroll areas take no focus; the fields and rows inside still scroll into view when focused. The queue rows now follow the quick-add field (`focus_order.insert_after`): with a scroll area that takes no focus, "before the scroll area" depended on which panel rendered first. A UI test checks that no scroll area is a Tab stop on the Focus and Settings pages. |
| 6 | low | Placeholders and tooltips used as accessible names went through the mnemonic stripping: "Tasks & notes" was read "Tasks  notes". | Search box, task picker, quick add fields and path rows take their placeholder, tooltip or label as is. Only captions and button texts are stripped. |
| 7 | cleanup (cost) | The presets panel reordered the Tab chain once per created button, which is quadratic. | One `insert_before` call after the loop, as in the other panels. |
| 8 | not kept | A combo box gets its accessible name both from `SnapshotComboBox.apply` and from `set_caption`. | Both read the same snapshot field (`ChoiceFieldSnapshot.label`, which is also the caption) in every panel, so the order does not matter. A combo without caption (filter bar) needs the first one. |
| 9 | low | The DEBUG line "Save of revision N took M ms" was also written for a refused or failed save, which read like a completed save. | "Save of revision N written in M ms", or "Save of revision N failed in M ms: [codes]". |

User-visible changes besides the fixed cases: none in `USAGE.md`. The Tab order section already promised no
empty stops.
