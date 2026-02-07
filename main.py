from fastapi import FastAPI
from datetime import datetime, timezone, timedelta
from app.database import SupabaseContextManager
from app.services import TrendService

app = FastAPI(title="Prosper Content Scout")
db = SupabaseContextManager()
trend_service = TrendService()

@app.get("/feed")
async def get_raw_trend_feed():
    # 1. Check for cached trends
    trends = db.fetch_top_trends(limit=10)
    
    should_sync = False
    if not trends:
        should_sync = True
    else:
        # Check if data is > 6 hours old
        last_sync = datetime.fromisoformat(trends[0]['created_at'].replace('Z', '+00:00'))
        if datetime.now(timezone.utc) - last_sync > timedelta(hours=6):
            should_sync = True

    if should_sync:
        print("🔄 Syncing fresh data...")
        raw_items = trend_service.get_raw_feeds()
        cleaned = trend_service.clean_trends(raw_items)
        db.push_new_trends(cleaned)
        trends = db.fetch_top_trends(limit=10)

    # Return raw trends for the iPhone to process locally
    return trends