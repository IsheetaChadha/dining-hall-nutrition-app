"""Plan one day: the orchestration shared by the CLI and the web API.

Reads free time from the calendar (clipped to now when planning today), builds the
per-meal goal from the user's settings plus any overrides, and ranks every reachable
hall/meal. Explains an empty result with a `notice` instead of leaving it blank.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from datetime import date, datetime, time
from typing import Optional, Protocol

import requests

from . import config
from .dietary_filter import DietaryFilter
from .dining_hall import DiningHall
from .models import AvailabilityWindow, Recommendation
from .nutrition_goal import NutritionGoal
from .recommendation_engine import RecommendationEngine
from .settings_store import UserSettings


class CalendarNotConfiguredError(Exception):
    pass


class UpstreamUnavailableError(Exception):
    pass


class CalendarSource(Protocol):
    def get_availability_windows(self, on_date: date, day_start: time, day_end: time) -> list[AvailabilityWindow]: ...


@dataclass
class DayPlan:
    date: date
    meal: Optional[str]
    goal_per_meal: NutritionGoal
    windows: list[AvailabilityWindow]
    recommendations: list[Recommendation]
    notice: Optional[str] = None
    warnings: list[str] = field(default_factory=list)


def plan_day(
    halls: list[DiningHall],
    calendar: Optional[CalendarSource],
    settings: UserSettings,
    on_date: Optional[date] = None,
    meal: Optional[str] = None,
    protein: Optional[float] = None,
    calories: Optional[float] = None,
    meals_per_day: Optional[int] = None,
    windows: Optional[list[AvailabilityWindow]] = None,
    now: Optional[datetime] = None,
) -> DayPlan:
    """Rank hall/meal options for `on_date` (default: today, from `now` on).

    Explicit `windows` are used as given; otherwise they come from `calendar`.
    """
    now = now or datetime.now().astimezone()
    on_date = on_date or now.date()

    if windows is None:
        if calendar is None:
            raise CalendarNotConfiguredError()
        windows = _read_calendar(calendar, on_date, settings)
        windows = clip_to_now(windows, on_date, now)

    goal = NutritionGoal(
        protein_target_g=protein if protein is not None else settings.protein_target_g,
        calorie_limit=calories if calories is not None else settings.calorie_limit,
        dietary_filter=DietaryFilter(restricted_keywords=list(settings.restricted_keywords)),
    ).per_meal(meals_per_day or settings.meals_per_day)

    plan = DayPlan(date=on_date, meal=meal, goal_per_meal=goal, windows=windows, recommendations=[])
    if not windows:
        plan.notice = _empty_notice(halls, on_date, meal, now) or f"No free time found on {on_date}."
        return plan

    # Rank hall by hall so one hall's menu failing to load skips just that hall.
    failed = []
    for hall in halls:
        engine = RecommendationEngine([hall], building_coords=settings.building_coords)
        try:
            plan.recommendations.extend(engine.recommend(on_date, windows, goal, meal_name=meal))
        except requests.RequestException:
            failed.append(hall.name)
    if halls and len(failed) == len(halls):
        raise UpstreamUnavailableError("Couldn't load any dining hall menus.")

    plan.recommendations.sort(key=lambda r: r.total_score, reverse=True)
    plan.warnings = [f"Couldn't load the {name} menu, so it was skipped." for name in failed]
    if not plan.recommendations:
        plan.notice = _empty_notice(halls, on_date, meal, now)
    return plan


def available_meals(halls: list[DiningHall], on_date: date) -> list[str]:
    """Distinct meal names served on `on_date`, ordered by their earliest start time."""
    earliest: dict[str, time] = {}
    for hall in halls:
        for name, (start, _end) in hall.open_meal_windows_on(on_date).items():
            if name not in earliest or start < earliest[name]:
                earliest[name] = start
    return sorted(earliest, key=lambda name: earliest[name])


def calendar_source_name() -> str:
    """Which calendar the planner reads: "ical" (private feed URL), "google" (OAuth), or "none"."""
    if os.path.exists(config.CALENDAR_URL_PATH):
        return "ical"
    if os.path.exists(config.CLIENT_SECRET_PATH):
        return "google"
    return "none"


def configured_calendar() -> Optional[CalendarSource]:
    source = calendar_source_name()
    if source == "ical":
        from .ical_calendar_client import ICalCalendarClient

        return ICalCalendarClient.from_url_file()
    if source == "google":
        from .google_calendar_client import GoogleCalendarClient

        return GoogleCalendarClient()
    return None


def clip_to_now(windows: list[AvailabilityWindow], on_date: date, now: datetime) -> list[AvailabilityWindow]:
    """Drop the already-passed part of today's free windows so a meal that's over
    (e.g. lunch, once it's dinner time) doesn't still get suggested."""
    if on_date != now.date():
        return windows

    clipped = []
    for window in windows:
        start = max(window.start, now)
        if start < window.end:
            clipped.append(replace(window, start=start))
    return clipped


def _read_calendar(calendar: CalendarSource, on_date: date, settings: UserSettings) -> list[AvailabilityWindow]:
    try:
        return calendar.get_availability_windows(on_date, settings.day_start, settings.day_end)
    except (requests.RequestException, OSError) as exc:
        raise UpstreamUnavailableError("Couldn't read your calendar.") from exc


def _empty_notice(halls: list[DiningHall], on_date: date, meal: Optional[str], now: datetime) -> Optional[str]:
    """Why nothing was recommended, when the reason is the dining schedule itself."""
    served = [
        (name, end)
        for hall in halls
        for name, (_start, end) in hall.open_meal_windows_on(on_date).items()
        if meal is None or name.lower() == meal.lower()
    ]
    if meal and not served:
        return f"No dining hall serves {meal} on {on_date}."
    if on_date == now.date() and served and all(end <= now.time() for _name, end in served):
        return f"{served[0][0]} has ended for today." if meal else "Every dining hall meal has ended for today."
    return None
