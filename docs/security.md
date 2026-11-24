# Security & trust 🔐

RintrofliX handles user-supplied playlist URLs, network responses, downloaded artwork, repository metadata and third-party Python add-ons. These surfaces have different risk profiles.

## Security controls in the 2.6.5 candidate

| Surface | Control | Limitation |
|---|---|---|
| HTTPS repository transport | TLS certificate validation plus final-URL HTTPS enforcement after redirects; repository URLs with embedded credentials are refused | Does not authenticate the repository publisher |
| Media network reads | Bounded HTTP(S) downloads | A trusted endpoint can still serve bad content |
| Add-on archives | Path/type/size validation | Not a sandbox or malware scanner |
| Add-on loading | Disabled until explicit enable | Enabled code runs with app permissions |
| Repository packages | SHA-256 compared with the index | Does not authenticate the index publisher |

## Trust model

\`\`\`mermaid
flowchart TD
    A[Repository URL] --> B[HTTPS transport]
    B --> C{Final URL still HTTPS and credential-free?}
    C -- No --> X[Reject redirect]
    C -- Yes --> D[Parse bounded index]
    D --> E[Read package URL + SHA-256]
    E --> F[Download bounded package over HTTPS]
    F --> G{Digest matches?}
    G -- No --> H[Reject package]
    G -- Yes --> I[Pass to archive validator]
    I --> J[Install disabled]
    J --> K[User explicitly enables]
    K --> L[Python code runs with app permissions]
\`\`\`

The repository client asks the built-in downloader to enforce HTTPS on both the requested URL and the final URL returned after urllib follows redirects. A repository index or package endpoint that redirects to plain HTTP, omits a hostname or embeds URL credentials is rejected before its response body is accepted. This strict option is limited to repository downloads: ordinary IPTV/media URLs continue to support HTTP where a user-supplied source requires it.

## Safe-use guidance

!!! danger "Treat add-ons as executable code"
    Only enable add-ons whose source and maintainer you trust. The current package manager does not sandbox Python.

!!! warning "Repository hashes do not authenticate publishers"
    A SHA-256 digest protects against mismatch between an index entry and downloaded package bytes. Publisher signatures and pinned trust keys are not implemented in this candidate.

- Never put private playlist URLs, credentials or tokens in source control.
- Do not disable TLS verification to work around certificate errors.
- Prefer HTTPS sources and inspect add-on permissions before enabling.
- Report security issues privately to the repository maintainer rather than posting exploitable details publicly.
