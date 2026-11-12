# Wiki source and publishing

The `wiki-source/` folder is the canonical source for short practical pages. The MkDocs site under `docs/` remains the detailed documentation reference.

## Page rules

- One topic per page.
- Start with a short explanation of what the topic is and when it is useful.
- Keep each bullet to one concept.
- Use **MUST KNOW!!** only for required safety, prerequisite or compatibility information.
- Use **Optional** only for non-essential enhancements.
- Leave basic concepts unlabelled.
- Keep code examples copyable and grounded in the documented 2.6.0 baseline.
- Do not imply that the partial source mirror is a complete application package.

## First-time Wiki activation

1. Open the [RintrofliX GitHub Wiki](https://github.com/SilverCrow2323/rintroflix-muos/wiki).
2. Create a page named **Home** and save a short draft.
3. From a clone with Git credentials, run `sh tools/publish_wiki.sh`.

The publisher copies reviewed Markdown pages from `wiki-source/` to the GitHub Wiki. Edit the source files here, not only the live Wiki.

## Detailed references

- [Installation](../docs/installation.md)
- [Features](../docs/features.md)
- [Architecture](../docs/architecture.md)
- [Add-on SDK](../docs/addons.md)
- [Security](../docs/security.md)
