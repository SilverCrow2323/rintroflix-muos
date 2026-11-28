import pytest

from rintroflix.addons import AddonError, AddonManager


class FakeConfig:
    def __init__(self, enabled):
        self.values = {"enabled_addons": list(enabled)}

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


class FakeApp:
    def __init__(self, enabled):
        self.cfg = FakeConfig(enabled)


def manifest(addon_id, dependencies=None):
    return {
        "id": addon_id,
        "version": "1.0.0",
        "api_version": 1,
        "requires": {
            "rintroflix": "",
            "addons": dependencies or {},
        },
    }


def manager_with(*manifests, enabled=()):
    manager = AddonManager.__new__(AddonManager)
    manager.app = FakeApp(enabled)
    manager.items = [
        {"manifest": item, "folder": None, "enabled": item["id"] in enabled}
        for item in manifests
    ]
    manager.actions = []
    manager.sources = []
    manager.errors = []
    return manager


def test_enabled_addons_are_ordered_after_their_dependencies():
    manager = manager_with(
        manifest("addon-a", {"addon-b": ">=1.0"}),
        manifest("addon-c", {"addon-a": ">=1.0"}),
        manifest("addon-b"),
        enabled=("addon-a", "addon-b", "addon-c"),
    )

    assert manager._dependency_order({"addon-a", "addon-b", "addon-c"}) == [
        "addon-b", "addon-a", "addon-c"
    ]


def test_dependency_cycle_is_reported_with_the_cycle_path():
    manager = manager_with(
        manifest("addon-a", {"addon-b": ">=1.0"}),
        manifest("addon-b", {"addon-a": ">=1.0"}),
    )

    with pytest.raises(AddonError, match=r"addon-a -> addon-b -> addon-a|addon-b -> addon-a -> addon-b"):
        manager._dependency_order({"addon-a", "addon-b"})


def test_enabling_an_addon_that_closes_a_dependency_cycle_is_refused():
    manager = manager_with(
        manifest("addon-a", {"addon-b": ">=1.0"}),
        manifest("addon-b", {"addon-a": ">=1.0"}),
        enabled=("addon-a",),
    )

    with pytest.raises(AddonError, match="dependency cycle"):
        manager.set_enabled("addon-b", True)

    assert manager.app.cfg.get("enabled_addons") == ["addon-a"]
