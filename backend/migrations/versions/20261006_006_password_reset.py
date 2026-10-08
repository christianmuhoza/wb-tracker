"""Add user email column and password reset token storage."""

from alembic import op

revision = "20261006_006"
down_revision = "20260914_005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE users
            ADD COLUMN IF NOT EXISTS email TEXT;

        CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email
            ON users (lower(email)) WHERE email IS NOT NULL;

        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id BIGSERIAL PRIMARY KEY,
            username TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
            token_hash TEXT NOT NULL UNIQUE,
            expires_at TIMESTAMPTZ NOT NULL,
            used_at TIMESTAMPTZ,
            issued_by TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_username
            ON password_reset_tokens (username, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires
            ON password_reset_tokens (expires_at);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS password_reset_tokens;
        DROP INDEX IF EXISTS uq_users_email;
        ALTER TABLE users DROP COLUMN IF EXISTS email;
        """
    )
