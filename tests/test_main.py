from datetime import date, datetime, time, timezone

from dining_planner.main import parse_args, settings_from_args
from dining_planner.models import AvailabilityWindow
from dining_planner.service import clip_to_now as _clip_to_now

TZ = timezone.utc
TODAY = date(2026, 9, 27)


def make_window(start_hm, end_hm, prev_loc=None, next_loc=None):
    start_h, start_m = start_hm
    end_h, end_m = end_hm
    return AvailabilityWindow(
        start=datetime(2026, 9, 27, start_h, start_m, tzinfo=TZ),
        end=datetime(2026, 9, 27, end_h, end_m, tzinfo=TZ),
        prev_event_location=prev_loc,
        next_event_location=next_loc,
    )


def test_drops_a_window_entirely_in_the_past():
    now = datetime(2026, 9, 27, 19, 47, tzinfo=TZ)
    windows = [make_window((7, 0), (14, 0))]

    result = _clip_to_now(windows, TODAY, now)

    assert result == []


def test_pulls_start_forward_to_now_for_a_window_straddling_now():
    now = datetime(2026, 9, 27, 19, 47, tzinfo=TZ)
    windows = [make_window((16, 0), (20, 0), prev_loc="WALC", next_loc="LWSN")]

    result = _clip_to_now(windows, TODAY, now)

    assert len(result) == 1
    assert result[0].start == now
    assert result[0].end == datetime(2026, 9, 27, 20, 0, tzinfo=TZ)
    assert result[0].prev_event_location == "WALC"
    assert result[0].next_event_location == "LWSN"


def test_leaves_a_future_window_unchanged():
    now = datetime(2026, 9, 27, 12, 0, tzinfo=TZ)
    windows = [make_window((16, 0), (20, 0))]

    result = _clip_to_now(windows, TODAY, now)

    assert result == windows


def test_leaves_windows_unchanged_when_on_date_is_not_today():
    now = datetime(2026, 9, 27, 19, 47, tzinfo=TZ)
    future_date = date(2026, 9, 28)
    windows = [make_window((7, 0), (14, 0))]

    result = _clip_to_now(windows, future_date, now)

    assert result == windows


def test_cli_args_become_settings_with_config_defaults_for_the_rest():
    args = parse_args(["--protein", "120", "--day-start", "08:30", "--meal", "Lunch"])

    settings = settings_from_args(args)

    assert settings.protein_target_g == 120
    assert settings.calorie_limit == 1800
    assert settings.day_start == time(8, 30)
    assert "beef" in settings.restricted_keywords
    assert args.meal == "Lunch"
