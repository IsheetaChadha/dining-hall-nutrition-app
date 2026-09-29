"""Pydantic request/response models: the API contract the web and future native clients share."""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime, time
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from ..models import AvailabilityWindow, MenuItem, Recommendation
from ..service import DayPlan
from ..settings_store import UserSettings

ClockTime = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$", description="24-hour HH:MM")
Latitude = Annotated[float, Field(ge=-90, le=90)]
Longitude = Annotated[float, Field(ge=-180, le=180)]


class Settings(BaseModel):
    protein_target_g: float = Field(gt=0)
    calorie_limit: float = Field(gt=0)
    meals_per_day: int = Field(ge=1, le=6)
    day_start: str = ClockTime
    day_end: str = ClockTime
    restricted_keywords: list[str]
    building_coords: dict[str, tuple[Latitude, Longitude]]

    @field_validator("day_end")
    @classmethod
    def _day_ends_after_it_starts(cls, day_end: str, info: ValidationInfo) -> str:
        day_start = info.data.get("day_start")
        if day_start and day_end <= day_start:  # zero-padded HH:MM strings compare in time order
            raise ValueError("Day end must be after day start.")
        return day_end

    @field_validator("restricted_keywords")
    @classmethod
    def _normalize_keywords(cls, keywords: list[str]) -> list[str]:
        normalized = [k.strip().lower() for k in keywords]
        if any(not k for k in normalized):
            raise ValueError("Keywords can't be blank.")
        return list(dict.fromkeys(normalized))

    @field_validator("building_coords")
    @classmethod
    def _normalize_buildings(cls, coords: dict[str, tuple[float, float]]) -> dict[str, tuple[float, float]]:
        normalized = {}
        for code, (lat, lon) in coords.items():
            code = code.strip().upper()
            if not code:
                raise ValueError("Building codes can't be blank.")
            normalized[code] = (lat, lon)
        return normalized

    @classmethod
    def from_domain(cls, settings: UserSettings) -> "Settings":
        return cls(**settings.to_dict())

    def to_domain(self) -> UserSettings:
        return UserSettings.from_dict(self.model_dump())


class RecommendationRequest(BaseModel):
    date: Optional[Date] = None
    meal: Optional[str] = None
    protein: Optional[float] = Field(default=None, gt=0)
    calories: Optional[float] = Field(default=None, gt=0)
    meals: Optional[int] = Field(default=None, ge=1, le=6)


class Window(BaseModel):
    start: datetime
    end: datetime
    prev_event_location: Optional[str] = None
    next_event_location: Optional[str] = None

    @classmethod
    def from_domain(cls, window: AvailabilityWindow) -> "Window":
        return cls(
            start=window.start,
            end=window.end,
            prev_event_location=window.prev_event_location,
            next_event_location=window.next_event_location,
        )


class Nutrition(BaseModel):
    calories: float
    protein_g: float
    fat_g: float
    carbs_g: float
    serving_size: str


class PlateItem(BaseModel):
    id: str
    name: str
    station: str
    is_vegetarian: bool
    allergens: list[str]
    nutrition: Optional[Nutrition]

    @classmethod
    def from_domain(cls, item: MenuItem) -> "PlateItem":
        n = item.nutrition
        return cls(
            id=item.id,
            name=item.name,
            station=item.station_name,
            is_vegetarian=item.is_vegetarian,
            allergens=item.allergens,
            nutrition=Nutrition(
                calories=n.calories, protein_g=n.protein_g, fat_g=n.fat_g, carbs_g=n.carbs_g, serving_size=n.serving_size
            )
            if n
            else None,
        )


class Scores(BaseModel):
    total: float
    nutrition: float
    time: float
    proximity: Optional[float] = Field(description="null when your location around the window is unknown")


class RecommendationOut(BaseModel):
    rank: int
    dining_hall: str
    meal: str
    window: Window
    scores: Scores
    plate: list[PlateItem]

    @classmethod
    def from_domain(cls, rank: int, rec: Recommendation) -> "RecommendationOut":
        return cls(
            rank=rank,
            dining_hall=rec.dining_hall_name,
            meal=rec.meal_name,
            window=Window.from_domain(rec.window),
            scores=Scores(
                total=rec.total_score, nutrition=rec.nutrition_score, time=rec.time_score, proximity=rec.proximity_score
            ),
            plate=[PlateItem.from_domain(item) for item in rec.suggested_items],
        )


class Goal(BaseModel):
    protein_g: float
    calories: float


class RecommendationsResponse(BaseModel):
    date: Date
    meal: Optional[str]
    goal_per_meal: Goal
    windows: list[Window]
    recommendations: list[RecommendationOut]
    notice: Optional[str] = None
    warnings: list[str] = []

    @classmethod
    def from_domain(cls, plan: DayPlan) -> "RecommendationsResponse":
        return cls(
            date=plan.date,
            meal=plan.meal,
            goal_per_meal=Goal(protein_g=plan.goal_per_meal.protein_target_g, calories=plan.goal_per_meal.calorie_limit),
            windows=[Window.from_domain(w) for w in plan.windows],
            recommendations=[RecommendationOut.from_domain(i, r) for i, r in enumerate(plan.recommendations, start=1)],
            notice=plan.notice,
            warnings=plan.warnings,
        )


class MealsResponse(BaseModel):
    date: Date
    meals: list[str]


class MetaResponse(BaseModel):
    calendar_source: Literal["ical", "google", "none"]


class ErrorBody(BaseModel):
    code: str
    message: str
    fields: Optional[dict[str, str]] = None


class ErrorResponse(BaseModel):
    error: ErrorBody
