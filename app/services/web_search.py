import requests
import json
from typing import Dict, List, Optional
import logging
from bs4 import BeautifulSoup
import re
from urllib.parse import quote

logger = logging.getLogger(__name__)

class WebSearchService:
    """Service to add web search capability for real-time information"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def should_search_web(self, query: str) -> bool:
        """Determine if query needs real-time web search"""
        real_time_keywords = [
            # Time-sensitive words
            'current', 'today', 'now', 'latest', 'recent', 'this year', '2024', '2025',
            # Price/market related
            'price', 'cost', 'rate', 'stock', 'market', 'trading', 'value',
            # News/events
            'news', 'breaking', 'update', 'announcement', 'happened',
            # Weather
            'weather', 'temperature', 'forecast', 'climate',
            # Sports/results
            'score', 'result', 'winner', 'match', 'game',
            # Technology
            'release date', 'launched', 'available',
            # General current info
            'who is the current', 'what happened to', 'when did', 'how much does'
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in real_time_keywords)
    
    def search_duckduckgo_instant(self, query: str) -> Optional[str]:
        """Get instant answer from DuckDuckGo"""
        try:
            url = "https://api.duckduckgo.com/"
            params = {
                'q': query,
                'format': 'json',
                'no_html': '1',
                'skip_disambig': '1'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            # Try instant answer first
            if data.get('Answer'):
                return data['Answer']
            
            if data.get('AbstractText'):
                return data['AbstractText']
            
            # Try related topics
            if data.get('RelatedTopics'):
                for topic in data['RelatedTopics'][:2]:
                    if isinstance(topic, dict) and 'Text' in topic:
                        return topic['Text']
            
            return None
            
        except Exception as e:
            logger.error(f"DuckDuckGo instant search failed: {e}")
            return None
    
    def scrape_search_results(self, query: str) -> List[str]:
        """Scrape search results for more comprehensive answers"""
        try:
            # Use DuckDuckGo HTML search (more results)
            search_url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
            
            response = self.session.get(search_url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            results = []
            # Extract snippets from search results
            for result in soup.find_all('div', class_='result__snippet')[:3]:
                snippet = result.get_text().strip()
                if snippet and len(snippet) > 20:
                    results.append(snippet)
            
            return results
            
        except Exception as e:
            logger.error(f"Web scraping failed: {e}")
            return []
    
    def get_financial_data(self, query: str) -> Optional[str]:
        """Get financial/price data for common requests"""
        try:
            query_lower = query.lower()
            
            # Gold price
            if 'gold' in query_lower and any(word in query_lower for word in ['price', 'rate', 'cost']):
                # Using a free API (you might need to register)
                url = "https://api.metals.live/v1/spot/gold"
                response = self.session.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    return f"Current gold price: ${data.get('price', 'N/A')} per ounce (as of {data.get('timestamp', 'now')})"
            
            # Bitcoin/crypto (using coindesk API - free)
            if any(crypto in query_lower for crypto in ['bitcoin', 'btc', 'cryptocurrency']):
                url = "https://api.coindesk.com/v1/bpi/currentprice.json"
                response = self.session.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    price = data['bpi']['USD']['rate']
                    return f"Current Bitcoin price: {price} (source: CoinDesk)"
            
            return None
            
        except Exception as e:
            logger.error(f"Financial data fetch failed: {e}")
            return None
    
    def search_web(self, query: str) -> Optional[str]:
        """Main web search function"""
        try:
            logger.info(f"Performing web search for: {query}")
            
            # Try financial data first
            financial_data = self.get_financial_data(query)
            if financial_data:
                return financial_data
            
            # Try instant answer
            instant_answer = self.search_duckduckgo_instant(query)
            if instant_answer and len(instant_answer) > 10:
                return f"Current information: {instant_answer}"
            
            # Try scraping search results
            search_results = self.scrape_search_results(query)
            if search_results:
                combined_results = " | ".join(search_results[:2])
                return f"Recent web search results: {combined_results[:500]}..."
            
            return None
            
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return None

# Global web search service
web_search_service = WebSearchService()