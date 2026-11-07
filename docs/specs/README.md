# Specifications — phase plan

The project is delivered in nine phases. Each phase ends with a **review gate**: the agent stops,
reports, and waits for the human to approve and tag `phase-<n>-accepted`. The timer comes first, the
TODO list manager last, as requested.

| Phase | Title | Main outcome | Depends on |
|---|---|---|---|
| 0 | [Foundations](phase-0-foundations.md) | Tooling, layers, shell window, i18n, logging, single instance, build | — |
| 1 | [Persistence](phase-1-persistence.md) | TOML user file, first launch, atomic save, recovery | 0 |
| 2 | [Timer core](phase-2-timer-core.md) | Countdown, state machine, alarm MP3, background alert, snooze, edit dialog | 1 |
| 3 | [Timer extras](phase-3-timer-extras.md) | Favorites (presets) and hourly chime | 2 |
| 4 | [Journal and settings](phase-4-journal-settings.md) | Menu B log viewer, Menu C editable settings | 1 |
| 5 | [TODO core](phase-5-todo-core.md) | Lists as tabs, tasks CRUD, states, table view | 1 |
| 6 | [TODO advanced](phase-6-todo-advanced.md) | Recurrence, history, filters, search, links, bulk actions | 5 |
| 7 | [Focus queue](phase-7-focus-queue.md) | Quick TODO in zone 2 fed from tasks, history on completion | 3, 6 |
| 8 | [Hardening and release](phase-8-release.md) | Performance, accessibility, packaging, documentation, v1.0.0 | all |

Phase 4 can be swapped with phase 3 if you need the journal earlier for debugging.

## Workflow per phase

1. **Plan** — the agent reads `AGENTS.md`, `docs/decisions.md` and the phase spec, then proposes a
   plan: files, tests, risks, questions. The human approves or amends.
2. **Build** — branch `phase-<n>-<slug>`, small Conventional Commits, tests written with the code,
   gates run before each commit (`uv run python scripts/check.py`).
3. **Report** — the agent stops and writes the review report (template below) in the pull request
   or in `docs/reviews/phase-<n>.md`.
4. **Review** — the human runs the manual test script on Windows 11, reads the diff, answers the
   open questions. Fixes go on the same branch.
5. **Accept** — merge, tag `phase-<n>-accepted`, update `docs/decisions.md` if something changed.

Prompt to start a phase with Claude Code:

```text
Read AGENTS.md, docs/decisions.md and docs/specs/phase-<n>-<slug>.md.
Propose a plan for phase <n> only. Do not write code until I approve the plan.
```

## Review report template

```markdown
# Phase <n> review report

## Summary
What was built, in 5 lines.

## Spec coverage
| Requirement | Status (done / partial / deviated) | Notes |

## Deviations and decisions
Each deviation from the spec with its reason; new entries added to docs/decisions.md.

## Gates
Output summary of: ruff format, ruff check, basedpyright, furryp, pytest.

## Coverage per layer
| Layer | Coverage | Threshold |

## Manual test script
Steps the human must run (copied from the spec), with what to observe.

## Open questions
Numbered, each with the default the agent would choose.
```

## Review checklist (human)

- [ ] Manual test script passes on Windows 11 (100 % and 150 % display scaling).
- [ ] No business logic in `ui/`; panels only render snapshots and emit signals.
- [ ] New enums have `UNKNOWN = -1` and `UNSET = 0`; new error codes have FR and EN messages.
- [ ] No hard-coded tunables or UI strings; new ini keys documented in the phase spec.
- [ ] Every new failure path returns an error code and has a test.
- [ ] `USAGE.md` and `docs/decisions.md` updated.
- [ ] Language switch FR/ENG updates every new text live.
