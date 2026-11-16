-- Run on the built-in serverless pool, connected to "master".
-- UTF-8 collation: avoids conversion warnings when reading Delta/Parquet strings.
IF DB_ID('velib') IS NULL
    CREATE DATABASE velib COLLATE Latin1_General_100_BIN2_UTF8;
