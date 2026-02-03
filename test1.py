import os
from dotenv import load_dotenv
from app.services import TrendService

load_dotenv()
token = os.getenv("APIFY_API_KEY")

print(f"Environment Check: Token found? {bool(token)}")

if token:
    try:
        service = TrendService(api_token=token)
        print("Starting Phase 1 & 2: Generative Sync...")
        result = service.sync_to_dummy(query="SaaS and AI startup trends")
        
        if result:
            print("Success! Check your 'dummy_trending_topics' table in Supabase.")
    except Exception as e:
        print(f"Error: {e}")
else:
    print("Token missing. Run fix_env.py first.")