# Source import status

> [!WARNING]
> This repository is still a **partial source mirror**, not a release-equivalent archive of the verified upstream RintrofliX working tree. The application modules and a version-matched muOS package builder are present, but artwork/fonts and full upstream parity still require review. Do not publish a stable release until that comparison and device qualification are complete.

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
| rintroflix/main.py | ✅ Imported | Main application and screen workflows |
| rintroflix/ui.py | ✅ Imported | Pygame interface |
| rintroflix/player.py | ✅ Imported | MPV IPC, playback OSD and controls |
| rintroflix/logos.py | ✅ Imported | Asynchronous channel-logo cache |

## Automated checks

The repository has two independent workflows:

- [Handbook build and deployment](https://github.com/SilverCrow2323/rintroflix-muos/actions/workflows/docs.yml) — MkDocs strict build and GitHub Pages deployment.
- [Source sanity checks](https://github.com/SilverCrow2323/rintroflix-muos/actions/workflows/source-checks.yml) — required runtime entry points, Python compilation, unit and package-builder tests, muOS .muxapp build/archive verification, shell syntax and imported core-module checks.

### Verified run — 27 November 2026

[Source sanity run #45972545453](https://github.com/SilverCrow2323/rintroflix-muos/actions/runs/45972545453) completed successfully on `feat/addon-actual-byte-budget`:

- Runtime entry points and imported core modules were present.
- Python application and test sources compiled.
- Add-on archive validation and staging tests passed.
- Shell scripts passed syntax validation.
- The CI package workflow verified the .muxapp builder and archive-safety path.

A green source workflow establishes only the checks actually run against the mirrored subset. It does not establish full upstream parity, publisher authenticity for add-ons or physical-device behavior.

## Remaining source assets and verification

| Item | Status |
|---|---|
| Cabin font files and font licence | ⏳ Pending |
| App glyph and artwork | ⏳ Pending |
| Add-on SDK, architecture, changelog and build report | ✅ Imported |
| Automated parser, add-on and package-builder tests | ✅ Present and exercised by CI |
| muOS package builder (tools/build_muxapp.py) | ✅ Present and exercised by CI |
| CI .muxapp build and archive-safety checks | ✅ Verified in the 27 November run |
| Full comparison against the verified upstream 2.6.4 working tree | ⏳ Pending |
| Device validation on RG35XX H / H700 | ⏳ Not run in this environment |

## Import rules

- Keep private playlist URLs out of source, fixtures, logs and release artifacts.
- Keep TLS certificate verification enabled.
- Treat add-ons as trusted Python code, not sandboxed extensions.
- A repository package digest checks integrity against its index; it does not authenticate the publisher.
- Do not publish a release from a partial source tree.

## Next integration milestone

Import the remaining licensed artwork/font assets, then compare the mirrored runtime and packaging contents against the verified upstream 2.6.4 working tree. After that, qualify installation, playback, controller navigation, add-on lifecycle and storage behavior on the RG35XX H/H700. Device qualification remains separate from CI.
