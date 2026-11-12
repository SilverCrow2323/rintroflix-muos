# Installation & controls 🎮

This guide describes the muOS installation flow for the 2.6.0 application baseline. Confirm the package version before installing.

## Install

1. Copy `RintrofliX.muxapp` into the microSD card's `ARCHIVE` folder.
2. Open **Applications → Archive Manager** and install the package.
3. Launch **Applications → RintrofliX**.
4. Open **Sources → Playlists** and add an M3U/M3U8 URL or a local playlist file.
5. Add XMLTV URLs under **Sources → TV guide data**, if they are not already declared in the playlist.

!!! info "Runtime lookup"
    The launcher checks Python 3 + Pygame in this order: system runtime, Pygame runtime installed by VoidDesk, then the legacy VoidDesk chroot.

## First-run checklist

- [ ] Confirm Python 3 and Pygame are available.
- [ ] Confirm MPV is installed for full player-overlay support.
- [ ] Add a playlist you are authorised to use.
- [ ] Check that channel groups and logos load.
- [ ] Add an XMLTV source and verify programme matching.
- [ ] Test volume, mute, channel navigation and exit behaviour.
- [ ] Add only trusted add-ons.

## Main interface

| Control | Action |
|---|---|
| D-pad | Navigate |
| A | Open / confirm / play |
| B | Back |
| X | Search in Watch TV |
| Y | Toggle favourite |
| L1 / R1 | Previous / next group |
| SELECT | Cycle Watch TV tabs |
| START | Channel details |

## MPV player

| Control | Action |
|---|---|
| A | Pause / resume |
| D-pad Left / Right | Previous / next channel |
| D-pad Up / Down | Seek ±30 seconds |
| L1 / R1 | Volume ±5 |
| X | Mute |
| SELECT | Player menu |
| START | Transport / now-next |
| L2 / R2 | Seek ±10 seconds |
| B | Close menu / exit playback |
| Y | Toggle favourite |

## Troubleshooting

??? question "The app opens but the screen stays blank"
    Check the Python/Pygame runtime and the launcher log. Also confirm that the installed package matches the device architecture and muOS release.

??? question "The video plays but the full overlay is missing"
    The complete overlay depends on MPV IPC support. FFplay is only a basic fallback.

??? question "A channel has no programme information"
    Check the playlist's `tvg-id`, the XMLTV source URL and the EPG matching rules. Some providers use different channel identifiers.

??? question "The volume indicator does not match the device volume"
    The in-player OSD reports MPV volume. It is not a readout of the global muOS mixer.
