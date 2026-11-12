# Controller controls

RintrofliX is designed around controller navigation on a compact 640×480 handheld display. The tables below describe the documented 2.6.0 baseline.

## Watch TV

| Input | Action |
|---|---|
| D-pad | Navigate channels, cards and guide rows |
| A | Open / confirm / play |
| B | Back |
| X | Search or edit channel search |
| Y | Toggle favourite |
| L1 / R1 | Previous / next channel group |
| SELECT | Cycle All → Favourites → Search → TV Guide |
| START | Show selected-channel details |

## MPV player overlay

| Input | Action |
|---|---|
| A | Pause / resume |
| D-pad Left / Right | Previous / next channel |
| D-pad Up / Down | Seek ±30 seconds |
| L1 / R1 | Volume −/+ 5 |
| X | Mute / unmute |
| SELECT | Player menu |
| START | Transport strip and now/next |
| L2 / R2 | Seek ±10 seconds |
| B | Close menu or exit playback |
| Y | Toggle favourite |

> [!NOTE]
> The volume OSD reads MPV's player volume and mute state. It is not a readout of the global muOS mixer.

## If a control does not behave as expected

- Check that the correct input profile is active for the device and firmware.
- Test the same control in the muOS frontend to separate device mapping from application behavior.
- Report the exact device model, muOS version and application baseline.

