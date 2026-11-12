# Source import status

> [!WARNING]
> This repository is not yet a complete application source mirror. Do not use the current main branch as a release/build source until every required runtime file and the release verification suite have been imported and CI is green.

## Imported modules

| Path | Status | Responsibility |
|---|---|---|
| rintroflix/__init__.py | ✅ Imported | Package version |
| rintroflix/config.py | ✅ Imported | Persistent settings and VoidCast migration |
| rintroflix/net.py | ✅ Imported | Bounded HTTP(S) downloads and cache |
| rintroflix/input.py | ✅ Imported | muOS evdev controller input |
| rintroflix/m3u.py | ✅ Imported | M3U/M3U8 parsing and channel metadata |
| rintroflix/epg.py | ✅ Imported | XMLTV guide parsing and matching |
| rintroflix/addons.py | ✅ Imported | Add-on API v1/v2, validation and lifecycle |
| rintroflix/repository.py | ✅ Imported | HTTPS index and SHA-256 package verification |
| rintroflix/fbdisplay.py | ✅ Imported | Optional framebuffer presentation |
| lib/glyph_install.sh | ✅ Imported | muOS theme glyph installation |
| mux_launch.sh | ⚠️ Imported; review required | muOS launcher and runtime discovery |
| rintroflix/main.py | ⏳ Pending | Main application and screen workflows |
| rintroflix/ui.py | ⏳ Pending | Pygame interface |
| rintroflix/player.py | ⏳ Pending | MPV IPC, playback OSD and controls |
| rintroflix/logos.py | ⏳ Pending | Asynchronous channel-logo cache |

## Remaining source assets and verification

| Item | Status |
|---|---|
| Cabin font files and font licence | ⏳ Pending |
| App glyph and artwork | ⏳ Pending |
| Add-on SDK and architecture source documents | ⏳ Pending |
| Automated tests (tests/test_core.py) | ⏳ Pending |
| Release builder (tools/build_release.py) | ⏳ Pending |
| 2.6.0 .muxapp and source archive generation in CI | ⏳ Pending |
| Device validation on RG35XX H / H700 | ⏳ Not run in this environment |

## Import rules

- Keep the known personal playlist URL out of source, fixtures, logs and release artifacts.
- Keep TLS certificate verification enabled.
- Treat add-ons as trusted Python code, not sandboxed extensions.
- A repository package digest checks integrity against its index; it does not authenticate the publisher.
- Do not publish a release from a partial source tree.

## Next integration milestone

Import the remaining UI/player modules and assets, then add the complete test suite and release builder. Only after that should CI run Python compilation, unit tests, shell validation, archive CRC/content checks and the private-URL scan before producing a .muxapp.
