from datetime import date, time

import pytest

from dining_planner.dietary_filter import DietaryFilter
from dining_planner.dining_hall import DiningHall
from dining_planner.menu_lookup import AmbiguousHallError, HallNotFoundError, filtered_menu, find_hall
from dining_planner.models import DailyMenu, Meal, MenuItem

ON_DATE = date(2026, 9, 8)


def make_item(name, ingredients_text=""):
    return MenuItem(
        id=name,
        name=name,
        station_name="Station",
        meal_name="Lunch",
        is_vegetarian=False,
        ingredients_text=ingredients_text,
    )


class FakeDiningClient:
    """Stands in for PurdueDiningClient: DailyMenu is supplied directly, no HTTP."""

    def __init__(self, menu: DailyMenu):
        self._menu = menu

    def get_daily_menu(self, hall_name, on_date):
        return self._menu

    def fetch_nutrition_for_menu(self, menu):
        pass


def make_hall(name, meals: dict[str, list[MenuItem]]) -> DiningHall:
    menu_meals = {
        meal_name: Meal(name=meal_name, start_time=time(11, 0), end_time=time(14, 0), items=items)
        for meal_name, items in meals.items()
    }
    menu = DailyMenu(dining_hall_name=name, date=ON_DATE, meals=menu_meals)
    client = FakeDiningClient(menu)
    return DiningHall(
        location_id=name.upper(),
        name=name,
        hall_type="Dining Courts",
        address="123 Main St",
        latitude=40.0,
        longitude=-86.0,
        phone="",
        _client=client,
    )


# ---- find_hall ----------------------------------------------------------


def test_find_hall_matches_exact_name():
    wiley = make_hall("Wiley", {})
    ford = make_hall("Ford", {})

    result = find_hall([wiley, ford], "Wiley")

    assert result is wiley


def test_find_hall_matches_case_insensitive_substring():
    hillenbrand = make_hall("Hillenbrand", {})

    result = find_hall([hillenbrand], "hillen")

    assert result is hillenbrand


def test_find_hall_raises_when_no_match():
    wiley = make_hall("Wiley", {})

    with pytest.raises(HallNotFoundError) as exc_info:
        find_hall([wiley], "Windsor")

    assert exc_info.value.available_names == ["Wiley"]


def test_find_hall_raises_when_ambiguous():
    earhart = make_hall("Earhart", {})
    earhart_gogo = make_hall("Earhart On-the-GO!", {})

    with pytest.raises(AmbiguousHallError) as exc_info:
        find_hall([earhart, earhart_gogo], "earhart")

    assert exc_info.value.candidate_names == ["Earhart", "Earhart On-the-GO!"]


# ---- filtered_menu --------------------------------------------------------


def test_filtered_menu_drops_restricted_items():
    hall = make_hall(
        "Wiley",
        {"Lunch": [make_item("Beef Tacos"), make_item("Veggie Burger")]},
    )

    menu = filtered_menu(hall, ON_DATE, DietaryFilter())

    assert [item.name for item in menu.meals["Lunch"].items] == ["Veggie Burger"]


def test_filtered_menu_matches_restricted_keywords_in_ingredients_too():
    hall = make_hall(
        "Wiley",
        {"Lunch": [make_item("Soup", ingredients_text="Chicken stock, ham, carrots")]},
    )

    menu = filtered_menu(hall, ON_DATE, DietaryFilter())

    assert "Lunch" not in menu.meals


def test_filtered_menu_drops_meals_left_with_no_items():
    hall = make_hall(
        "Wiley",
        {
            "Breakfast": [make_item("Bacon")],
            "Lunch": [make_item("Veggie Burger")],
        },
    )

    menu = filtered_menu(hall, ON_DATE, DietaryFilter())

    assert "Breakfast" not in menu.meals
    assert "Lunch" in menu.meals
