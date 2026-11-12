# Installation and first launch

This page describes the documented muOS installation path for the 2.6.0 application baseline. Confirm that a complete release package exists before attempting installation.

> [!IMPORTANT]
> **MUST KNOW!!** The repository README says the GitHub source mirror is incomplete. Do not treat the source ZIP as a runnable `.muxapp`. Use a complete, versioned package from [Releases](https://github.com/SilverCrow2323/rintroflix-muos/releases) only when one is published.

## Install a complete package

1. Copy the published `RintrofliX.muxapp` to the SD card's `ARCHIVE/` folder.
2. Open **Applications → Archive Manager** in muOS.
3. Install the package.
4. Launch **Applications → RintrofliX**.

## First-run checklist

- Confirm Python 3 and Pygame are available.
- Confirm MPV is installed for the complete player overlay.
- Add an M3U/M3U8 playlist that you are authorised to use.
- Add an XMLTV guide source when the playlist does not provide one.
- Check channel groups, logos and programme matching.
- Test volume, mute, channel changes and exit behaviour.
- Enable only trusted add-ons.

## Runtime lookup

The documented launcher searches for Python 3 and Pygame in this order:

1. System runtime.
2. Pygame runtime installed by Void Desk.
3. Legacy Void Desk chroot.

MPV is the primary playback backend. FFplay is a basic fallback and does not provide the full MPV overlay.

See [Controls](Controls) and [Troubleshooting](Troubleshooting).
