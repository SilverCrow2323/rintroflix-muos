# Changelog

## 2.0.0 — Handheld Media Centre

- Rebuilt the interface around a Kodi-inspired handheld media-centre layout.
- Set all in-app labels and muOS launcher metadata to English.
- Added a dashboard with icon-led destinations for Watch TV, Local Library, Add-ons, Sources and Settings.
- Unified all channels, favourites, search, groups and the EPG timeline inside Watch TV.
- Added asynchronous M3U `tvg-logo` downloads, local caching and TV-icon fallbacks.
- Grouped playlist and XMLTV source management under Sources; moved About to the bottom of Settings.
- Added a skippable, configurable RintrofliX boot animation.
- Added a local video library with user-selected roots and on-demand folder browsing.
- Added a local add-on manager with manifest/API checks, explicit enable confirmation and safe archive extraction limits.
- Reworked the MPV OSD: A toggles pause/resume, D-pad left/right zaps channels, SELECT opens the player menu, START displays controls and current/next EPG.
- Added real MPV volume readback and mute state in the OSD.
- Optimised the background and logo rendering for the handheld CPU.
- Preserved local settings migration from VoidCast 2.2 without deleting the old app data or shipping personal playlist URLs.
- Corrected the framebuffer flip/update restoration when handing the display to and from MPV.

## 1.0.0

Initial independent RintrofliX package based on the VoidCast 2.2 technical engine.

## 2.1.0 — Visual refinement

- Refined the global midnight-blue palette with a restrained cyan ambient glow and subtle star texture.
- Reworked shared panels and dashboard cards with deeper shadows, cleaner outlines, and clearer focus hierarchy.
- Kept the visual effects pre-rendered or lightweight for the H700 handheld target.
- No IPTV, EPG, player, add-on, or configuration migration behavior was intentionally changed.

## 2.2.0 — Dashboard layout redesign

- Rebuilt the home dashboard hierarchy with a shorter hero panel, a dedicated status row, and a balanced destination grid.
- Settings now spans the full final row, giving the fifth destination deliberate visual weight instead of leaving an awkward empty card slot.
- Tightened vertical spacing so all five destinations remain above the footer on the native 640×480 display.
- Home status now distinguishes a configured playlist from the first-run/no-source state.
- IPTV, EPG, playback, add-on, and settings behavior is unchanged.

## 2.3.0 — Contextual screen redesign

- Sources, Local Library, Add-ons and Settings now use a consistent two-column layout with contextual detail panels.
- Source management surfaces active playlist, loaded channel count, XMLTV source count and indexed guide keys.
- Local Library explains the selected path's availability and reiterates on-demand browsing without recursive SD-card scans.
- Add-ons show selected package metadata, enable state and explicit Python-code trust warnings.
- Settings provide a live explanation and current value for every preference while keeping About as the final entry.
- Footer hints and panel geometry are aligned to the 640×480 handheld display.

## 2.4.0 — Add-on API v2 and source providers

- Preserved API v1 as actions/toasts/logging/settings only.
- Added API v2 `register_source(source_id, label, loader, play=None)`.
- Aggregated enabled add-on source channels into Watch TV, search, groups and favourites.
- Added playback routing hook so a source add-on can handle its own channel playback; returning `True` prevents fallback playback, while `False`/`None` delegates to MPV/FFplay.
- Added source ID validation, duplicate-source protection, Channel type validation and isolated provider/playback errors.
- Reworked the Add-on SDK with v1/v2 compatibility and a complete source-provider example.
- Added regression tests for API v1 restrictions, API v2 channel registration and playback routing.

## 2.5.0 — Add-on compatibility and dependency management

- Add-on manifests can declare minimum/maximum-compatible RintrofliX versions and versioned add-on dependencies.
- Enabling an add-on checks all declared requirements before importing its Python entry point.
- Disabling a dependency is blocked while enabled add-ons still require it.
- Runtime loading isolates incompatible extensions and records a diagnostic instead of executing them.
- Add-ons UI shows API version and compatibility problems in the detail panel.
- API v1 remains actions-only; API v2 source registration and playback routing are unchanged.

## 2.6.0 — HTTPS repository foundation

- Added a repository client for versioned JSON indexes over HTTPS.
- Repository entries validate IDs, versions, HTTPS package URLs and SHA-256 digests.
- Package downloads are size-bounded and digest-checked before the existing safe archive installer is called.
- Repository URLs are stored in configuration for the next UI integration step.
- SHA-256 detects corruption or index/package mismatch; it is not publisher authentication. Signed repository metadata remains a separate future security milestone.
