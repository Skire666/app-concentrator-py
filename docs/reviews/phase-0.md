# Phase 0 review report

Branch `phase-0-foundations`, 9 commits on top of `main`, not pushed.

## Summary

Every cross-cutting mechanism of the phase 0 spec is in place: results and error codes, enums,
configuration (`concentrator.ini` -> pydantic -> `AppConfig`), logging (file, journal ring buffer,
hooks, Qt bridge, faulthandler), i18n (EN/FR, live switch), render coordination, action gating,
scheduling, single instance, layout persistence, build and quality gates. The window shell shows the
full-height module bar, three placeholder pages and a one-line status bar with the FRA/ENG button.
`scripts/build.py` produces `dist/Concentrator/Concentrator.exe`, and the frozen self-check passes.

## Spec coverage

| Requirement | Status | Notes |
|---|---|---|
| Repository files (`README`, `CONTRIBUTING`, `USAGE`, `.python-version`, `.vscode/`, `tests/conftest.py`) | done | plus `.gitattributes` (LF, ADR-017 amendment) |
| `scripts/check.py`, `coverage_gate.py`, `clean.py`, `build.py` | done | `build.py` runs PyInstaller in a subprocess (ADR-025) |
| Domain kernel (`domain/common/`, `LanguageEnum`) | done | plus `ErrorCategoryEnum`; `ValidationResult.baseline` (ADR-025) |
| Application kernel (ports, `EventBus`, `AppConfig`, `AppTicker`) | done | plus `ErrorReporterPort`; `TranslatorPort.has` (ADR-023) |
| Infrastructure: paths, clock, ids, Windows shell | done | plus `allow_set_foreground_window` for the second launch |
| Infrastructure: ini loader | done | `model_validate_strings`, `CONFIG_KEY_UNEXPECTED` (ADR-003 amendment) |
| Infrastructure: logging, ring buffer, exception hooks | done | |
| Infrastructure: JSON catalog translator | done | |
| Infrastructure: Qt scheduler, dispatcher, single instance, QSettings, Qt log bridge | done | Qt adapters use composition (private `QObject`) |
| Presentation kernel (enums, `RenderCoordinator`, `ActionGate`, snapshots, `FormState`, `DialogPort`) | done | gate renders only the action's sections (ADR-023) |
| Presentation: shell snapshot and presenter | done | two snapshots: `ShellSnapshot`, `StatusBarSnapshot` |
| Layout persistence | done | `LayoutStateKeeper` + `layout/*` keys (ADR-022), requested at plan review |
| UI: `MainWindow`, `ModuleBarPanel`, `StatusBarPanel`, pages, `SnapshotButton`, `QtDialogService` | done | panels use `render_snapshot` (ADR-025) |
| Bootstrap sequence 1-9 and `CONCENTRATOR_SELF_CHECK=1` | done | self-check also renders the module SVGs (ADR-024) |
| `concentrator.ini` phase 0 keys | done | plus `[app] single_instance_timeout_ms = 1000` |
| Error codes | done | plus `3005 CONFIG_KEY_UNEXPECTED` |
| i18n key families | deviated | module buttons use `action.shell_show_*` (+ `.tooltip`), not `shell.module.*` (ADR-023) |
| Placeholder icon script | not needed | `assets/icons/concentrator.ico` provided (renamed from `.ico.ico`) |
| Tests listed in the spec | done | see Gates |

## Deviations and decisions

Approved with the plan:

- ADR-021: `EventBus` dispatch catches `Exception`, logs it with the traceback and forwards it to the
  reporter shared with the global hooks. AGENTS rule 4 lists exactly these two places.
- New error code `3005 CONFIG_KEY_UNEXPECTED` and new ini key `[app] single_instance_timeout_ms`.
- Temporary placeholder keys (see open question 2).
- Config validated with `model_validate_strings(strict=True, extra="forbid")`.
- `ActionGate.run` returns `ValidationResult.skipped()` for a busy action.
- Qt adapters use composition; two shell snapshots; single-instance details; logging and self-check
  behavior; absolute paths in `build.py`; bootstrap split; plain English config error (ADR-024).

Requested at plan review:

- ADR-022: `LayoutStateKeeper` and `layout/*` keys; AGENTS §7.3 and §8.5, and the phase 5 spec, updated.
- ADR-023: action-to-sections mapping for `ActionGate` (`request_all` reserved for language and data
  file switches); `action.<name>` keys as the single source of action labels.
- AGENTS §9: the date formatter zero-pads values before filling the templates (no formatter yet).

Decided during the build (please confirm):

- ADR-017 amendment (owner decision during step 1): ruff 0.17 rejects rule codes in `per-file-ignores`
  and `# noqa`. `pyproject.toml` is no longer linted by ruff; AGENTS rule 14 names `# ruff: ignore[...]`.
- ADR-025: `render_snapshot` instead of `render` (`QWidget.render` clash); `ui/windows/*_page.py` and
  `*_page.py` in the naming list; `ShellLayout` passed to the ui; PyInstaller in a subprocess; catalog
  key literal scan limited to `presentation/` and `ui/`; `ValidationResult.baseline`.
