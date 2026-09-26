"""Calendar-source-agnostic event type and the events -> free-time windows logic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, tzinfo
from typing import Optional

from .models import AvailabilityWindow


@dataclass
class CalendarEvent:
    start: datetime
    end: datetime
    location: Optional[str]
    summary: str


def availability_windows_from_events(
    events: list[CalendarEvent],
    on_date: date,
    day_start: time,
    day_end: time,
    tz: tzinfo,
    min_gap_minutes: float = 15,
) -> list[AvailabilityWindow]:
    window_start = datetime.combine(on_date, day_start, tzinfo=tz)
    window_end = datetime.combine(on_date, day_end, tzinfo=tz)

    events = sorted((e for e in events if e.end > window_start and e.start < window_end), key=lambda e: e.start)

    windows: list[AvailabilityWindow] = []
    cursor = window_start
    prev_location: Optional[str] = None
    for event in events:
        clipped_start = max(event.start, window_start)
        clipped_end = min(event.end, window_end)
        if clipped_start > cursor:
            gap_minutes = (clipped_start - cursor).total_seconds() / 60
            if gap_minutes >= min_gap_minutes:
                windows.append(
                    AvailabilityWindow(
                        start=cursor,
                        end=clipped_start,
                        prev_event_location=prev_location,
                        next_event_location=event.location,
                    )
                )
        cursor = max(cursor, clipped_end)
        prev_location = event.location

    if (window_end - cursor).total_seconds() / 60 >= min_gap_minutes:
        windows.append(
            AvailabilityWindow(start=cursor, end=window_end, prev_event_location=prev_location, next_event_location=None)
        )
    return windows
