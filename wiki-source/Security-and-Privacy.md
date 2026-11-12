# Security and privacy

RintrofliX handles playlist URLs, network responses, downloaded artwork, repository metadata and third-party Python add-ons. Treat each source according to its trust level.

## Safe-use basics

- Use HTTPS sources where available.
- Keep TLS certificate verification enabled.
- Do not commit private playlist URLs, credentials or tokens.
- Add only extensions from maintainers you trust.
- Review an add-on before enabling it.
- Keep diagnostic logs free of personal URLs and account details.

> [!IMPORTANT]
> **MUST KNOW!!** Enabled add-on code runs with application permissions. The current add-on system does not provide a Python sandbox.

## Repository integrity

The documented repository foundation checks downloaded package bytes against a SHA-256 digest in the index.

- A matching digest detects a package/index mismatch.
- A digest does not prove who published the index.
- Signed publisher metadata and pinned trust keys are future work in the 2.6.0 baseline.

## Content and sources

RintrofliX does not provide a personal TV playlist or paid content subscription. Configure only playlists and streams you are authorised to access.

See the [security reference](https://github.com/SilverCrow2323/rintroflix-muos/blob/main/docs/security.md).
