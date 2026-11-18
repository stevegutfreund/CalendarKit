"""Hebrew-calendar helpers built on pyluach, with the shkia (sunset) rule.

A Hebrew day starts at nightfall, so something that happened *after shkia*
on civil date D belongs to the Hebrew date of D + 1. Every function that
turns a civil date into a Hebrew one takes an ``after_shkia`` flag for this.

Month numbers follow pyluach: 1 = Nissan ... 6 = Elul, 7 = Tishrei ...
12 = Adar (Adar I in a leap year), 13 = Adar II.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional, Tuple, Union

from pyluach import dates as _dates
from pyluach import hebrewcal as _hebrewcal

HebrewDate = _dates.HebrewDate

DateLike = Union[date, datetime]

MONTH_NAMES_EN = {
    1: "Nissan", 2: "Iyar", 3: "Sivan", 4: "Tammuz",
    5: "Av", 6: "Elul", 7: "Tishrei", 8: "Cheshvan",
    9: "Kislev", 10: "Tevet", 11: "Shvat", 12: "Adar",
    13: "Adar II",
}

NISSAN, ELUL, TISHREI, ADAR, ADAR_II = 1, 6, 7, 12, 13


# ---------------------------------------------------------------------------
# Shkia (day boundary)
# ---------------------------------------------------------------------------

def _as_date(d: DateLike) -> date:
    return d.date() if isinstance(d, datetime) else d


def halachic_civil_date(day: DateLike, after_shkia: bool = False) -> date:
    """The civil date whose daytime shares *day*'s Hebrew date.

    That is *day* itself, or the next day when the moment was after shkia.
    """
    d = _as_date(day)
    return d + timedelta(days=1) if after_shkia else d


def to_hebrew(day: DateLike, after_shkia: bool = False) -> HebrewDate:
    """Hebrew date of a civil date, honouring the shkia rule."""
    return HebrewDate.from_pydate(halachic_civil_date(day, after_shkia))


def hebrew_days_between(
    later: DateLike, later_after_shkia: bool,
    earlier: DateLike, earlier_after_shkia: bool,
) -> int:
    """Number of Hebrew days from *earlier* to *later* (same Hebrew day -> 0)."""
    return (halachic_civil_date(later, later_after_shkia)
            - halachic_civil_date(earlier, earlier_after_shkia)).days


# ---------------------------------------------------------------------------
# Calendar arithmetic
# ---------------------------------------------------------------------------

def is_leap_year(hebrew_year: int) -> bool:
    return _hebrewcal.Year(hebrew_year).leap


def hebrew_year_of(day: DateLike) -> int:
    return HebrewDate.from_pydate(_as_date(day)).year


def anniversary_in_year(original: HebrewDate, year: int) -> Optional[HebrewDate]:
    """The anniversary of *original* in Hebrew *year*, or None if it does not exist.

    Adar II (13) falls back to Adar (12) in a non-leap year. A day that does
    not exist in *year* (e.g. 30 Cheshvan in a short year) returns None.
    """
    month = original.month
    if month == ADAR_II and not is_leap_year(year):
        month = ADAR
    try:
        return HebrewDate(year, month, original.day)
    except ValueError:
        return None


def next_anniversary(
    original: HebrewDate, on_or_after: date, search_years: int = 3
) -> Optional[Tuple[date, int]]:
    """Next civil date (>= *on_or_after*) of *original*'s Hebrew anniversary.

    Returns ``(civil_date, years_since_original)`` or None if none is found
    within *search_years* Hebrew years.
    """
    first = hebrew_year_of(on_or_after)
    for year in range(first, first + search_years):
        h = anniversary_in_year(original, year)
        if h is None:
            continue
        g = h.to_pydate()
        if g >= on_or_after:
            return g, year - original.year
    return None


def same_day_next_month(h: HebrewDate) -> HebrewDate:
    """The same day-of-month in the following Hebrew month.

    Adar (non-leap) / Adar II -> Nissan; Adar I -> Adar II;
    Elul -> Tishrei of the next year. Raises ValueError if the day does not
    exist in the next month (day 30 of a 29-day month).
    """
    leap = is_leap_year(h.year)
    if (leap and h.month == ADAR_II) or (not leap and h.month == ADAR):
        return HebrewDate(h.year, NISSAN, h.day)
    if h.month == ELUL:
        return HebrewDate(h.year + 1, TISHREI, h.day)
    return HebrewDate(h.year, h.month + 1, h.day)


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def format_hebrew(h: HebrewDate, lang: str = "en") -> str:
    """Human-readable Hebrew date.

    ``lang="en"`` -> "6 Kislev 5787"; ``lang="he"`` -> Hebrew letters
    (e.g. "ו׳ כסלו תשפ״ז").
    """
    if lang == "he":
        return h.hebrew_date_string()
    return f"{h.day} {MONTH_NAMES_EN.get(h.month, f'Month {h.month}')} {h.year}"
