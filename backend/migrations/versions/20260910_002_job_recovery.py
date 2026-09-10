"""Add retry and lease metadata to durable jobs."""

from alembic import op

revision = "20260910_002"
down_revision = "20260910_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE fetch_jobs
            ADD COLUMN IF NOT EXISTS attempt_count INT NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS max_attempts INT NOT NULL DEFAULT 3,
            ADD COLUMN IF NOT EXISTS next_attempt_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS locked_at TIMESTAMPTZ;
        CREATE INDEX IF NOT EXISTS idx_fetch_jobs_ready
            ON fetch_jobs (status, next_attempt_at, created_at);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS idx_fetch_jobs_ready;
        ALTER TABLE fetch_jobs
            DROP COLUMN IF EXISTS locked_at,
            DROP COLUMN IF EXISTS next_attempt_at,
            DROP COLUMN IF EXISTS max_attempts,
            DROP COLUMN IF EXISTS attempt_count;
        """
    )
