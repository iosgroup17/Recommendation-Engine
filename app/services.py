# app/services.py
import os
import json
from apify_client import ApifyClient
from app.database import SupabaseContextManager
from google import genai
from google.genai import types

class TrendService:
    def __init__(self, api_token: str):
        if not api_token:
            raise ValueError("No Apify Token provided.")
        self.client = ApifyClient(api_token)
        self.db = SupabaseContextManager()
        self.ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def sync_to_dummy(self, query: str = "AI SaaS trends 2026"):
        run_input = {
            "platforms": [
                "instagram",
                "youtube",
                "reddit",
                "twitter",
            ],
            "region": "IN",
            "timeRange": "4h",
            "maxTrends": 25,
            "includeMetrics": False,
            "enableComparison": False,
            "comparisonType": "comprehensive",
        }
        print(f"📡 Scraping raw data for: {query}...")
        run = self.client.actor("manju4k/social-media-trend-scraper-6-in-1-ai-analysis").call(run_input=run_input)
        
        raw_items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
        
        if not raw_items:
            print("Apify returned no items.")
            return None
        
        print(f"Gemini is cleaning {len(raw_items)} raw items...")
        cleaned_trends = self._clean_data_with_gemini(raw_items)

        if cleaned_trends:
            print(f"Inserting {len(cleaned_trends)} structured trends into Supabase...")
            return self.db.supabase.table("dummy_trending_topics").insert(cleaned_trends).execute()
        
        return None
    
    # app/services.py (Updated for UI-Ready Data)

    def _clean_data_with_gemini(self, raw_data: list):
        # Strict schema for App Store UI consistency
        response_schema = {
            "type": "object",
            "properties": {
                "trends": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "topic_name": {"type": "string"},
                            "short_description": {"type": "string", "description": "A punchy 1-sentence summary."},
                            "platform_icon": {
                                "type": "string", 
                                "enum": ["icon-x", "icon-instagram", "icon-linkedin"], # Strict UI mapping
                                "description": "Choose the most relevant platform for this trend."
                            },
                            "hashtags": {
                                "type": "array", 
                                "items": {"type": "string"},
                                "minItems": 2, 
                                "maxItems": 2 # Enforces exactly two hashtags
                            },
                            "sector": {"type": "string"}
                        },
                        "required": ["topic_name", "short_description", "platform_icon", "hashtags"]
                    }
                }
            }
        }

        prompt = f"""
        Analyze these raw social media trends. 
        1. Extract the top 5 high-signal topics for personal branding.
        2. Map them to 'icon-x', 'icon-instagram', or 'icon-linkedin'.
        3. Generate exactly 2 relevant hashtags for each.
        4. Keep descriptions under 50 characters for mobile cards, keep words short they should fit in two lines in a short card.
        5. Keep the post title also about 30 characters.
        
        Raw Data: {json.dumps(raw_data[:12])}
        """

        response = self.ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema
            )
        )
        
        structured_output = json.loads(response.text)
        return structured_output.get("trends", [])