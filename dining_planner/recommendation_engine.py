"""Combines dining hall menus + nutrition goal + calendar availability into ranked picks.

For each free-time window, finds every (dining hall, meal) whose open hours overlap
the window, scores it on nutrition fit / time fit / proximity, and combines those via
config.SCORE_WEIGHTS (which reflects the stated priority: Nutrition > Time > Proximity).
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional

from . import config
from .dining_hall import DiningHall
from .models import AvailabilityWindow, Recommendation
from .nutrition_goal import NutritionGoal
from .nutrition_scorer import NutritionScorer

REASONABLE_MEAL_MINUTES = 30.0
PROXIMITY_FAR_MILES = 2.0
UNKNOWN_LOCATION_PROXIMITY_SCORE = 0.5


class RecommendationEngine:
    def __init__(
        self,
        dining_halls: list[DiningHall],
        scorer: Optional[NutritionScorer] = None,
        building_coords: Optional[dict[str, tuple[float, float]]] = None,
        weights: Optional[dict[str, float]] = None,
    ):
        self.dining_halls = dining_halls
        self.scorer = scorer or NutritionScorer()
        self.building_coords = building_coords if building_coords is not None else config.BUILDING_COORDS
        self.weights = weights or config.SCORE_WEIGHTS

    def recommend(
        self,
        on_date: date,
        windows: list[AvailabilityWindow],
        goal: NutritionGoal,
    ) -> list[Recommendation]:
        recommendations: list[Recommendation] = []
        for window in windows:
            for hall in self.dining_halls:
                for meal_name, (meal_start, meal_end) in hall.open_meal_windows_on(on_date).items():
                    overlap_minutes = self._overlap_minutes(window, on_date, meal_start, meal_end)
                    if overlap_minutes <= 0:
                        continue

                    menu = hall.get_menu(on_date)
                    meal = menu.meals.get(meal_name)
                    if not meal:
                        continue

                    nutrition_score, plate = self.scorer.score(meal.items, goal)
                    if not plate:
                        continue

                    time_score = min(overlap_minutes / REASONABLE_MEAL_MINUTES, 1.0)
                    proximity_score = self._proximity_score(hall, window)

                    total_score = (
                        self.weights["nutrition"] * nutrition_score
                        + self.weights["time"] * time_score
                        + self.weights["proximity"] * proximity_score
                    )
                    recommendations.append(
                        Recommendation(
                            dining_hall_name=hall.name,
                            meal_name=meal_name,
                            window=window,
                            nutrition_score=nutrition_score,
                            time_score=time_score,
                            proximity_score=proximity_score,
                            total_score=total_score,
                            suggested_items=plate,
                        )
                    )

        recommendations.sort(key=lambda r: r.total_score, reverse=True)
        # A meal overlapping several free windows would otherwise repeat; keep its best window.
        best: dict[tuple[str, str], Recommendation] = {}
        for rec in recommendations:
            best.setdefault((rec.dining_hall_name, rec.meal_name), rec)
        return list(best.values())

    def _overlap_minutes(self, window: AvailabilityWindow, on_date: date, meal_start: time, meal_end: time) -> float:
        tz = window.start.tzinfo
        meal_start_dt = datetime.combine(on_date, meal_start, tzinfo=tz)
        meal_end_dt = datetime.combine(on_date, meal_end, tzinfo=tz)
        latest_start = max(window.start, meal_start_dt)
        earliest_end = min(window.end, meal_end_dt)
        return max(0.0, (earliest_end - latest_start).total_seconds() / 60)

    def _proximity_score(self, hall: DiningHall, window: AvailabilityWindow) -> float:
        coords = self._coords_for(window.prev_event_location) or self._coords_for(window.next_event_location)
        if coords is None:
            return UNKNOWN_LOCATION_PROXIMITY_SCORE
        distance = hall.distance_to(*coords)
        return max(0.0, 1.0 - distance / PROXIMITY_FAR_MILES)

    def _coords_for(self, location: Optional[str]) -> Optional[tuple[float, float]]:
        # Exact match first, then the building code before the room number ("WALC 2121" -> "WALC").
        if not location:
            return None
        return self.building_coords.get(location) or self.building_coords.get(location.split()[0])
