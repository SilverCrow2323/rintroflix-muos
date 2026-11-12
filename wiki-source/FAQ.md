# FAQ

## Is RintrofliX a TV subscription?

No. It is a media-player interface. It does not ship a personal playlist URL or paid content service. Add only media sources you are authorised to access.

## Is the GitHub source mirror complete?

Not yet. The repository README identifies the 2.6.0 source mirror as a partial import. Core UI/player modules, artwork/fonts, tests and the release builder still need to be imported.

## What device is the UI designed for?

The documented target is the Anbernic H700 handheld family, with a 640×480 display class. Physical validation on the RG35XX H / muOS remains pending in the documented baseline.

## Which playlist formats are supported?

M3U and M3U8 playlists, local or HTTPS/HTTP sources. The application reads channel metadata such as `tvg-id`, `tvg-name`, `tvg-logo` and `group-title`.

## Where does programme information come from?

XMLTV/EPG sources. Add the guide URL in Sources and check channel ID matching when data is missing.

## Are add-ons sandboxed?

No. Archive validation checks package structure and size, but enabled add-on Python code runs with the application's permissions. Only enable add-ons from sources you trust.

## Does SHA-256 authenticate an add-on publisher?

No. It checks that downloaded bytes match the digest in the repository index. Signed publisher metadata and pinned trust keys are not implemented in the documented 2.6.0 baseline.
