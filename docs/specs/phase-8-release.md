# Phase 8 — Hardening and release 1.0.0

Depends on: phases 0-7. Branch: `phase-8-release`.

## Goal

Turn the feature-complete application into a release: measured performance, keyboard and display
robustness, reviewed messages, frozen file schema with a migration path, a reproducible Windows
build, and complete user documentation.

## Work items

### Quality and robustness

- Coverage: thresholds of `AGENTS.md` §12 met with margin; untested error codes listed and covered.
- Error messages: every `error.*` key read in English and French by the human; each one says what
  happened and what to do.
- Logs: audit that no task text, path or URL is logged at INFO or above.
- Security: HTML escaping in every rich-text widget; links opened as-is without checks, by design
  (ADR-014); the data file written only through the atomic writer.
- Exception hooks: a forced exception in a slot shows the error dialog and lands in the log.

### Performance targets (measured with `scripts/bench_storage.py` and timing logs)

| Scenario | Target |
|---|---|
| Startup to window shown, 2,000 tasks, 20 history events each | <= 2 s |
| Save of the same file | off the UI thread, <= 1 s on the writer thread |
| Task table snapshot, 2,000 rows | <= 100 ms |
| Typing in the search box, 2,000 tasks | no visible lag (debounced, <= 50 ms per filter) |

If the JSON5 decoder misses the startup target, apply ADR-002: keep the JSON5 format and swap in a
faster JSON5 decoder behind `Json5Codec`, after a decision at review.

### Display and keyboard

- Windows display scaling 100 %, 125 %, 150 %, 200 %: no clipped text, timer digits sharp.
- Light and dark Windows themes: colors come from palette roles, no hard-coded colors outside the
  style sheet of `ui.support`; contrast checked for overdue and alert states.
- Full keyboard use: tab order on every page and dialog, mnemonics, the shortcuts listed in
  `USAGE.md`; accessible names set from snapshots.
- Minimum window size from the ini respected; layouts degrade gracefully.

### Data file

- Freeze schema version 1. Add the migration framework (`schema_version` -> ordered dict-to-dict
  steps, run before validation) with a test-only v1 -> v2 migration proving the mechanism.
- A file written by a newer app (`schema_version` 2) is refused with
  `STORAGE_SCHEMA_VERSION_UNSUPPORTED` and never overwritten.

### Packaging

- `scripts/build.py --release`: version from `pyproject.toml`, Windows version resource
  (`--version-file` generated into `build/`), product and company names, then
  `dist/Concentrator-<version>-win64.zip` containing the `onedir` folder.
- Smoke test on a Windows 11 account without Python: first run, create file, timer rings with sound,
  notification, lists and tasks, restart, data intact.
- Document the SmartScreen warning for an unsigned executable; code signing and an installer
  (Inno Setup or MSIX) are optional follow-ups, not part of 1.0.0.

### Documentation

- `README.md`: purpose, screenshots, requirements, quick start, data locations.
- `USAGE.md`: every feature, shortcuts, file locations, backup and recovery, how to edit the ini.
- `CONTRIBUTING.md`: setup, gates, phase workflow, commit conventions, how to add an error code, an
  enum, an i18n key, an ini key.
- `CHANGELOG.md` starting at 1.0.0.

## Acceptance criteria

- [ ] All gates green; coverage per layer reported.
- [ ] Performance table filled with measured values, all targets met or an approved ADR.
- [ ] Manual checks at four scaling levels and both themes done.
- [ ] Release zip runs on a clean account; data survives an update from the previous build.
- [ ] Documentation complete in English; tag `v1.0.0`.

## Review gate questions

1. Code signing or installer needed for 1.0.0?
2. Any feature from the "not planned" notes of earlier phases to schedule for 1.1?
