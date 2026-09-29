from datetime import time

from dining_planner.settings_store import SettingsStore, UserSettings


def test_unknown_user_gets_the_defaults(tmp_path):
    store = SettingsStore(str(tmp_path / "app.db"))

    assert store.get("local") == UserSettings.defaults()


def test_saved_settings_round_trip_across_store_instances(tmp_path):
    path = str(tmp_path / "app.db")
    custom = UserSettings.defaults().with_updates(
        protein_target_g=140,
        day_start=time(8, 15),
        restricted_keywords=["beef"],
        building_coords={"WALC": (40.4274, -86.9132)},
    )

    SettingsStore(path).save("local", custom)

    assert SettingsStore(path).get("local") == custom


def test_users_settings_are_kept_apart(tmp_path):
    store = SettingsStore(str(tmp_path / "app.db"))
    store.save("alice", UserSettings.defaults().with_updates(protein_target_g=150))

    assert store.get("bob") == UserSettings.defaults()
    assert store.get("alice").protein_target_g == 150


def test_saving_again_replaces_the_previous_settings(tmp_path):
    store = SettingsStore(str(tmp_path / "app.db"))
    store.save("local", UserSettings.defaults().with_updates(meals_per_day=2))
    store.save("local", UserSettings.defaults().with_updates(meals_per_day=4))

    assert store.get("local").meals_per_day == 4


def test_store_creates_its_parent_directory(tmp_path):
    store = SettingsStore(str(tmp_path / "nested" / "app.db"))

    store.save("local", UserSettings.defaults())

    assert (tmp_path / "nested" / "app.db").exists()
