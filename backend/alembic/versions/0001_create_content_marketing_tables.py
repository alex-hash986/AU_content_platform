"""Create content marketing tables"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

channel_type = postgresql.ENUM(
    "telegram", "vk", "instagram", "wordpress", "mailchimp",
    name="channel_type", create_type=False,
)
post_status = postgresql.ENUM(
    "draft", "scheduled", "published", "failed", name="post_status", create_type=False
)
variant_label = postgresql.ENUM("A", "B", name="variant_label", create_type=False)


def upgrade() -> None:
    for enum in (channel_type, post_status, variant_label):
        enum.create(op.get_bind())
    op.create_table(
        'channels',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', channel_type, nullable=False),
        sa.Column('credentials_json', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'content_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('target_audience', sa.Text(), nullable=False),
        sa.Column('tone_of_voice', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('month BETWEEN 1 AND 12', name='valid_month'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'posts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('channel_type', channel_type, nullable=False),
        sa.Column('topic', sa.Text(), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', post_status, server_default='draft', nullable=False),
        sa.ForeignKeyConstraint(['plan_id'], ['content_plans.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_posts_plan_id'), 'posts', ['plan_id'], unique=False)
    op.create_table(
        'post_variants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('body_text', sa.Text(), nullable=False),
        sa.Column('cta', sa.Text(), nullable=False),
        sa.Column('variant_label', variant_label, nullable=False),
        sa.Column('is_selected', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('post_id', 'id', name='unique_post_variant_id'),
        sa.UniqueConstraint('post_id', 'variant_label', name='unique_post_variant_label'),
    )
    op.create_table(
        'metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('variant_id', sa.Integer(), nullable=True),
        sa.Column('views', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('likes', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('shares', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('clicks', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('conversions', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['post_id', 'variant_id'], ['post_variants.post_id', 'post_variants.id'], name='metric_post_variant_fk'),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_metrics_post_id'), 'metrics', ['post_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_metrics_post_id'), table_name='metrics')
    op.drop_table('metrics')
    op.drop_table('post_variants')
    op.drop_index(op.f('ix_posts_plan_id'), table_name='posts')
    op.drop_table('posts')
    op.drop_table('content_plans')
    op.drop_table('channels')
    for enum in (variant_label, post_status, channel_type):
        enum.drop(op.get_bind())
