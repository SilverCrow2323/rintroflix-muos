# Changelog 📦

This page summarises the documented application baseline. It is not a substitute for release artifacts or commit history.

## 2.6.5 — HTTPS repository redirect hardening

- Repository index and package downloads now reject redirects whose final URL is not HTTPS.
- The HTTPS-only transport rule is scoped to add-on repository traffic; user-configured HTTP media sources remain supported.
- Added standard-library regression tests for redirect downgrade rejection, HTTPS redirects, repository index validation and package digest/identity checks.
- Source and package workflows now run the regression suite.
- The package builder derives its default artifact filename from the tracked VERSION file.

## 2.6.0 — Repository service foundation

- Added HTTPS-only repository index handling.
- Added bounded index/package downloads.
- Added SHA-256 package integrity checks before installation.
- Added repository index validation and relative package URL resolution.
- Publisher signatures and a full repository-management UI are not included.

## 2.5.0 — Add-on compatibility

- Added application-version and add-on dependency constraints.
- Prevented disabling dependencies required by enabled add-ons.
- Added compatibility diagnostics before extension code is loaded.

## 2.4.x — Add-on API v2

- Added source registration and a playback hook for API v2.
- Preserved API v1 as an actions-only contract.

## Earlier visual direction

- Dark media-centre visual identity with cyan, violet, amber and crimson accents.
- Larger Cabin typography, taller selection rows and clearer focus states.
- Skippable boot animation and scalable UI.
- Shared two-column contextual layouts for secondary screens.
