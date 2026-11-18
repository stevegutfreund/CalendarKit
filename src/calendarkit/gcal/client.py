"""A small, app-agnostic wrapper around the Google Calendar v3 API.

The underlying API service is built lazily on first use, so an app can start
(and run every non-calendar page) without Google credentials present.
"""

from __future__ import annotations

import logging
import os
from datetime import date, datetime
from typing import Callable, Iterator, Optional, Sequence

from calendarkit.gcal.auth import CALENDAR_SCOPES, load_credentials

log = logging.getLogger(__name__)

EventPredicate = Callable[[dict], bool]

# Sentinel: "use the client's default reminder" (None means "calendar default").
DEFAULT_REMINDER = object()


def to_rfc3339(dt: datetime) -> str:
    """Format *dt* for timeMin/timeMax. Naive datetimes are treated as UTC."""
    return dt.isoformat("T") + ("Z" if dt.tzinfo is None else "")


def summary_contains(text: str, case_sensitive: bool = True) -> EventPredicate:
    """Predicate: the event summary contains *text*."""
    if case_sensitive:
        return lambda ev: text in ev.get("summary", "")
    needle = text.lower()
    return lambda ev: needle in ev.get("summary", "").lower()


class CalendarClient:
    """Create, list and delete events in Google calendars.

    Parameters
    ----------
    credentials_file, token_file:
        OAuth client secrets and the cached user token.
    timezone:
        IANA zone used for timed events (all-day events carry no zone).
    reminder_minutes:
        Default popup reminder for created events; ``None`` keeps the
        calendar's default reminders.
    """

    def __init__(
        self,
        credentials_file: os.PathLike | str,
        token_file: os.PathLike | str,
        *,
        scopes: Sequence[str] = CALENDAR_SCOPES,
        timezone: str = "UTC",
        reminder_minutes: Optional[int] = 30,
        allow_browser_flow: bool = True,
        num_retries: int = 3,
    ) -> None:
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.scopes = tuple(scopes)
        self.timezone = timezone
        self.reminder_minutes = reminder_minutes
        self.allow_browser_flow = allow_browser_flow
        self.num_retries = num_retries
        self._service = None
        self.last_error: Optional[str] = None

    # -- connection -----------------------------------------------------------

    @property
    def service(self):
        """The googleapiclient service object (built on first access)."""
        if self._service is None:
            from googleapiclient.discovery import build

            try:
                creds = load_credentials(
                    self.credentials_file, self.token_file, self.scopes, self.allow_browser_flow
                )
                self._service = build("calendar", "v3", credentials=creds)
                self.last_error = None
            except Exception as exc:
                self.last_error = str(exc)
                raise
        return self._service

    def is_available(self) -> bool:
        """True if the API can be reached with the configured credentials."""
        try:
            self.service
            return True
        except Exception:
            return False

    def reset(self) -> None:
        """Drop the cached service so the next call re-authenticates."""
        self._service = None

    # -- events -----------------------------------------------------------------

    def _reminders(self, reminder_minutes) -> dict:
        if reminder_minutes is DEFAULT_REMINDER:
            reminder_minutes = self.reminder_minutes
        if reminder_minutes is None:
            return {"useDefault": True}
        return {"useDefault": False, "overrides": [{"method": "popup", "minutes": reminder_minutes}]}

    def _insert(self, calendar_id: str, body: dict) -> dict:
        return self.service.events().insert(calendarId=calendar_id, body=body).execute(
            num_retries=self.num_retries
        )

    def create_all_day_event(
        self,
        calendar_id: str,
        day: date,
        summary: str,
        *,
        color_id: Optional[str] = None,
        reminder_minutes: Optional[int] | object = DEFAULT_REMINDER,
    ) -> dict:
        """Create an all-day event on *day*. Returns the created event resource."""
        stamp = day.strftime("%Y-%m-%d")
        body = {
            "summary": summary,
            "start": {"date": stamp},
            "end": {"date": stamp},
            "reminders": self._reminders(reminder_minutes),
        }
        if color_id is not None:
            body["colorId"] = color_id
        return self._insert(calendar_id, body)

    def create_timed_event(
        self,
        calendar_id: str,
        start: datetime,
        summary: str,
        *,
        end: Optional[datetime] = None,
        color_id: Optional[str] = None,
        reminder_minutes: Optional[int] | object = DEFAULT_REMINDER,
    ) -> dict:
        """Create an event at *start* (zero-length unless *end* is given)."""
        end = end or start
        body = {
            "summary": summary,
            "start": {"dateTime": start.isoformat(), "timeZone": self.timezone},
            "end": {"dateTime": end.isoformat(), "timeZone": self.timezone},
            "reminders": self._reminders(reminder_minutes),
        }
        if color_id is not None:
            body["colorId"] = color_id
        return self._insert(calendar_id, body)

    def delete_event(self, calendar_id: str, event_id: str) -> None:
        self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute(
            num_retries=self.num_retries
        )

    def iter_events(
        self,
        calendar_id: str,
        time_min: datetime,
        time_max: datetime,
        *,
        order_by_start: bool = False,
        page_size: int = 2500,
    ) -> Iterator[dict]:
        """Yield every (expanded, single-instance) event in the time window."""
        params = dict(
            calendarId=calendar_id,
            timeMin=to_rfc3339(time_min),
            timeMax=to_rfc3339(time_max),
            singleEvents=True,
            maxResults=page_size,
        )
        if order_by_start:
            params["orderBy"] = "startTime"
        page_token = None
        while True:
            result = self.service.events().list(pageToken=page_token, **params).execute(
                num_retries=self.num_retries
            )
            yield from result.get("items", [])
            page_token = result.get("nextPageToken")
            if not page_token:
                return

    def delete_events(
        self,
        calendar_id: str,
        time_min: datetime,
        time_max: datetime,
        where: Optional[EventPredicate] = None,
    ) -> int:
        """Delete events in the window matching *where* (all if None).

        Individual delete failures are logged and skipped. Returns the number deleted.
        """
        matches = [ev for ev in self.iter_events(calendar_id, time_min, time_max)
                   if where is None or where(ev)]
        deleted = 0
        for ev in matches:
            try:
                self.delete_event(calendar_id, ev["id"])
                deleted += 1
            except Exception as exc:
                log.warning("Could not delete event %s (%s): %s", ev.get("id"), ev.get("summary"), exc)
        return deleted

    # -- calendars --------------------------------------------------------------

    def create_calendar(self, name: str, *, timezone: Optional[str] = None,
                        description: Optional[str] = None) -> str:
        """Create a new secondary calendar owned by the signed-in account.

        Returns its calendar id (``...@group.calendar.google.com``), which is
        what the apps store in their config.
        """
        body = {"summary": name, "timeZone": timezone or self.timezone}
        if description:
            body["description"] = description
        created = self.service.calendars().insert(body=body).execute(num_retries=self.num_retries)
        return created["id"]

    def list_calendars(self) -> list:
        """Calendars in the signed-in account's list: [{"id", "summary", "accessRole"}, ...]."""
        out, page_token = [], None
        while True:
            result = self.service.calendarList().list(pageToken=page_token).execute(
                num_retries=self.num_retries
            )
            out += [{k: c.get(k) for k in ("id", "summary", "accessRole")} for c in result.get("items", [])]
            page_token = result.get("nextPageToken")
            if not page_token:
                return out

    def set_calendar_color(self, calendar_id: str, background_hex: str,
                           foreground_hex: str = "#000000") -> None:
        """Set the calendar's own display colour (sidebar swatch) in the user's list."""
        self.service.calendarList().patch(
            calendarId=calendar_id,
            colorRgbFormat=True,
            body={"backgroundColor": background_hex, "foregroundColor": foreground_hex},
        ).execute(num_retries=self.num_retries)
