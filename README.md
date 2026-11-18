# CalendarKit

Shared Python building blocks for calendar apps (BDays, PTracker, …): Google Calendar,
Hebrew dates with the shkia rule, and `.env` settings. Imported as `calendarkit`.

| Module               | What it gives you |
| -------------------- | ----------------- |
| `calendarkit.env`    | Load a project's `.env` file; typed getters (`get`, `get_int`, `get_bool`, `get_path`, `require`). No dependencies. |
| `calendarkit.gcal`   | Google OAuth (`load_credentials`) and `CalendarClient` – create/list calendars, create all-day/timed events, list (paginated), delete by predicate, set calendar colour; browser links (`calendar_view_url`); a CLI (`python -m calendarkit.gcal`). Lazy: an app starts fine without credentials. |
| `calendarkit.hebrew` | Hebrew dates with the **before/after shkia** rule, anniversaries (Adar II → Adar, missing 30th days), same-day-next-month, formatting. |

## Used by

| App | Uses |
| --- | --- |
| [BDays](../BDays) | `env`, `gcal`, `hebrew` |
| [PTracker](../PTracker) | `env`, `gcal`, `hebrew` |

Both apps expect this repo to be cloned next to them (`../CalendarKit`). A change here
affects both: run their tests (and this package's) after editing.

## Install

From an app folder (the apps' `requirements.txt` already contain this line):

```bash
pip install -e ../CalendarKit
```

Editable install: changes here are picked up by every app on restart.

## Usage

```python
from datetime import date
from calendarkit import env, hebrew
from calendarkit.gcal import CalendarClient, summary_contains

env.load_dotenv(".env")
client = CalendarClient(env.get_path("GOOGLE_CREDENTIALS_FILE", "credentials.json"),
                        env.get_path("GOOGLE_TOKEN_FILE", "token.json"),
                        timezone="Asia/Jerusalem")

# A birth after shkia on 16 Nov belongs to the next Hebrew day.
born = hebrew.to_hebrew(date(2026, 11, 16), after_shkia=True)
hebrew.format_hebrew(born)                       # "7 Kislev 5787"
when, years = hebrew.next_anniversary(born, date.today())

client.create_all_day_event(calendar_id, when, f"Birthday ({years})", color_id="6")
client.delete_events(calendar_id, start, end, where=summary_contains("Birthday"))
```

## Google Calendar: setting up a new calendar

### 1. One-time: an OAuth client (`credentials.json`)

Skip this if the app folder already has a working `credentials.json`.

1. Go to <https://console.cloud.google.com/>, create a project (or pick an existing one).
2. **APIs & Services → Library**: enable **Google Calendar API**.
3. **APIs & Services → OAuth consent screen**: user type *External*; fill in the
   app name and your email; under **Test users** add the Google account whose
   calendars the app will write to.
4. **APIs & Services → Credentials → Create credentials → OAuth client ID**,
   application type **Desktop app**. Download the JSON and save it in the app
   folder as `credentials.json` (or point `GOOGLE_CREDENTIALS_FILE` in `.env` at it).
5. Start the app and trigger any calendar action (or run `python -m calendarkit.gcal list`
   from the app folder). A browser tab asks you to approve access, then
   `token.json` is written next to it. Both files are git-ignored.

> While the consent screen is in **Testing** status, Google expires the
> token after **7 days**, so you would have to approve again weekly. To avoid this,
> click **Publish app** on the consent screen. You'll see an "unverified app" warning
> once when approving, which is fine for personal use.

### 2. Create the calendar

The calendar must belong to the account you approved in step 1, or be
shared with it with **Make changes to events** permission.

**Option A, in Google Calendar (web):**

1. Left sidebar → **Other calendars → + → Create new calendar**.
2. Give it a name and time zone (Asia/Jerusalem) → **Create calendar**.
3. Open the new calendar's **Settings and sharing → Integrate calendar** and
   copy the **Calendar ID** (`…@group.calendar.google.com`).

**Option B, from the command line** (run in the app folder, so it uses that app's
`credentials.json` / `token.json`):

```bash
python -m calendarkit.gcal create "Smith birthdays" --timezone Asia/Jerusalem
#   id:   abc123...@group.calendar.google.com
python -m calendarkit.gcal list            # all calendars the account can see, with ids
```

Or from code: `CalendarClient(...).create_calendar("Smith birthdays")` returns the id.

### 3. Connect it to an app

| App      | Where the id goes |
| -------- | ----------------- |
| BDays    | **Add family** page, or **Settings** → paste the Calendar ID (saved in `config.json`). |
| PTracker | `.env` → `CALENDAR_ID=…`, then restart the app. |

Then use the app's *Push all* / *Copy all* actions to fill the calendar. Each app
links to its calendar in the UI (built with `calendar_view_url`).

### Links

`calendar_view_url(id, timezone=None, mode=None)` gives a page showing only that
calendar (`mode`: `WEEK`, `MONTH` or `AGENDA`). `calendar_open_url(id)` opens
Google Calendar with the calendar added to the viewer's list. Neither needs
credentials. For a private calendar, the viewer must be signed in to an
account that has access.

## Tests

```bash
python -m unittest discover -s tests
```

The Google tests use a fake service and never touch a real calendar.
