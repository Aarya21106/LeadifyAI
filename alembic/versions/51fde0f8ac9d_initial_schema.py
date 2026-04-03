"""initial_schema

Revision ID: 51fde0f8ac9d
Revises: 
Create Date: 2026-04-03 01:39:13.219025

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '51fde0f8ac9d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Create leads table
    op.create_table(
        'leads',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('company', sa.String(), nullable=True),
        sa.Column('first_email_sent_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.Enum('ACTIVE', 'PAUSED', 'CONVERTED', 'DEAD', name='leadstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_leads_email'), 'leads', ['email'], unique=True)
    op.create_index(op.f('ix_leads_status'), 'leads', ['status'], unique=False)

    # Create lead_events table
    op.create_table(
        'lead_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.Enum('OPENED', 'REPLIED', 'BOUNCED', 'OUT_OF_OFFICE', 'SIGNAL_DETECTED', name='leadeventtype'), nullable=False),
        sa.Column('raw_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('detected_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lead_events_lead_id'), 'lead_events', ['lead_id'], unique=False)
    op.create_index(op.f('ix_lead_events_event_type'), 'lead_events', ['event_type'], unique=False)

    # Create lead_scores table
    op.create_table(
        'lead_scores',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('delta', sa.Integer(), nullable=False),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('scored_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lead_scores_lead_id'), 'lead_scores', ['lead_id'], unique=False)

    # Create follow_up_drafts table
    op.create_table(
        'follow_up_drafts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('score_at_draft', sa.Integer(), nullable=False),
        sa.Column('signal_summary', sa.Text(), nullable=True),
        sa.Column('writer_model', sa.String(), nullable=False),
        sa.Column('reviewer_feedback', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('PENDING_REVIEW', 'APPROVED', 'SENT', 'SKIPPED', 'REVISION_NEEDED', name='followupdraftstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_follow_up_drafts_lead_id'), 'follow_up_drafts', ['lead_id'], unique=False)
    op.create_index(op.f('ix_follow_up_drafts_status'), 'follow_up_drafts', ['status'], unique=False)

    # Create gmail_credentials table
    op.create_table(
        'gmail_credentials',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_email', sa.String(), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=False),
        sa.Column('token_expiry', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_gmail_credentials_user_email'), 'gmail_credentials', ['user_email'], unique=True)

def downgrade() -> None:
    op.drop_index(op.f('ix_gmail_credentials_user_email'), table_name='gmail_credentials')
    op.drop_table('gmail_credentials')
    op.drop_index(op.f('ix_follow_up_drafts_status'), table_name='follow_up_drafts')
    op.drop_index(op.f('ix_follow_up_drafts_lead_id'), table_name='follow_up_drafts')
    op.drop_table('follow_up_drafts')
    op.drop_index(op.f('ix_lead_scores_lead_id'), table_name='lead_scores')
    op.drop_table('lead_scores')
    op.drop_index(op.f('ix_lead_events_event_type'), table_name='lead_events')
    op.drop_index(op.f('ix_lead_events_lead_id'), table_name='lead_events')
    op.drop_table('lead_events')
    op.drop_index(op.f('ix_leads_status'), table_name='leads')
    op.drop_index(op.f('ix_leads_email'), table_name='leads')
    op.drop_table('leads')
    
    # Drop enums
    sa.Enum(name='leadstatus').drop(op.get_bind())
    sa.Enum(name='leadeventtype').drop(op.get_bind())
    sa.Enum(name='followupdraftstatus').drop(op.get_bind())
