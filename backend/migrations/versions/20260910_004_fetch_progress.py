"""Add structured fetch progress and worker heartbeats."""

from alembic import op

revision = "20260910_004"
down_revision = "20260910_003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE fetch_jobs
            ADD COLUMN IF NOT EXISTS progress_data JSONB NOT NULL DEFAULT '{}'::jsonb,
            ADD COLUMN IF NOT EXISTS heartbeat_at TIMESTAMPTZ;

        UPDATE fetch_jobs
        SET heartbeat_at = COALESCE(locked_at, updated_at)
        WHERE heartbeat_at IS NULL;

        CREATE INDEX IF NOT EXISTS idx_fetch_jobs_heartbeat
            ON fetch_jobs (status, heartbeat_at);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS idx_fetch_jobs_heartbeat;
        ALTER TABLE fetch_jobs
            DROP COLUMN IF EXISTS heartbeat_at,
            DROP COLUMN IF EXISTS progress_data;
        """
    )
