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
        self.apify_client = ApifyClient(api_token)
        self.db = SupabaseContextManager()
        self.ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def sync_all_industries(self):
        industries = [
            "Technology & Software",
            "Marketing, Branding & Growth",
            "Finance, Strategy & Operations",
            "Design, Product & UX",
            "Education, Coaching & Knowledge",
            "Media, Content & Community"
        ]
        
        for industry in industries:
            print(f"Processing Industry: {industry}")

            print(f"Clearing old entries for {industry}...")
            self.db.supabase.table("trending_topics").delete().eq("category", industry).execute()
            
            run_input = {
                "search": industry,
                "platforms": ["twitter", "instagram"],
                "maxTrends": 10,
                "region": "IN"
            }
            
            try:
                run = self.apify_client.actor("manju4k/social-media-trend-scraper-6-in-1-ai-analysis").call(run_input=run_input)
                raw_items = list(self.apify_client.dataset(run["defaultDatasetId"]).iterate_items())
                
                if not raw_items:
                    print(f"No items found for {industry}")
                    continue
                
                cleaned_trends = self._clean_data_with_gemini(raw_items, industry)
                
                if cleaned_trends:
                    batch_to_insert = []
                    for trend in cleaned_trends:
                        trend["category"] = industry 
                        batch_to_insert.append(trend)
                    
                    print(f"Inserting {len(batch_to_insert)} rows for category: '{batch_to_insert[0]['category']}'")
                    
                    self.db.supabase.table("trending_topics").insert(batch_to_insert).execute()
                    print(f"Successfully updated {industry}")
                    
            except Exception as e:
                print(f"Error syncing {industry}: {str(e)}")

    def _clean_data_with_gemini(self, raw_data: list, industry: str):
        """Refines raw data into structured cards for the iOS UI."""
        response_schema = {
            "type": "object",
            "properties": {
                "trends": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "topic_name": {"type": "string"},
                            "short_description": {"type": "string"},
                            "trending_context": {
                                "type": "string", 
                                "description": "Elaborate 2-3 sentence catalyst for the local AI."
                            },
                            "platform_icon": {
                                "type": "string", 
                                "enum": ["icon-x", "icon-instagram", "icon-linkedin"]
                            },
                            "hashtags": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["topic_name", "short_description", "platform_icon", "trending_context"]
                    }
                }
            }
        }

        prompt = f"""
        Extract 5 trends for entrepreneurs in {industry} from: {json.dumps(raw_data[:10])}.
        
        RULES:
        1.  For 'source', identify which platform the trend originated from (X, Instagram, or LinkedIn).
        2. 'topic_name': Under 30 chars, catchy and short.
        3. 'trending_context': MUST be elaborate. Explain the 'Why' and the 'How' for a professional brand.
        4. 'platform_icon': Must be 'icon-instagram', 'icon-x', or 'icon-linkedin'.
        5. 'short_description': Under 50 chars for mobile cards.
        """

        response = self.ai_client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema
            )
        )
        return json.loads(response.text).get("trends", [])