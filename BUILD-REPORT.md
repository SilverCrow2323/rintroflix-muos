# RintrofliX 2.6.5 — Build report

## Scope

Security hardening for add-on repository downloads, regression coverage for repository/network boundaries, and alignment of the release metadata/build workflow.

## Changes in this candidate

- Keep repository index and package downloads HTTPS-only after redirect resolution; reject an HTTP final URL.
- Preserve ordinary HTTP support for user-configured IPTV/media sources.
- Add 12 host-side regression tests for redirect handling, repository index validation, package digest verification, and package identity checks.
- Run the regression suite in both source-check and MUX package CI.
- Derive the package builder default output filename from the tracked VERSION file.
- Align the build workflow upload path with the versioned 2.6.5 output filename.

## Verification

- Source-check run [#45326736972](https://github.com/SilverCrow2323/rintroflix-muos/actions/runs/45326736972): passed Python compilation, 12 unit tests and shell syntax checks.
- Package run [#45326764767](https://github.com/SilverCrow2323/rintroflix-muos/actions/runs/45326764767): passed source validation, all 12 tests, MUX package construction and artifact upload.
- Built package: 65,679 bytes, 25 files.
- GitHub Actions artifact: [RintrofliX-2.6.5-muOS](https://github.com/SilverCrow2323/rintroflix-muos/actions/runs/45326764767/artifacts/14889059983), artifact ID 14889059983. This is a retained CI artifact, not a published GitHub Release.
- Physical RG35XX H/H700 installation, controller mapping, display, playback and extended stability remain unverified.

## Security boundary

SHA-256 verifies that downloaded package bytes match the digest in the fetched index. It does not authenticate the index publisher. Signed metadata and pinned publisher keys are not claimed as implemented. Add-on Python code remains unsandboxed.
