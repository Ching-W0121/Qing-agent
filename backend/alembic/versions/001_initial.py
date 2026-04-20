"""initial migration

Revision ID: 001_initial
Revises:
Create Date: 2026-03-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 users 表
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('auth0_id', sa.String(length=255), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('username', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_auth0_id'), 'users', ['auth0_id'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # 创建 user_profiles 表
    op.create_table(
        'user_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('target_positions', sa.JSON(), nullable=True),
        sa.Column('target_cities', sa.JSON(), nullable=True),
        sa.Column('exclude_areas', sa.JSON(), nullable=True),
        sa.Column('salary_min', sa.Integer(), nullable=True),
        sa.Column('salary_max', sa.Integer(), nullable=True),
        sa.Column('experience_min', sa.Integer(), nullable=True),
        sa.Column('experience_max', sa.Integer(), nullable=True),
        sa.Column('platform_credentials', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_profiles_id'), 'user_profiles', ['id'], unique=False)
    op.create_index(op.f('ix_user_profiles_user_id'), 'user_profiles', ['user_id'], unique=True)

    # 创建 jobs 表
    op.create_table(
        'jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=True),
        sa.Column('platform_job_id', sa.String(length=255), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('company', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('area', sa.String(length=100), nullable=True),
        sa.Column('salary_min', sa.Integer(), nullable=True),
        sa.Column('salary_max', sa.Integer(), nullable=True),
        sa.Column('experience', sa.String(length=100), nullable=True),
        sa.Column('education', sa.String(length=50), nullable=True),
        sa.Column('job_type', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('requirements', sa.Text(), nullable=True),
        sa.Column('skills', sa.JSON(), nullable=True),
        sa.Column('industry', sa.String(length=100), nullable=True),
        sa.Column('source_url', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_jobs_id'), 'jobs', ['id'], unique=False)
    op.create_index(op.f('ix_jobs_platform'), 'jobs', ['platform'], unique=False)
    op.create_index(op.f('ix_jobs_platform_job_id'), 'jobs', ['platform_job_id'], unique=False)
    op.create_unique_constraint('uq_platform_job_id', ['jobs'], ['platform', 'platform_job_id'])

    # 创建 applications 表
    op.create_table(
        'applications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('job_id', sa.Integer(), nullable=True),
        sa.Column('platform', sa.String(length=50), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'SUBMITTED', 'ALREADY_APPLIED', 'FAILED', 'REJECTED', name='applicationstatus'), nullable=True),
        sa.Column('applied_at', sa.DateTime(), nullable=True),
        sa.Column('failed_reason', sa.Text(), nullable=True),
        sa.Column('apply_url', sa.String(length=500), nullable=True),
        sa.Column('apply_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_applications_id'), 'applications', ['id'], unique=False)
    op.create_index(op.f('ix_applications_user_id'), 'applications', ['user_id'], unique=False)

    # 创建 task_runs 表
    op.create_table(
        'task_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('task_type', sa.Enum('SEARCH', 'APPLY', 'VERIFY', name='tasktype'), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', name='taskstatus'), nullable=True),
        sa.Column('jobs_found', sa.Integer(), nullable=True),
        sa.Column('jobs_filtered', sa.Integer(), nullable=True),
        sa.Column('applications_submitted', sa.Integer(), nullable=True),
        sa.Column('applications_failed', sa.Integer(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_task_runs_id'), 'task_runs', ['id'], unique=False)
    op.create_index(op.f('ix_task_runs_user_id'), 'task_runs', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_task_runs_user_id'), table_name='task_runs')
    op.drop_index(op.f('ix_task_runs_id'), table_name='task_runs')
    op.drop_table('task_runs')

    op.drop_index(op.f('ix_applications_user_id'), table_name='applications')
    op.drop_index(op.f('ix_applications_id'), table_name='applications')
    op.drop_table('applications')

    op.drop_constraint('uq_platform_job_id', table_name='jobs', type_='unique')
    op.drop_index(op.f('ix_jobs_platform_job_id'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_platform'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_id'), table_name='jobs')
    op.drop_table('jobs')

    op.drop_index(op.f('ix_user_profiles_user_id'), table_name='user_profiles')
    op.drop_index(op.f('ix_user_profiles_id'), table_name='user_profiles')
    op.drop_table('user_profiles')

    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_auth0_id'), table_name='users')
    op.drop_table('users')
