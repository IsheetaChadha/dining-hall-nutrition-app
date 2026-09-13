"""DiningHall: a single dining location plus behavior (menus, hours, distance)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import TYPE_CHECKING, Optional

from .models import DailyMenu

if TYPE_CHECKING:
    from .purdue_dining_client import PurdueDiningClient

EARTH_RADIUS_MILES = 3958.8


@dataclass
class DiningHall:
    location_id: str
    name: str
    hall_type: str
    address: str
    latitude: float
    longitude: float
    phone: str
    normal_hours: list[dict] = field(default_factory=list, repr=False)
    _client: "PurdueDiningClient" = field(default=None, repr=False, compare=False)
    _menu_cache: dict[date, DailyMenu] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_api(cls, raw: dict, client: "PurdueDiningClient") -> "DiningHall":
        addr = raw.get("Address") or {}
        street = addr.get("Street", "")
        city = addr.get("City", "")
        state = addr.get("State", "")
        zip_code = addr.get("ZipCode", "")
        address = f"{street}, {city}, {state} {zip_code}".strip(", ")
        return cls(
            location_id=raw["LocationId"],
            name=raw["Name"],
            hall_type=raw.get("Type", ""),
            address=address,
            latitude=raw["Latitude"],
            longitude=raw["Longitude"],
            phone=raw.get("PhoneNumber", ""),
            normal_hours=raw.get("NormalHours", []),
            _client=client,
        )

    def get_menu(self, on_date: date, fetch_nutrition: bool = True) -> DailyMenu:
        if on_date not in self._menu_cache:
            menu = self._client.get_daily_menu(self.name, on_date)
            if fetch_nutrition:
                self._client.fetch_nutrition_for_menu(menu)
            self._menu_cache[on_date] = menu
        return self._menu_cache[on_date]

    def meal_window_on(self, on_date: date, meal_name: str) -> Optional[tuple[time, time]]:
        for meal in self._meals_for_date(on_date):
            if meal["Name"].lower() == meal_name.lower() and meal.get("Status") == "Open":
                hours = meal.get("Hours") or {}
                start = _parse_time(hours.get("StartTime"))
                end = _parse_time(hours.get("EndTime"))
                if start and end:
                    return start, end
        return None

    def open_meal_windows_on(self, on_date: date) -> dict[str, tuple[time, time]]:
        windows = {}
        for meal in self._meals_for_date(on_date):
            if meal.get("Status") != "Open":
                continue
            hours = meal.get("Hours") or {}
            start = _parse_time(hours.get("StartTime"))
            end = _parse_time(hours.get("EndTime"))
            if start and end:
                windows[meal["Name"]] = (start, end)
        return windows

    def is_open_at(self, when: datetime) -> bool:
        for start, end in self.open_meal_windows_on(when.date()).values():
            if start <= when.time() <= end:
                return True
        return False

    def distance_to(self, latitude: float, longitude: float) -> float:
        """Great-circle distance in miles (haversine)."""
        lat1, lon1, lat2, lon2 = map(math.radians, [self.latitude, self.longitude, latitude, longitude])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return EARTH_RADIUS_MILES * 2 * math.asin(math.sqrt(a))

    def _meals_for_date(self, on_date: date) -> list[dict]:
        hours_entry = self._effective_hours_entry(on_date)
        if hours_entry is None:
            return []
        day_name = on_date.strftime("%A")
        for day in hours_entry.get("Days", []):
            if day.get("Name") == day_name:
                return day.get("Meals", [])
        return []

    def _effective_hours_entry(self, on_date: date) -> Optional[dict]:
        """Pick the NormalHours entry whose EffectiveDate is the latest one <= on_date."""
        candidates = []
        for entry in self.normal_hours:
            effective = entry.get("EffectiveDate")
            if not effective:
                continue
            effective_date = datetime.fromisoformat(effective).date()
            if effective_date <= on_date:
                candidates.append((effective_date, entry))
        if not candidates:
            return self.normal_hours[0] if self.normal_hours else None
        candidates.sort(key=lambda pair: pair[0])
        return candidates[-1][1]


def _parse_time(value: Optional[str]) -> Optional[time]:
    if not value:
        return None
    return datetime.strptime(value, "%H:%M:%S").time()
