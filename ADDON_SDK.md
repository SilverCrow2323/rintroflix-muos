# RintrofliX Add-on SDK · API 2

RintrofliX supports two extension API generations. API v1 is deliberately limited
to labelled actions, notifications, logging and namespaced settings. It cannot
register/inject channel sources and cannot intercept playback. Add-ons that add
sources **must declare `api_version: 2`**.

Add-ons are disabled by default. Enabling one imports and executes its Python
entry point. Python extensions are not sandboxed: only enable code from sources
you trust.

## Manifest

```json
{
  "id": "sample-source",
  "name": "Sample Source",
  "version": "1.0.0",
  "api_version": 2,
  "entrypoint": "addon.py",
  "description": "An example channel source",
  "capabilities": ["source", "playback"],
  "requires": {
    "rintroflix": ">=2.5.0",
    "addons": {"shared-auth": ">=1.2.0"}
  }
}
```

`id` must be lowercase and unique. `entrypoint` must be a relative `.py` path
inside the package. API versions 1 and 2 are accepted; v1 packages continue to
work but do not receive source-registration methods. The optional `requires`
object can declare a `rintroflix` version constraint and an `addons` map of
required add-on IDs to version constraints. Supported operators are `>=`, `<=`,
`==`, `>`, `<` and `~=`. An add-on cannot be enabled until all requirements
are satisfied; a required add-on cannot be disabled while enabled dependants remain.

## API v1: actions only

```python
def register(api):
    def show_status():
        api.toast("The add-on is working")
        api.log("status action executed")
    return [{"label": "Show status", "action": show_status}]
```

## API v2: register a channel source

A source loader returns an iterable of `rintroflix.m3u.Channel` objects. The
application aggregates channels from the core playlist and all enabled sources
inside Watch TV, search and favourites. A source ID is attached to each provided
channel for routing playback back to its owning add-on.

```python
from rintroflix.m3u import Channel

def register(api):
    def load_channels():
        return [
            Channel(
                name="Example Live",
                url="plugin://example/live",
                tvg_id="example.live",
                group="Example Source",
            )
        ]

    def play_channel(channel):
        api.toast("Opening " + channel.name)
        return True

    api.register_source(
        source_id="example-source",
        label="Example Source",
        loader=load_channels,
        play=play_channel,
    )
    return []
```

`api.register_source(source_id, label, loader, play=None)` is API v2 only.

- `source_id`: unique lowercase source identifier.
- `label`: user-facing source name.
- `loader()`: returns `Channel` objects; it is called when Watch TV builds its
  channel catalogue. Keep it fast and use the add-on's own cache for network data.
- `play(channel)`: optional playback hook. Return exactly `True` when the add-on
  has taken responsibility for playback. Return `False` or `None` to delegate to
  the built-in MPV/FFplay player. Exceptions are logged and surfaced as an error;
  the core player is not launched after a hook exception.

## Shared API methods

- `api.toast(message, ok=True)` — show a short notification.
- `api.log(message)` — write a namespaced application log entry.
- `api.get_setting(key, default=None)` / `api.set_setting(key, value)` — persist
  settings under the add-on's own namespace.
- `api.channels()` — read-only tuple of channels from the core M3U playlist.

## Package layout

```text
sample-source.rfxaddon
└── sample-source/
    ├── addon.json
    ├── addon.py
    └── README.md
```

The installer validates the manifest, API version, archive size, expanded size,
file types and archive paths. It does not prove Python code is safe. Core files
are not modified by add-on installation or removal.

## Compatibility and dependency management

Declare only hard dependencies. Requirements are checked before the entry point
is imported, so an incompatible add-on is not executed. Dependencies must already
be installed and enabled. RintrofliX reports missing or incompatible requirements
in the Add-ons detail panel. Avoid depending on undocumented internal modules;
only the documented `rintroflix.m3u.Channel` model and `AddonAPI` methods are
considered public SDK surface in this release.
