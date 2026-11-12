# RintrofliX Architecture

RintrofliX is structured as a handheld media-centre application with replaceable
presentation and playback layers. The current interface is Python + Pygame/SDL2;
Lua/LÖVE is deliberately not a runtime dependency.

## Layers

### muOS integration

- `mux_launch.sh` resolves the available Python/Pygame runtime and launches the app.
- `lib/glyph_install.sh` installs the app glyph into the active muOS theme when possible.
- `fbdisplay.py` provides a framebuffer presentation path for the VoidDesk Pygame wheel
  and restores SDL display functions when the video player takes over the display.

### Presentation

- `ui.py` owns drawing primitives, fonts, icons, cards, panels, menus, focus states,
  layout measurements and themes.
- `main.py` owns the screen stack, navigation, user workflows and application lifecycle.
- Screens call application actions; they do not implement M3U parsing, XMLTV parsing,
  HTTP downloading or MPV IPC.

### Media and source services

- `m3u.py` parses playlists and channel metadata.
- `epg.py` parses XMLTV and resolves current/next programmes.
- `net.py` handles bounded network fetches and cache operations.
- `logos.py` downloads and caches `tvg-logo` artwork asynchronously. Image surfaces
  are created on the Pygame/UI thread.
- `config.py` owns persistent settings and the one-time VoidCast 2.2 migration.

### Playback adapter

- `player.py` is the playback boundary used by the application coordinator.
- MPV is the full-featured backend and owns the video display while playing.
- Player controls, volume readback, transport OSD and the navigable player menu are
  sent through MPV's JSON IPC socket.
- FFplay is a basic fallback; it does not implement the complete RintrofliX OSD.

### Extensions

- `addons.py` manages local `.rfxaddon` packages and the API described in `ADDON_SDK.md`.
- Add-ons are disabled until the user explicitly enables them. Python add-ons are not
  sandboxed and therefore must come from trusted sources.

## Replacing the frontend later

A future frontend (including a Lua/LÖVE implementation) should keep the following
boundaries:

1. Use the same persistent configuration and media service modules, or replace them
   behind equivalent service interfaces.
2. Present channel, EPG, library and add-on data as view models; do not duplicate
   network/parser logic inside screen widgets.
3. Delegate playback to the playback adapter and consume its transport/volume events.
4. Keep controller input mapping in the platform/input adapter, not in individual
   catalogue widgets.

This keeps a future visual rewrite independent from the M3U/XMLTV engine, logo cache,
add-on package manager and player command protocol. It does not claim that a Lua
frontend exists in this release.

## Target profile

- muOS Andromeda 2606.0
- Anbernic RG35XX H / H700
- 640×480 landscape panel
- Gamepad-first navigation, 30 FPS UI loop
