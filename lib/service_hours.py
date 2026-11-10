"""Whether Member Services can take a chat now, from lib/data/service_hours.json.

The hours follow the season: 7 days a week from October 1 to March 31, weekdays only from April 1
to September 30.

`project.hours_profile` (seeded from session-start metadata) forces the answer for tests:
`always_open` or `never_open`. Leave it unset in production.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

_CONFIG = json.loads((Path(__file__).parent / "data" / "service_hours.json").read_text())
TIMEZONE = ZoneInfo(_CONFIG["timezone"])
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def _in_season(season: dict[str, Any], month_day: str) -> bool:
    start, end = season["from"], season["to"]
    return start <= month_day <= end if start <= end else (month_day >= start or month_day <= end)


def _clock(value: str) -> str:
    """"08:00" -> "8 a.m.", "20:00" -> "8 p.m."."""
    hour = int(value[:2])
    suffix = "a.m." if hour < 12 else "p.m."
    return f"{hour % 12 or 12} {suffix}"


def hours_text() -> str:
    """The hours of both seasons, as one sentence for the closed-hours response."""
    parts = []
    for season in _CONFIG["seasons"]:
        days = "7 days a week" if len(season["days"]) == 7 else "Monday to Friday"
        start, end = season["hours"]
        parts.append(f"{season['name']}: {days}, {_clock(start)} to {_clock(end)} Eastern Time")
    return "; ".join(parts)


def _open_at(now: datetime) -> bool:
    if now.date().isoformat() in _CONFIG["closed_dates"]:
        return False
    month_day = now.strftime("%m-%d")
    for season in _CONFIG["seasons"]:
        if _in_season(season, month_day):
            start, end = season["hours"]
            return DAYS[now.weekday()] in season["days"] and start <= now.strftime("%H:%M") < end
    return False


def member_services_open(context: Any, now: datetime | None = None) -> bool:
    profile = context.memory.get("project.hours_profile")
    if profile == "always_open":
        return True
    if profile == "never_open":
        return False
    return _open_at(now or datetime.now(TIMEZONE))
