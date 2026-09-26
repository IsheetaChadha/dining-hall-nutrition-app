"""CLI entrypoint: rank dining hall/meal options for a day against your nutrition goal
and calendar availability (iCal feed or Google Calendar API).

Usage:
    python -m dining_planner.main
    python -m dining_planner.main --date 2026-09-08 --protein 120 --calories 1800
    python -m dining_planner.main --window 11:30-13:00 --window 17:30-19:00   # skip Google Calendar
"""

from __future__ import annotations

import argparse
import os
from datetime import date, datetime, time

from . import config
from .google_calendar_client import GoogleCalendarClient
from .ical_calendar_client import ICalCalendarClient
from .models import AvailabilityWindow
from .nutrition_goal import NutritionGoal
from .purdue_dining_client import PurdueDiningClient
from .recommendation_engine import RecommendationEngine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--date", default=None, help="YYYY-MM-DD, defaults to today")
    parser.add_argument("--protein", type=float, default=100.0, help="Daily protein target in grams")
    parser.add_argument("--calories", type=float, default=1800.0, help="Daily calorie limit")
    parser.add_argument("--day-start", default="07:00", help="Earliest time to consider for availability (HH:MM)")
    parser.add_argument("--day-end", default="21:00", help="Latest time to consider for availability (HH:MM)")
    parser.add_argument(
        "--window",
        action="append",
        default=None,
        metavar="HH:MM-HH:MM",
        help="Manually specify a free-time window instead of reading Google Calendar (repeatable)",
    )
    parser.add_argument("--top", type=int, default=5, help="How many recommendations to print")
    return parser.parse_args()


def _parse_clock_time(value: str) -> time:
    return datetime.strptime(value, "%H:%M").time()


def _manual_windows(on_date: date, specs: list[str]) -> list[AvailabilityWindow]:
    tz = datetime.now().astimezone().tzinfo
    windows = []
    for spec in specs:
        start_str, end_str = spec.split("-")
        start = datetime.combine(on_date, _parse_clock_time(start_str), tzinfo=tz)
        end = datetime.combine(on_date, _parse_clock_time(end_str), tzinfo=tz)
        windows.append(AvailabilityWindow(start=start, end=end, prev_event_location=None, next_event_location=None))
    return windows


def main() -> None:
    args = parse_args()
    on_date = date.fromisoformat(args.date) if args.date else date.today()

    dining_client = PurdueDiningClient()
    halls = dining_client.list_locations()

    if args.window:
        windows = _manual_windows(on_date, args.window)
    else:
        if os.path.exists(config.CALENDAR_URL_PATH):
            calendar_client = ICalCalendarClient.from_url_file()
        elif os.path.exists(config.CLIENT_SECRET_PATH):
            calendar_client = GoogleCalendarClient()
        else:
            print(
                "No calendar configured. Either save your calendar's private iCal URL to\n"
                f"  {config.CALENDAR_URL_PATH}\n"
                f"or add Google OAuth credentials at {config.CLIENT_SECRET_PATH} (see README.md).\n"
                "Or test without a calendar with e.g.:\n"
                "  python -m dining_planner.main --window 11:30-13:00 --window 17:30-19:00"
            )
            return
        windows = calendar_client.get_availability_windows(
            on_date, _parse_clock_time(args.day_start), _parse_clock_time(args.day_end)
        )

    if not windows:
        print(f"No free-time windows found for {on_date}.")
        return

    goal = NutritionGoal(protein_target_g=args.protein, calorie_limit=args.calories)
    engine = RecommendationEngine(halls)
    recommendations = engine.recommend(on_date, windows, goal)

    if not recommendations:
        print(f"No dining hall/meal matched your availability for {on_date}.")
        return

    print(f"Top picks for {on_date}:\n")
    for rank, rec in enumerate(recommendations[: args.top], start=1):
        window = rec.window
        print(
            f"{rank}. {rec.dining_hall_name} — {rec.meal_name} "
            f"(score {rec.total_score:.2f} | nutrition {rec.nutrition_score:.2f}, "
            f"time {rec.time_score:.2f}, proximity {rec.proximity_score:.2f})"
        )
        print(f"   during your free window {window.start.strftime('%H:%M')}-{window.end.strftime('%H:%M')}")
        item_names = ", ".join(item.name for item in rec.suggested_items)
        print(f"   suggested plate: {item_names}\n")


if __name__ == "__main__":
    main()
