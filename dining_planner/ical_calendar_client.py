"""Calendar access via a private iCal (.ics) feed URL -> free-time AvailabilityWindows.

An alternative to GoogleCalendarClient that needs no Google Cloud project or OAuth:
Google Calendar's "Secret address in iCal format" (or any Outlook/Apple .ics
publish link) is fetched directly. Recurring events (RRULE/EXDATE) are expanded.
The URL is a secret, so it's read from a gitignored file (config.CALENDAR_URL_PATH).
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, tzinfo
from typing import Callable, Optional

import icalendar
import recurring_ical_events
import requests

from . import config
from .calendar_events import CalendarEvent, availability_windows_from_events
from .models import AvailabilityWindow


def _http_fetch(url: str) -> str:
    # Google hands out webcal:// in some places; it's plain https underneath.
    if url.startswith("webcal://"):
        url = "https://" + url[len("webcal://") :]
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return response.text


class ICalCalendarClient:
    def __init__(self, url: str, fetch: Callable[[str], str] = _http_fetch, tz: Optional[tzinfo] = None):
        self.url = url
        self._fetch = fetch
        self.tz = tz or datetime.now().astimezone().tzinfo
        self._calendar = None

    @classmethod
    def from_url_file(cls, path: str = config.CALENDAR_URL_PATH, **kwargs) -> "ICalCalendarClient":
        with open(path) as f:
            return cls(url=f.read().strip(), **kwargs)

    def _get_calendar(self):
        if self._calendar is None:
            self._calendar = icalendar.Calendar.from_ical(self._fetch(self.url))
        return self._calendar

    def get_events(self, on_date: date) -> list[CalendarEvent]:
        day_start = datetime.combine(on_date, time.min, tzinfo=self.tz)
        day_end = day_start + timedelta(days=1)
        occurrences = recurring_ical_events.of(self._get_calendar()).between(day_start, day_end)

        events = []
        for component in occurrences:
            start = component.get("DTSTART").dt
            end = component.get("DTEND").dt if component.get("DTEND") else None
            if not isinstance(start, datetime) or not isinstance(end, datetime):
                continue  # skip all-day events (date, not datetime) for availability purposes
            if start.tzinfo is None:  # "floating" times mean local time
                start, end = start.replace(tzinfo=self.tz), end.replace(tzinfo=self.tz)
            location = component.get("LOCATION")
            events.append(
                CalendarEvent(
                    start=start.astimezone(self.tz),
                    end=end.astimezone(self.tz),
                    location=str(location) if location else None,
                    summary=str(component.get("SUMMARY", "")),
                )
            )
        events.sort(key=lambda e: e.start)
        return events

    def get_availability_windows(
        self,
        on_date: date,
        day_start: time,
        day_end: time,
        min_gap_minutes: float = 15,
    ) -> list[AvailabilityWindow]:
        return availability_windows_from_events(
            self.get_events(on_date), on_date, day_start, day_end, self.tz, min_gap_minutes
        )
