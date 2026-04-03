"""
Padel court availability checker for Royal Parks Sports & Leisure.

Uses the flow.onl REST API directly — no browser required.

API:
  GET https://flow.onl/api/activities/venue/{venue_slug}/activity/padel/v2/times?date={date}
  Origin: https://sportsandleisureroyalparks.bookings.flow.onl

Response shape (relevant fields):
  data[].starts_at.format_24_hour  — "11:00"
  data[].action_to_show.status     — "BOOK" (available) | "FULL" | "LOGIN" | ...
  data[].spaces                    — remaining spaces (int)
  data[].location                  — court name e.g. "Padel Court 1"
"""

import logging
from dataclasses import dataclass
from typing import Optional

import requests

logger = logging.getLogger(__name__)

TARGET_DATE = "2026-04-10"
TARGET_TIMES = {"11:00", "12:00"}  # 24-hour start times

API_BASE = "https://flow.onl/api/activities"
BOOKING_ORIGIN = "https://sportsandleisureroyalparks.bookings.flow.onl"

LOCATIONS = {
    "Hyde Park": {
        "venue_slug": "hyde-park-courts",
        "url": f"{BOOKING_ORIGIN}/location/hyde-park-courts/padel/{TARGET_DATE}/by-location",
    },
    "Regent's Park": {
        "venue_slug": "the-regents-park-courts",
        "url": f"{BOOKING_ORIGIN}/location/the-regents-park-courts/padel/{TARGET_DATE}/by-location",
    },
}

HEADERS = {
    "Origin": BOOKING_ORIGIN,
    "Referer": f"{BOOKING_ORIGIN}/",
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}


@dataclass
class AvailableSlot:
    location: str
    time: str
    court: Optional[str]
    url: str
    spaces: int = 1

    def __str__(self):
        court_info = f" ({self.court})" if self.court else ""
        return f"{self.location}{court_info} — {self.time} on {TARGET_DATE}"


def check_location(location_name: str, venue_slug: str, booking_url: str) -> list[AvailableSlot]:
    """Fetch availability for one location and return available target slots."""
    api_url = f"{API_BASE}/venue/{venue_slug}/activity/padel/v2/times"
    params = {"date": TARGET_DATE}

    try:
        resp = requests.get(api_url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.error(f"Request failed for {location_name}: {exc}")
        return []
    except ValueError as exc:
        logger.error(f"JSON parse error for {location_name}: {exc}")
        return []

    slots = data.get("data", [])
    if not isinstance(slots, list):
        logger.warning(f"Unexpected API response shape for {location_name}")
        return []

    logger.debug(f"{location_name}: {len(slots)} total slots returned")

    available = []
    for slot in slots:
        start_time = (slot.get("starts_at") or {}).get("format_24_hour", "")
        if start_time not in TARGET_TIMES:
            continue

        status = (slot.get("action_to_show") or {}).get("status", "")
        spaces = slot.get("spaces", 0)
        court = slot.get("location")  # e.g. "Padel Court 1" or "Multiple"

        is_available = (status == "BOOK") and (spaces > 0)

        if is_available:
            available.append(AvailableSlot(
                location=location_name,
                time=start_time,
                court=court,
                url=booking_url,
                spaces=spaces,
            ))
            logger.info(
                f"AVAILABLE: {location_name} — {start_time}  "
                f"(status={status}, spaces={spaces}, court={court})"
            )
        else:
            logger.debug(
                f"Not available: {location_name} — {start_time}  "
                f"(status={status}, spaces={spaces})"
            )

    return available


def check_all_courts(**_kwargs) -> list[AvailableSlot]:
    """Check all configured locations and return available slots."""
    all_available: list[AvailableSlot] = []
    for location_name, info in LOCATIONS.items():
        slots = check_location(
            location_name=location_name,
            venue_slug=info["venue_slug"],
            booking_url=info["url"],
        )
        all_available.extend(slots)
    return all_available
