"""Browser links to a Google calendar (no API call, no credentials needed).

Both links open in the browser of whoever clicks them. Private calendars
show their events only to a Google account that has access to them.
"""

from typing import Optional
from urllib.parse import urlencode

_BASE = "https://calendar.google.com/calendar"


def calendar_view_url(calendar_id: str, timezone: Optional[str] = None, mode: Optional[str] = None) -> str:
    """A page showing only this calendar.

    *mode* may be "WEEK", "MONTH" or "AGENDA" (default: Google's month view).
    """
    params = {"src": calendar_id}
    if timezone:
        params["ctz"] = timezone
    if mode:
        params["mode"] = mode
    return f"{_BASE}/embed?{urlencode(params)}"


def calendar_open_url(calendar_id: str) -> str:
    """Google Calendar itself, with this calendar added to the viewer's list."""
    return f"{_BASE}/r?{urlencode({'cid': calendar_id})}"
