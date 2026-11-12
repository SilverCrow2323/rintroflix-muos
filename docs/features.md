# Product features 🌈

RintrofliX is organised around five clear destinations. Each area has a defined job, so the handheld interface stays predictable.

## Watch TV 📡

The live-TV area combines channel discovery and guide information.

- All channels, favourites and search.
- Group filtering and channel logos from playlist metadata.
- XMLTV guide data with local caching and ID/name matching.
- A two-hour guide timeline in the documented baseline.
- Current/next programme information in the player overlay.

| Input | Action |
|---|---|
| D-pad | Navigate channels, cards and guide rows |
| A | Open or play |
| X | Start/edit channel search |
| Y | Toggle favourites |
| L1 / R1 | Previous/next channel group |
| SELECT | Cycle All → Favourites → Search → TV Guide |
| START | Show selected-channel details |

## Local Library 🎞️

Add one or more folders on SD card or USB storage. Browse them when needed and play supported local video files.

!!! success "No full-card crawl"
    The application does not recursively scan the entire SD card in the background. Library paths are user-selected and browsing is on demand.

Common extensions include MKV, MP4, AVI, MOV, M4V, WebM, TS, MPG, MPEG, M2TS and FLV. Actual playback depends on the installed MPV build and codecs.

## Add-ons 🧩

Add-ons are general extensions, not a separate category of source providers.

- Install local `.rfxaddon` or `.zip` packages.
- Validate archive paths, file types and package size.
- Review metadata before enabling.
- Check app/add-on dependencies.
- Run registered actions and show user-facing toasts.
- API v2 can register a channel source and participate in the playback hook.

See the [Add-on SDK](addons.md) for the exact API boundary.

## Sources & Settings 🛠️

**Sources** manages media inputs:
- M3U / M3U8 playlists.
- XMLTV / EPG URLs.
- Playlist-declared guide URLs when discovery is enabled.
- Public iptv-org presets.

**Settings** manages application behaviour:
- Interface scale and accent colour.
- Channel logos and boot animation.
- Playback backend and stream cache.
- Guide cache and User-Agent.
- About information at the bottom of the menu.

## In-video controls 🎮

| Button | Playback action |
|---|---|
| A | Pause / resume |
| D-pad Left / Right | Previous / next channel |
| D-pad Up / Down | Seek −/+ 30 seconds |
| L1 / R1 or hardware volume | MPV volume −/+ |
| X | Mute / unmute |
| SELECT | Open / close player menu |
| START | Transport strip + now/next programme |
| L2 / R2 | Seek −/+ 10 seconds |
| B | Close menu, otherwise exit playback |
| Y | Toggle current channel favourite |

The documented player overlay includes transport controls, programme information, favourites, audio tracks, subtitles and exit. Recording is shown only when supported by the installed MPV build.

!!! note "Volume truth"
    The volume OSD reads MPV's actual `volume` and `mute` properties after changes. It is intended to report player volume, not simulate the global muOS mixer level.

## Formats & network behaviour

| Capability | Support |
|---|---|
| Playlists | M3U / M3U8, local or HTTP(S) |
| Channel metadata | `tvg-id`, `tvg-name`, `tvg-logo`, `group-title` |
| Headers | Per-channel `EXTVLCOPT` and `EXTHTTP` |
| Guide | XMLTV, gzip, multiple sources, cache |
| Transport security | HTTPS certificate validation enabled |

