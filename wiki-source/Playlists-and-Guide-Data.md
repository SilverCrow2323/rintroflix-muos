# Playlists and TV guide data

RintrofliX uses playlists for channels and XMLTV data for programme information. Sources are configured separately from general app settings.

## Add a playlist

1. Open **Sources → Playlists**.
2. Add an M3U/M3U8 URL or choose a local playlist file.
3. Refresh the channel list.
4. Check that groups, logos and channel names are present.

## Add guide data

1. Open **Sources → TV guide data**.
2. Add an XMLTV URL when the playlist does not declare one.
3. Refresh the guide data.
4. Check the programme match for a channel with a known listing.

## Useful playlist fields

| Field | Purpose |
|---|---|
| `tvg-id` | Match a channel to an XMLTV programme listing |
| `tvg-name` | Alternate channel name used for matching/display |
| `tvg-logo` | Channel logo |
| `group-title` | Channel group/category |

## Troubleshooting missing guide entries

- Confirm the XMLTV source is reachable.
- Compare the playlist channel's `tvg-id` with the XMLTV channel ID.
- Check whether the provider uses a different channel identifier.
- Allow the local guide cache to refresh.

> **Optional** — Add multiple XMLTV sources when a single provider does not cover every channel.
