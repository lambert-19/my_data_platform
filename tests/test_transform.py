import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pytest

pyspark = pytest.importorskip("pyspark")
from pyspark.sql import SparkSession

from data_platform_project import transform

DATA_DIR = Path(__file__).parent / "data"

# Two snapshots, 5 minutes apart, like the ADF trigger.
SNAPSHOTS = ("2026/11/15/10/00", "2026/11/15/10/05")
FIRST_SNAPSHOT = "2026-11-15 10:00:00"  # UTC


def _fix_windows_spark_env():
    """Work around spark-submit.cmd on Windows.

    The batch scripts break when SPARK_HOME contains spaces (this repo lives in
    "Data Platform Project") and when JAVA_HOME points to the ``bin`` folder.
    SPARK_HOME is always set to the project's PySpark, so that a system-wide
    Spark install of another version is not picked up.
    """
    if os.name != "nt":
        return
    import ctypes

    java_home = os.environ.get("JAVA_HOME", "").rstrip("\\/")
    if java_home.lower().endswith("bin"):
        os.environ["JAVA_HOME"] = os.path.dirname(java_home)
    spark_home = os.path.dirname(pyspark.__file__)
    buffer = ctypes.create_unicode_buffer(1024)
    if ctypes.windll.kernel32.GetShortPathNameW(spark_home, buffer, len(buffer)):
        spark_home = buffer.value
    os.environ["SPARK_HOME"] = spark_home


