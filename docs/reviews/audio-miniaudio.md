# Audio on miniaudio: report

Branch `audio-miniaudio`, from `phase-8-release` (`48f7496`); not pushed. Owner request (2026-11-12):
replace Qt Multimedia and FFmpeg with miniaudio 1.73 to play the MP3 sounds. Decisions in ADR-045.

## Summary

- `miniaudio==1.73` is a runtime dependency (prebuilt wheel for CPython 3.14 on Windows; it brings `cffi`).
- `infrastructure/audio/MiniaudioSoundPlayer` replaces `infrastructure/qt/QtSoundPlayer` behind the same
  `SoundPlayerPort`: same files tried in order, same loops (N times or until stopped), same volume curve,
  same beep as last resort. Nothing changed above the infrastructure layer.
- Qt Multimedia is neither imported nor bundled: architecture tests forbid the import, the build excludes
  the modules, and the bundle holds no FFmpeg or multimedia file.
- The self-check decodes the default alarm and chime sounds with miniaudio in the frozen build.

## Blockers met, and how they were solved

| # | Blocker | Solution |
|---|---|---|
| 1 | miniaudio has no type information (`py.typed`); basedpyright strict refused it. | Local stub `typings/miniaudio.pyi` (default stub path of basedpyright) for the part used. No setting changed, no ignore comment. |
| 2 | The frozen app stopped at startup, before writing any log: the native `_miniaudio` extension imports `_cffi_backend`, which PyInstaller cannot see. | `--hidden-import _cffi_backend` in `scripts/build.py`, with a test. |
| 3 | Stopping a sound froze the window for 0.5 s: closing a miniaudio stream waits about 2.5 audio periods (200 ms by default). OK on the alarm, a favorite, closing a preview would all wait. | Period of 20 ms (55 ms to stop), as the new ini key `[timer] audio_buffer_ms` [10..200]. |
| 4 | miniaudio calls the sound generator from its own audio thread (a new thread for `AGENTS.md` section 6.4). An exception there would be lost. | The generator only decodes, never raises, logs a decoding error and ends the sound; the end of a sound comes back through `MainThreadDispatcherPort`. Recorded in ADR-045 and `AGENTS.md`. |
| 5 | A missing file raises `FileNotFoundError`, not `MiniaudioError` (found by the self-check test). | Both are handled; a file that disappears between two loops ends the sound (test). |
| 6 | `AUDIO_PLAYBACK_FAILED` was no longer produced (it came from Qt's error codes); the error-code test failed. | It now means "the output opened but refused to start" (test). |

Not a blocker: `furryp.json` lists only forbidden imports, so it needed no change.

## Comparison with the previous build

Same PC, same day, `scripts/build.py --release` and `scripts/bench_app.py --startup --exe` (1,000 tasks).

| | Qt Multimedia + FFmpeg (`48f7496`) | miniaudio |
|---|---|---|
| Bundle | 92.5 MB, 82 files | **70.7 MB**, 75 files (−21.8 MB, −24 %) |
| Release zip | 42.5 MB | **32.6 MB** (−23 %); 23.4 MB as `.7z` |
| Removed | — | `avcodec` 14.1, `avformat` 2.9, `Qt6Multimedia` 1.4, `swscale` 1.3, `avutil` 1.2, FFmpeg plugin 0.8, `QtMultimedia.pyd` 0.6, Windows media plugin 0.3, `swresample` 0.2 MB |
| Added | — | `_miniaudio.pyd` 0.63 MB, `_cffi_backend` 0.18 MB |
| Startup to window shown | 1.35 to 1.57 s | **1.26 to 1.31 s** (FFmpeg no longer loaded at startup) |
| Save, read, table, search | 0.25 s, 0.32 s, 44 ms, ≤ 12 ms | unchanged |
| `play()` / `stop()` on the main thread | asynchronous in Qt | 26 ms / 56 ms (20 ms buffer) |
| Reliability (real device, volume 0) | — | 25 of 25 looped plays ended on time; 4 plays under a saturated main thread: 5.16 s for 5.12 s of sound |

## Gates

`uv run python scripts/check.py`: ruff format and check, basedpyright strict, furryp and pytest passed;
coverage domain 99.81 %, application 99.00 %, presentation 99.03 %, overall 98.4 %. The frozen self-check
passed.

## To check by ear (not possible here)

1. Alarm: a 10-second timer rings with the default sound at 80 %, then with 3 plays, then "Repeat until
   stopped": OK stops it at once.
2. Volume: preview at 10 %, 50 % and 100 % in the timer dialog: the steps sound like before.
3. Your own MP3 (long file, other sample rate, mono): plays fully, loops without a gap.
4. Hourly chime at a full hour, and a chime while the timer rings (skipped).
5. Busy computer (build running): the alarm does not crackle; if it does, set `audio_buffer_ms = 50`.
6. Unplug the headphones while it rings, then start another sound: it plays on the speakers (or the beep
   sounds and the journal says why).
