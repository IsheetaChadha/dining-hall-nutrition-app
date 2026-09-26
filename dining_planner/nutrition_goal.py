"""The day's nutrition target: maximize protein, stay under a calorie cap, minimize fat."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from .dietary_filter import DietaryFilter


@dataclass
class NutritionGoal:
    protein_target_g: float
    calorie_limit: float
    minimize_fat: bool = True
    dietary_filter: DietaryFilter = field(default_factory=DietaryFilter)

    def per_meal(self, meals_per_day: int) -> "NutritionGoal":
        """This day's goal split evenly across meals, since each plate is one meal."""
        return replace(
            self,
            protein_target_g=self.protein_target_g / meals_per_day,
            calorie_limit=self.calorie_limit / meals_per_day,
        )