@pytest.fixture(scope="session")
def spark():
    _fix_windows_spark_env()
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    session = (
        SparkSession.builder.master("local[1]")
        .appName("test-transform")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    yield session
    session.stop()


@pytest.fixture(scope="session")
def bronze_root(tmp_path_factory):
    """Bronze layout with the sample files: status at every snapshot, information once."""
    root = tmp_path_factory.mktemp("bronze")
    for snapshot in SNAPSHOTS:
        path = root / "velib" / "station_status" / f"{snapshot}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(DATA_DIR / "station_status_sample.json", path)
    info = root / "velib" / "station_information" / f"{SNAPSHOTS[0]}.json"
    info.parent.mkdir(parents=True)
    shutil.copy(DATA_DIR / "station_information_sample.json", info)
    return root.as_uri()


@pytest.fixture(scope="session")
def raw(spark, bronze_root):
    return {
        feed: transform.read_bronze(spark, bronze_root, feed)
        for feed in transform.BRONZE_SCHEMAS
    }


@pytest.fixture(scope="session")
def silver(raw):
    return transform.to_silver(
        raw["station_status"], raw["station_information"]
    ).cache()


def by_id(df, station_id):
    return df.filter(df.station_id == station_id).orderBy("ingested_at").collect()


# ---------- Bronze ----------


def test_read_bronze_rejects_unknown_feed(spark, bronze_root):
    with pytest.raises(ValueError):
        transform.read_bronze(spark, bronze_root, "free_bike_status")


def test_ingested_at_comes_from_the_bronze_path(raw):
    stations = transform.explode_stations(raw["station_status"])
    # Formatted by Spark (session in UTC): collect() would convert to local time.
    times = stations.selectExpr("date_format(ingested_at, 'yyyy-MM-dd HH:mm') AS t")
    assert sorted(r.t for r in times.distinct().collect()) == [
        "2026-11-15 10:00",
        "2026-11-15 10:05",
    ]


def test_camel_case_duplicates_are_dropped(raw):
    columns = transform.explode_stations(raw["station_status"]).columns
    assert "numBikesAvailable" not in columns
    assert "numDocksAvailable" not in columns


# ---------- Silver ----------


def test_silver_has_one_row_per_station_and_snapshot(silver):
    assert silver.count() == 20 * len(SNAPSHOTS)


def test_silver_is_idempotent_when_bronze_is_replayed(raw):
    replayed = raw["station_status"].unionByName(raw["station_status"])
    assert transform.to_silver(replayed, raw["station_information"]).count() == 40


def test_bike_types_are_split(silver):
    row = by_id(silver, 323616530)[0]
    assert (row.bikes, row.mechanical_bikes, row.ebikes) == (17, 13, 4)
    assert silver.filter("mechanical_bikes + ebikes != bikes").count() == 0


def test_station_information_is_joined(silver):
    row = by_id(silver, 213688169)[0]
    assert row.name == "Benjamin Godard - Victor Hugo"
    assert row.capacity == 35
    assert row.lat == pytest.approx(48.865983)
    assert silver.filter("capacity IS NULL").count() == 0


def test_occupancy_rate(silver):
    assert by_id(silver, 323616530)[0].occupancy_rate == pytest.approx(1.0)
    # Capacity 0: no division by zero.
    assert by_id(silver, 88140066)[0].occupancy_rate is None


def test_station_states_are_exclusive(silver):
    one_snapshot = silver.filter(f"ingested_at = '{FIRST_SNAPSHOT}'")
    assert one_snapshot.filter("is_empty").count() == 3
    assert one_snapshot.filter("is_full").count() == 2
    assert one_snapshot.filter("is_out_of_service").count() == 2
    assert (
        one_snapshot.filter("is_out_of_service AND (is_empty OR is_full)").count() == 0
    )


def test_zone_pads_short_station_codes(silver):
    assert by_id(silver, 210403080)[0].zone == "05"  # stationCode 5110
    assert by_id(silver, 210403080)[0].is_paris
    assert not by_id(silver, 19179944124)[0].is_paris  # stationCode 40001


# ---------- Gold ----------


def test_network_snapshot(silver):
    rows = transform.network_snapshot(silver).orderBy("ingested_at").collect()
    assert len(rows) == len(SNAPSHOTS)
    first = rows[0]
    assert first.stations == 20
    assert first.bikes == 185
    assert first.mechanical_bikes + first.ebikes == first.bikes
    assert first.empty_stations == 3
    assert first.full_stations == 2
    assert first.out_of_service_stations == 2


def test_zone_snapshot_sums_to_network(silver):
    zones = transform.zone_snapshot(silver).filter(f"ingested_at = '{FIRST_SNAPSHOT}'")
    assert zones.agg({"bikes": "sum"}).first()[0] == 185


def test_station_timeseries_flags_anomalies(silver):
    series = transform.station_timeseries(silver)
    # Empty on both snapshots (5 min apart, within the 30-min window).
    assert by_id(series, 516709288)[-1].anomaly == "vide_prolongee"
    assert by_id(series, 129032910)[-1].anomaly == "pleine_prolongee"
    assert by_id(series, 88140066)[-1].anomaly == "hors_service"
    # A single snapshot is not enough to call a station "stuck".
    assert by_id(series, 516709288)[0].anomaly is None
    assert by_id(series, 213688169)[-1].anomaly is None


def test_station_timeseries_detects_sudden_drop(spark):
    rows = [
        (1, datetime(2026, 11, 15, 10, m), bikes)
        for m, bikes in ((0, 20), (5, 20), (10, 20), (15, 2))
    ]
    silver = spark.createDataFrame(
        rows, "station_id long, ingested_at timestamp, bikes long"
    )
    for flag in ("is_out_of_service", "is_empty", "is_full"):
        silver = silver.withColumn(flag, silver.bikes < 0)
    last = transform.station_timeseries(silver).orderBy("ingested_at").collect()[-1]
    assert last.bikes_rolling_avg == pytest.approx(15.5)
    assert last.anomaly == "chute_brutale"


# ---------- Incremental ----------


def test_watermark_keeps_only_new_snapshots(silver):
    watermark = transform.max_ingested_at(
        silver.filter(f"ingested_at = '{FIRST_SNAPSHOT}'")
    )
    assert transform.new_since(silver, watermark).count() == 20
    assert transform.new_since(silver, None).count() == 40
