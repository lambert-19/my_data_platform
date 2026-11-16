"""PySpark transformations for the Vélib' pipeline: bronze → silver → gold.

The functions are pure DataFrame → DataFrame transformations so they can be
unit-tested locally on ``tests/data/`` and reused as-is in the Synapse notebooks.

Compatibility: the Synapse pool runs Spark 3.4 / Python 3.10, while local
development uses a more recent PySpark. Only APIs available in both are used,
and the module avoids Python syntax newer than 3.10.

All timestamps are UTC: set ``spark.sql.session.timeZone`` to ``UTC``.
"""

from __future__ import annotations

from datetime import datetime

from pyspark.sql import Column, DataFrame, SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql.types import (
    ArrayType,
    DoubleType,
    LongType,
    StringType,
    StructField,
    StructType,
)

# ---------- Bronze schemas ----------
# Explicit schemas instead of inference: stable types across snapshots, and the
# camelCase duplicates of the API (numBikesAvailable, numDocksAvailable) are dropped.

_STATUS_STATION = StructType(
    [
        StructField("station_id", LongType()),
        StructField("stationCode", StringType()),
        StructField("num_bikes_available", LongType()),
        StructField(
            "num_bikes_available_types",
            ArrayType(
                StructType(
                    [
                        StructField("mechanical", LongType()),
                        StructField("ebike", LongType()),
                    ]
                )
            ),
        ),
        StructField("num_docks_available", LongType()),
        StructField("is_installed", LongType()),
        StructField("is_renting", LongType()),
        StructField("is_returning", LongType()),
        StructField("last_reported", LongType()),
    ]
)

_INFORMATION_STATION = StructType(
    [
        StructField("station_id", LongType()),
        StructField("stationCode", StringType()),
        StructField("name", StringType()),
        StructField("lat", DoubleType()),
        StructField("lon", DoubleType()),
        StructField("capacity", LongType()),
    ]
)


def _gbfs_schema(station: StructType) -> StructType:
    return StructType(
        [
            StructField("lastUpdatedOther", LongType()),
            StructField("ttl", LongType()),
            StructField(
                "data", StructType([StructField("stations", ArrayType(station))])
            ),
        ]
    )


BRONZE_SCHEMAS: dict[str, StructType] = {
    "station_status": _gbfs_schema(_STATUS_STATION),
    "station_information": _gbfs_schema(_INFORMATION_STATION),
}

# Bronze files are written as velib/<feed>/yyyy/MM/dd/HH/mm.json (see velib.bronze_path).
_SNAPSHOT_PATH_PATTERN = r"\d{4}/\d{2}/\d{2}/\d{2}/\d{2}(?=\.json$)"


# ---------- Bronze ----------


def read_bronze(spark: SparkSession, root: str, feed: str) -> DataFrame:
    """Read every bronze snapshot of ``feed`` under ``root``, keeping the source path.

    ``root`` is the bronze container, e.g.
    ``abfss://bronze@stvelibmwzyy4.dfs.core.windows.net`` or a local folder.
    """
    if feed not in BRONZE_SCHEMAS:
        raise ValueError(
            f"Unknown feed {feed!r}, expected one of {list(BRONZE_SCHEMAS)}"
        )
    return (
        spark.read.schema(BRONZE_SCHEMAS[feed])
        .option("multiLine", True)
        .json(f"{root.rstrip('/')}/velib/{feed}/*/*/*/*/*.json")
        .withColumn("source_file", F.col("_metadata.file_path"))
    )


def ingested_at_from_path(path: Column) -> Column:
    """Snapshot timestamp (UTC) parsed from a bronze path ``.../yyyy/MM/dd/HH/mm.json``."""
    return F.to_timestamp(
        F.regexp_extract(path, _SNAPSHOT_PATH_PATTERN, 0), "yyyy/MM/dd/HH/mm"
    )


def explode_stations(raw: DataFrame) -> DataFrame:
    """One row per station and snapshot, with the snapshot time ``ingested_at``."""
    return raw.select(
        ingested_at_from_path(F.col("source_file")).alias("ingested_at"),
        F.explode("data.stations").alias("station"),
    ).select("ingested_at", "station.*")


# ---------- Silver ----------


def _bike_type_count(bike_type: str) -> Column:
    # num_bikes_available_types looks like [{"mechanical": 10}, {"ebike": 2}].
    return F.expr(
        f"aggregate(coalesce(num_bikes_available_types, array()), 0L, "
        f"(acc, t) -> acc + coalesce(t.{bike_type}, 0L))"
    )


def zone_from_code(station_code: Column) -> Column:
    """First two digits of the 5-digit station code.

    For Paris intra-muros this matches the arrondissement (01 to 20); other
    values are suburban towns. To be confirmed against the official mapping.
    """
    return F.substring(F.lpad(station_code, 5, "0"), 1, 2)


def latest_station_information(information_raw: DataFrame) -> DataFrame:
    """Most recent name / location / capacity of each station."""
    stations = explode_stations(information_raw).dropna(subset=["station_id"])
    newest_first = Window.partitionBy("station_id").orderBy(F.col("ingested_at").desc())
    return (
        stations.withColumn("_rank", F.row_number().over(newest_first))
        .filter(F.col("_rank") == 1)
        .select("station_id", "name", "lat", "lon", "capacity")
    )


