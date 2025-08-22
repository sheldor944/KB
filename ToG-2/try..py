import requests
import json
import time
from typing import Dict, List, Optional
import urllib.parse

class WikidataAPIClient:
    def __init__(self):
        self.base_url = "https://www.wikidata.org/w/api.php"
        self.sparql_url = "https://query.wikidata.org/sparql"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ToG-WikidataClient/1.0 (https://example.com/contact)'
        })
    
    def _make_request(self, url: str, params: dict, retries: int = 3) -> Optional[dict]:
        """Make API request with retries and rate limiting"""
        for attempt in range(retries):
            try:
                time.sleep(0.1)  # Rate limiting
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                if attempt == retries - 1:
                    print(f"API request failed after {retries} attempts: {e}")
                    return None
                time.sleep(1)
        return None

client = WikidataAPIClient()
params = {
            'action': 'wbsearchentities',
            'search': '1994 winter olympics',
            'language': 'en',
            'format': 'json',
            'type': 'property',
            'limit': 10
        }

result = client._make_request(client.base_url, params)
print(result)
