# Add-ons

Add-ons extend RintrofliX through explicit versioned APIs. The manager validates package metadata and dependencies before loading an extension.

## Install and enable

1. Obtain a local `.rfxaddon` or supported `.zip` package from a source you trust.
2. Install it through the add-on manager.
3. Review the add-on metadata and declared dependencies.
4. Enable it explicitly when you are ready to run its code.

## API versions

| Capability | API v1 | API v2 |
|---|---:|---:|
| Register actions | Yes | Yes |
| Show toast notifications | Yes | Yes |
| Namespaced settings | Yes | Yes |
| Register channel sources | No | Yes |
| Join the playback hook | No | Yes |

API v2 is required for source-provider registration and playback hooks. API v1 remains action-oriented.

> [!IMPORTANT]
> **MUST KNOW!!** Add-ons are Python code. They are not sandboxed. Once enabled, an add-on runs with the application's permissions. Archive validation is not malware detection.

## Before enabling

- Check the add-on ID, version and maintainer.
- Review declared dependencies.
- Prefer code you can inspect.
- Disable or remove extensions you no longer trust.

See the [Add-on SDK](https://github.com/SilverCrow2323/rintroflix-muos/blob/main/docs/addons.md) for the complete contract.
