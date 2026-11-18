"""Small Google Calendar CLI.

    python -m calendarkit.gcal list   --credentials credentials.json --token token.json
    python -m calendarkit.gcal create "Smith birthdays" --credentials ... --token ... [--timezone Asia/Jerusalem]

Run it from an app folder so the default credentials.json / token.json are
that app's files.
"""

import argparse
import sys

from calendarkit.gcal import CalendarClient, calendar_view_url


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m calendarkit.gcal", description=__doc__.split("\n\n")[0])
    p.add_argument("--credentials", default="credentials.json", help="OAuth client file (default: %(default)s)")
    p.add_argument("--token", default="token.json", help="cached user token (default: %(default)s)")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="list the calendars this account can see")
    c = sub.add_parser("create", help="create a new calendar and print its id")
    c.add_argument("name")
    c.add_argument("--timezone", default="Asia/Jerusalem")
    c.add_argument("--description")

    args = p.parse_args(argv)
    client = CalendarClient(args.credentials, args.token)

    if args.command == "list":
        for cal in client.list_calendars():
            print(f"{cal['accessRole']:<8} {cal['summary']:<35} {cal['id']}")
        return 0

    cal_id = client.create_calendar(args.name, timezone=args.timezone, description=args.description)
    print(f"Created '{args.name}'\n  id:   {cal_id}\n  view: {calendar_view_url(cal_id)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
