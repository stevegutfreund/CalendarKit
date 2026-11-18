import unittest
from datetime import date, datetime

from calendarkit.gcal import CalendarClient, calendar_open_url, calendar_view_url, summary_contains, to_rfc3339


class _Req:
    def __init__(self, fn):
        self.fn = fn

    def execute(self, num_retries=0):
        return self.fn()


class FakeService:
    """Records calls; ``pages`` is a list of event lists returned page by page."""

    def __init__(self, pages=()):
        self.pages = [list(p) for p in pages] or [[]]
        self.calls = []

    def events(self):
        return self

    def insert(self, calendarId, body):
        return _Req(lambda: self.calls.append(("insert", calendarId, body)) or body)

    def delete(self, calendarId, eventId):
        def run():
            if eventId == "boom":
                raise RuntimeError("fail")
            self.calls.append(("delete", calendarId, eventId))
        return _Req(run)

    def list(self, pageToken=None, **params):
        def run():
            self.calls.append(("list", pageToken, params))
            i = int(pageToken or 0)
            out = {"items": self.pages[i]}
            if i + 1 < len(self.pages):
                out["nextPageToken"] = str(i + 1)
            return out
        return _Req(run)


def client_with(fake, **kw):
    c = CalendarClient("missing-credentials.json", "missing-token.json", **kw)
    c._service = fake
    return c


class EventBodies(unittest.TestCase):
    def test_all_day_event(self):
        fake = FakeService()
        client_with(fake).create_all_day_event("cal", date(2026, 3, 5), "Hi", color_id="6")
        _, cal, body = fake.calls[0]
        self.assertEqual(cal, "cal")
        self.assertEqual(body, {
            "summary": "Hi",
            "start": {"date": "2026-03-05"},
            "end": {"date": "2026-03-05"},
            "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 30}]},
            "colorId": "6",
        })

    def test_no_color_means_no_colorId(self):
        fake = FakeService()
        client_with(fake).create_all_day_event("cal", date(2026, 3, 5), "Hi")
        self.assertNotIn("colorId", fake.calls[0][2])

    def test_timed_event_uses_client_timezone(self):
        fake = FakeService()
        client_with(fake, timezone="Asia/Jerusalem").create_timed_event("cal", datetime(2026, 3, 5, 23), "X")
        body = fake.calls[0][2]
        self.assertEqual(body["start"], {"dateTime": "2026-03-05T23:00:00", "timeZone": "Asia/Jerusalem"})
        self.assertEqual(body["end"], body["start"])

    def test_reminder_override(self):
        fake = FakeService()
        c = client_with(fake)
        c.create_all_day_event("cal", date(2026, 3, 5), "A", reminder_minutes=None)
        c.create_all_day_event("cal", date(2026, 3, 5), "B", reminder_minutes=5)
        self.assertEqual(fake.calls[0][2]["reminders"], {"useDefault": True})
        self.assertEqual(fake.calls[1][2]["reminders"]["overrides"][0]["minutes"], 5)


class ListingAndDeleting(unittest.TestCase):
    def test_paginates(self):
        fake = FakeService(pages=[[{"id": "1"}], [{"id": "2"}], [{"id": "3"}]])
        ids = [e["id"] for e in client_with(fake).iter_events("cal", datetime(2000, 1, 1), datetime(2001, 1, 1))]
        self.assertEqual(ids, ["1", "2", "3"])
        _, _, params = fake.calls[0]
        self.assertEqual(params["timeMin"], "2000-01-01T00:00:00Z")
        self.assertTrue(params["singleEvents"])
        self.assertNotIn("orderBy", params)

    def test_delete_events_filters_and_skips_failures(self):
        fake = FakeService(pages=[[
            {"id": "a", "summary": "Vesset - x"},
            {"id": "b", "summary": "Period (3)"},
            {"id": "boom", "summary": "Vesset - y"},
        ]])
        n = client_with(fake).delete_events("cal", datetime(2000, 1, 1), datetime(2001, 1, 1),
                                            where=summary_contains("Vesset"))
        self.assertEqual(n, 1)
        self.assertIn(("delete", "cal", "a"), fake.calls)

    def test_summary_contains_case(self):
        ev = {"summary": "Cake Alice (3)"}
        self.assertFalse(summary_contains("alice")(ev))
        self.assertTrue(summary_contains("alice", case_sensitive=False)(ev))


class Availability(unittest.TestCase):
    def test_missing_credentials_reports_error(self):
        c = CalendarClient("does-not-exist.json", "does-not-exist-token.json")
        self.assertFalse(c.is_available())
        self.assertIn("does-not-exist.json", c.last_error)

    def test_rfc3339(self):
        self.assertEqual(to_rfc3339(datetime(2001, 2, 3)), "2001-02-03T00:00:00Z")


class Calendars(unittest.TestCase):
    def test_create_calendar_returns_id(self):
        sent = {}

        class Cals:
            def insert(self, body):
                sent.update(body)
                return _Req(lambda: {"id": "new@group.calendar.google.com", **body})

        class Svc:
            def calendars(self):
                return Cals()

        c = client_with(Svc(), timezone="Asia/Jerusalem")
        self.assertEqual(c.create_calendar("Smith", description="d"), "new@group.calendar.google.com")
        self.assertEqual(sent, {"summary": "Smith", "timeZone": "Asia/Jerusalem", "description": "d"})


class Links(unittest.TestCase):
    def test_view_url_encodes_id(self):
        url = calendar_view_url("abc@group.calendar.google.com", timezone="Asia/Jerusalem", mode="AGENDA")
        self.assertEqual(url, "https://calendar.google.com/calendar/embed?"
                              "src=abc%40group.calendar.google.com&ctz=Asia%2FJerusalem&mode=AGENDA")

    def test_open_url(self):
        self.assertEqual(calendar_open_url("a@b"), "https://calendar.google.com/calendar/r?cid=a%40b")


if __name__ == "__main__":
    unittest.main()
