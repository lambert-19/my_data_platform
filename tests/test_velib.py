import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import requests

from data_platform_project import velib

DATA_DIR = Path(__file__).parent / "data"


def load_sample(feed: str) -> dict:
    return json.loads((DATA_DIR / f"{feed}_sample.json").read_text(encoding="utf-8"))


class FakeResponse:
    def __init__(self, payload=None, status=200, text=None):
        self._payload = payload
        self.status_code = status
        self._text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        if self._text is not None:
            return json.loads(self._text)
        return self._payload


class FakeSession:
    """Returns a canned response per feed and records requested URLs."""

    def __init__(self, responses: dict[str, FakeResponse]):
        self.responses = responses
        self.urls = []

    def get(self, url, timeout):
        self.urls.append(url)
        feed = url.rsplit("/", 1)[-1].removesuffix(".json")
        return self.responses[feed]


@pytest.mark.parametrize("feed", velib.FEEDS)
def test_validate_payload_accepts_real_sample(feed):
    stations = velib.validate_payload(feed, load_sample(feed))
    assert len(stations) == 20


@pytest.mark.parametrize(
    "payload",
    [None, [], {}, {"data": {}}, {"data": {"stations": []}}],
)
def test_validate_payload_rejects_empty(payload):
    with pytest.raises(velib.InvalidPayloadError):
        velib.validate_payload("station_status", payload)


def test_validate_payload_rejects_missing_keys():
    payload = load_sample("station_status")
    del payload["data"]["stations"][3]["num_bikes_available"]
    with pytest.raises(velib.InvalidPayloadError, match="num_bikes_available"):
        velib.validate_payload("station_status", payload)


def test_validate_payload_rejects_unknown_feed():
    with pytest.raises(ValueError):
        velib.validate_payload("nope", {})


def test_fetch_feed_returns_payload():
    sample = load_sample("station_status")
    session = FakeSession({"station_status": FakeResponse(sample)})
    assert velib.fetch_feed("station_status", session=session) == sample
    assert session.urls == [f"{velib.BASE_URL}/station_status.json"]


def test_fetch_feed_raises_on_http_error():
    session = FakeSession({"station_status": FakeResponse(status=503)})
    with pytest.raises(requests.HTTPError):
        velib.fetch_feed("station_status", session=session)


def test_fetch_feed_raises_on_invalid_json():
    session = FakeSession({"station_status": FakeResponse(text="<html>oops</html>")})
    with pytest.raises(velib.InvalidPayloadError):
        velib.fetch_feed("station_status", session=session)


def test_bronze_path_is_utc_partitioned():
    ts = datetime(2026, 11, 7, 16, 5, tzinfo=UTC)
    assert velib.bronze_path("station_status", ts) == (
        "velib/station_status/2026/11/07/16/05.json"
    )


def test_save_snapshot_writes_raw_payloads(tmp_path):
    samples = {feed: load_sample(feed) for feed in velib.FEEDS}
    session = FakeSession({f: FakeResponse(p) for f, p in samples.items()})
    now = datetime(2026, 11, 7, 16, 5, tzinfo=UTC)

    written = velib.save_snapshot(tmp_path, session=session, now=now)

    assert len(written) == 2
    for feed in velib.FEEDS:
        path = tmp_path / velib.bronze_path(feed, now)
        assert json.loads(path.read_text(encoding="utf-8")) == samples[feed]
