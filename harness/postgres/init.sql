-- Mira's prices, and what makes Thursday reproducible on a laptop.
--
-- The service reads `prices` (sku, amount_cents). It is a view: every read of
-- it costs 25 ms times the number of reads of it running at that moment, the
-- way a busy primary slows down under a herd. One read on its own stays cheap.
-- Every read also bumps the `store_reads` sequence, which `make reads` and
-- `make burst` print. None of this is the service's business.

CREATE TABLE price_rows (
    sku          text PRIMARY KEY,
    amount_cents integer NOT NULL
);

INSERT INTO price_rows
SELECT 'sku-' || n, 999 + n * 300 FROM generate_series(1, 50) AS n;

CREATE SEQUENCE store_reads;

CREATE FUNCTION store_read() RETURNS boolean
LANGUAGE plpgsql VOLATILE AS $$
DECLARE
    in_flight integer;
BEGIN
    PERFORM nextval('store_reads');
    SELECT count(*) INTO in_flight
      FROM pg_stat_activity
     WHERE state = 'active' AND query ILIKE '%prices%' AND backend_type = 'client backend';
    PERFORM pg_sleep(0.025 * greatest(in_flight, 1));
    RETURN true;
END $$;

-- The uncorrelated subquery runs once per query, however many rows match.
CREATE VIEW prices AS
SELECT sku, amount_cents FROM price_rows WHERE (SELECT store_read());
