"""A user's saved planner settings (goals, day hours, dietary keywords, buildings).

Seeded from config.py defaults. Stored per user_id so accounts can be added later
without changing the shape of anything that reads settings.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, time

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