def to_silver(status_raw: DataFrame, information_raw: DataFrame) -> DataFrame:
    """Clean station status snapshots and enrich them with station information.

    Deduplicates on (station_id, ingested_at): replaying the same bronze files
    yields the same rows. last_reported is not used as a key because a station
    that does not change keeps the same value, and dropping those rows would
    distort network totals per snapshot.
    """
    status = (
        explode_stations(status_raw)
        .dropna(subset=["station_id", "ingested_at"])
        .dropDuplicates(["station_id", "ingested_at"])
        .select(
            "ingested_at",
            "station_id",
            F.col("stationCode").alias("station_code"),
            F.coalesce("num_bikes_available", F.lit(0)).alias("bikes"),
            _bike_type_count("mechanical").alias("mechanical_bikes"),
            _bike_type_count("ebike").alias("ebikes"),
            F.coalesce("num_docks_available", F.lit(0)).alias("docks"),
            (F.coalesce("is_installed", F.lit(0)) == 1).alias("is_installed"),
            (F.coalesce("is_renting", F.lit(0)) == 1).alias("is_renting"),
            (F.coalesce("is_returning", F.lit(0)) == 1).alias("is_returning"),
            F.timestamp_seconds("last_reported").alias("last_reported"),
        )
    )

    in_service = F.col("is_installed") & F.col("is_renting")
    return (
        status.join(latest_station_information(information_raw), "station_id", "left")
        .withColumn("zone", zone_from_code(F.col("station_code")))
        .withColumn("is_paris", F.col("zone").between("01", "20"))
        .withColumn(
            "occupancy_rate",
            F.when(F.col("capacity") > 0, F.col("bikes") / F.col("capacity")),
        )
        .withColumn("is_out_of_service", ~in_service)
        .withColumn("is_empty", in_service & (F.col("bikes") == 0))
        .withColumn(
            "is_full", in_service & F.col("is_returning") & (F.col("docks") == 0)
        )
        .withColumn("snapshot_date", F.to_date("ingested_at"))
    )


# ---------- Gold ----------


def _snapshot_kpis() -> list[Column]:
    return [
        F.count("*").alias("stations"),
        F.sum("bikes").alias("bikes"),
        F.sum("mechanical_bikes").alias("mechanical_bikes"),
        F.sum("ebikes").alias("ebikes"),
        F.sum("docks").alias("docks"),
        F.sum("capacity").alias("capacity"),
        (F.sum("bikes") / F.sum("capacity")).alias("occupancy_rate"),
        F.sum(F.col("is_empty").cast("int")).alias("empty_stations"),
        F.sum(F.col("is_full").cast("int")).alias("full_stations"),
        F.sum(F.col("is_out_of_service").cast("int")).alias("out_of_service_stations"),
    ]


def network_snapshot(silver: DataFrame) -> DataFrame:
    """Network-wide KPIs per snapshot (one row per ingested_at)."""
    return silver.groupBy("snapshot_date", "ingested_at").agg(*_snapshot_kpis())


def zone_snapshot(silver: DataFrame) -> DataFrame:
    """KPIs per zone (arrondissement or town) and snapshot."""
    return silver.groupBy("snapshot_date", "ingested_at", "zone", "is_paris").agg(
        *_snapshot_kpis()
    )


def station_timeseries(
    silver: DataFrame,
    rolling_minutes: int = 60,
    stuck_minutes: int = 30,
    drop_ratio: float = 0.5,
    drop_min_bikes: float = 5.0,
) -> DataFrame:
    """Per-station history with a rolling average and anomaly flags.

    Anomalies, by priority:
    - ``hors_service``: station not installed or not renting;
    - ``vide_prolongee`` / ``pleine_prolongee``: empty / full on every snapshot
      of the last ``stuck_minutes`` (at least two snapshots);
    - ``chute_brutale``: bikes below ``drop_ratio`` × the rolling average, when
      that average is at least ``drop_min_bikes``.
    """
    by_station = Window.partitionBy("station_id").orderBy(
        F.col("ingested_at").cast("long")
    )
    rolling = by_station.rangeBetween(-rolling_minutes * 60, 0)
    recent = by_station.rangeBetween(-stuck_minutes * 60, 0)

    recent_count = F.count("*").over(recent)
    stuck_empty = (recent_count >= 2) & (
        F.sum(F.col("is_empty").cast("int")).over(recent) == recent_count
    )
    stuck_full = (recent_count >= 2) & (
        F.sum(F.col("is_full").cast("int")).over(recent) == recent_count
    )

    return (
        silver.withColumn("bikes_rolling_avg", F.avg("bikes").over(rolling))
        .withColumn(
            "sudden_drop",
            (F.col("bikes_rolling_avg") >= drop_min_bikes)
            & (F.col("bikes") < F.col("bikes_rolling_avg") * drop_ratio),
        )
        .withColumn(
            "anomaly",
            F.when(F.col("is_out_of_service"), "hors_service")
            .when(stuck_empty, "vide_prolongee")
            .when(stuck_full, "pleine_prolongee")
            .when(F.col("sudden_drop"), "chute_brutale"),
        )
    )


# ---------- Incremental processing ----------


def new_since(df: DataFrame, watermark: datetime | None) -> DataFrame:
    """Rows ingested strictly after ``watermark`` (all rows when it is None)."""
    if watermark is None:
        return df
    return df.filter(F.col("ingested_at") > F.lit(watermark))


def max_ingested_at(df: DataFrame) -> datetime | None:
    """Latest ingested_at of ``df``: the next watermark (None when ``df`` is empty)."""
    row = df.agg(F.max("ingested_at").alias("watermark")).first()
    if row is None:
        return None
    watermark: datetime | None = row["watermark"]
    return watermark
