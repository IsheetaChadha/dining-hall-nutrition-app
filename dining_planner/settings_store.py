"""A user's saved planner settings (goals, day hours, dietary keywords, buildings).

Seeded from config.py defaults. Stored per user_id so accounts can be added later
without changing the shape of anything that reads settings.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import datetime, time, timezone
from typing import Iterator, Optional

from . import config


def _clock(value: str) -> time:
    return datetime.strptime(value, "%H:%M").time()


@dataclass(frozen=True)
class UserSettings:
    protein_target_g: float
    calorie_limit: float
    meals_per_day: int
    day_start: time
    day_end: time
    restricted_keywords: list[str] = field(default_factory=list)
    building_coords: dict[str, tuple[float, float]] = field(default_factory=dict)

    @classmethod
    def defaults(cls) -> "UserSettings":
        return cls(
            protein_target_g=config.DEFAULT_PROTEIN_TARGET_G,
            calorie_limit=config.DEFAULT_CALORIE_LIMIT,
            meals_per_day=config.DEFAULT_MEALS_PER_DAY,
            day_start=_clock(config.DEFAULT_DAY_START),
            day_end=_clock(config.DEFAULT_DAY_END),
            restricted_keywords=list(config.DEFAULT_RESTRICTED_KEYWORDS),
            building_coords=dict(config.BUILDING_COORDS),
        )

    def with_updates(self, **changes) -> "UserSettings":
        return replace(self, **changes)

    def to_dict(self) -> dict:
        return {
            "protein_target_g": self.protein_target_g,
            "calorie_limit": self.calorie_limit,
            "meals_per_day": self.meals_per_day,
            "day_start": self.day_start.strftime("%H:%M"),
            "day_end": self.day_end.strftime("%H:%M"),
            "restricted_keywords": list(self.restricted_keywords),
            "building_coords": {code: list(coords) for code, coords in self.building_coords.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserSettings":
        return cls(
            protein_target_g=data["protein_target_g"],
            calorie_limit=data["calorie_limit"],
            meals_per_day=data["meals_per_day"],
            day_start=_clock(data["day_start"]),
            day_end=_clock(data["day_end"]),
            restricted_keywords=list(data["restricted_keywords"]),
            building_coords={code: (lat, lon) for code, (lat, lon) in data["building_coords"].items()},
        )


class SettingsStore:
    """SQLite-backed settings, one row per user; a user with no row gets the defaults."""

    def __init__(self, path: str = config.APP_DB_PATH):
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS settings (user_id TEXT PRIMARY KEY, json TEXT NOT NULL, updated_at TEXT NOT NULL)"
            )

    def get(self, user_id: str) -> UserSettings:
        with self._connect() as conn:
            row: Optional[tuple] = conn.execute("SELECT json FROM settings WHERE user_id = ?", (user_id,)).fetchone()
        return UserSettings.from_dict(json.loads(row[0])) if row else UserSettings.defaults()

    def save(self, user_id: str, settings: UserSettings) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO settings (user_id, json, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET json = excluded.json, updated_at = excluded.updated_at",
                (user_id, json.dumps(settings.to_dict()), datetime.now(timezone.utc).isoformat()),
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        try:
            with conn:  # commits on success, rolls back on error
                yield conn
        finally:
            conn.close()
