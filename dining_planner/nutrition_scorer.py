"""Turns a dining hall's available items into a "best plate" and a fit score.

`best_plate` is a greedy v1 heuristic (sort by protein-per-calorie, fill up to the
calorie cap). Good enough to rank dining halls against each other; swap for a real
knapsack solver later if you want the *exact* optimal combination.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import config
from .models import MenuItem
from .nutrition_goal import NutritionGoal


@dataclass
class PlateTotals:
    calories: float = 0.0
    protein_g: float = 0.0
    fat_g: float = 0.0
    carbs_g: float = 0.0


class NutritionScorer:
    def __init__(self, max_plate_items: int = config.MAX_PLATE_ITEMS):
        self.max_plate_items = max_plate_items

    def best_plate(self, items: list[MenuItem], goal: NutritionGoal) -> tuple[list[MenuItem], PlateTotals]:
        # The same food is sometimes listed at multiple stations (e.g. a shared
        # condiment bar); dedupe by item id so it isn't double-counted as two servings.
        deduped: dict[str, MenuItem] = {}
        for item in items:
            deduped.setdefault(item.id, item)

        candidates = [item for item in deduped.values() if goal.dietary_filter.is_allowed(item) and item.nutrition]
        candidates.sort(key=_protein_per_calorie, reverse=True)

        # Anchor the plate on the most protein-efficient main dish that fits the calorie budget.
        mains = [
            item
            for item in candidates
            if not _is_topping(item) and item.nutrition.calories <= goal.calorie_limit
        ]
        if mains:
            anchor = max(mains, key=_protein_per_calorie)
            candidates.remove(anchor)
            candidates.insert(0, anchor)

        selected: list[MenuItem] = []
        totals = PlateTotals()
        for item in candidates:
            if len(selected) >= self.max_plate_items:
                break
            projected_calories = totals.calories + item.nutrition.calories
            if projected_calories > goal.calorie_limit and selected:
                continue
            selected.append(item)
            totals.calories += item.nutrition.calories
            totals.protein_g += item.nutrition.protein_g
            totals.fat_g += item.nutrition.fat_g
            totals.carbs_g += item.nutrition.carbs_g
            if totals.calories >= goal.calorie_limit:
                break
            if goal.protein_target_g > 0 and totals.protein_g >= goal.protein_target_g:
                break  # protein score is capped at the target; more items would only add fat

        return selected, totals

    def score(self, items: list[MenuItem], goal: NutritionGoal) -> tuple[float, list[MenuItem]]:
        """Returns (nutrition_score in [0, 1], suggested plate) for one dining-hall/meal candidate."""
        selected, totals = self.best_plate(items, goal)
        if not selected:
            return 0.0, []

        protein_score = min(totals.protein_g / goal.protein_target_g, 1.0) if goal.protein_target_g > 0 else 0.0

        if totals.calories <= goal.calorie_limit:
            calorie_score = 1.0
        else:
            overage = totals.calories - goal.calorie_limit
            calorie_score = max(0.0, 1.0 - overage / goal.calorie_limit)

        fat_score = max(0.0, 1.0 - totals.fat_g / config.FAT_SOFT_CEILING_G) if goal.minimize_fat else 1.0

        weights = config.NUTRITION_SUBWEIGHTS
        nutrition_score = (
            weights["protein"] * protein_score
            + weights["calories"] * calorie_score
            + weights["fat"] * fat_score
        )
        return nutrition_score, selected


def _is_topping(item: MenuItem) -> bool:
    return item.nutrition.serving_size.strip().lower() in config.TOPPING_SERVING_SIZES


def _protein_per_calorie(item: MenuItem) -> float:
    return item.nutrition.protein_g / max(item.nutrition.calories, 1.0)
