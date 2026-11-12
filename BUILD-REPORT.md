# RintrofliX 2.6.0 — Build report

## Scope

Repository service foundation for add-on distribution. Existing API v1/v2, source registration, playback routing, dependency checks and local package installation are retained.

## Changes

- HTTPS-only repository index retrieval using the existing TLS-verifying downloader.
- Versioned JSON index validation (`format: 1`), unique add-on IDs, version validation and HTTPS package URL enforcement.
- Bounded package download and SHA-256 verification before handing bytes to the existing safe archive installer.
- Repository URL configuration slot added for subsequent UI integration.

## Security boundary

SHA-256 verifies that downloaded package bytes match the digest in the fetched index. It does not authenticate the index publisher. Signed metadata and pinned publisher keys are not claimed as implemented in this release. Add-on Python code remains unsandboxed.

## Verification

Host unit tests cover HTTPS enforcement, index parsing, URL resolution and digest mismatch rejection. Hardware rendering and RG35XX H playback are not covered by host tests.
