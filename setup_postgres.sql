-- Business Analytics Assistant — Connector B (PostgreSQL) setup
-- Run this against a fresh Postgres database, then COPY the two CSVs in.
-- Usage:
--   psql -h <host> -U <user> -d <db> -f setup_postgres.sql
--   Then load data (adjust local paths as needed):
--     \copy orders FROM 'orders.csv' WITH (FORMAT csv, HEADER true)
--     \copy footfall FROM 'footfall.csv' WITH (FORMAT csv, HEADER true)

DROP TABLE IF EXISTS orders;
CREATE TABLE orders (
    order_id     INTEGER PRIMARY KEY,
    branch       TEXT NOT NULL,
    city         TEXT NOT NULL,
    date         DATE NOT NULL,
    item         TEXT NOT NULL,
    category     TEXT NOT NULL,
    quantity     INTEGER,          -- intentionally contains a few -1 rows (data-quality test case)
    revenue      NUMERIC(10, 2),   -- intentionally contains a few NULL rows (data-quality test case)
    order_value  NUMERIC(10, 2)
);

DROP TABLE IF EXISTS footfall;
CREATE TABLE footfall (
    branch          TEXT NOT NULL,
    city            TEXT NOT NULL,
    week_start      DATE NOT NULL,
    footfall_count  INTEGER,
    PRIMARY KEY (branch, week_start)
);

CREATE INDEX idx_orders_branch ON orders(branch);
CREATE INDEX idx_orders_city ON orders(city);
CREATE INDEX idx_orders_date ON orders(date);
CREATE INDEX idx_footfall_branch ON footfall(branch);

-- After running this file, load data with psql \copy (client-side, works with any host):
-- \copy orders FROM 'orders.csv' WITH (FORMAT csv, HEADER true)
-- \copy footfall FROM 'footfall.csv' WITH (FORMAT csv, HEADER true)
--
-- Or from Python (psycopg2 / SQLAlchemy) during backend startup, e.g.:
-- with open('orders.csv') as f:
--     cur.copy_expert("COPY orders FROM STDIN WITH (FORMAT csv, HEADER true)", f)
