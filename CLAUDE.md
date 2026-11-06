@AGENTS.md

## Claude Code specifics

- `AGENTS.md` (imported above) is the single source of truth. Do not duplicate its rules here.
- Read `docs/decisions.md` and the current phase spec in `docs/specs/` before planning.
- Begin each phase with a written plan and wait for approval before editing files.
- The GUI cannot be inspected from here: list the manual checks from the phase spec in the review
  report instead of claiming they pass.
- Run `uv run python scripts/check.py` before proposing a commit. Never commit with a failing gate.
- Never edit `furryp.json`, coverage thresholds or lint/type settings without explicit approval.
