"""Create the WB Tracker application schema.

This baseline is intentionally idempotent so it can adopt databases created
by the previous runtime DDL helpers without losing data.
"""

from alembic import op

revision = "20260910_001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        INSERT INTO app_settings (key, value)
        VALUES
            ('baseline_date', (CURRENT_DATE - INTERVAL '2 years')::text),
            ('country_batch', '5'),
            ('request_delay', '1.2'),
            ('auto_sync_hour', '06:00')
        ON CONFLICT (key) DO NOTHING;

        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            is_admin BOOLEAN NOT NULL DEFAULT FALSE,
            role TEXT NOT NULL DEFAULT 'viewer',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'viewer';
        UPDATE users SET role = 'admin' WHERE is_admin;

        CREATE TABLE IF NOT EXISTS target_countries (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            query_aliases TEXT[] DEFAULT '{}',
            storage_aliases TEXT[] DEFAULT '{}',
            sync_order INT DEFAULT 0,
            added_at TIMESTAMPTZ DEFAULT NOW()
        );
        ALTER TABLE target_countries ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
        ALTER TABLE target_countries ADD COLUMN IF NOT EXISTS query_aliases TEXT[] DEFAULT '{}';
        ALTER TABLE target_countries ADD COLUMN IF NOT EXISTS storage_aliases TEXT[] DEFAULT '{}';
        ALTER TABLE target_countries ADD COLUMN IF NOT EXISTS sync_order INT DEFAULT 0;

        CREATE TABLE IF NOT EXISTS procurement_notices (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            project_name TEXT,
            country TEXT,
            notice_no TEXT,
            notice_type TEXT,
            notice_status TEXT,
            procurement_method TEXT,
            language TEXT,
            title TEXT,
            description TEXT,
            borrower_bid_reference TEXT,
            notice_date DATE,
            submission_deadline TIMESTAMPTZ,
            submission_date DATE,
            contract_amount NUMERIC,
            currency TEXT,
            borrower TEXT,
            contact_name TEXT,
            contact_org TEXT,
            contact_address TEXT,
            contact_city TEXT,
            contact_phone TEXT,
            contact_email TEXT,
            contact_website TEXT,
            url TEXT,
            status TEXT,
            fetched_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        ALTER TABLE procurement_notices ADD COLUMN IF NOT EXISTS notice_no TEXT;
        ALTER TABLE procurement_notices ADD COLUMN IF NOT EXISTS notice_status TEXT;
        ALTER TABLE procurement_notices ADD COLUMN IF NOT EXISTS language TEXT;
        ALTER TABLE procurement_notices ADD COLUMN IF NOT EXISTS borrower_bid_reference TEXT;
        ALTER TABLE procurement_notices ADD COLUMN IF NOT EXISTS submission_deadline TIMESTAMPTZ;
        ALTER TABLE procurement_notices ADD COLUMN IF NOT EXISTS submission_date DATE;
        ALTER TABLE procurement_notices ADD COLUMN IF NOT EXISTS contract_amount NUMERIC;
        ALTER TABLE procurement_notices ADD COLUMN IF NOT EXISTS currency TEXT;
        ALTER TABLE procurement_notices ADD COLUMN IF NOT EXISTS contact_name TEXT;
        ALTER TABLE procurement_notices ADD COLUMN IF NOT EXISTS contact_org TEXT;
        ALTER TABLE procurement_notices ADD COLUMN IF NOT EXISTS contact_address TEXT;
        ALTER TABLE procurement_notices ADD COLUMN IF NOT EXISTS contact_city TEXT;
        ALTER TABLE procurement_notices ADD COLUMN IF NOT EXISTS contact_phone TEXT;
        ALTER TABLE procurement_notices ADD COLUMN IF NOT EXISTS contact_website TEXT;

        CREATE TABLE IF NOT EXISTS fetch_runs (
            id SERIAL PRIMARY KEY,
            run_at TIMESTAMPTZ DEFAULT NOW(),
            country TEXT,
            notice_type TEXT,
            fetched INT,
            new_records INT,
            success BOOLEAN,
            error_msg TEXT
        );
        CREATE TABLE IF NOT EXISTS country_fetch_status (
            country TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'not_started',
            last_started_at TIMESTAMPTZ,
            last_finished_at TIMESTAMPTZ,
            last_success_at TIMESTAMPTZ,
            last_attempted_since DATE,
            last_page_size INT,
            fetched_records INT DEFAULT 0,
            new_records INT DEFAULT 0,
            total_available INT DEFAULT 0,
            row_count INT DEFAULT 0,
            first_notice_date DATE,
            last_notice_date DATE,
            error_msg TEXT,
            api_url TEXT,
            retry_count INT DEFAULT 0,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS bidders (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            category TEXT,
            contact_name TEXT,
            contact_email TEXT,
            contact_phone TEXT,
            linkedin_url TEXT,
            contact_org TEXT,
            country TEXT,
            business_model TEXT,
            core_products TEXT,
            corporate_activities TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        ALTER TABLE bidders ADD COLUMN IF NOT EXISTS category TEXT;
        ALTER TABLE bidders ADD COLUMN IF NOT EXISTS contact_name TEXT;
        ALTER TABLE bidders ADD COLUMN IF NOT EXISTS contact_email TEXT;
        ALTER TABLE bidders ADD COLUMN IF NOT EXISTS contact_phone TEXT;
        ALTER TABLE bidders ADD COLUMN IF NOT EXISTS linkedin_url TEXT;
        ALTER TABLE bidders ADD COLUMN IF NOT EXISTS contact_org TEXT;
        ALTER TABLE bidders ADD COLUMN IF NOT EXISTS country TEXT;
        ALTER TABLE bidders ADD COLUMN IF NOT EXISTS business_model TEXT;
        ALTER TABLE bidders ADD COLUMN IF NOT EXISTS core_products TEXT;
        ALTER TABLE bidders ADD COLUMN IF NOT EXISTS corporate_activities TEXT;
        CREATE TABLE IF NOT EXISTS bidder_awards (
            id SERIAL PRIMARY KEY,
            bidder_id INTEGER NOT NULL REFERENCES bidders(id) ON DELETE CASCADE,
            notice_id TEXT NOT NULL REFERENCES procurement_notices(id) ON DELETE CASCADE,
            won BOOLEAN DEFAULT FALSE,
            award_amount NUMERIC,
            currency TEXT,
            award_date DATE,
            role TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(bidder_id, notice_id)
        );
        CREATE TABLE IF NOT EXISTS award_alerts (
            id SERIAL PRIMARY KEY,
            source_notice_id TEXT NOT NULL REFERENCES procurement_notices(id) ON DELETE CASCADE,
            award_notice_id TEXT NOT NULL REFERENCES procurement_notices(id) ON DELETE CASCADE,
            match_status TEXT NOT NULL DEFAULT 'auto_matched',
            match_score INT NOT NULL DEFAULT 0,
            matched_reason TEXT,
            seen_at TIMESTAMPTZ,
            dismissed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(source_notice_id, award_notice_id)
        );
        CREATE TABLE IF NOT EXISTS fetch_jobs (
            id SERIAL PRIMARY KEY,
            job_type TEXT NOT NULL,
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            status TEXT NOT NULL DEFAULT 'queued',
            progress TEXT,
            error TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            started_at TIMESTAMPTZ,
            finished_at TIMESTAMPTZ,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );

        ALTER TABLE procurement_notices ADD COLUMN IF NOT EXISTS is_software_related BOOLEAN;
        ALTER TABLE procurement_notices ADD COLUMN IF NOT EXISTS software_work_type TEXT;
        ALTER TABLE procurement_notices ADD COLUMN IF NOT EXISTS software_product_category TEXT;
        ALTER TABLE procurement_notices ADD COLUMN IF NOT EXISTS software_product_name TEXT;
        ALTER TABLE procurement_notices ADD COLUMN IF NOT EXISTS software_confidence TEXT;
        ALTER TABLE procurement_notices ADD COLUMN IF NOT EXISTS software_reason TEXT;
        ALTER TABLE procurement_notices ADD COLUMN IF NOT EXISTS software_classification_source TEXT;
        ALTER TABLE procurement_notices ADD COLUMN IF NOT EXISTS software_classified_at TIMESTAMPTZ;
        ALTER TABLE procurement_notices ADD COLUMN IF NOT EXISTS software_reviewed BOOLEAN NOT NULL DEFAULT FALSE;

        CREATE INDEX IF NOT EXISTS idx_country ON procurement_notices (country);
        CREATE INDEX IF NOT EXISTS idx_notice_type ON procurement_notices (notice_type);
        CREATE INDEX IF NOT EXISTS idx_notice_date ON procurement_notices (notice_date);
        CREATE INDEX IF NOT EXISTS idx_status ON procurement_notices (status);
        CREATE INDEX IF NOT EXISTS idx_award_alerts_seen ON award_alerts (seen_at);
        CREATE INDEX IF NOT EXISTS idx_award_alerts_status ON award_alerts (match_status);
        CREATE INDEX IF NOT EXISTS idx_award_alerts_award ON award_alerts (award_notice_id);
        CREATE INDEX IF NOT EXISTS idx_fetch_jobs_status ON fetch_jobs (status);
        CREATE INDEX IF NOT EXISTS idx_notices_software_related ON procurement_notices (is_software_related);
        CREATE INDEX IF NOT EXISTS idx_notices_software_category ON procurement_notices (software_product_category);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS fetch_jobs;
        DROP TABLE IF EXISTS award_alerts;
        DROP TABLE IF EXISTS bidder_awards;
        DROP TABLE IF EXISTS bidders;
        DROP TABLE IF EXISTS country_fetch_status;
        DROP TABLE IF EXISTS fetch_runs;
        DROP TABLE IF EXISTS procurement_notices;
        DROP TABLE IF EXISTS target_countries;
        DROP TABLE IF EXISTS users;
        DROP TABLE IF EXISTS app_settings;
        """
    )
