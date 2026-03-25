from django.db import migrations


SYNC_FORWARD_SQL = """
ALTER TABLE stocks_stockuniverse
    ADD COLUMN IF NOT EXISTS quote_symbol varchar(32) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS source_file varchar(255) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS raw_sector_label varchar(255) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS series varchar(20) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS isin_code varchar(32) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS weight numeric(12, 4) NULL,
    ADD COLUMN IF NOT EXISTS is_active boolean NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS imported_at timestamp with time zone NULL;

UPDATE stocks_stockuniverse
SET quote_symbol = CASE
    WHEN quote_symbol = '' AND market = 'INDIA' AND position('.' in symbol) = 0 THEN symbol || '.NS'
    WHEN quote_symbol = '' THEN symbol
    ELSE quote_symbol
END;

UPDATE stocks_stockuniverse
SET imported_at = NOW()
WHERE imported_at IS NULL;

ALTER TABLE stocks_stockuniverse
    ALTER COLUMN imported_at SET DEFAULT NOW(),
    ALTER COLUMN imported_at SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS stocks_stockuniverse_market_symbol_uidx
    ON stocks_stockuniverse (market, symbol);
"""

SYNC_REVERSE_SQL = """
DROP INDEX IF EXISTS stocks_stockuniverse_market_symbol_uidx;
"""


class Migration(migrations.Migration):
    dependencies = [
        ('stocks', '0003_stockuniverse'),
    ]

    operations = [
        migrations.RunSQL(SYNC_FORWARD_SQL, SYNC_REVERSE_SQL),
    ]
