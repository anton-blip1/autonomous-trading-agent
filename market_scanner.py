"""
Market Scanner - Fetch Kalshi + Polymarket prediction markets
Shared across all users (same data for everyone)
Uses synchronous code to run in background thread (no async issues)
"""

import time
import requests
from typing import List, Dict
from datetime import datetime

from config import Config


class MarketScanner:
    """Scan prediction markets from Kalshi + Polymarket."""
    
    def __init__(self):
        self.kalshi_url = Config.KALSHI_BASE_URL
        self.polymarket_url = Config.POLYMARKET_BASE_URL
        self.scan_interval = Config.MARKET_SCAN_INTERVAL_SECONDS
        self.markets = []
    
    def fetch_kalshi_markets(self) -> List[Dict]:
        """
        Fetch weather + event markets from Kalshi.
        
        Kalshi focuses on:
        - Weather (rain, snow, temperature)
        - Sports
        - Economics
        
        Returns:
            List of markets
        """
        
        try:
            # Get active markets
            url = f"{self.kalshi_url}/markets"
            params = {
                'limit': 50,
                'status': 'active'
            }
            
            resp = requests.get(url, params=params, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                markets = data.get('markets', [])
                
                print(f"[KALSHI] Fetched {len(markets)} markets")
                
                # Parse into standard format (NO filtering—fetch all)
                formatted = []
                for market in markets:
                    formatted.append({
                        'id': market.get('market_id'),
                        'market_id': market.get('market_id'),
                        'title': market.get('title', ''),
                        'category': self._infer_category(market.get('title', '')),
                        'platform': 'kalshi',
                        'current_price': market.get('yes_price', 0.5),  # 0-1 scale
                        'description': market.get('description', ''),
                        'volume': market.get('volume_24h', 0),
                        'expires_at': market.get('expiration_time'),
                    })
                
                return formatted
            else:
                print(f"[KALSHI] Error: {resp.status_code}")
                return []
        
        except Exception as e:
            print(f"[KALSHI] Exception: {e}")
            return []
    
    def fetch_polymarket_markets(self) -> List[Dict]:
        """
        Fetch event prediction markets from Polymarket.
        
        Polymarket focuses on:
        - Politics (elections, bills)
        - Crypto (price targets, events)
        - Sports
        - General (misc. events)
        
        Returns:
            List of markets
        """
        
        try:
            # Get active markets
            url = f"{self.polymarket_url}/markets"
            params = {
                'limit': 50,
                'status': 'active'
            }
            
            resp = requests.get(url, params=params, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                markets = data if isinstance(data, list) else data.get('markets', [])
                
                print(f"[POLYMARKET] Fetched {len(markets)} markets")
                
                # Parse into standard format (NO filtering—fetch all)
                formatted = []
                for market in markets:
                    formatted.append({
                        'id': market.get('market_id', market.get('id')),
                        'market_id': market.get('market_id', market.get('id')),
                        'title': market.get('title', ''),
                        'category': self._infer_category(market.get('title', '')),
                        'platform': 'polymarket',
                        'current_price': market.get('bid', 0.5),  # 0-1 scale
                        'description': market.get('description', ''),
                        'volume': market.get('volume_24h', 0),
                        'expires_at': market.get('expiration_date'),
                    })
                
                return formatted
            else:
                print(f"[POLYMARKET] Error: {resp.status_code}")
                return []
        
        except Exception as e:
            print(f"[POLYMARKET] Exception: {e}")
            return []
    
    def scan_all_markets(self) -> List[Dict]:
        """
        Fetch all markets from all platforms.
        
        Returns:
            Combined list of markets
        """
        
        # Fetch sequentially (no async in thread)
        kalshi_markets = self.fetch_kalshi_markets()
        poly_markets = self.fetch_polymarket_markets()
        
        all_markets = kalshi_markets + poly_markets
        
        print(f"[SCANNER] Total markets: {len(all_markets)}")
        
        self.markets = all_markets
        return all_markets
    
    def get_market_page(self, page: int = 1, category: str = None) -> List[Dict]:
        """
        Get markets with pagination.
        
        Args:
            page: Page number (1-indexed)
            category: Optional category filter (weather, politics, crypto, event, etc)
        
        Returns:
            List of markets for page
        """
        
        # Filter by category if specified
        if category:
            filtered_markets = [m for m in self.markets if m['category'] == category]
        else:
            filtered_markets = self.markets
        
        # Pagination
        page_size = 5
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        return filtered_markets[start_idx:end_idx]
    
    def get_total_pages(self, category: str = None) -> int:
        """Get total pages for category."""
        
        if category:
            filtered = [m for m in self.markets if m['category'] == category]
        else:
            filtered = self.markets
        
        page_size = 5
        return (len(filtered) + page_size - 1) // page_size
    
    def get_market_by_id(self, market_id: str) -> Dict:
        """Get specific market by ID."""
        
        for market in self.markets:
            if market['id'] == market_id or market['market_id'] == market_id:
                return market
        
        return None
    
    def _infer_category(self, title: str) -> str:
        """Infer market category from title (for metadata only, not filtering)."""
        
        title_lower = title.lower()
        
        # Weather indicators
        if any(w in title_lower for w in ['weather', 'snow', 'rain', 'temperature', 'storm', 'wind', 'frost']):
            return 'weather'
        
        # Politics indicators
        if any(p in title_lower for p in ['election', 'trump', 'biden', 'vote', 'senate', 'congress', 'bill']):
            return 'politics'
        
        # Crypto indicators
        if any(c in title_lower for c in ['bitcoin', 'ethereum', 'btc', 'eth', 'crypto', 'defi', 'nft']):
            return 'crypto'
        
        # Sports indicators
        if any(s in title_lower for s in ['nfl', 'nba', 'world cup', 'super bowl', 'world series', 'championship']):
            return 'sports'
        
        # Economics indicators
        if any(e in title_lower for e in ['inflation', 'unemployment', 'gdp', 'fed', 'interest rate']):
            return 'economics'
        
        # Default to 'event'
        return 'event'
    
    def start_continuous_scan(self):
        """
        Start background task to continuously scan markets.
        Updates database every N seconds.
        Runs in a thread (synchronous, no async).
        """
        
        while True:
            try:
                print(f"[SCANNER] Scanning markets...")
                self.scan_all_markets()
                print(f"[SCANNER] Next scan in {self.scan_interval}s")
                time.sleep(self.scan_interval)
            except Exception as e:
                print(f"[SCANNER] Error: {e}")
                time.sleep(self.scan_interval)


# Global instance
market_scanner = MarketScanner()
scanner = market_scanner  # Alias for compatibility
