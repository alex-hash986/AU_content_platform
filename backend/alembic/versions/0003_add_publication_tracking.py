"""Track publication results and distinguish simulated metrics."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("posts", sa.Column("published_variant_id", sa.Integer()))
    op.add_column("posts", sa.Column("published_at", sa.DateTime(timezone=True)))
    op.add_column("posts", sa.Column("external_id", sa.Text()))
    op.add_column("posts", sa.Column("publication_error", sa.Text()))
    op.create_foreign_key(
        "post_published_variant_fk", "posts", "post_variants",
        ["id", "published_variant_id"], ["post_id", "id"],
    )
    op.create_index("ix_posts_status_scheduled_at", "posts", ["status", "scheduled_at"])
    op.add_column(
        "metrics", sa.Column("is_simulated", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.create_index(
        "uq_metrics_simulated_variant", "metrics", ["post_id", "variant_id"],
        unique=True, postgresql_where=sa.text("is_simulated"),
    )


def downgrade() -> None:
    op.drop_index("uq_metrics_simulated_variant", table_name="metrics")
    op.drop_column("metrics", "is_simulated")
    op.drop_index("ix_posts_status_scheduled_at", table_name="posts")
    op.drop_constraint("post_published_variant_fk", "posts", type_="foreignkey")
    op.drop_column("posts", "publication_error")
    op.drop_column("posts", "external_id")
    op.drop_column("posts", "published_at")
    op.drop_column("posts", "published_variant_id")
