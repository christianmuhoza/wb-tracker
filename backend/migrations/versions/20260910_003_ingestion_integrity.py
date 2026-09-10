"""Prevent duplicate active jobs and duplicate ingestion identities."""

from alembic import op

revision = "20260910_003"
down_revision = "20260910_002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE fetch_jobs
            ADD COLUMN IF NOT EXISTS idempotency_key TEXT;

        CREATE UNIQUE INDEX IF NOT EXISTS uq_fetch_jobs_active_idempotency
            ON fetch_jobs (idempotency_key)
            WHERE idempotency_key IS NOT NULL
              AND status IN ('queued', 'running');

        CREATE TEMP TABLE notice_duplicates ON COMMIT DROP AS
        SELECT id,
               FIRST_VALUE(id) OVER (
                   PARTITION BY LOWER(TRIM(country)), LOWER(TRIM(notice_no))
                   ORDER BY id
               ) AS keeper_id
        FROM procurement_notices
        WHERE NULLIF(TRIM(country), '') IS NOT NULL
          AND NULLIF(TRIM(notice_no), '') IS NOT NULL;

        DELETE FROM bidder_awards ba
        USING notice_duplicates d
        WHERE ba.notice_id = d.id
          AND d.id <> d.keeper_id
          AND EXISTS (
              SELECT 1
              FROM bidder_awards kept
              WHERE kept.notice_id = d.keeper_id
                AND kept.bidder_id = ba.bidder_id
          );

        UPDATE bidder_awards ba
        SET notice_id = d.keeper_id
        FROM notice_duplicates d
        WHERE ba.notice_id = d.id
          AND d.id <> d.keeper_id;

        DELETE FROM award_alerts aa
        USING notice_duplicates d
        WHERE aa.source_notice_id = d.id
          AND d.id <> d.keeper_id
          AND EXISTS (
              SELECT 1
              FROM award_alerts kept
              WHERE kept.source_notice_id = d.keeper_id
                AND kept.award_notice_id = aa.award_notice_id
          );

        UPDATE award_alerts aa
        SET source_notice_id = d.keeper_id
        FROM notice_duplicates d
        WHERE aa.source_notice_id = d.id
          AND d.id <> d.keeper_id;

        DELETE FROM award_alerts aa
        USING notice_duplicates d
        WHERE aa.award_notice_id = d.id
          AND d.id <> d.keeper_id
          AND EXISTS (
              SELECT 1
              FROM award_alerts kept
              WHERE kept.source_notice_id = aa.source_notice_id
                AND kept.award_notice_id = d.keeper_id
          );

        UPDATE award_alerts aa
        SET award_notice_id = d.keeper_id
        FROM notice_duplicates d
        WHERE aa.award_notice_id = d.id
          AND d.id <> d.keeper_id;

        DELETE FROM procurement_notices n
        USING notice_duplicates d
        WHERE n.id = d.id
          AND d.id <> d.keeper_id;

        CREATE UNIQUE INDEX IF NOT EXISTS uq_procurement_notices_country_notice
            ON procurement_notices (LOWER(TRIM(country)), LOWER(TRIM(notice_no)))
            WHERE NULLIF(TRIM(country), '') IS NOT NULL
              AND NULLIF(TRIM(notice_no), '') IS NOT NULL;

        CREATE TEMP TABLE bidder_duplicates ON COMMIT DROP AS
        SELECT id,
               FIRST_VALUE(id) OVER (
                   PARTITION BY LOWER(TRIM(name))
                   ORDER BY id
               ) AS keeper_id
        FROM bidders
        WHERE NULLIF(TRIM(name), '') IS NOT NULL;

        DELETE FROM bidder_awards ba
        USING bidder_duplicates d
        WHERE ba.bidder_id = d.id
          AND d.id <> d.keeper_id
          AND EXISTS (
              SELECT 1
              FROM bidder_awards kept
              WHERE kept.bidder_id = d.keeper_id
                AND kept.notice_id = ba.notice_id
          );

        UPDATE bidder_awards ba
        SET bidder_id = d.keeper_id
        FROM bidder_duplicates d
        WHERE ba.bidder_id = d.id
          AND d.id <> d.keeper_id;

        DELETE FROM bidders b
        USING bidder_duplicates d
        WHERE b.id = d.id
          AND d.id <> d.keeper_id;

        CREATE UNIQUE INDEX IF NOT EXISTS uq_bidders_normalized_name
            ON bidders (LOWER(TRIM(name)));
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS uq_bidders_normalized_name;
        DROP INDEX IF EXISTS uq_procurement_notices_country_notice;
        DROP INDEX IF EXISTS uq_fetch_jobs_active_idempotency;
        ALTER TABLE fetch_jobs DROP COLUMN IF EXISTS idempotency_key;
        """
    )
