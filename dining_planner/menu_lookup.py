"""Look up a dining hall by a partial name query and return its dietary-filtered menu."""

from __future__ import annotations

from datetime import date

from .dietary_filter import DietaryFilter
from .dining_hall import DiningHall
from .models import DailyMenu, Meal


class HallNotFoundError(Exception):
    def __init__(self, query: str, available_names: list[str]):
        self.query = query
        self.available_names = available_names
        super().__init__(f"No dining hall matches '{query}'. Available: {', '.join(available_names)}")


class AmbiguousHallError(Exception):
    def __init__(self, query: str, candidate_names: list[str]):
        self.query = query
        self.candidate_names = candidate_names
        super().__init__(f"'{query}' matches multiple dining halls: {', '.join(candidate_names)}")


def find_hall(halls: list[DiningHall], query: str) -> DiningHall:
    query_lower = query.lower()
    matches = [hall for hall in halls if query_lower in hall.name.lower()]

    if not matches:
        raise HallNotFoundError(query, [hall.name for hall in halls])
    if len(matches) > 1:
        raise AmbiguousHallError(query, [hall.name for hall in matches])
    return matches[0]


def filtered_menu(hall: DiningHall, on_date: date, dietary_filter: DietaryFilter) -> DailyMenu:
    menu = hall.get_menu(on_date)
    filtered_meals: dict[str, Meal] = {}
    for meal_name, meal in menu.meals.items():
        items = dietary_filter.filter_items(meal.items)
        if items:
            filtered_meals[meal_name] = Meal(
                name=meal.name, start_time=meal.start_time, end_time=meal.end_time, items=items
            )
    return DailyMenu(dining_hall_name=menu.dining_hall_name, date=menu.date, meals=filtered_meals)
