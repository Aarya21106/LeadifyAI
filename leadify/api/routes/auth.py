import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from cryptography.fernet import Fernet

from leadify.api.dependencies import get_db
from leadify.common.settings import settings
from leadify.common.schemas import GmailStatus
from leadify.db.models import GmailCredentials

# Allow HTTP for local development (OAuth requires HTTPS by default)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

router = APIRouter()

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


def _get_flow() -> Flow:
    """Build a Google OAuth flow from settings."""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )
    return flow


def _encrypt(value: str) -> str:
    """Encrypt a string using the configured Fernet key."""
    f = Fernet(settings.ENCRYPTION_KEY.encode())
    return f.encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    """Decrypt a Fernet-encrypted string."""
    f = Fernet(settings.ENCRYPTION_KEY.encode())
    return f.decrypt(value.encode()).decode()


@router.get("/gmail")
async def gmail_auth():
    """Redirect user to Google OAuth consent screen."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured",
        )

    flow = _get_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return RedirectResponse(url=auth_url)


@router.get("/gmail/callback")
async def gmail_callback(code: str, db: AsyncSession = Depends(get_db)):
    """Handle OAuth callback, exchange code for tokens, store encrypted."""
    flow = _get_flow()
    flow.fetch_token(code=code)
    credentials = flow.credentials

    # Get user email from id_token or userinfo
    user_email = "unknown"
    if hasattr(credentials, "id_token") and credentials.id_token:
        user_email = credentials.id_token.get("email", "unknown")

    # Upsert gmail credentials
    result = await db.execute(
        select(GmailCredentials).where(GmailCredentials.user_email == user_email)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.access_token = _encrypt(credentials.token)
        existing.refresh_token = _encrypt(credentials.refresh_token or "")
        existing.token_expiry = credentials.expiry or datetime.utcnow()
    else:
        gmail_creds = GmailCredentials(
            user_email=user_email,
            access_token=_encrypt(credentials.token),
            refresh_token=_encrypt(credentials.refresh_token or ""),
            token_expiry=credentials.expiry or datetime.utcnow(),
        )
        db.add(gmail_creds)

    await db.flush()

    # Redirect back to frontend
    return RedirectResponse(url=f"{settings.FRONTEND_URL}?gmail=connected")


@router.get("/gmail/status", response_model=GmailStatus)
async def gmail_status(db: AsyncSession = Depends(get_db)):
    """Check if any Gmail account is connected."""
    result = await db.execute(select(GmailCredentials).limit(1))
    creds = result.scalar_one_or_none()

    if creds:
        return GmailStatus(connected=True, email=creds.user_email)
    return GmailStatus(connected=False, email=None)
