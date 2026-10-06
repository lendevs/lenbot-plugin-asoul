"""ICS parsing kept from the previous host plugin.

ICS folding, text escaping and date decoding are adapted from
LEN5010/astrbot_plugin_asoul at 5a945f6. See LICENSE and SOURCE.md.
"""
from __future__ import annotations

import re
from datetime import datetime, time as wall_time, timedelta, timezone
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict


class CalendarEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
    source_uid: str
    recurrence_id: str | None
    start_at: datetime
    end_at: datetime | None
    duration_seconds: float | None
    all_day: bool
    title: str
    description: str
    location: str
    categories: str
    url: str | None
    status: str | None
    cancelled: bool
    source_updated_at: datetime | None
    source_stamp: datetime | None
    host_signature: str | None


def unfold_lines(text: str) -> list[str]:
    lines = []
    for raw in text.splitlines():
        if raw.startswith((" ", "\t")):
            if not lines:
                raise ValueError("ICS begins with an invalid folded line")
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def content_line(line: str) -> tuple[str, dict[str, str], str]:
    # A property parameter may contain ':' inside quotes (for example a URI).
    quoted = False
    separator = None
    for index, char in enumerate(line):
        if char == '"':
            quoted = not quoted
        elif char == ":" and not quoted:
            separator = index
            break
    if separator is None:
        raise ValueError("ICS content line has no property separator")
    pieces = line[:separator].split(";")
    params = {}
    for piece in pieces[1:]:
        key, value = piece.split("=", 1)
        params[key.upper()] = value.strip('"')
    return pieces[0].upper(), params, line[separator + 1:]


def decode_text(value: str) -> str:
    replacements = {"n": "\n", "N": "\n", ",": ",", ";": ";", "\\": "\\"}
    return re.sub(r"\\([nN,;\\])", lambda match: replacements[match[1]], value)


def parse_datetime(value: str, params: dict[str, str], floating_timezone: ZoneInfo) -> tuple[datetime, bool]:
    if params.get("VALUE") == "DATE":
        day = datetime.strptime(value, "%Y%m%d").date()
        return datetime.combine(day, wall_time.min, floating_timezone), True
    if params.get("VALUE", "DATE-TIME") != "DATE-TIME":
        raise ValueError("Unsupported ICS date value type")
    if value.endswith("Z"):
        if "TZID" in params:
            raise ValueError("UTC ICS time cannot also specify TZID")
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc), False
    zone = ZoneInfo(params["TZID"]) if "TZID" in params else floating_timezone
    return datetime.strptime(value, "%Y%m%dT%H%M%S").replace(tzinfo=zone), False


def parse_duration(value: str) -> timedelta:
    match = re.fullmatch(r"P(?:(\d+)W|(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?)", value)
    if match is None or not any(match.groups()):
        raise ValueError("Unsupported or empty ICS DURATION")
    weeks, days, hours, minutes, seconds = (int(part) if part else 0 for part in match.groups())
    return timedelta(weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds)


def parse_calendar(text: str, floating_timezone: ZoneInfo) -> tuple[CalendarEvent, ...]:
    lines = unfold_lines(text)
    if not lines or lines[0] != "BEGIN:VCALENDAR" or lines[-1] != "END:VCALENDAR":
        raise ValueError("Calendar source did not return a complete VCALENDAR")
    events = []
    current = None
    nested_components = 0
    identities = set()
    for line in lines:
        if line == "BEGIN:VEVENT":
            if current is not None:
                raise ValueError("Nested VEVENT is invalid")
            current = {}
            continue
        if current is None:
            continue
        if line == "END:VEVENT":
            if nested_components:
                raise ValueError("Unclosed component in VEVENT")
            event = build_event(current, floating_timezone)
            identity = (event.source_uid, event.recurrence_id)
            if identity in identities:
                raise ValueError(f"Duplicate calendar source identity: {event.source_uid}")
            identities.add(identity)
            events.append(event)
            current = None
            continue
        if line.startswith("BEGIN:"):
            nested_components += 1
        elif line.startswith("END:"):
            nested_components -= 1
        elif not nested_components:
            name, params, value = content_line(line)
            current.setdefault(name, []).append((params, value))
    if current is not None:
        raise ValueError("Calendar source contains an unfinished VEVENT")
    return tuple(sorted(events, key=lambda event: (event.start_at, event.source_uid, event.recurrence_id or "")))


def build_event(properties, floating_timezone: ZoneInfo) -> CalendarEvent:
    def one(name, *, required=False):
        values = properties.get(name, [])
        if len(values) > 1 or required and not values:
            raise ValueError(f"ICS event requires exactly one {name}")
        return values[0] if values else None

    def text(name):
        item = one(name)
        return decode_text(item[1]) if item else ""

    def timestamp(name):
        item = one(name)
        return parse_datetime(item[1], item[0], floating_timezone)[0] if item else None

    uid = one("UID", required=True)[1]
    if not uid:
        raise ValueError("ICS event UID cannot be empty")
    # Repeating source events need an explicit occurrence representation.
    # Never silently omit a repetition rule or invent occurrence identities.
    if any(name in properties for name in ("RRULE", "RDATE", "EXDATE")):
        raise ValueError(f"ICS recurrence is not supported for source event {uid}")
    start_params, start_value = one("DTSTART", required=True)
    start_at, all_day = parse_datetime(start_value, start_params, floating_timezone)
    end_at = timestamp("DTEND")
    raw_duration = one("DURATION")
    if raw_duration is not None and end_at is not None:
        raise ValueError("ICS event cannot contain both DTEND and DURATION")
    duration = parse_duration(raw_duration[1]) if raw_duration is not None else None
    if duration is not None:
        end_at = start_at + duration
    if end_at is not None and end_at <= start_at:
        raise ValueError("ICS event end must be later than start")
    recurrence = one("RECURRENCE-ID")
    description = text("DESCRIPTION")
    first_line = description.splitlines()[0] if description else ""
    signature = first_line.split("|", 1)[1].strip() if "|" in first_line else None
    status = text("STATUS") or None
    return CalendarEvent(
        source_uid=uid, recurrence_id=recurrence[1] if recurrence else None,
        start_at=start_at, end_at=end_at, duration_seconds=duration.total_seconds() if duration is not None else None,
        all_day=all_day, title=text("SUMMARY"), description=description,
        location=text("LOCATION"), categories=text("CATEGORIES"), url=text("URL") or None,
        status=status, cancelled=status == "CANCELLED", source_updated_at=timestamp("LAST-MODIFIED"),
        source_stamp=timestamp("DTSTAMP"),
        host_signature=signature,
    )
