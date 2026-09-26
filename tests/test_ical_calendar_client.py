from datetime import date, datetime, time, timedelta, timezone

from dining_planner.ical_calendar_client import ICalCalendarClient

EST = timezone(timedelta(hours=-4))

# Weekly MWF class (with one cancelled occurrence), a one-off Tuesday event,
# and an all-day event that must not block availability.
SAMPLE_ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//test//EN
BEGIN:VEVENT
UID:cs180
SUMMARY:CS 180
LOCATION:WALC 1055
DTSTART;TZID=America/Indiana/Indianapolis:20260831T093000
DTEND;TZID=America/Indiana/Indianapolis:20260831T102000
RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR;UNTIL=20261211T235959Z
EXDATE;TZID=America/Indiana/Indianapolis:20260909T093000
END:VEVENT
BEGIN:VEVENT
UID:ma261
SUMMARY:MA 261
LOCATION:MATH 175
DTSTART;TZID=America/Indiana/Indianapolis:20260908T130000
DTEND;TZID=America/Indiana/Indianapolis:20260908T141500
END:VEVENT
BEGIN:VEVENT
UID:holiday
SUMMARY:Some All-Day Thing
DTSTART;VALUE=DATE:20260908
DTEND;VALUE=DATE:20260909
END:VEVENT
END:VCALENDAR
"""


def make_client():
    return ICalCalendarClient(url="https://example.invalid/basic.ics", fetch=lambda url: SAMPLE_ICS, tz=EST)


def test_expands_recurring_event_onto_matching_day():
    events = make_client().get_events(date(2026, 9, 7))  # a Monday
    assert [e.summary for e in events] == ["CS 180"]
    assert events[0].location == "WALC 1055"
    assert events[0].start == datetime(2026, 9, 7, 9, 30, tzinfo=EST)
    assert events[0].end == datetime(2026, 9, 7, 10, 20, tzinfo=EST)


def test_skips_all_day_events_and_non_matching_recurrences():
    events = make_client().get_events(date(2026, 9, 8))  # a Tuesday
    assert [e.summary for e in events] == ["MA 261"]


def test_respects_exdate_cancellation():
    assert make_client().get_events(date(2026, 9, 9)) == []  # the cancelled Wednesday


def test_availability_windows_split_around_events_with_locations():
    windows = make_client().get_availability_windows(date(2026, 9, 8), time(12, 0), time(16, 0))
    assert [(w.start.time(), w.end.time()) for w in windows] == [(time(12, 0), time(13, 0)), (time(14, 15), time(16, 0))]
    assert windows[0].next_event_location == "MATH 175"
    assert windows[1].prev_event_location == "MATH 175"


def test_reads_url_from_file(tmp_path):
    url_file = tmp_path / "calendar_url.txt"
    url_file.write_text("  https://example.invalid/basic.ics\n")
    fetched = []
    client = ICalCalendarClient.from_url_file(str(url_file), fetch=lambda url: fetched.append(url) or SAMPLE_ICS, tz=EST)
    client.get_events(date(2026, 9, 7))
    assert fetched == ["https://example.invalid/basic.ics"]
