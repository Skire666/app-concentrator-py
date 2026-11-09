# Built-in sounds

Every `*.mp3` file of this folder is a built-in sound, offered for the timer alarm and for the hourly
chime. Its file name without `.mp3` is the value stored in the data file
(`sound = { kind = 1, value = '<name>' }`), the value of `timer.default_sound` and
`chime.default_sound` in `concentrator.ini`, and the label key `sound.builtin.<name>` of the catalogs.
A file added here without a label is listed under its file name.

| File | Author | Default for |
|---|---|---|
| `alarm.mp3` | Universfield | the timer alarm (`timer.default_sound`) |
| `beep.mp3` | Universfield | |
| `chime.mp3` | lesiakower | the hourly chime (`chime.default_sound`) |
| `notification.mp3` | Universfield | |
| `soft.mp3` | Universfield | |

The files were provided by the owner, who renamed them on 2026-11-09 and confirmed on 2026-11-07 that
their license allows their use in this personal project without commercial use (ADR-038, ADR-039).
