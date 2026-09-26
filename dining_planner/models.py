"""Plain data classes shared across the dining planner."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Optional


@dataclass
class NutritionInfo:
    calories: float
    protein_g: float
    fat_g: float
    carbs_g: float
    serving_size: str = ""


@dataclass
class MenuItem:
    id: str
    name: str
    station_name: str
    meal_name: str
    is_vegetarian: bool
    allergens: list[str] = field(default_factory=list)
    ingredients_text: str = ""
    nutrition: Optional[NutritionInfo] = None


@dataclass
class Meal:
    name: str
    start_time: time
    end_time: time
    items: list[MenuItem] = field(default_factory=list)


@dataclass
class DailyMenu:
    dining_hall_name: str
    date: date
    meals: dict[str, Meal] = field(default_factory=dict)

    def all_items(self) -> list[MenuItem]:
        return [item for meal in self.meals.values() for item in meal.items]


@dataclass
class AvailabilityWindow:
    start: datetime
    end: datetime
    prev_event_location: Optional[str] = None
    next_event_location: Optional[str] = None

    @property
    def duration_minutes(self) -> float:
        return (self.end - self.start).total_seconds() / 60


@dataclass
class Recommendation:
    dining_hall_name: str
    meal_name: str
    window: AvailabilityWindow
    nutrition_score: float
    time_score: float
    proximity_score: Optional[float]  # None when your location around the window is unknown
    total_score: float
    suggested_items: list[MenuItem] = field(default_factory=list)
