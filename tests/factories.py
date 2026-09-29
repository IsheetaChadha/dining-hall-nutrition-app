"""Shared test builders: dining halls with in-memory menus (no HTTP) and fixed calendars."""

from datetime import date, time

import requests

from dining_planner.dining_hall import DiningHall
from dining_planner.models import AvailabilityWindow, DailyMenu, Meal, MenuItem, NutritionInfo


def make_item(name, calories=200, protein_g=40, fat_g=5, meal_name="Lunch"):
    return MenuItem(
        id=name,
        name=name,
        station_name="Station",
        meal_name=meal_name,
        is_vegetarian=False,
        nutrition=NutritionInfo(calories=calories, protein_g=protein_g, fat_g=fat_g, carbs_g=0.0),
    )


class FakeDiningClient:
    """Stands in for PurdueDiningClient: DailyMenu is supplied directly, no HTTP."""

    def __init__(self, menu: DailyMenu, fail: bool = False):
        self._menu = menu
        self._fail = fail

    def get_daily_menu(self, hall_name, on_date):
        if self._fail:
            raise requests.ConnectionError(f"{hall_name} menu unavailable")
        return self._menu

    def fetch_nutrition_for_menu(self, menu):
        pass


def make_hall(name, on_date: date, meals, latitude=40.0, longitude=-86.0, fail=False) -> DiningHall:
    """A hall open on `on_date`; `meals` is a list of (meal_name, start, end, items)."""
    menu = DailyMenu(
        dining_hall_name=name,
        date=on_date,
        meals={m: Meal(name=m, start_time=s, end_time=e, items=items) for m, s, e, items in meals},
    )
    normal_hours = [
        {
            "EffectiveDate": "2020-01-01T00:00:00",
            "Days": [
                {
                    "Name": on_date.strftime("%A"),
                    "Meals": [
                        {
                            "Name": m,
                            "Status": "Open",
                            "Hours": {"StartTime": s.strftime("%H:%M:%S"), "EndTime": e.strftime("%H:%M:%S")},
                        }
                        for m, s, e, _ in meals
                    ],
                }
            ],
        }
    ]
    return DiningHall(
        location_id=name.upper(),
        name=name,
        hall_type="Dining Courts",
        address="",
        latitude=latitude,
        longitude=longitude,
        phone="",
        normal_hours=normal_hours,
        _client=FakeDiningClient(menu, fail=fail),
    )


class FixedCalendar:
    """Stands in for a calendar client: returns the given windows and records what it was asked."""

    def __init__(self, windows: list[AvailabilityWindow]):
        self.windows = windows
        self.calls: list[tuple[date, time, time]] = []

    def get_availability_windows(self, on_date, day_start, day_end):
        self.calls.append((on_date, day_start, day_end))
        return list(self.windows)
