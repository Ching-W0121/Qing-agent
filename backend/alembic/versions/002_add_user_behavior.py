"""Add user_behavior and job fields

Revision ID: 002_add_user_behavior
Revises: 001_initial
Create Date: 2026-04-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_add_user_behavior'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to jobs table
    op.add_column('jobs', sa.Column('publish_time', sa.DateTime(), nullable=True))
    op.add_column('jobs', sa.Column('tags', sa.JSON(), nullable=True))
    op.add_column('jobs', sa.Column('source', sa.String(length=50), nullable=True))
    op.add_column('jobs', sa.Column('is_exposed', sa.Boolean(), nullable=True))

    # Create user_behaviors table
    op.create_table(
        'user_behaviors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('job_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_behaviors_id'), 'user_behaviors', ['id'], unique=False)
    op.create_index(op.f('ix_user_behaviors_job_id'), 'user_behaviors', ['job_id'], unique=False)
    op.create_index(op.f('ix_user_behaviors_user_id'), 'user_behaviors', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_behaviors_user_id'), table_name='user_behaviors')
    op.drop_index(op.f('ix_user_behaviors_job_id'), table_name='user_behaviors')
    op.drop_index(op.f('ix_user_behaviors_id'), table_name='user_behaviors')
    op.drop_table('user_behaviors')

    op.drop_column('jobs', 'is_exposed')
    op.drop_column('jobs', 'source')
    op.drop_column('jobs', 'tags')
    op.drop_column('jobs', 'publish_time')
