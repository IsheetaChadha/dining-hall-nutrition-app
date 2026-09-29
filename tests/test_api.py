from datetime import date, datetime, time, timezone

import pytest
import requests
from fastapi.testclient import TestClient

from dining_planner.api import deps
from dining_planner.api.app import create_app
from dining_planner.models import AvailabilityWindow
from dining_planner.settings_store import SettingsStore
from tests.factories import FixedCalendar, make_hall, make_item

TZ = timezone.utc
TODAY = date(2026, 9, 29)
NOW = datetime(2026, 9, 29, 9, 0, tzinfo=TZ)


def lunch_and_dinner_hall(name, on_date=TODAY, fail=False, items=None):
    items = items or [make_item("Chicken", calories=300, protein_g=45, fat_g=6)]
    return make_hall(
        name, on_date, [("Lunch", time(11), time(14), items), ("Dinner", time(17), time(20), items)], fail=fail
    )


def free_all_day(on_date=TODAY):
    return FixedCalendar(
        [AvailabilityWindow(start=datetime.combine(on_date, time(7), tzinfo=TZ), end=datetime.combine(on_date, time(21), tzinfo=TZ))]
    )


@pytest.fixture
def env(tmp_path):
    """Overridable collaborators for one test: halls, calendar, clock and a temp settings DB."""

    class Env:
        halls = [lunch_and_dinner_hall("Wiley"), lunch_and_dinner_hall("Ford")]
        calendar = free_all_day()
        calendar_source = "ical"
        now = NOW
        store = SettingsStore(str(tmp_path / "app.db"))

    app = create_app(serve_web=False)
    app.dependency_overrides[deps.get_halls] = lambda: Env.halls
    app.dependency_overrides[deps.get_calendar] = lambda: Env.calendar
    app.dependency_overrides[deps.get_calendar_source] = lambda: Env.calendar_source
    app.dependency_overrides[deps.get_now] = lambda: Env.now
    app.dependency_overrides[deps.get_settings_store] = lambda: Env.store
    Env.client = TestClient(app)
    return Env


# ---- settings ---------------------------------------------------------------


def test_get_settings_returns_the_defaults_for_a_new_user(env):
    body = env.client.get("/api/v1/settings").json()

    assert body["protein_target_g"] == 100
    assert body["meals_per_day"] == 3
    assert body["day_start"] == "07:00"
    assert "beef" in body["restricted_keywords"]
    assert body["building_coords"]["WALC"] == [40.4274, -86.9132]


def test_put_settings_saves_normalized_values(env):
    settings = env.client.get("/api/v1/settings").json()
    settings.update(
        protein_target_g=130,
        restricted_keywords=[" Beef ", "beef", "Pork"],
        building_coords={"lwsn": [40.4278, -86.9170]},
    )

    saved = env.client.put("/api/v1/settings", json=settings)

    assert saved.status_code == 200
    body = env.client.get("/api/v1/settings").json()
    assert body["protein_target_g"] == 130
    assert body["restricted_keywords"] == ["beef", "pork"]
    assert body["building_coords"] == {"LWSN": [40.4278, -86.9170]}


def test_put_settings_rejects_bad_values_with_field_errors(env):
    settings = env.client.get("/api/v1/settings").json()
    settings.update(protein_target_g=0, meals_per_day=9, building_coords={"WALC": [140, -86.9]})

    resp = env.client.put("/api/v1/settings", json=settings)

    assert resp.status_code == 422
    error = resp.json()["error"]
    assert error["code"] == "invalid_settings"
    assert set(error["fields"]) == {"protein_target_g", "meals_per_day", "building_coords.WALC"}


def test_put_settings_rejects_a_day_that_ends_before_it_starts(env):
    settings = env.client.get("/api/v1/settings").json()
    settings.update(day_start="20:00", day_end="08:00")

    resp = env.client.put("/api/v1/settings", json=settings)

    assert resp.status_code == 422
    assert "day_end" in resp.json()["error"]["fields"]


def test_put_settings_rejects_a_blank_keyword(env):
    settings = env.client.get("/api/v1/settings").json()
    settings.update(restricted_keywords=["beef", "  "])

    resp = env.client.put("/api/v1/settings", json=settings)

    assert resp.status_code == 422
    assert "restricted_keywords" in resp.json()["error"]["fields"]


# ---- recommendations ----------------------------------------------------------


