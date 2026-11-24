# RintrofliX 2.6.5 — Build report

## Scope

Security hardening for add-on repository downloads, regression coverage for repository/network boundaries, and alignment of the release metadata/build workflow.

## Changes in this candidate

- Keep repository index and package downloads HTTPS-only after redirect resolution; reject an HTTP final URL.
- Preserve ordinary HTTP support for user-configured IPTV/media sources.
- Add host-side regression tests for redirect handling, repository index validation, package digest verification and package identity checks.
- Run the regression suite in both the source-check and package-build workflows.
- Derive the package builder default output filename from the tracked VERSION file.

## Verification status

- Source changes and test cases are committed to the candidate branch.
- GitHub Actions has not yet reported a result for this candidate at the time this report was prepared.
- Physical RG35XX H/H700 installation, controller mapping, display, playback and extended stability remain unverified.

## Security boundary

SHA-256 verifies that downloaded package bytes match the digest in the fetched index. It does not authenticate the index publisher. Signed metadata and pinned publisher keys are not claimed as implemented. Add-on Python code remains unsandboxed.
