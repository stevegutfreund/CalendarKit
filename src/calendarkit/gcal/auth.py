"""Google OAuth for desktop-style ("installed app") clients.

Token handling:
  * a valid token file is used as-is;
  * an expired token with a refresh token is refreshed and re-saved;
  * a corrupt or unrefreshable token file is deleted, and - if allowed - the
    browser consent flow runs and writes a fresh token.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Sequence

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

log = logging.getLogger(__name__)

CALENDAR_SCOPES = ("https://www.googleapis.com/auth/calendar",)


class CalendarAuthError(RuntimeError):
    """Credentials are missing or could not be obtained."""


def _read_token(token_file: Path, scopes: Sequence[str]):
    if not token_file.exists():
        return None
    try:
        return Credentials.from_authorized_user_file(str(token_file), list(scopes))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        log.warning("Token file %s is corrupt (%s); deleting it.", token_file, exc)
        token_file.unlink(missing_ok=True)
        return None


def load_credentials(
    credentials_file: os.PathLike | str,
    token_file: os.PathLike | str,
    scopes: Sequence[str] = CALENDAR_SCOPES,
    allow_browser_flow: bool = True,
) -> Credentials:
    """Return valid Google credentials, refreshing or re-authorising as needed.

    Raises :class:`CalendarAuthError` if no valid credentials can be obtained.
    """
    credentials_file, token_file = Path(credentials_file), Path(token_file)
    creds = _read_token(token_file, scopes)
    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError as exc:
            log.warning("Token refresh failed (%s); deleting %s.", exc, token_file)
            token_file.unlink(missing_ok=True)
            creds = None

    if not (creds and creds.valid):
        if not credentials_file.exists():
            raise CalendarAuthError(
                f"{credentials_file.name} not found at {credentials_file}. Download an OAuth "
                f"'Desktop app' client from Google Cloud Console, or set GOOGLE_CREDENTIALS_FILE."
            )
        if not allow_browser_flow:
            raise CalendarAuthError(
                "No valid Google token and the browser consent flow is disabled "
                "(GOOGLE_ALLOW_BROWSER_AUTH=false)."
            )
        log.info("Starting Google OAuth consent flow in the browser.")
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), list(scopes))
        creds = flow.run_local_server(port=0)

    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(creds.to_json(), encoding="utf-8")
    return creds
