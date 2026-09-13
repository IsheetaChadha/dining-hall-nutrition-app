from dining_planner.dietary_filter import DietaryFilter
from dining_planner.models import MenuItem


def make_item(name: str, ingredients: str = "") -> MenuItem:
    return MenuItem(
        id="x",
        name=name,
        station_name="Station",
        meal_name="Lunch",
        is_vegetarian=False,
        ingredients_text=ingredients,
    )


def test_excludes_item_named_with_restricted_keyword():
    f = DietaryFilter()
    assert f.is_allowed(make_item("Grilled Chicken")) is True
    assert f.is_allowed(make_item("Pulled Pork Sandwich")) is False
    assert f.is_allowed(make_item("Beef Tacos")) is False


def test_excludes_based_on_ingredients_not_just_name():
    f = DietaryFilter()
    item = make_item("House Special Fried Rice", ingredients="Rice, Egg, Ham, Scallions")
    assert f.is_allowed(item) is False


def test_is_case_insensitive():
    f = DietaryFilter()
    assert f.is_allowed(make_item("BACON Bits")) is False


def test_word_boundary_avoids_false_positive_substrings():
    f = DietaryFilter()
    # "ham" is a restricted keyword but must not match inside "graham"
    assert f.is_allowed(make_item("Graham Cracker Pie Crust")) is True


def test_filter_items_keeps_only_allowed():
    f = DietaryFilter()
    items = [make_item("Grilled Chicken"), make_item("Bacon Strips"), make_item("Veggie Burger")]
    allowed = f.filter_items(items)
    assert [i.name for i in allowed] == ["Grilled Chicken", "Veggie Burger"]
