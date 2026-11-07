# Built-in sounds

Every `*.mp3` file of this folder is a built-in alarm sound. Its file name without `.mp3` is the value
stored in the data file (`sound = { kind = 1, value = '<name>' }`), the value of
`timer.default_sound` in `concentrator.ini`, and the label key `sound.builtin.<name>` of the catalogs.
A file added here without a label is listed under its file name.

| File | Author (from the file name) |
|---|---|
| `alarm-lesiakower-reverby-notification-sound.mp3` | lesiakower |
| `alarm-universfield-new-notification.mp3` | Universfield |
| `alarm-universfield-new-notifications.mp3` | Universfield |
| `alarm-universfield-notification-beep.mp3` | Universfield |
| `alarm-universfield-soft-notification.mp3` | Universfield |

The files were provided by the owner, who confirmed on 2026-11-07 that their license allows their use
in this personal project without commercial use (ADR-038).
