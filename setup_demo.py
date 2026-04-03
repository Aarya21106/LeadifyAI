import asyncio
from leadify.db.session import engine, async_session_maker
from leadify.db.models import Base, GmailCredentials
from leadify.common.settings import settings
from cryptography.fernet import Fernet
import datetime

async def setup_demo():
    print("🚀 Initializing Leadify Demo Environment...")
    
    # 1. Drop and recreate all tables (fresh start)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    # 2. Add dummy Gmail credentials so the app appears "connected"
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
        
        print("✅ Database tables created (fresh)")
        print("✅ Gmail credentials set: demo-user@leadify.ai")
        
        await db.commit()

    print("\n🎉 Setup Complete!")
    print("─" * 50)
    print("Run the app with:")
    print("  uvicorn leadify.api.main:app --reload")
    print("")
    print("Then click 'Run Agents Now' to see:")
    print("  • 50 realistic B2B leads generated")
    print("  • Email opens & replies detected")
    print("  • Company signals discovered")
    print("  • AI scores calculated per lead")
    print("  • Follow-up drafts created & reviewed")
    print("─" * 50)

if __name__ == "__main__":
    asyncio.run(setup_demo())
