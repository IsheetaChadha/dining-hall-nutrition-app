from datetime import date, datetime, time, timezone

from dining_planner.dining_hall import DiningHall
from dining_planner.models import AvailabilityWindow, DailyMenu, Meal, MenuItem, NutritionInfo
from dining_planner.nutrition_goal import NutritionGoal
from dining_planner.recommendation_engine import RecommendationEngine

TZ = timezone.utc
ON_DATE = date(2026, 9, 8)


def make_item(name, calories, protein_g, fat_g):
    return MenuItem(
        id=name,
        name=name,
        station_name="Station",
        meal_name="Lunch",
        is_vegetarian=False,
        nutrition=NutritionInfo(calories=calories, protein_g=protein_g, fat_g=fat_g, carbs_g=0.0),
    )


class FakeDiningClient:
    """Stands in for PurdueDiningClient: DailyMenu is supplied directly, no HTTP."""

    def __init__(self, menu: DailyMenu):
        self._menu = menu

    def get_daily_menu(self, hall_name, on_date):
        return self._menu

    def fetch_nutrition_for_menu(self, menu):
        pass


def make_hall(name, latitude, longitude, meal_name, start, end, items) -> DiningHall:
    menu = DailyMenu(dining_hall_name=name, date=ON_DATE, meals={meal_name: Meal(name=meal_name, start_time=start, end_time=end, items=items)})
    client = FakeDiningClient(menu)
    normal_hours = [
        {
            "EffectiveDate": "2020-01-01T00:00:00",
            "Days": [
                {
                    "Name": ON_DATE.strftime("%A"),
                    "Meals": [
                        {
                            "Name": meal_name,
                            "Status": "Open",
                            "Hours": {"StartTime": start.strftime("%H:%M:%S"), "EndTime": end.strftime("%H:%M:%S")},
                        }
                    ],
                }
            ],
        }
    ]
    return DiningHall(
        location_id=name.upper(),
        name=name,
        hall_type="Dining Courts",
        address="123 Main St",
        latitude=latitude,
        longitude=longitude,
        phone="",
        normal_hours=normal_hours,
        _client=client,
    )


def test_recommend_finds_overlapping_meal_and_scores_it():
    hall = make_hall(
        "Near Hall", 40.0, -86.0, "Lunch", time(11, 0), time(14, 0), [make_item("Chicken", 200, 40, 5)]
    )
    window = AvailabilityWindow(
        start=datetime.combine(ON_DATE, time(12, 0), tzinfo=TZ),
        end=datetime.combine(ON_DATE, time(13, 0), tzinfo=TZ),
    )
    goal = NutritionGoal(protein_target_g=40, calorie_limit=500)
    engine = RecommendationEngine([hall], building_coords={})

    recs = engine.recommend(ON_DATE, [window], goal)
    assert len(recs) == 1
    assert recs[0].dining_hall_name == "Near Hall"
    assert recs[0].meal_name == "Lunch"
    assert recs[0].suggested_items[0].name == "Chicken"


def test_recommend_skips_meals_outside_the_availability_window():
    hall = make_hall("Hall", 40.0, -86.0, "Dinner", time(17, 0), time(20, 0), [make_item("Chicken", 200, 40, 5)])
    window = AvailabilityWindow(
        start=datetime.combine(ON_DATE, time(9, 0), tzinfo=TZ),
        end=datetime.combine(ON_DATE, time(10, 0), tzinfo=TZ),
    )
    goal = NutritionGoal(protein_target_g=40, calorie_limit=500)
    engine = RecommendationEngine([hall], building_coords={})

    recs = engine.recommend(ON_DATE, [window], goal)
    assert recs == []


def test_recommend_ranks_better_nutrition_fit_higher():
    good_hall = make_hall("Good Hall", 40.0, -86.0, "Lunch", time(11, 0), time(14, 0), [make_item("Lean Chicken", 200, 100, 2)])
    bad_hall = make_hall("Bad Hall", 40.0, -86.0, "Lunch", time(11, 0), time(14, 0), [make_item("Fatty Fries", 200, 2, 40)])
    window = AvailabilityWindow(
        start=datetime.combine(ON_DATE, time(12, 0), tzinfo=TZ),
        end=datetime.combine(ON_DATE, time(13, 0), tzinfo=TZ),
    )
    goal = NutritionGoal(protein_target_g=100, calorie_limit=500)
    engine = RecommendationEngine([good_hall, bad_hall], building_coords={})

    recs = engine.recommend(ON_DATE, [window], goal)
    assert recs[0].dining_hall_name == "Good Hall"
    assert recs[0].total_score > recs[1].total_score


def test_proximity_score_favors_closer_hall_when_location_known():
    close_hall = make_hall("Close Hall", 40.0, -86.0, "Lunch", time(11, 0), time(14, 0), [make_item("Chicken", 200, 40, 5)])
    far_hall = make_hall("Far Hall", 41.0, -87.0, "Lunch", time(11, 0), time(14, 0), [make_item("Chicken", 200, 40, 5)])
    window = AvailabilityWindow(
        start=datetime.combine(ON_DATE, time(12, 0), tzinfo=TZ),
        end=datetime.combine(ON_DATE, time(13, 0), tzinfo=TZ),
        prev_event_location="MyBuilding",
    )
    goal = NutritionGoal(protein_target_g=40, calorie_limit=500)
    engine = RecommendationEngine([close_hall, far_hall], building_coords={"MyBuilding": (40.0, -86.0)})

    recs = engine.recommend(ON_DATE, [window], goal)
    by_name = {r.dining_hall_name: r for r in recs}
    assert by_name["Close Hall"].proximity_score > by_name["Far Hall"].proximity_score
    assert recs[0].dining_hall_name == "Close Hall"


def test_unknown_location_gets_neutral_proximity_score():
    hall = make_hall("Hall", 40.0, -86.0, "Lunch", time(11, 0), time(14, 0), [make_item("Chicken", 200, 40, 5)])
    window = AvailabilityWindow(
        start=datetime.combine(ON_DATE, time(12, 0), tzinfo=TZ),
        end=datetime.combine(ON_DATE, time(13, 0), tzinfo=TZ),
        prev_event_location="Somewhere Unmapped",
    )
    goal = NutritionGoal(protein_target_g=40, calorie_limit=500)
    engine = RecommendationEngine([hall], building_coords={})

    recs = engine.recommend(ON_DATE, [window], goal)
    assert recs[0].proximity_score == 0.5


def test_location_with_room_number_matches_building_code():
    hall = make_hall("Hall", 40.0, -86.0, "Lunch", time(11, 0), time(14, 0), [make_item("Chicken", 200, 40, 5)])
    window = AvailabilityWindow(
        start=datetime.combine(ON_DATE, time(12, 0), tzinfo=TZ),
        end=datetime.combine(ON_DATE, time(13, 0), tzinfo=TZ),
        prev_event_location="WALC 2121",
    )
    goal = NutritionGoal(protein_target_g=40, calorie_limit=500)
    engine = RecommendationEngine([hall], building_coords={"WALC": (40.0, -86.0)})

    recs = engine.recommend(ON_DATE, [window], goal)
    assert recs[0].proximity_score == 1.0
