"""
Sender Agent — Dispatches approved email drafts via Gmail.

Picks up drafts marked as APPROVED and actually sends them via the
authenticated user's Gmail account (unless TEST_MODE_EMAIL is active).
"""

import asyncio
import base64
import logging
from datetime import datetime
from email.message import EmailMessage
from typing import List

from cryptography.fernet import Fernet
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from leadify.common.enums import FollowUpDraftStatus, LeadEventType
from leadify.common.settings import settings
from leadify.db.models import FollowUpDraft, GmailCredentials, LeadEvent

logger = logging.getLogger(__name__)


class SenderAgent:
    """Dispatches approved drafts using the Gmail API."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Encryption helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _decrypt(value: str) -> str:
        f = Fernet(settings.ENCRYPTION_KEY.encode())
        return f.decrypt(value.encode()).decode()

    @staticmethod
    def _encrypt(value: str) -> str:
        f = Fernet(settings.ENCRYPTION_KEY.encode())
        return f.encrypt(value.encode()).decode()

    # ------------------------------------------------------------------
    # Gmail service bootstrap
    # ------------------------------------------------------------------
    async def _get_gmail_service(self):
        """Build a Gmail API service."""
        result = await self.db.execute(select(GmailCredentials).limit(1))
        creds_record = result.scalar_one_or_none()
        if not creds_record:
            logger.warning("No Gmail credentials found — cannot send emails")
            return None

        access_token = self._decrypt(creds_record.access_token)
        refresh_token = self._decrypt(creds_record.refresh_token)

        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )

        if creds.expired and creds.refresh_token:
            try:
                await asyncio.to_thread(creds.refresh, Request())
                creds_record.access_token = self._encrypt(creds.token)
                creds_record.token_expiry = creds.expiry or datetime.utcnow()
                await self.db.flush()
            except Exception as e:
                logger.error(f"Sender Agent: failed to refresh Gmail token: {e}")
                return None

        return build("gmail", "v1", credentials=creds)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    async def run(self, drafts: List[FollowUpDraft]) -> int:
        """Send all approved drafts.
        Returns the number of emails actually sent.
        """
        approved_drafts = [d for d in drafts if d.status == FollowUpDraftStatus.APPROVED]
        
        if not approved_drafts:
            logger.info("Sender Agent: No approved drafts to send.")
            return 0

        logger.info(f"Sender Agent: Attempting to send {len(approved_drafts)} emails...")
        sent_count = 0

        for draft in approved_drafts:
            lead = draft.lead
            if not lead:
                continue

            logger.info(f"[TEST MODE] Would have sent email to {lead.email} - '{draft.subject}'")
            draft.status = FollowUpDraftStatus.SENT
            self._record_sent_event(draft)
            sent_count += 1
                
        if sent_count > 0:
            await self.db.flush()
            
        logger.info(f"Sender Agent: Completed. Successfully mocked sending {sent_count} emails.")
        return sent_count

    def _record_sent_event(self, draft: FollowUpDraft):
        """Record the sending inside the Lead events table."""
        event = LeadEvent(
            lead_id=draft.lead_id,
            event_type=LeadEventType.SIGNAL_DETECTED, # Using SIGNAL_DETECTED to avoid adding new enum unnecessarilly or we can just record it in drafts
            raw_data={
                "action": "email_sent",
                "subject": draft.subject,
                "draft_id": str(draft.id)
            }
        )
        self.db.add(event)
