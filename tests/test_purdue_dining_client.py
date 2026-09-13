from datetime import date, time
from unittest.mock import MagicMock, patch

from dining_planner.purdue_dining_client import PurdueDiningClient

LOCATIONS_RESPONSE = {
    "Types": ["Dining Courts"],
    "Location": [
        {
            "LocationId": "WILY",
            "Name": "Wiley",
            "Address": {"Street": "498 North Martin Jischke Drive", "City": "West Lafayette", "State": "IN", "ZipCode": "47906"},
            "PhoneNumber": "(765) 494-2264",
            "Latitude": 40.428705,
            "Longitude": -86.920867,
            "Type": "Dining Courts",
            "NormalHours": [
                {
                    "Name": "Fall 2026",
                    "EffectiveDate": "2026-08-23T00:00:00",
                    "Days": [
                        {
                            "Name": "Tuesday",
                            "DayOfWeek": 2,
                            "Meals": [
                                {"Name": "Lunch", "Order": 1, "Status": "Open", "Hours": {"StartTime": "11:00:00", "EndTime": "14:00:00"}},
                            ],
                        }
                    ],
                }
            ],
        }
    ],
}

MENU_RESPONSE = {
    "Location": "Wiley",
    "Date": "9/8/2026",
    "IsPublished": True,
    "Meals": [
        {
            "ID": "meal-1",
            "Name": "Lunch",
            "Status": "Open",
            "Hours": {"StartTime": "11:00:00", "EndTime": "14:00:00"},
            "Stations": [
                {
                    "Name": "Grill",
                    "Items": [
                        {
                            "ID": "item-1",
                            "Name": "Scrambled Eggs",
                            "IsVegetarian": True,
                            "NutritionReady": True,
                            "Allergens": [{"Name": "Eggs", "Value": True}, {"Name": "Milk", "Value": True}],
                        },
                        {"ID": "item-2", "Name": "Mystery Skillet", "IsVegetarian": False, "NutritionReady": False},
                    ],
                }
            ],
        }
    ],
}

ITEM_RESPONSE_READY = {
    "ID": "item-1",
    "Name": "Scrambled Eggs",
    "IsVegetarian": True,
    "NutritionReady": True,
    "Ingredients": "Whole Eggs, Milk",
    "Allergens": [{"Name": "Eggs", "Value": True}, {"Name": "Milk", "Value": True}],
    "Nutrition": [
        {"Name": "Serving Size", "LabelValue": "1/2 Cup", "Ordinal": 0},
        {"Name": "Calories", "Value": 154.5, "LabelValue": "155", "Ordinal": 1},
        {"Name": "Total fat", "Value": 12.2, "LabelValue": "12g", "Ordinal": 3},
        {"Name": "Total Carbohydrate", "Value": 2.2, "LabelValue": "2g", "Ordinal": 7},
        {"Name": "Protein", "Value": 11.1, "LabelValue": "11g", "Ordinal": 11},
    ],
}

ITEM_RESPONSE_NOT_READY = {"ID": "item-2", "Name": "Mystery Skillet", "IsVegetarian": False, "NutritionReady": False}


def _client_with_mocked_get(responses_by_path: dict[str, dict], tmp_path, monkeypatch) -> PurdueDiningClient:
    import dining_planner.config as config

    monkeypatch.setattr(config, "CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(config, "NUTRITION_CACHE_PATH", str(tmp_path / "nutrition_cache.json"))

    client = PurdueDiningClient()

    def fake_get(path: str) -> dict:
        return responses_by_path[path]

    client._get = fake_get  # type: ignore[method-assign]
    return client


def test_list_locations_raw_parses_fields(tmp_path, monkeypatch):
    client = _client_with_mocked_get({"/locations": LOCATIONS_RESPONSE}, tmp_path, monkeypatch)
    locations = client.list_locations_raw()
    assert len(locations) == 1
    assert locations[0]["Name"] == "Wiley"


def test_list_locations_builds_dining_hall_objects(tmp_path, monkeypatch):
    client = _client_with_mocked_get({"/locations": LOCATIONS_RESPONSE}, tmp_path, monkeypatch)
    halls = client.list_locations()
    assert len(halls) == 1
    hall = halls[0]
    assert hall.name == "Wiley"
    assert hall.latitude == 40.428705
    assert "West Lafayette" in hall.address


def test_get_daily_menu_parses_meals_stations_items(tmp_path, monkeypatch):
    client = _client_with_mocked_get(
        {"/locations/Wiley/09-08-2026": MENU_RESPONSE}, tmp_path, monkeypatch
    )
    menu = client.get_daily_menu("Wiley", date(2026, 9, 8))
    assert list(menu.meals.keys()) == ["Lunch"]
    lunch = menu.meals["Lunch"]
    assert lunch.start_time == time(11, 0)
    assert lunch.end_time == time(14, 0)
    assert len(lunch.items) == 2
    eggs = next(i for i in lunch.items if i.id == "item-1")
    assert eggs.station_name == "Grill"
    assert eggs.is_vegetarian is True
    assert eggs.allergens == ["Eggs", "Milk"]


def test_fetch_nutrition_for_menu_fills_in_nutrition_and_skips_not_ready(tmp_path, monkeypatch):
    client = _client_with_mocked_get(
        {
            "/locations/Wiley/09-08-2026": MENU_RESPONSE,
            "/items/item-1": ITEM_RESPONSE_READY,
            "/items/item-2": ITEM_RESPONSE_NOT_READY,
        },
        tmp_path,
        monkeypatch,
    )
    menu = client.get_daily_menu("Wiley", date(2026, 9, 8))
    client.fetch_nutrition_for_menu(menu)

    items_by_id = {i.id: i for i in menu.all_items()}
    eggs = items_by_id["item-1"]
    assert eggs.nutrition is not None
    assert eggs.nutrition.calories == 154.5
    assert eggs.nutrition.protein_g == 11.1
    assert eggs.ingredients_text == "Whole Eggs, Milk"

    skillet = items_by_id["item-2"]
    assert skillet.nutrition is None


def test_nutrition_cache_persists_across_client_instances(tmp_path, monkeypatch):
    client1 = _client_with_mocked_get(
        {
            "/locations/Wiley/09-08-2026": MENU_RESPONSE,
            "/items/item-1": ITEM_RESPONSE_READY,
            "/items/item-2": ITEM_RESPONSE_NOT_READY,
        },
        tmp_path,
        monkeypatch,
    )
    menu = client1.get_daily_menu("Wiley", date(2026, 9, 8))
    client1.fetch_nutrition_for_menu(menu)

    # A second client instance should load the cache from disk without any HTTP calls.
    client2 = _client_with_mocked_get({}, tmp_path, monkeypatch)
    nutrition = client2.get_item_nutrition("item-1")
    assert nutrition is not None
    assert nutrition.calories == 154.5
