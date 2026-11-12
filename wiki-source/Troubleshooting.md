# Troubleshooting

Start with the least destructive checks. Confirm the device, muOS version and application baseline before changing configuration.

## Common problems

| Symptom | First check |
|---|---|
| Blank screen at launch | Check Python 3, Pygame and the launcher log |
| App launches but has no channels | Confirm a playlist is configured under Sources → Playlists |
| Programme guide is empty | Check the XMLTV URL and playlist `tvg-id` values |
| Channel logos are missing | Check `tvg-logo` metadata and the logo cache setting |
| Video plays without full controls | The full overlay requires MPV IPC; FFplay is only a basic fallback |
| Volume indicator differs from device volume | The OSD reports MPV volume, not the global muOS mixer |
| Add-on does not load | Check API version, manifest and dependency requirements |

## First diagnostic steps

- Confirm that the installed application package matches the device architecture and runtime.
- Check the application log before deleting any cache or configuration.
- Try one known playlist and one known XMLTV source.
- Disable a recently added extension if the issue started after enabling it.

## Report a problem

Include the exact device model, muOS version, app baseline, steps to reproduce, expected and actual behavior, and relevant redacted logs.

Never include private playlist URLs, credentials, tokens, ROMs or unrelated personal data.
