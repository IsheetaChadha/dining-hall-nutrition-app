"""CLI: show a dining hall's dietary-filtered menu for a given day.

Usage:
    python -m dining_planner.menu "wiley"
    python -m dining_planner.menu "hillenbrand" --date 2026-09-15
"""

from __future__ import annotations

import argparse
from datetime import date

from .dietary_filter import DietaryFilter
from .menu_lookup import AmbiguousHallError, HallNotFoundError, filtered_menu, find_hall
from .purdue_dining_client import PurdueDiningClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("query", help="Dining hall name or partial name, e.g. 'wiley'")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD, defaults to today")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    on_date = date.fromisoformat(args.date) if args.date else date.today()

    dining_client = PurdueDiningClient()
    halls = dining_client.list_locations()

    try:
        hall = find_hall(halls, args.query)
    except HallNotFoundError as e:
        print(str(e))
        return
    except AmbiguousHallError as e:
        print(str(e))
        return

    menu = filtered_menu(hall, on_date, DietaryFilter())

    if not menu.meals:
        print(f"No items at {hall.name} on {on_date} pass the dietary filter (or the hall is closed).")
        return

    print(f"{hall.name} — {on_date}\n")
    for meal_name, meal in menu.meals.items():
        print(f"{meal_name} ({meal.start_time.strftime('%H:%M')}-{meal.end_time.strftime('%H:%M')}):")
        by_station: dict[str, list[str]] = {}
        for item in meal.items:
            by_station.setdefault(item.station_name, []).append(item.name)
        for station, item_names in by_station.items():
            print(f"  {station}: {', '.join(item_names)}")
        print()


if __name__ == "__main__":
    main()
