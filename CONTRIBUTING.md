# Contributing to RintrofliX

Thanks for helping improve RintrofliX! The project is designed for a constrained handheld environment, so reliability and readability matter as much as features.

## Before opening a pull request

1. Search existing issues and pull requests.
2. Describe the device, muOS release and runtime involved.
3. Keep UI text in English.
4. Prefer small, testable changes with clear failure handling.
5. Update the handbook when behaviour, controls, APIs or compatibility change.
6. Never include personal playlist URLs, credentials, tokens or private EPG endpoints.

## Documentation workflow

The handbook uses MkDocs Material.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-docs.txt
mkdocs serve
```

Build the strict production site with:

```bash
mkdocs build --strict
```

## Pull request checklist

- [ ] The change has a clear purpose and scope.
- [ ] User-facing strings are English.
- [ ] Tests or reproducible verification steps are included.
- [ ] Documentation and diagrams are updated.
- [ ] No private URLs, credentials or copyrighted assets were added without permission.
- [ ] Hardware-dependent behaviour is labelled as tested or untested accurately.

## Device testing

When reporting a device test, include the exact device model, muOS version, runtime, playback backend and steps performed. Do not describe emulator or host-only checks as physical-device validation.
