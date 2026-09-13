"""The day's nutrition target: maximize protein, stay under a calorie cap, minimize fat."""

from __future__ import annotations

from dataclasses import dataclass, field

from .dietary_filter import DietaryFilter


@dataclass
class NutritionGoal:
    protein_target_g: float
    calorie_limit: float
    minimize_fat: bool = True
    dietary_filter: DietaryFilter = field(default_factory=DietaryFilter)
