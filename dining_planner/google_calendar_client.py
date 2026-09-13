"""Google Calendar access: today's events -> free-time AvailabilityWindows.

Uses the standard OAuth "installed app" flow (the correct flow for reading a
personal calendar, as opposed to a service account). On first run this opens a
browser for consent and caches a refresh token at config.TOKEN_PATH.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from . import config
from .models import AvailabilityWindow


@dataclass
class CalendarEvent:
    start: datetime
    end: datetime
    location: Optional[str]
    summary: str


class GoogleCalendarClient:
    def __init__(
        self,
        client_secret_path: str = config.CLIENT_SECRET_PATH,
        token_path: str = config.TOKEN_PATH,
        scopes: list[str] = config.GOOGLE_CALENDAR_SCOPES,
        calendar_id: str = "primary",
    ):
        self.client_secret_path = client_secret_path
        self.token_path = token_path
        self.scopes = scopes
        self.calendar_id = calendar_id
        self._service = None

    def _get_service(self):
        if self._service is not None:
            return self._service

        creds = None
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, self.scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.client_secret_path, self.scopes)
                creds = flow.run_local_server(port=0)
            os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
            with open(self.token_path, "w") as f:
                f.write(creds.to_json())

        self._service = build("calendar", "v3", credentials=creds)
        return self._service

    def get_events(self, on_date: date) -> list[CalendarEvent]:
        service = self._get_service()
        tz = datetime.now().astimezone().tzinfo
        day_start = datetime.combine(on_date, time.min, tzinfo=tz)
        day_end = datetime.combine(on_date, time.max, tzinfo=tz)

        events_result = (
            service.events()
            .list(
                calendarId=self.calendar_id,
                timeMin=day_start.isoformat(),
                timeMax=day_end.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = []
        for raw in events_result.get("items", []):
            start = _parse_event_datetime(raw.get("start", {}))
            end = _parse_event_datetime(raw.get("end", {}))
            if start is None or end is None:
                continue  # skip all-day events (no "dateTime", just a "date") for availability purposes
            events.append(
                CalendarEvent(start=start, end=end, location=raw.get("location"), summary=raw.get("summary", ""))
            )
        return events

    def get_availability_windows(
        self,
        on_date: date,
        day_start: time,
        day_end: time,
        min_gap_minutes: float = 15,
    ) -> list[AvailabilityWindow]:
        tz = datetime.now().astimezone().tzinfo
        window_start = datetime.combine(on_date, day_start, tzinfo=tz)
        window_end = datetime.combine(on_date, day_end, tzinfo=tz)

        events = [e for e in self.get_events(on_date) if e.end > window_start and e.start < window_end]
        events.sort(key=lambda e: e.start)

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


def _parse_event_datetime(endpoint: dict) -> Optional[datetime]:
    raw = endpoint.get("dateTime")
    if not raw:
        return None
    return datetime.fromisoformat(raw)
