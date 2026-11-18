"""Google Calendar access shared by the home apps.

    from calendarkit.gcal import CalendarClient
    client = CalendarClient("credentials.json", "token.json", timezone="Asia/Jerusalem")
    client.create_all_day_event(calendar_id, date(2026, 1, 1), "Hello")

Command line (see README): python -m calendarkit.gcal --help
"""

from calendarkit.gcal.auth import CALENDAR_SCOPES, CalendarAuthError, load_credentials
from calendarkit.gcal.client import CalendarClient, summary_contains, to_rfc3339
from calendarkit.gcal.links import calendar_open_url, calendar_view_url

__all__ = [
    "CALENDAR_SCOPES",
    "CalendarAuthError",
    "CalendarClient",
    "calendar_open_url",
    "calendar_view_url",
    "load_credentials",
    "summary_contains",
    "to_rfc3339",
]
