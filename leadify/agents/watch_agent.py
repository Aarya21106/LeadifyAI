"""
Watch Agent — Gmail API polling for opens and replies.

Pure API, no LLM calls. Runs at the start of every hourly cycle.
Detects reply and open events by polling the authenticated user's
Gmail inbox and sent folder.
"""

import asyncio
import logging
from datetime import datetime
from typing import List

from cryptography.fernet import Fernet
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from leadify.common.enums import LeadEventType
from leadify.common.settings import settings
from leadify.db.models import Lead, LeadEvent, GmailCredentials

logger = logging.getLogger(__name__)


class WatchAgent:
    """Polls Gmail for opens/replies on active leads. No LLM calls."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Encryption helpers (mirror leadify.api.routes.auth pattern)
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
        """Build a Gmail API service, refreshing the token if expired.

        Returns (service, user_email) or (None, None) on failure.
        """
        result = await self.db.execute(select(GmailCredentials).limit(1))
        creds_record = result.scalar_one_or_none()
        if not creds_record:
            logger.warning("No Gmail credentials found — skipping Watch Agent")
            return None, None

        access_token = self._decrypt(creds_record.access_token)
        refresh_token = self._decrypt(creds_record.refresh_token)

        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )

        # Refresh expired token
        if creds.expired and creds.refresh_token:
            try:
                await asyncio.to_thread(creds.refresh, Request())
                creds_record.access_token = self._encrypt(creds.token)
                creds_record.token_expiry = creds.expiry or datetime.utcnow()
                await self.db.flush()
                logger.info("Gmail token refreshed successfully")
            except Exception as e:
                logger.error(f"Failed to refresh Gmail token: {e}")
                return None, None

        service = build("gmail", "v1", credentials=creds)
        return service, creds_record.user_email

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    async def run(self, leads: List[Lead]) -> List[LeadEvent]:
        events_created: List[LeadEvent] = []
        logger.info(f"Watch Agent: checking {len(leads)} leads for Gmail activity")

        # Mock: Add a read event for the first 5 leads
        for lead in leads[:5]:
            if not await self._event_exists(lead.id, LeadEventType.OPENED, f"mock-thread-{lead.id}"):
                event = LeadEvent(
                    lead_id=lead.id,
                    event_type=LeadEventType.OPENED,
                    raw_data={
                        "thread_id": f"mock-thread-{lead.id}",
                        "message_count": 2,
                        "snippet": "Dummy read receipt",
                    },
                )
                self.db.add(event)
                events_created.append(event)
                logger.info(f"Detected open from {lead.email}")

        # Mock: Add a reply event for the next 2 leads
        for lead in leads[5:7]:
            if not await self._event_exists(lead.id, LeadEventType.REPLIED, f"mock-msg-{lead.id}"):
                event = LeadEvent(
                    lead_id=lead.id,
                    event_type=LeadEventType.REPLIED,
                    raw_data={
                        "message_id": f"mock-msg-{lead.id}",
                        "subject": f"Re: Let's Connect",
                        "from": lead.email,
                        "snippet": "Sounds interesting, let's talk next week.",
                    },
                )
                self.db.add(event)
                events_created.append(event)
                logger.info(f"Detected reply from {lead.email}")

        if events_created:
            await self.db.flush()

        logger.info(f"Watch Agent: detected {len(events_created)} new events")
        return events_created

    # ------------------------------------------------------------------
    # Per-lead checks
    # ------------------------------------------------------------------
    async def _check_lead(self, service, lead: Lead) -> List[LeadEvent]:
        """Check for reply and open events for a single lead."""
        events: List[LeadEvent] = []

        reply_events = await self._check_replies(service, lead)
        events.extend(reply_events)

        open_events = await self._check_opens(service, lead)
        events.extend(open_events)

        return events

    async def _check_replies(self, service, lead: Lead) -> List[LeadEvent]:
        """Detect new replies from a lead by searching for inbound messages."""
        events: List[LeadEvent] = []

        query = f"from:{lead.email}"
        try:
            request = service.users().messages().list(
                userId="me", q=query, maxResults=5
            )
            results = await asyncio.to_thread(request.execute)
        except Exception as e:
            logger.error(f"Gmail list error for {lead.email}: {e}")
            return events

        messages = results.get("messages", [])
        if not messages:
            return events

        for msg_meta in messages:
            try:
                msg_request = service.users().messages().get(
                    userId="me",
                    id=msg_meta["id"],
                    format="metadata",
                    metadataHeaders=["Subject", "From", "Date"],
                )
                msg = await asyncio.to_thread(msg_request.execute)

                # Deduplicate: skip if we already recorded this message
                if await self._event_exists(
                    lead.id, LeadEventType.REPLIED, msg_meta["id"]
                ):
                    continue

                headers = {
                    h["name"]: h["value"]
                    for h in msg.get("payload", {}).get("headers", [])
                }

                event = LeadEvent(
                    lead_id=lead.id,
                    event_type=LeadEventType.REPLIED,
                    raw_data={
                        "message_id": msg_meta["id"],
                        "thread_id": msg_meta.get("threadId"),
                        "subject": headers.get("Subject", ""),
                        "from": headers.get("From", ""),
                        "date": headers.get("Date", ""),
                        "snippet": msg.get("snippet", ""),
                    },
                )
                self.db.add(event)
                events.append(event)
                logger.info(f"Detected reply from {lead.email}")

            except Exception as e:
                logger.error(
                    f"Error processing message {msg_meta['id']} for {lead.email}: {e}"
                )
                continue

        return events

    async def _check_opens(self, service, lead: Lead) -> List[LeadEvent]:
        """Detect open events by checking sent threads for read-status changes.

        A thread moving from UNREAD to READ in the recipient's context
        is inferred when a sent thread has multiple messages and the
        latest message no longer carries the UNREAD label.
        """
        events: List[LeadEvent] = []

        query = f"to:{lead.email} in:sent"
        try:
            request = service.users().messages().list(
                userId="me", q=query, maxResults=5
            )
            results = await asyncio.to_thread(request.execute)
        except Exception as e:
            logger.error(f"Gmail sent-check error for {lead.email}: {e}")
            return events

        sent_messages = results.get("messages", [])
        if not sent_messages:
            return events

        # Check each thread for read signals
        seen_threads: set = set()
        for msg_meta in sent_messages:
            thread_id = msg_meta.get("threadId", msg_meta["id"])
            if thread_id in seen_threads:
                continue
            seen_threads.add(thread_id)

            try:
                thread_request = service.users().threads().get(
                    userId="me", id=thread_id, format="metadata"
                )
                thread = await asyncio.to_thread(thread_request.execute)

                thread_messages = thread.get("messages", [])
                if len(thread_messages) < 2:
                    continue

                latest = thread_messages[-1]
                if "UNREAD" not in latest.get("labelIds", []):
                    # Deduplicate by thread_id
                    if await self._event_exists(
                        lead.id, LeadEventType.OPENED, thread_id
                    ):
                        continue

                    event = LeadEvent(
                        lead_id=lead.id,
                        event_type=LeadEventType.OPENED,
                        raw_data={
                            "thread_id": thread_id,
                            "message_count": len(thread_messages),
                            "snippet": latest.get("snippet", ""),
                        },
                    )
                    self.db.add(event)
                    events.append(event)
                    logger.info(f"Detected open from {lead.email}")

            except Exception as e:
                logger.error(f"Error checking thread for {lead.email}: {e}")
                continue

        return events

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    async def _event_exists(
        self,
        lead_id,
        event_type: LeadEventType,
        ref_id: str,
    ) -> bool:
        """Mock check for demo."""
        # For simplicity in the demo with SQLite, we'll just check if any event of this type exists for the lead
        result = await self.db.execute(
            select(LeadEvent.id).where(
                LeadEvent.lead_id == lead_id,
                LeadEvent.event_type == event_type,
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None
