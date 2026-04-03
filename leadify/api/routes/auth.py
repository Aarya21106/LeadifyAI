import os
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Response
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from cryptography.fernet import Fernet

from leadify.api.dependencies import get_db
from leadify.common.settings import settings
from leadify.common.schemas import GmailStatus
from leadify.db.models import GmailCredentials

# SETUP REQUIRED IN GOOGLE CLOUD CONSOLE:
# 1. Go to APIs & Services > Credentials
# 2. Create OAuth 2.0 Client ID (Web Application type)
# 3. Add Authorized Redirect URI: http://localhost:8000/auth/gmail/callback (dev)
#    and https://yourapp.railway.app/auth/gmail/callback (prod)
# 4. Enable Gmail API at APIs & Services > Library
# 5. If app is in testing mode, add your email as a Test User under OAuth Consent Screen

# Allow HTTP for local development (OAuth requires HTTPS by default)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

router = APIRouter()

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
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
    if not value: return ""
    f = Fernet(settings.ENCRYPTION_KEY.encode())
    return f.encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    """Decrypt a Fernet-encrypted string."""
    if not value: return ""
    f = Fernet(settings.ENCRYPTION_KEY.encode())
    return f.decrypt(value.encode()).decode()


@router.get("/gmail")
async def gmail_auth(response: Response):
    """Return JSON with Google OAuth authorization URL and set CSRF state in cookie."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured",
        )

    state = secrets.token_urlsafe(32)
    flow = _get_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state
    )

    # Set CSRF check state token in browser cookie
    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        samesite="lax",
        max_age=600  # 10 minute expiry
    )
    return {"auth_url": auth_url}


@router.get("/gmail/callback")
async def gmail_callback(
    request: Request,
    response: Response,
    code: str = Query(...),
    state: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Handle OAuth callback, validate state, exchange code, fetch email, store encrypted tokens."""
    cookie_state = request.cookies.get("oauth_state")
    if not cookie_state or cookie_state != state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid state token (CSRF validation failed)."
        )

    # State validation succeeded so clear the cookie
    response.delete_cookie("oauth_state")

    flow = _get_flow()
    # The flow requires state if we initialized authorization_url with it, but setting code directly handles the token exchange
    try:
        flow.fetch_token(code=code)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Token exchange failed: {e}")
        
    credentials = flow.credentials

    # Call Gmail API userinfo to get authenticated user's email address
    try:
        service = build('gmail', 'v1', credentials=credentials)
        profile = service.users().getProfile(userId='me').execute()
        user_email = profile.get('emailAddress', 'unknown')
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch user email: {e}")

    # Upsert gmail credentials into database
    result = await db.execute(
        select(GmailCredentials).where(GmailCredentials.user_email == user_email)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.access_token = _encrypt(credentials.token)
        existing.refresh_token = _encrypt(credentials.refresh_token or existing.refresh_token or "") # Fallback to existing or ""
        existing.token_expiry = credentials.expiry or datetime.utcnow()
    else:
        gmail_creds = GmailCredentials(
            user_email=user_email,
            access_token=_encrypt(credentials.token),
            refresh_token=_encrypt(credentials.refresh_token or ""),
            token_expiry=credentials.expiry or datetime.utcnow(),
        )
        db.add(gmail_creds)

    await db.commit()

    # Redirect securely back to frontend
    redirect_url = f"{settings.FRONTEND_URL}/settings?gmail=connected"
    return RedirectResponse(url=redirect_url)


@router.get("/gmail/status", response_model=GmailStatus)
async def gmail_status(db: AsyncSession = Depends(get_db)):
    """Check if any Gmail account is connected (returns the first found)."""
    result = await db.execute(select(GmailCredentials).limit(1))
    creds = result.scalar_one_or_none()

    if creds:
        return GmailStatus(connected=True, email=creds.user_email)
    return GmailStatus(connected=False, email=None)


@router.delete("/gmail/disconnect")
async def gmail_disconnect(db: AsyncSession = Depends(get_db)):
    """Delete the configured Gmail credentials from the database."""
    result = await db.execute(select(GmailCredentials).limit(1))
    creds = result.scalar_one_or_none()

    if creds:
        await db.delete(creds)
        await db.commit()
        
    return {"success": True}
