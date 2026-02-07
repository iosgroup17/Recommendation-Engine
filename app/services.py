import os
import json
from apify_client import ApifyClient
from google import genai
from google.genai import types

class TrendService:
    def __init__(self):
        self.apify_client = ApifyClient(os.getenv("APIFY_API_KEY"))
        self.ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def get_raw_feeds(self):
        """Triggers the manju4k 6-in-1 scraper with corrected platform names."""
        run_input = {
            # IMPORTANT: Use "twitter", NOT "x"
            "platforms": ["twitter", "instagram", "reddit", "youtube"], 
            "region": "US",
            "timeRange": "24h",
            "maxTrends": 10,
            "includeMetrics": False # Set to False to keep the data clean for Gemini
        }

        print("📡 Triggering Apify with corrected platform names...")
        # This line was crashing because of the input above
        run = self.apify_client.actor("manju4k/social-media-trend-scraper-6-in-1-ai-analysis").call(run_input=run_input)
    
        dataset = self.apify_client.dataset(run["defaultDatasetId"])
        return list(dataset.iterate_items())

    def clean_trends(self, raw_data: list):
        """Gemini translates raw scrapings into our iOS-ready schema with elaborate context."""
        response_schema = {
            "type": "object",
            "properties": {
                "trends": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string", "enum": ["X", "LinkedIn", "Reddit", "YouTube"]},
                            "topic_name": {"type": "string"},
                            "short_description": {"type": "string"},
                            "trending_context": {
                                "type": "string", 
                                "description": "An elaborate 2-3 sentence explanation of the 'Why' behind the trend, including specific catalysts or debate points."
                            },
                            "platform_icon": {
                                "type": "string", 
                                "enum": ["icon-instagram", "icon-x", "icon-linkedin"] # Corrected platform names
                            },
                            "hashtags": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["source", "topic_name", "trending_context", "platform_icon"]
                    }
                }
            }
        }

        prompt = f"""
        Analyze these raw social media trends for a personal branding app: {json.dumps(raw_data[:10])}.
        
        TASK:
        1. Extract the top 5 highest-signal trends for professional branding.
        2. The 'trending_context' MUST be elaborate: explain the specific catalyst (e.g., a new policy, a viral tweet, or a market shift) and the core tension/debate currently happening.
        3. Ensure 'platform_icon' strictly follows the enum: icon-instagram, icon-x, or icon-linkedin.
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