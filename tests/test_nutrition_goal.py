from dining_planner.dietary_filter import DietaryFilter
from dining_planner.nutrition_goal import NutritionGoal


def test_per_meal_splits_daily_targets_evenly_and_keeps_preferences():
    dietary_filter = DietaryFilter()
    daily = NutritionGoal(protein_target_g=120, calorie_limit=1800, minimize_fat=False, dietary_filter=dietary_filter)

    meal = daily.per_meal(3)

    assert (meal.protein_target_g, meal.calorie_limit) == (40, 600)
    assert meal.minimize_fat is False
    assert meal.dietary_filter is dietary_filter
