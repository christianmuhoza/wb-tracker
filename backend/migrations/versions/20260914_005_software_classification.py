"""Add explainable software classification fields and history."""

from alembic import op

revision = "20260914_005"
down_revision = "20260910_004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE procurement_notices
            ADD COLUMN IF NOT EXISTS classification TEXT,
            ADD COLUMN IF NOT EXISTS classification_status TEXT,
            ADD COLUMN IF NOT EXISTS technology_related BOOLEAN,
            ADD COLUMN IF NOT EXISTS primary_deliverable TEXT,
            ADD COLUMN IF NOT EXISTS software_subcategory TEXT,
            ADD COLUMN IF NOT EXISTS classification_evidence JSONB,
            ADD COLUMN IF NOT EXISTS classifier_name TEXT,
            ADD COLUMN IF NOT EXISTS classifier_version TEXT,
            ADD COLUMN IF NOT EXISTS prompt_version TEXT,
            ADD COLUMN IF NOT EXISTS classification_model TEXT;

        CREATE INDEX IF NOT EXISTS idx_notices_classification
            ON procurement_notices (classification);
        CREATE INDEX IF NOT EXISTS idx_notices_classification_status
            ON procurement_notices (classification_status);

        CREATE TABLE IF NOT EXISTS notice_classifications (
            id BIGSERIAL PRIMARY KEY,
            notice_id TEXT NOT NULL REFERENCES procurement_notices(id) ON DELETE CASCADE,
            classification TEXT NOT NULL,
            classification_status TEXT NOT NULL,
            is_software_related BOOLEAN NOT NULL,
            technology_related BOOLEAN,
            primary_deliverable TEXT,
            software_work_type TEXT,
            software_product_category TEXT,
            software_subcategory TEXT,
            software_product_name TEXT,
            confidence TEXT NOT NULL,
            reason TEXT,
            evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
            rule_signals JSONB NOT NULL DEFAULT '[]'::jsonb,
            classifier_name TEXT NOT NULL,
            classifier_version TEXT NOT NULL,
            prompt_version TEXT,
            classification_model TEXT,
            source TEXT NOT NULL,
            reviewed BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_notice_classifications_notice
            ON notice_classifications (notice_id, created_at DESC);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS notice_classifications;
        DROP INDEX IF EXISTS idx_notices_classification_status;
        DROP INDEX IF EXISTS idx_notices_classification;
        ALTER TABLE procurement_notices
            DROP COLUMN IF EXISTS classification_model,
            DROP COLUMN IF EXISTS prompt_version,
            DROP COLUMN IF EXISTS classifier_version,
            DROP COLUMN IF EXISTS classifier_name,
            DROP COLUMN IF EXISTS classification_evidence,
            DROP COLUMN IF EXISTS software_subcategory,
            DROP COLUMN IF EXISTS primary_deliverable,
            DROP COLUMN IF EXISTS technology_related,
            DROP COLUMN IF EXISTS classification_status,
            DROP COLUMN IF EXISTS classification;
        """
    )
