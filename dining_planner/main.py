"""CLI entrypoint: rank dining hall/meal options for a day against your nutrition goal
and calendar availability (iCal feed or Google Calendar API).

Usage:
    python -m dining_planner.main
    python -m dining_planner.main --date 2026-09-08 --protein 120 --calories 1800
    python -m dining_planner.main --meal Dinner
    python -m dining_planner.main --window 11:30-13:00 --window 17:30-19:00   # skip Google Calendar
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, time
from typing import Optional

from . import config
from .models import AvailabilityWindow
from .purdue_dining_client import PurdueDiningClient
from .service import CalendarNotConfiguredError, configured_calendar, plan_day
from .settings_store import UserSettings


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--date", default=None, help="YYYY-MM-DD, defaults to today")
    parser.add_argument("--meal", default=None, help="Only rank this meal (e.g. Lunch); defaults to every meal")
    parser.add_argument("--protein", type=float, default=config.DEFAULT_PROTEIN_TARGET_G, help="Daily protein target in grams")
    parser.add_argument("--calories", type=float, default=config.DEFAULT_CALORIE_LIMIT, help="Daily calorie limit")
    parser.add_argument(
        "--meals",
        type=int,
        default=config.DEFAULT_MEALS_PER_DAY,
        help="Meals per day; each plate targets this share of the daily goal",
    )
    parser.add_argument("--day-start", default=config.DEFAULT_DAY_START, help="Earliest time to consider for availability (HH:MM)")
    parser.add_argument("--day-end", default=config.DEFAULT_DAY_END, help="Latest time to consider for availability (HH:MM)")
    parser.add_argument(
        "--window",
        action="append",
        default=None,
        metavar="HH:MM-HH:MM",
        help="Manually specify a free-time window instead of reading Google Calendar (repeatable)",
    )
    parser.add_argument("--top", type=int, default=5, help="How many recommendations to print")
    return parser.parse_args(argv)


def _parse_clock_time(value: str) -> time:
    return datetime.strptime(value, "%H:%M").time()


def settings_from_args(args: argparse.Namespace) -> UserSettings:
    return UserSettings.defaults().with_updates(
        protein_target_g=args.protein,
        calorie_limit=args.calories,
        meals_per_day=args.meals,
        day_start=_parse_clock_time(args.day_start),
        day_end=_parse_clock_time(args.day_end),
    )


def _manual_windows(on_date: date, specs: list[str]) -> list[AvailabilityWindow]:
    tz = datetime.now().astimezone().tzinfo
    windows = []
    for spec in specs:
        start_str, end_str = spec.split("-")
        start = datetime.combine(on_date, _parse_clock_time(start_str), tzinfo=tz)
        end = datetime.combine(on_date, _parse_clock_time(end_str), tzinfo=tz)
        windows.append(AvailabilityWindow(start=start, end=end, prev_event_location=None, next_event_location=None))
    return windows


def _fmt_score(score: Optional[float]) -> str:
    return "n/a" if score is None else f"{score:.2f}"


def main() -> None:
    args = parse_args()
    on_date = date.fromisoformat(args.date) if args.date else date.today()

    halls = PurdueDiningClient().list_locations()
    windows = _manual_windows(on_date, args.window) if args.window else None

    try:
        plan = plan_day(
            halls, configured_calendar(), settings_from_args(args), on_date=on_date, meal=args.meal, windows=windows
        )
    except CalendarNotConfiguredError:
        print(
            "No calendar configured. Either save your calendar's private iCal URL to\n"
            f"  {config.CALENDAR_URL_PATH}\n"
            f"or add Google OAuth credentials at {config.CLIENT_SECRET_PATH} (see README.md).\n"
            "Or test without a calendar with e.g.:\n"
            "  python -m dining_planner.main --window 11:30-13:00 --window 17:30-19:00"
        )
        return

    for warning in plan.warnings:
        print(f"Warning: {warning}")
    if not plan.recommendations:
        print(plan.notice or f"No dining hall/meal matched your availability for {on_date}.")
        return

    print(f"Top picks for {on_date}:\n")
    for rank, rec in enumerate(plan.recommendations[: args.top], start=1):
        window = rec.window
        print(
            f"{rank}. {rec.dining_hall_name} — {rec.meal_name} "
            f"(score {rec.total_score:.2f} | nutrition {rec.nutrition_score:.2f}, "
            f"time {rec.time_score:.2f}, proximity {_fmt_score(rec.proximity_score)})"
        )
        print(f"   during your free window {window.start.strftime('%H:%M')}-{window.end.strftime('%H:%M')}")
        item_names = ", ".join(item.name for item in rec.suggested_items)
        print(f"   suggested plate: {item_names}\n")


if __name__ == "__main__":
    main()
