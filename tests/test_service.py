from datetime import date, datetime, time, timezone

import pytest

from dining_planner.models import AvailabilityWindow
from dining_planner.service import (
    CalendarNotConfiguredError,
    UpstreamUnavailableError,
    available_meals,
    calendar_source_name,
    configured_calendar,
    plan_day,
)
from dining_planner.settings_store import UserSettings
from tests.factories import FixedCalendar, make_hall, make_item

TZ = timezone.utc
TODAY = date(2026, 9, 29)
TOMORROW = date(2026, 9, 30)
CHICKEN = [make_item("Chicken")]


def window(on_date, start_h, end_h, prev_loc=None):
    return AvailabilityWindow(
        start=datetime.combine(on_date, time(start_h), tzinfo=TZ),
        end=datetime.combine(on_date, time(end_h), tzinfo=TZ),
        prev_event_location=prev_loc,
    )


def three_meal_hall(name, on_date=TODAY, items=CHICKEN, **kwargs):
    return make_hall(
        name,
        on_date,
        [
            ("Breakfast", time(7), time(10), items),
            ("Lunch", time(11), time(14), items),
            ("Dinner", time(17), time(20), items),
        ],
        **kwargs,
    )


def settings(**overrides):
    return UserSettings.defaults().with_updates(**overrides)


def at(hour, minute=0, on_date=TODAY):
    return datetime.combine(on_date, time(hour, minute), tzinfo=TZ)


def test_defaults_to_today_and_skips_meals_already_over():
    calendar = FixedCalendar([window(TODAY, 7, 21)])

    plan = plan_day([three_meal_hall("Hall")], calendar, settings(), now=at(15))

    assert plan.date == TODAY
    assert calendar.calls[0][0] == TODAY
    assert [r.meal_name for r in plan.recommendations] == ["Dinner"]
    assert plan.windows[0].start == at(15)


def test_future_date_ranks_every_meal_without_clipping():
    calendar = FixedCalendar([window(TOMORROW, 7, 21)])

    plan = plan_day([three_meal_hall("Hall", TOMORROW)], calendar, settings(), on_date=TOMORROW, now=at(15))

    assert sorted(r.meal_name for r in plan.recommendations) == ["Breakfast", "Dinner", "Lunch"]
    assert plan.windows[0].start == at(7, on_date=TOMORROW)


def test_calendar_is_read_with_the_settings_day_hours():
    calendar = FixedCalendar([window(TODAY, 7, 21)])

    plan_day([three_meal_hall("Hall")], calendar, settings(day_start=time(8), day_end=time(19)), now=at(6))

    assert calendar.calls == [(TODAY, time(8), time(19))]


def test_meal_filter_limits_to_that_meal():
    calendar = FixedCalendar([window(TOMORROW, 7, 21)])

    plan = plan_day(
        [three_meal_hall("Hall", TOMORROW)], calendar, settings(), on_date=TOMORROW, meal="lunch", now=at(15)
    )

    assert [r.meal_name for r in plan.recommendations] == ["Lunch"]
    assert plan.notice is None


def test_meal_that_already_ended_today_gives_a_notice():
    calendar = FixedCalendar([window(TODAY, 7, 21)])

    plan = plan_day([three_meal_hall("Hall")], calendar, settings(), meal="Lunch", now=at(15))

    assert plan.recommendations == []
    assert plan.notice == "Lunch has ended for today."


def test_every_meal_over_for_today_gives_a_notice():
    calendar = FixedCalendar([window(TODAY, 7, 22)])

    plan = plan_day([three_meal_hall("Hall")], calendar, settings(), now=at(21))

    assert plan.recommendations == []
    assert plan.notice == "Every dining hall meal has ended for today."


def test_meal_not_served_that_day_gives_a_notice():
    calendar = FixedCalendar([window(TODAY, 7, 21)])

    plan = plan_day([three_meal_hall("Hall")], calendar, settings(), meal="Brunch", now=at(6))

    assert plan.recommendations == []
    assert plan.notice == "No dining hall serves Brunch on 2026-09-29."


def test_no_free_time_gives_a_notice():
    calendar = FixedCalendar([])

    plan = plan_day([three_meal_hall("Hall")], calendar, settings(), now=at(6))

    assert plan.recommendations == []
    assert plan.notice == "No free time found on 2026-09-29."


def test_goal_falls_back_to_settings_split_per_meal():
    calendar = FixedCalendar([window(TODAY, 7, 21)])

    plan = plan_day(
        [three_meal_hall("Hall")], calendar, settings(protein_target_g=120, calorie_limit=1800, meals_per_day=3), now=at(6)
    )

    assert plan.goal_per_meal.protein_target_g == pytest.approx(40)
    assert plan.goal_per_meal.calorie_limit == pytest.approx(600)


def test_explicit_goal_overrides_settings():
    calendar = FixedCalendar([window(TODAY, 7, 21)])

    plan = plan_day(
        [three_meal_hall("Hall")], calendar, settings(), protein=90, calories=1500, meals_per_day=2, now=at(6)
    )

    assert plan.goal_per_meal.protein_target_g == pytest.approx(45)
    assert plan.goal_per_meal.calorie_limit == pytest.approx(750)


