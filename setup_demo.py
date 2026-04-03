import asyncio
from leadify.db.session import engine, async_session_maker
from leadify.db.models import Base, GmailCredentials, Lead
from leadify.common.enums import LeadStatus
from leadify.common.settings import settings
from cryptography.fernet import Fernet
import datetime

async def setup_demo():
    print("🚀 Initializing Leadify Dummy Demo...")
    
    # 1. Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    # 2. Add dummy Gmail credentials
    f = Fernet(settings.ENCRYPTION_KEY.encode())
    access_token = f.encrypt(b"dummy-access-token").decode()
    refresh_token = f.encrypt(b"dummy-refresh-token").decode()
    
    async with async_session_maker() as db:
        dummy_creds = GmailCredentials(
            user_email="demo-user@leadify.ai",
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=datetime.datetime.utcnow() + datetime.timedelta(days=365)
        )
        db.add(dummy_creds)
        
        # 3. Add a few starting leads if we want, 
        # though FinderAgent will do this automatically on first run.
        print("✅ Tables created.")
        print("✅ Dummy Gmail connected: demo-user@leadify.ai")
        
        await db.commit()

    print("\n🎉 Setup Complete!")
    print("Run the app with: uvicorn leadify.api.main:app --reload")
    print("Then click 'Run Agent Cycle' in the dashboard to see the magic happen.")

if __name__ == "__main__":
    asyncio.run(setup_demo())
