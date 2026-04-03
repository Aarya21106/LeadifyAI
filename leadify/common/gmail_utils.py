import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from cryptography.fernet import Fernet

from leadify.db.models import GmailCredentials
from leadify.common.settings import settings

logger = logging.getLogger(__name__)

def _decrypt(value: str) -> str:
    """Decrypt a Fernet-encrypted string."""
    if not value: return ""
    f = Fernet(settings.ENCRYPTION_KEY.encode())
    return f.decrypt(value.encode()).decode()

def _encrypt(value: str) -> str:
    """Encrypt a string using the configured Fernet key."""
    if not value: return ""
    f = Fernet(settings.ENCRYPTION_KEY.encode())
    return f.encrypt(value.encode()).decode()

async def get_valid_credentials(db: AsyncSession) -> Credentials | None:
    """
    Fetches stored credentials, refreshes if expired, saves updated tokens.
    Returns a valid google.oauth2.credentials.Credentials object or None if not connected.
    """
    # Query gmail_credentials for the first row
    result = await db.execute(select(GmailCredentials).limit(1))
    creds_row = result.scalar_one_or_none()
    
    if not creds_row:
        return None

    # Decrypt tokens using Fernet
    try:
        access_token = _decrypt(creds_row.access_token)
        refresh_token = _decrypt(creds_row.refresh_token)
    except Exception as e:
        logger.error(f"Failed to decrypt Gmail credentials: {e}")
        return None

    # Build google.oauth2.credentials.Credentials
    credentials = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=[
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.modify"
        ]
    )

    # Check if expired: if credentials.expired and credentials.refresh_token exists
    if credentials.expired and credentials.refresh_token:
        logger.info("Gmail credentials expired, attempting to refresh...")
        try:
            credentials.refresh(Request())
            
            # If refreshed, encrypt and save new access_token + token_expiry back to DB
            creds_row.access_token = _encrypt(credentials.token)
            creds_row.token_expiry = credentials.expiry
            await db.flush()
            
            logger.info("Successfully refreshed and stored new Gmail access token.")
        except Exception as e:
            logger.error(f"Failed to refresh Gmail token. It may be revoked. Error: {e}")
            return None
            
    elif credentials.expired and not credentials.refresh_token:
        logger.warning("Gmail credentials expired and no refresh token is available.")
        return None

    return credentials
