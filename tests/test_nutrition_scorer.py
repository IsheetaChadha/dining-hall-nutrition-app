from dining_planner.dietary_filter import DietaryFilter
from dining_planner.models import MenuItem, NutritionInfo
from dining_planner.nutrition_goal import NutritionGoal
from dining_planner.nutrition_scorer import NutritionScorer


def make_item(name, calories, protein_g, fat_g, carbs_g=0.0, ingredients="", serving_size=""):
    return MenuItem(
        id=name,
        name=name,
        station_name="Station",
        meal_name="Lunch",
        is_vegetarian=False,
        ingredients_text=ingredients,
        nutrition=NutritionInfo(calories=calories, protein_g=protein_g, fat_g=fat_g, carbs_g=carbs_g, serving_size=serving_size),
    )


def test_best_plate_respects_calorie_cap():
    items = [
        make_item("Chicken Breast", calories=200, protein_g=40, fat_g=5),
        make_item("Rice", calories=200, protein_g=5, fat_g=1),
        make_item("Fries", calories=500, protein_g=3, fat_g=25),
    ]
    goal = NutritionGoal(protein_target_g=100, calorie_limit=450)
    scorer = NutritionScorer()
    selected, totals = scorer.best_plate(items, goal)
    assert totals.calories <= 450
    assert {i.name for i in selected} == {"Chicken Breast", "Rice"}


def test_best_plate_always_includes_at_least_one_item_even_if_it_exceeds_cap_alone():
    items = [make_item("Giant Burger", calories=900, protein_g=50, fat_g=40)]
    goal = NutritionGoal(protein_target_g=50, calorie_limit=500)
    scorer = NutritionScorer()
    selected, totals = scorer.best_plate(items, goal)
    assert len(selected) == 1
    assert totals.calories == 900


def test_best_plate_excludes_dietary_restricted_items():
    items = [
        make_item("Bacon", calories=100, protein_g=10, fat_g=8),
        make_item("Turkey Slices", calories=100, protein_g=15, fat_g=2),
    ]
    goal = NutritionGoal(protein_target_g=50, calorie_limit=1000, dietary_filter=DietaryFilter())
    scorer = NutritionScorer()
    selected, _ = scorer.best_plate(items, goal)
    assert {i.name for i in selected} == {"Turkey Slices"}


def test_best_plate_ignores_items_without_nutrition_data():
    no_nutrition = MenuItem(id="mystery", name="Mystery Dish", station_name="S", meal_name="Lunch", is_vegetarian=False)
    items = [no_nutrition, make_item("Chicken", calories=200, protein_g=30, fat_g=5)]
    goal = NutritionGoal(protein_target_g=50, calorie_limit=1000)
    scorer = NutritionScorer()
    selected, _ = scorer.best_plate(items, goal)
    assert [i.name for i in selected] == ["Chicken"]


def test_score_rewards_hitting_protein_target_and_penalizes_fat():
    high_protein_low_fat = [make_item("Lean Chicken", calories=200, protein_g=100, fat_g=2)]
    high_fat = [make_item("Fatty Sausage", calories=200, protein_g=100, fat_g=90)]
    goal = NutritionGoal(protein_target_g=100, calorie_limit=1000)
    scorer = NutritionScorer()

    lean_score, _ = scorer.score(high_protein_low_fat, goal)
    fatty_score, _ = scorer.score(high_fat, goal)
    assert lean_score > fatty_score


def test_best_plate_dedupes_same_item_listed_at_multiple_stations():
    shared_condiment = make_item("Shredded Lettuce", calories=5, protein_g=0.1, fat_g=0.0)
    duplicate_listing = MenuItem(
        id=shared_condiment.id,
        name=shared_condiment.name,
        station_name="Other Station",
        meal_name="Lunch",
        is_vegetarian=False,
        nutrition=shared_condiment.nutrition,
    )
    items = [shared_condiment, duplicate_listing, make_item("Chicken", calories=200, protein_g=40, fat_g=5)]
    goal = NutritionGoal(protein_target_g=50, calorie_limit=1000)
    scorer = NutritionScorer()
    selected, totals = scorer.best_plate(items, goal)
    assert [i.name for i in selected].count("Shredded Lettuce") == 1
    assert totals.calories == 205


def test_score_is_zero_when_no_eligible_items():
    goal = NutritionGoal(protein_target_g=100, calorie_limit=1000)
    scorer = NutritionScorer()
    score, plate = scorer.score([], goal)
    assert score == 0.0
    assert plate == []


def test_best_plate_is_built_around_a_main_dish_not_a_topping():
    # Parmesan has the best protein-per-calorie, but taking it first would leave no room for the entree.
    items = [
        make_item("Grated Parmesan Cheese", calories=113, protein_g=11.3, fat_g=7, serving_size="Ounce"),
        make_item("Indian Butter Chicken", calories=431, protein_g=25.1, fat_g=20, serving_size="6 oz Ladle"),
    ]
    goal = NutritionGoal(protein_target_g=35, calorie_limit=500)
    selected, _ = NutritionScorer().best_plate(items, goal)
    assert [i.name for i in selected] == ["Indian Butter Chicken"]


def test_best_plate_stops_adding_items_once_protein_target_is_met():
    items = [
        make_item("Chicken Breast", calories=200, protein_g=40, fat_g=5),
        make_item("Shredded Cheddar", calories=110, protein_g=7, fat_g=9, serving_size="Ounce"),
    ]
    goal = NutritionGoal(protein_target_g=35, calorie_limit=600)
    selected, _ = NutritionScorer().best_plate(items, goal)
    assert [i.name for i in selected] == ["Chicken Breast"]