def test_recommendations_default_to_now_and_rank_remaining_meals(env):
    body = env.client.post("/api/v1/recommendations", json={}).json()

    assert body["date"] == "2026-09-29"
    assert body["meal"] is None
    assert {(r["dining_hall"], r["meal"]) for r in body["recommendations"]} == {
        ("Wiley", "Lunch"), ("Wiley", "Dinner"), ("Ford", "Lunch"), ("Ford", "Dinner")
    }
    assert [r["rank"] for r in body["recommendations"]] == [1, 2, 3, 4]
    first = body["recommendations"][0]
    assert set(first["scores"]) == {"total", "nutrition", "time", "proximity"}
    assert first["plate"][0]["name"] == "Chicken"
    assert first["plate"][0]["nutrition"]["protein_g"] == 45
    assert body["windows"][0]["start"] == "2026-09-29T09:00:00Z"


def test_recommendations_goal_falls_back_to_saved_settings(env):
    settings = env.client.get("/api/v1/settings").json()
    settings.update(protein_target_g=120, calorie_limit=1500, meals_per_day=3)
    env.client.put("/api/v1/settings", json=settings)

    body = env.client.post("/api/v1/recommendations", json={"calories": 1800}).json()

    assert body["goal_per_meal"] == {"protein_g": 40, "calories": 600}


def test_recommendations_for_one_meal_on_a_chosen_date(env):
    tomorrow = date(2026, 9, 30)
    env.halls = [lunch_and_dinner_hall("Wiley", on_date=tomorrow)]
    env.calendar = free_all_day(tomorrow)

    body = env.client.post("/api/v1/recommendations", json={"date": "2026-09-30", "meal": "Dinner"}).json()

    assert [(r["dining_hall"], r["meal"]) for r in body["recommendations"]] == [("Wiley", "Dinner")]
    assert env.calendar.calls[0][0] == tomorrow


def test_recommendations_for_a_meal_that_already_ended(env):
    env.now = datetime(2026, 9, 29, 15, 0, tzinfo=TZ)

    resp = env.client.post("/api/v1/recommendations", json={"meal": "Lunch"})

    assert resp.status_code == 200
    assert resp.json()["recommendations"] == []
    assert resp.json()["notice"] == "Lunch has ended for today."


def test_recommendations_report_a_skipped_hall(env):
    env.halls = [lunch_and_dinner_hall("Wiley"), lunch_and_dinner_hall("Ford", fail=True)]

    body = env.client.post("/api/v1/recommendations", json={}).json()

    assert {r["dining_hall"] for r in body["recommendations"]} == {"Wiley"}
    assert body["warnings"] == ["Couldn't load the Ford menu, so it was skipped."]


def test_recommendations_without_a_calendar_is_a_conflict(env):
    env.calendar = None

    resp = env.client.post("/api/v1/recommendations", json={})

    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "calendar_not_configured"


def test_recommendations_when_every_hall_fails_is_a_bad_gateway(env):
    env.halls = [lunch_and_dinner_hall("Wiley", fail=True)]

    resp = env.client.post("/api/v1/recommendations", json={})

    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "upstream_unavailable"


def test_recommendations_reject_a_non_positive_goal(env):
    resp = env.client.post("/api/v1/recommendations", json={"protein": -5})

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "invalid_request"
    assert "protein" in resp.json()["error"]["fields"]


# ---- meals & meta --------------------------------------------------------------


def test_meals_lists_the_days_meal_names_in_order(env):
    body = env.client.get("/api/v1/meals", params={"date": "2026-09-29"}).json()

    assert body == {"date": "2026-09-29", "meals": ["Lunch", "Dinner"]}


def test_meals_default_to_today(env):
    assert env.client.get("/api/v1/meals").json()["date"] == "2026-09-29"


def test_meta_reports_the_calendar_source(env):
    env.calendar_source = "none"

    assert env.client.get("/api/v1/meta").json() == {"calendar_source": "none"}


def test_hall_list_outage_is_a_bad_gateway(env):
    def broken_halls():
        raise requests.ConnectionError("api.hfs.purdue.edu unreachable")

    env.client.app.dependency_overrides[deps.get_halls] = broken_halls

    resp = env.client.get("/api/v1/meals")

    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "upstream_unavailable"


def test_unknown_api_route_uses_the_error_shape(env):
    resp = env.client.get("/api/v1/nope")

    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"
