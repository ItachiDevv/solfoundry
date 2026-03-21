"""PostgreSQL migration: creates contributors, payouts, buybacks tables."""

UPGRADE_SQL = """
CREATE TABLE IF NOT EXISTS contributors (
    id UUID PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    avatar_url VARCHAR(500),
    bio TEXT,
    skills JSON DEFAULT '[]',
    badges JSON DEFAULT '[]',
    social_links JSON DEFAULT '{}',
    total_contributions INTEGER DEFAULT 0,
    total_bounties_completed INTEGER DEFAULT 0,
    total_earnings FLOAT DEFAULT 0.0,
    reputation_score INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_contributors_username ON contributors (username);

CREATE TABLE IF NOT EXISTS payouts (
    id UUID PRIMARY KEY,
    recipient VARCHAR(100) NOT NULL,
    recipient_wallet VARCHAR(64),
    amount FLOAT NOT NULL,
    token VARCHAR(20) DEFAULT 'FNDRY',
    bounty_id VARCHAR(100),
    bounty_title VARCHAR(200),
    tx_hash VARCHAR(128) UNIQUE,
    status VARCHAR(20) DEFAULT 'pending',
    solscan_url VARCHAR(256),
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_payouts_recipient ON payouts (recipient);
CREATE INDEX IF NOT EXISTS ix_payouts_status ON payouts (status);

CREATE TABLE IF NOT EXISTS buybacks (
    id UUID PRIMARY KEY,
    amount_sol FLOAT NOT NULL,
    amount_fndry FLOAT NOT NULL,
    price_per_fndry FLOAT NOT NULL,
    tx_hash VARCHAR(128) UNIQUE,
    solscan_url VARCHAR(256),
    created_at TIMESTAMPTZ NOT NULL
);
"""

DOWNGRADE_SQL = """
DROP TABLE IF EXISTS buybacks;
DROP TABLE IF EXISTS payouts;
DROP TABLE IF EXISTS contributors;
"""

if __name__ == "__main__":
    import asyncio
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from app.database import engine

    async def run():
        """Execute the migration against the configured database."""
        from sqlalchemy import text
        async with engine.begin() as conn:
            for statement in UPGRADE_SQL.strip().split(";"):
                if statement.strip():
                    await conn.execute(text(statement))
        print("Migration 002 applied successfully")

    asyncio.run(run())
