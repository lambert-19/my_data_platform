"""Client for the Vélib' Métropole open data API (GBFS format).

Two feeds are used, joined on ``station_id``:

- ``station_status``: bikes / docks available per station (updated ~every minute)
- ``station_information``: station name, coordinates and capacity (static)

The API is public and needs no key.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

BASE_URL = "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole"

FEEDS = ("station_status", "station_information")

# Keys every station must have, per feed. Used to reject invalid payloads.
REQUIRED_STATION_KEYS: dict[str, set[str]] = {
    "station_status": {
        "station_id",
        "num_bikes_available",
        "num_docks_available",
        "is_installed",
        "is_renting",
        "last_reported",
    },
    "station_information": {"station_id", "name", "lat", "lon", "capacity"},
}


class InvalidPayloadError(ValueError):
    """Raised when an API response is empty or does not match the expected schema."""


def build_session(retries: int = 3, backoff_factor: float = 1.0) -> requests.Session:
    """Return a session that retries on connection errors and 429/5xx responses."""
    retry = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def validate_payload(feed: str, payload: Any) -> list[dict[str, Any]]:
    """Check a GBFS payload and return its list of stations.

    Raises:
        InvalidPayloadError: if the payload is empty, malformed, or a station
            is missing a required key.
    """
    if feed not in REQUIRED_STATION_KEYS:
        raise ValueError(f"Unknown feed {feed!r}, expected one of {FEEDS}")
    if not isinstance(payload, dict):
        raise InvalidPayloadError(f"{feed}: payload is not a JSON object")

    stations = (payload.get("data") or {}).get("stations")
    if not isinstance(stations, list) or not stations:
        raise InvalidPayloadError(f"{feed}: no stations in payload")

    required = REQUIRED_STATION_KEYS[feed]
    for i, station in enumerate(stations):
        missing = required - station.keys()
        if missing:
            raise InvalidPayloadError(
                f"{feed}: station #{i} is missing keys {sorted(missing)}"
            )
    return stations


def fetch_feed(
    feed: str,
    session: requests.Session | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Download one feed, validate it and return the raw JSON payload."""
    if feed not in FEEDS:
        raise ValueError(f"Unknown feed {feed!r}, expected one of {FEEDS}")
    session = session or build_session()
    response = session.get(f"{BASE_URL}/{feed}.json", timeout=timeout)
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as exc:
        raise InvalidPayloadError(f"{feed}: response is not valid JSON") from exc

    stations = validate_payload(feed, payload)
    logger.info("Fetched %s: %d stations", feed, len(stations))
    return payload


def bronze_path(feed: str, ts: datetime) -> str:
    """Relative bronze path for a snapshot, partitioned by date and time (UTC).

    Example: ``velib/station_status/2026/11/07/16/35.json``
    """
    ts = ts.astimezone(UTC)
    return f"velib/{feed}/{ts:%Y/%m/%d/%H}/{ts:%M}.json"


def save_snapshot(
    out_dir: str | Path,
    feeds: tuple[str, ...] = FEEDS,
    session: requests.Session | None = None,
    now: datetime | None = None,
) -> list[Path]:
    """Fetch the given feeds and write them unchanged under ``out_dir`` (bronze layout).

    Local equivalent of the ADF copy activity, useful for tests and the local fallback.
    """
    session = session or build_session()
    now = now or datetime.now(UTC)
    written = []
    for feed in feeds:
        payload = fetch_feed(feed, session=session)
        path = Path(out_dir) / bronze_path(feed, now)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        written.append(path)
    return written


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    target = sys.argv[1] if len(sys.argv) > 1 else "data/bronze"
    for p in save_snapshot(target):
        print(p)
