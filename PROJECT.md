# Project: RintrofliX for muOS

## Purpose
Build a controller-first media centre for muOS handhelds, focused on live-TV playlists, a local video library, add-on providers, source management and playback controls on 640×480 H700-class devices.

## Users and use cases
- RG35XX H/H700 muOS owners navigating media with a D-pad and face buttons.
- Maintainers integrating playback, playlist/EPG parsing, add-on repositories and .muxapp packaging.
- Add-on authors using the versioned SDK and explicit activation model.

## Scope and boundaries
In scope: Python application UI/services, MPV integration, user-configured IPTV/local sources, EPG, add-on archive validation and explicit activation, and muOS package building.

Out of scope: bundled private playlists or credentials, DRM circumvention, claims that add-ons are sandboxed, and treating SHA-256 integrity as publisher authentication. Add-ons execute Python with application permissions when enabled. The GitHub mirror README explicitly states that the source tree is still being recovered; a passing partial build is not proof that the full 2.6.x working tree has been imported.

## Target
- muOS on Anbernic RG35XX H / Allwinner H700, 640×480.
- Controller-first operation and bounded memory/storage behavior.
- Python runtime, MPV and a self-contained .muxapp package.

## Architecture
- UI/input: focus-driven navigation and localization.
- Media services: M3U/playlist parsing, EPG/XMLTV, source providers and playback orchestration.
- Add-on manager: manifest validation, bounded archives, dependency checks and explicit enable/disable.
- Repository layer: HTTPS indexes, digest checks and repository metadata.
- Packaging: staged RintrofliX/ archive with launcher, resources and runtime bootstrap.

## Dependencies and integrations
muOS MUX launcher and runtime bootstrap; MPV IPC/playback; Python application modules; external IPTV/EPG sources selected by the user. Repository URLs and add-on archives are untrusted input. Publisher signatures and trust-key management are not part of the stated 2.6.0 baseline.

## Safety, accessibility and localization
Keep TLS verification enabled, bound network and archive reads, reject traversal/symlinks, never log credentials, and clearly warn that enabled add-ons run as Python code. The UI must remain usable with a controller and legible at 640×480. Keep source/docs in English and user-configurable media data out of source control.

## Verified baseline
The repository tracks the application framework, docs, add-on SDK, launcher and package builder. Existing CI compiles source and builds a .muxapp artifact. The README marks the source mirror as incomplete, and physical muOS playback qualification remains unverified.