- `ErrorReporterPort` (application port), implemented by `UnexpectedErrorPresenter`. It shows one
  translated dialog at a time; errors before the window exists are only logged.
- `TranslatorPort.has(key)` for the optional `action.<name>.tooltip`.
- `.gitattributes` forces LF (Git for Windows defaults to `core.autocrlf=true`).
- One justified suppression in the whole code base:
  `concentrator/infrastructure/qt/qt_main_thread_dispatcher.py` (`no-self-use`). The queued
  connection needs a bound slot of the main-thread `QObject`.

## Gates

`uv run python scripts/check.py` on the final commit:

| Gate | Result |
|---|---|
| `ruff format` | passed (no change) |
| `ruff check` | passed |
| `basedpyright` (strict) | 0 errors, 0 warnings, 0 notes |
| `furryp check concentrator` | all checks passed |
| `pytest --cov` | 324 passed, 0 failed, 0 skipped |
| `coverage_gate.py` | passed |

Also run here (not part of the gates):

- `uv run python scripts/build.py`: PyInstaller build in about 1 minute, 123 MB, frozen self-check passed.
- Process-level smoke test of the built exe, with scratch `%APPDATA%`/`%LOCALAPPDATA%`:
  - the first instance shows its window;
  - a second launch exits 0 after 0.6 s and the first logs "Another launch asked this instance to
    show itself";
  - a graceful close exits 0 and writes the `layout/*` keys;
  - the log contains the startup and shutdown sequence;
  - with the ini renamed, the self-check exits 1.

## Coverage per layer

Branch coverage (statements + branches):

| Layer | Coverage | Threshold |
|---|---|---|
| domain | 100.00 % | 90 % |
| application | 100.00 % | 85 % |
| presentation | 99.73 % | 80 % |
| infrastructure | 96.19 % | — |
| ui | 97.84 % | — |
| bootstrap | 87.14 % | — |
| overall | 96.50 % | 75 % |

Not covered by design: the non-Windows branches of `windows_shell.py`, the modal file pickers of
`QtDialogService`, the config error dialog and the `app.exec()` path of `bootstrap/app.py`. The
second-instance send path runs in a child process, where coverage is not measured.

## Manual test script

The GUI cannot be inspected from here; please run these on Windows 11 at 100 % and 150 % scaling.

1. `uv run concentrator`: no console window. The module bar is 100 px wide over the full window
   height, and the status bar is one line under the pages only.
2. Click Focus, Journal and Settings: the page changes and only the active button is highlighted. The
   module icons are visible (also in the built exe).
3. Click the language button twice: every text (title, module buttons, placeholders, status bar,
   button tooltip) switches to French, then back to English. The button shows `FRA`, then `ENG`.
4. Run `uv run concentrator` again while the first is open: the first window comes to the front (or
   its taskbar button flashes) and the second process exits.
5. Resize and move the window, drag the splitter, close, reopen: geometry and splitter are restored.
   Delete `%APPDATA%\Concentrator\ui-state.ini`: the next start uses 1400 x 860, centered, with the
   splitter at 70 %.
6. `uv run python scripts/build.py`, open `dist\Concentrator`, set `module_bar_width_px = 140` in
   `concentrator.ini`, start `Concentrator.exe`: the bar is wider, without rebuilding.
7. Rename `concentrator.ini` and start: a dialog names the missing file (`CONFIG_FILE_NOT_FOUND`).
   Delete one key instead: the dialog names the key (`CONFIG_KEY_MISSING`).
8. Check `%LOCALAPPDATA%\Concentrator\logs\concentrator.log`: it contains the startup sequence.
9. The taskbar shows the Concentrator icon, not the Python icon (both with `uv run concentrator` and
   with the built exe).
10. Copy `dist\Concentrator` to a Windows account without Python and start it.

## Open questions

1. **Unguarded single-instance mode.** If the lock cannot be created, the application runs unguarded
   after an ERROR log. From phase 1 on, two instances could then write the same data file, so this
   case will need at least a visible warning. Default: add the warning in phase 1.
2. **Temporary placeholder keys**, to remove when the real panels arrive:
   - `placeholder.focus.zone1` (phase 5);
   - `placeholder.focus.zone2` (phase 2);
   - `placeholder.journal` and `placeholder.settings` (phase 4);
   - the matching `ShellSnapshot` fields.
3. **Shared log file.** Per the spec, a second launch configures logging (step 3) before the
   single-instance check (step 4), so it appends a few lines to the same rotating log as the running
   instance. A rollover by that short-lived process could fail on Windows, where the file is locked.
   Default: keep the spec order and revisit in phase 8 if rollover problems appear.
4. **Bundle size** is 123 MB. PyInstaller collects every Qt image format plugin and other unused Qt
   files. Default: trim in phase 8.
5. **Multi-size application icon.** The current `.ico` has one 256 px frame; you will provide a
   multi-size icon later.
6. **The language is not remembered** across restarts (in memory, as specified). The phase 1 spec stores it
   in `UserSettings` (`change_language`), so nothing to do before then.
7. **Your uncommitted `.claude/settings.json` fix** (missing comma) is still in the working tree and
   is not part of these commits. Default: leave it to you.
