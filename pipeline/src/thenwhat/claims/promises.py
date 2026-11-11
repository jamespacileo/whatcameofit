"""Reading a date out of a promised timeline. Pure: no database, network or clock."""

import re
from datetime import date

NUMBER_WORDS = {
    "a": 1,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}

# "within five years", "in the next 3 years", "in a year"
RELATIVE_YEARS = re.compile(
    rf"\b(?:within|in)\s+(?:the\s+next\s+)?(\d{{1,2}}|{'|'.join(NUMBER_WORDS)})\s+years?\b",
    re.IGNORECASE,
)
CALENDAR_YEAR = re.compile(r"\b((?:19|20)\d{2})\b")


def parse_promise_date(description: str, published_date: date) -> date | None:
    """The date a promise points to, or None when the wording gives no single clear date.

    A span of years counts from the article's publication date. A lone calendar
    year means the end of that year.
    """
    relative = RELATIVE_YEARS.search(description)
    if relative:
        amount = relative.group(1).lower()
        years = NUMBER_WORDS[amount] if amount in NUMBER_WORDS else int(amount)
        return _years_later(published_date, years)

    calendar_years = set(CALENDAR_YEAR.findall(description))
    if len(calendar_years) == 1:
        return date(int(calendar_years.pop()), 12, 31)
    return None


def _years_later(start: date, years: int) -> date:
    try:
        return start.replace(year=start.year + years)
    except ValueError:  # 29 February in a year that has none
        return start.replace(year=start.year + years, day=28)
