-- Run on the built-in serverless pool, after 02_create_gold_views.sql.
-- Analysis views built on top of the gold views, for extra Power BI visuals.
-- Each statement goes through EXEC so the script runs in one go (no GO separators).

USE velib;

-- Net change in bikes per zone between two consecutive snapshots:
-- positive = the zone receives bikes, negative = it sends them out.
EXEC(N'CREATE OR ALTER VIEW dbo.zone_flow AS
       SELECT ingested_at,
              zone,
              is_paris,
              bikes,
              bikes - LAG(bikes) OVER (PARTITION BY zone ORDER BY ingested_at) AS net_flow,
              DATEDIFF(minute, LAG(ingested_at) OVER (PARTITION BY zone ORDER BY ingested_at), ingested_at)
                  AS minutes_since_previous
       FROM dbo.zone_snapshot');

-- Service quality per zone and snapshot.
-- tension_rate: share of working stations that are empty or full (user cannot rent or return).
-- ebike_share: share of electric bikes among available bikes (they are rented first).
EXEC(N'CREATE OR ALTER VIEW dbo.zone_indicators AS
       SELECT ingested_at,
              zone,
              is_paris,
              stations,
              bikes,
              occupancy_rate,
              CAST(empty_stations + full_stations AS float)
                  / NULLIF(stations - out_of_service_stations, 0) AS tension_rate,
              CAST(ebikes AS float) / NULLIF(mechanical_bikes + ebikes, 0) AS ebike_share
       FROM dbo.zone_snapshot');

-- Paris (arrondissements 01-20) compared with the suburbs, per snapshot.
EXEC(N'CREATE OR ALTER VIEW dbo.paris_vs_suburbs AS
       SELECT ingested_at,
              CASE WHEN is_paris = 1 THEN ''Paris'' ELSE ''Banlieue'' END AS area,
              SUM(stations) AS stations,
              SUM(bikes) AS bikes,
              SUM(capacity) AS capacity,
              CAST(SUM(bikes) AS float) / NULLIF(SUM(capacity), 0) AS occupancy_rate,
              CAST(SUM(empty_stations) + SUM(full_stations) AS float)
                  / NULLIF(SUM(stations) - SUM(out_of_service_stations), 0) AS tension_rate,
              CAST(SUM(ebikes) AS float) / NULLIF(SUM(mechanical_bikes) + SUM(ebikes), 0) AS ebike_share
       FROM dbo.zone_snapshot
       GROUP BY ingested_at, CASE WHEN is_paris = 1 THEN ''Paris'' ELSE ''Banlieue'' END');

-- Problem stations over the whole history (use a Top N filter in Power BI).
-- problem_rate: share of snapshots where the station was empty or full.
EXEC(N'CREATE OR ALTER VIEW dbo.station_issues AS
       SELECT station_id,
              station_code,
              MAX(name) AS name,
              MAX(zone) AS zone,
              MAX(lat) AS lat,
              MAX(lon) AS lon,
              MAX(capacity) AS capacity,
              COUNT(*) AS snapshots,
              SUM(CAST(is_empty AS int)) AS empty_snapshots,
              SUM(CAST(is_full AS int)) AS full_snapshots,
              SUM(CAST(is_out_of_service AS int)) AS out_of_service_snapshots,
              SUM(CAST(sudden_drop AS int)) AS sudden_drops,
              CAST(SUM(CAST(is_empty AS int)) + SUM(CAST(is_full AS int)) AS float) / COUNT(*) AS problem_rate
       FROM dbo.station_timeseries
       GROUP BY station_id, station_code');

-- Quick check
SELECT area, stations, bikes, occupancy_rate, tension_rate, ebike_share
FROM dbo.paris_vs_suburbs
WHERE ingested_at = (SELECT MAX(ingested_at) FROM dbo.zone_snapshot);