def test_restricted_keywords_come_from_settings():
    calendar = FixedCalendar([window(TODAY, 7, 21)])
    hall = three_meal_hall("Hall", items=[make_item("Beef Stew"), make_item("Tofu Bowl", protein_g=10)])

    restricted = plan_day([hall], calendar, settings(restricted_keywords=["beef"]), meal="Lunch", now=at(6))
    unrestricted = plan_day([hall], calendar, settings(restricted_keywords=[]), meal="Lunch", now=at(6))

    assert "Beef Stew" not in [i.name for i in restricted.recommendations[0].suggested_items]
    assert "Beef Stew" in [i.name for i in unrestricted.recommendations[0].suggested_items]


def test_building_coords_come_from_settings():
    calendar = FixedCalendar([window(TODAY, 11, 13, prev_loc="ABC 101")])

    plan = plan_day(
        [three_meal_hall("Hall")], calendar, settings(building_coords={"ABC": (40.0, -86.0)}), now=at(6)
    )

    assert plan.recommendations[0].proximity_score == 1.0


def test_a_failing_hall_is_skipped_with_a_warning():
    calendar = FixedCalendar([window(TODAY, 7, 21)])
    halls = [three_meal_hall("Good"), three_meal_hall("Broken", fail=True)]

    plan = plan_day(halls, calendar, settings(), meal="Lunch", now=at(6))

    assert [r.dining_hall_name for r in plan.recommendations] == ["Good"]
    assert plan.warnings == ["Couldn't load the Broken menu, so it was skipped."]


def test_every_hall_failing_raises_upstream_unavailable():
    calendar = FixedCalendar([window(TODAY, 7, 21)])

    with pytest.raises(UpstreamUnavailableError):
        plan_day([three_meal_hall("Broken", fail=True)], calendar, settings(), now=at(6))


def test_results_from_several_halls_are_ranked_by_total_score():
    calendar = FixedCalendar([window(TODAY, 7, 21)])
    weak = three_meal_hall("Weak", items=[make_item("Fries", protein_g=2, fat_g=40)])
    strong = three_meal_hall("Strong", items=[make_item("Lean Chicken", protein_g=100, fat_g=2)])

    plan = plan_day([weak, strong], calendar, settings(), meal="Lunch", now=at(6))

    assert [r.dining_hall_name for r in plan.recommendations] == ["Strong", "Weak"]


def test_missing_calendar_raises_calendar_not_configured():
    with pytest.raises(CalendarNotConfiguredError):
        plan_day([three_meal_hall("Hall")], None, settings(), now=at(6))


def test_explicit_windows_skip_the_calendar_and_are_not_clipped():
    plan = plan_day(
        [three_meal_hall("Hall")], None, settings(), windows=[window(TODAY, 11, 13)], now=at(15)
    )

    assert [r.meal_name for r in plan.recommendations] == ["Lunch"]


def test_available_meals_are_distinct_and_ordered_by_start_time():
    late = make_hall("Late", TODAY, [("Dinner", time(17), time(20), CHICKEN), ("Late Lunch", time(14), time(16), CHICKEN)])

    assert available_meals([three_meal_hall("Hall"), late], TODAY) == ["Breakfast", "Lunch", "Late Lunch", "Dinner"]


def test_ended_notice_uses_the_menu_spelling_of_the_meal():
    calendar = FixedCalendar([window(TODAY, 7, 21)])

    plan = plan_day([three_meal_hall("Hall")], calendar, settings(), meal="lunch", now=at(15))

    assert plan.notice == "Lunch has ended for today."


def test_meal_still_served_at_another_hall_has_not_ended():
    early = make_hall("Early", TODAY, [("Lunch", time(11), time(14), CHICKEN)])
    late = make_hall("Late", TODAY, [("Lunch", time(11), time(16), CHICKEN)])

    plan = plan_day([late, early], FixedCalendar([window(TODAY, 7, 15)]), settings(), meal="Lunch", now=at(15, 30))

    assert plan.notice == "No free time found on 2026-09-29."


@pytest.fixture
def credential_paths(tmp_path, monkeypatch):
    from dining_planner import config

    ical, secret = tmp_path / "calendar_url.txt", tmp_path / "client_secret.json"
    monkeypatch.setattr(config, "CALENDAR_URL_PATH", str(ical))
    monkeypatch.setattr(config, "CLIENT_SECRET_PATH", str(secret))
    return ical, secret


def test_calendar_source_is_none_without_credentials(credential_paths):
    assert calendar_source_name() == "none"
    assert configured_calendar() is None


def test_ical_url_file_wins_over_google_credentials(credential_paths):
    ical, secret = credential_paths
    ical.write_text("https://example.com/cal.ics")
    secret.write_text("{}")

    assert calendar_source_name() == "ical"


def test_google_credentials_alone_select_google(credential_paths):
    _ical, secret = credential_paths
    secret.write_text("{}")

    assert calendar_source_name() == "google"
