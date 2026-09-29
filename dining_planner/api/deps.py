"""Request-scoped collaborators for the API. Tests (and, later, real auth) override these."""

from __future__ import annotations

import threading
from datetime import date, datetime
from functools import lru_cache
from typing import Optional

from ..dining_hall import DiningHall
from ..purdue_dining_client import PurdueDiningClient
from ..service import CalendarSource, calendar_source_name, configured_calendar
from ..settings_store import SettingsStore

# The dining client's caches aren't built for concurrent writers; plan one day at a time.
planning_lock = threading.Lock()

_halls_by_day: dict[date, list[DiningHall]] = {}


def get_current_user() -> str:
    """Single-user for now; swap for real auth when accounts arrive."""
    return "local"


def get_now() -> datetime:
    return datetime.now().astimezone()


@lru_cache(maxsize=1)
def _dining_client() -> PurdueDiningClient:
    return PurdueDiningClient()


def get_halls() -> list[DiningHall]:
    """Hall list (and each hall's menu cache) is kept for the day, then refetched."""
    today = date.today()
    if today not in _halls_by_day:
        _halls_by_day.clear()
        _halls_by_day[today] = _dining_client().list_locations()
    return _halls_by_day[today]


def get_calendar() -> Optional[CalendarSource]:
    return configured_calendar()


def get_calendar_source() -> str:
    return calendar_source_name()


@lru_cache(maxsize=1)
def get_settings_store() -> SettingsStore:
    return SettingsStore()
