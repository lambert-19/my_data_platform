-- Run on the built-in serverless pool, after 01_create_database.sql.
-- Views over the gold Delta tables written by nb_velib_processing; Power BI reads them
-- in DirectQuery. No credential: the caller's Entra ID identity is used to read the lake
-- (Storage Blob Data Contributor), so there is no key or password anywhere.
-- Each statement goes through EXEC so the script runs in one go (no GO separators).

USE velib;

IF NOT EXISTS (SELECT 1 FROM sys.external_data_sources WHERE name = 'gold_velib')
    EXEC(N'CREATE EXTERNAL DATA SOURCE gold_velib
           WITH (LOCATION = ''https://stvelibmwzyy4.dfs.core.windows.net/gold/velib'')');

-- Network-wide KPIs per snapshot (trend lines, KPI cards).
EXEC(N'CREATE OR ALTER VIEW dbo.network_snapshot AS
       SELECT * FROM OPENROWSET(BULK ''network_snapshot/'', DATA_SOURCE = ''gold_velib'', FORMAT = ''DELTA'') AS r');

-- KPIs per zone (arrondissement 01-20 or suburban town) and snapshot.
EXEC(N'CREATE OR ALTER VIEW dbo.zone_snapshot AS
       SELECT * FROM OPENROWSET(BULK ''zone_snapshot/'', DATA_SOURCE = ''gold_velib'', FORMAT = ''DELTA'') AS r');

-- Per-station history with rolling average and anomaly flags.
EXEC(N'CREATE OR ALTER VIEW dbo.station_timeseries AS
       SELECT * FROM OPENROWSET(BULK ''station_timeseries/'', DATA_SOURCE = ''gold_velib'', FORMAT = ''DELTA'') AS r');

-- Latest state of every station (map, anomaly table).
EXEC(N'CREATE OR ALTER VIEW dbo.station_latest AS
       SELECT * FROM OPENROWSET(BULK ''station_latest/'', DATA_SOURCE = ''gold_velib'', FORMAT = ''DELTA'') AS r');

-- Quick check
SELECT TOP 5 ingested_at, stations, bikes, occupancy_rate, empty_stations, full_stations, out_of_service_stations
FROM dbo.network_snapshot
ORDER BY ingested_at DESC;
