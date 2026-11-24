# Source import status

> [!WARNING]
> The repository now contains the core Python application modules, muOS launcher, add-on services and a MUX package builder. It is still an incomplete mirror of the full working application: runtime artwork/font/glyph assets are not present in the tracked tree, and automated coverage is being rebuilt. Do not treat a green source compile as device certification.

## Imported runtime and tooling

| Path | Status | Responsibility |
|---|---|---|
| rintroflix/main.py | ✅ Imported | Main application and screen workflows |
| rintroflix/ui.py | ✅ Imported | Pygame interface, drawing primitives and focus states |
| rintroflix/player.py | ✅ Imported | MPV IPC, playback OSD and controls |
| rintroflix/config.py | ✅ Imported | Persistent settings and VoidCast migration |
| rintroflix/net.py | ✅ Imported | Bounded HTTP(S) downloads and cache |
| rintroflix/input.py | ✅ Imported | muOS evdev controller input |
| rintroflix/m3u.py | ✅ Imported | M3U/M3U8 parsing and channel metadata |
| rintroflix/epg.py | ✅ Imported | XMLTV guide parsing and matching |
| rintroflix/addons.py | ✅ Imported | Add-on API v1/v2, validation and lifecycle |
| rintroflix/repository.py | ✅ Imported | HTTPS index and SHA-256 package verification |
| rintroflix/fbdisplay.py | ✅ Imported | Optional framebuffer presentation |
| rintroflix/logos.py | ✅ Imported | Asynchronous channel-logo cache |
| lib/glyph_install.sh | ✅ Imported | muOS theme glyph installation helper |
| mux_launch.sh | ✅ Imported | muOS launcher and runtime discovery |
| tools/bootstrap_runtime.py | ✅ Imported | Runtime bootstrap helper |
| tools/build_muxapp.py | ✅ Imported | Installable muOS MUX package builder |

## Regression coverage

The 2.6.5 candidate adds a standard-library unittest suite under tests/:

- tests/test_net.py — HTTPS redirect downgrade rejection, normal HTTPS redirects, and preservation of ordinary HTTP media support.
- tests/test_repository.py — HTTPS URL validation, relative package URL resolution, duplicate-ID and digest validation, digest mismatch refusal, and package identity handling.

GitHub Actions runs the suite alongside Python compilation, shell syntax checks and package construction. The tests are host-side checks; they do not prove muOS rendering, controller mappings, playback or long-session stability.

## Remaining source and release gates

| Item | Status |
|---|---|
| Core Python UI/player and service modules | ✅ Tracked |
| muOS launcher and MUX package builder | ✅ Tracked |
| Standard-library repository/network regression tests | ✅ Added in 2.6.5 candidate; CI result pending |
| Runtime font files and associated font licence | ⏳ Not present in the tracked tree |
| Device-app glyph and full runtime artwork bundle | ⏳ Not present in the tracked tree; docs brand mark is not a device asset pack |
| Full package-content/asset verification | ⏳ Needs dedicated packaging assertions |
| Physical RG35XX H / H700 validation | ⏳ Not run in this environment |
| Signed repository metadata / publisher identity | ⏳ Future security milestone |

## Import and release rules

- Keep private playlist URLs out of source, fixtures, logs and release artifacts.
- Keep TLS certificate verification enabled.
- Treat add-ons as trusted Python code, not sandboxed extensions.
- A package digest checks integrity against its index; it does not authenticate the publisher.
- Do not publish a release from an incomplete asset tree or without physical-device acceptance.

## Next integration milestone

Complete the runtime font/glyph/artwork import with licence provenance, add package-content assertions for every required runtime asset, then validate installation, display, input and playback on a physical RG35XX H/H700 running the documented muOS version.
