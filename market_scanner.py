"""
Market Scanner - Fetches and scores markets from Polymarket and Kalshi.
Updates every 5 seconds and returns top opportunities.
"""
import asyncio
import aiohttp
import requests
import json
from datetime import datetime
from typing import List, Dict, Optional
from config import (
    POLYMARKET_API_BASE,
    KALSHI_API_BASE,
    MIN_VOLUME_USD,
    MIN_LIQUIDITY_USD,
    SCAN_INTERVAL_SECONDS,
)
from database import db


class MarketScanner:
    """Scans and scores prediction markets from multiple platforms."""

    def __init__(self):
        self.last_scan = None
        self.market_cache = {}
        self.scores = {}

    async def scan_polymarket(self) -> List[Dict]:
        """Fetch markets from Polymarket API."""
        try:
            url = f"{POLYMARKET_API_BASE}/markets?limit=100"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        markets = []
                        for m in data.get("data", []):
                            market = {
                                "market_id": m.get("id"),
                                "platform": "polymarket",
                                "title": m.get("title"),
                                "description": m.get("description"),
                                "yes_price": float(m.get("yes_price", 0.5)),
                                "no_price": float(m.get("no_price", 0.5)),
                                "volume_usd": float(m.get("volume_24h", 0)),
                                "liquidity_usd": float(
                                    m.get("order_book", {}).get("depth", 0)
                                ),
                                "closes_at": m.get("end_date"),
                                "status": m.get("active") and "open" or "closed",
                                "category": m.get("category"),
                            }
                            if (
                                market["volume_usd"] >= MIN_VOLUME_USD
                                and market["liquidity_usd"] >= MIN_LIQUIDITY_USD
                            ):
                                markets.append(market)
                        return markets
        except Exception as e:
            print(f"[SCANNER] Polymarket fetch error: {e}")
            return []

    async def scan_kalshi(self) -> List[Dict]:
        """Fetch markets from Kalshi API."""
        try:
            url = f"{KALSHI_API_BASE}/markets"
            params = {"status": "active", "limit": 100}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        markets = []
                        for m in data.get("markets", []):
                            market = {
                                "market_id": m.get("id"),
                                "platform": "kalshi",
                                "title": m.get("title"),
                                "description": m.get("description"),
                                "yes_price": float(m.get("yes_price", 0.5)),
                                "no_price": float(m.get("no_price", 0.5)),
                                "volume_usd": float(m.get("volume_24h", 0)),
                                "liquidity_usd": float(m.get("liquidity", 0)),
                                "closes_at": m.get("expiration_date"),
                                "status": m.get("status"),
                                "category": m.get("category"),
                            }
                            if (
                                market["volume_usd"] >= MIN_VOLUME_USD
                                and market["liquidity_usd"] >= MIN_LIQUIDITY_USD
                            ):
                                markets.append(market)
                        return markets
        except Exception as e:
            print(f"[SCANNER] Kalshi fetch error: {e}")
            return []

    def calculate_spread(self, yes_price: float, no_price: float) -> float:
        """Calculate bid-ask spread as percentage."""
        if yes_price == 0 or no_price == 0:
            return 100.0
        return abs(yes_price - no_price) / ((yes_price + no_price) / 2)

    def score_market(
        self, market: Dict, fair_value: float = None
    ) -> Dict:
        """Score a market based on liquidity, volume, and spread."""
        spread = self.calculate_spread(market["yes_price"], market["no_price"])

        # Score components (0-100 each)
        volume_score = min(market["volume_usd"] / 10000, 100)  # 0-100 based on $10k volume
        liquidity_score = min(market["liquidity_usd"] / 1000, 100)  # 0-100 based on $1k depth
        spread_score = max(100 - (spread * 100), 0)  # Lower spread = higher score

        # Weighted average (volume + liquidity + spread)
        overall_score = (volume_score * 0.4 + liquidity_score * 0.4 + spread_score * 0.2)

        market_score = {
            "market_id": market["market_id"],
            "platform": market["platform"],
            "title": market["title"],
            "yes_price": market["yes_price"],
            "no_price": market["no_price"],
            "spread": spread,
            "volume_score": volume_score,
            "liquidity_score": liquidity_score,
            "spread_score": spread_score,
            "overall_score": overall_score,
            "scored_at": datetime.now().isoformat(),
        }

        return market_score

    async def scan_all_markets(self) -> List[Dict]:
        """Scan both Polymarket and Kalshi, score, and return top opportunities."""
        print(f"[SCANNER] Starting market scan at {datetime.now().isoformat()}")

        # Fetch from both platforms in parallel
        poly_markets, kalshi_markets = await asyncio.gather(
            self.scan_polymarket(), self.scan_kalshi()
        )

        all_markets = poly_markets + kalshi_markets
        print(f"[SCANNER] Found {len(all_markets)} qualifying markets")

        # Score and rank markets
        scored = [self.score_market(m) for m in all_markets]
        scored.sort(key=lambda x: x["overall_score"], reverse=True)

        # Store in cache
        for market in all_markets:
            self.market_cache[market["market_id"]] = market
            db.add_market(market)

        self.last_scan = datetime.now()
        return scored[:20]  # Return top 20 opportunities

    def get_market_by_id(self, market_id: str) -> Optional[Dict]:
        """Fetch a specific market from cache or API."""
        if market_id in self.market_cache:
            return self.market_cache[market_id]

        # TODO: Fetch from API if not in cache
        return None

    async def run_continuous(self):
        """Run scanner continuously."""
        print("[SCANNER] Starting continuous market scanning...")
        while True:
            try:
                opportunities = await self.scan_all_markets()
                print(f"[SCANNER] Top opportunities found: {len(opportunities)}")
                for i, opp in enumerate(opportunities[:5]):
                    print(
                        f"  {i+1}. {opp['title'][:50]} - Score: {opp['overall_score']:.1f}"
                    )
            except Exception as e:
                print(f"[SCANNER ERROR] {e}")
            await asyncio.sleep(SCAN_INTERVAL_SECONDS)


# Global scanner instance
scanner = MarketScanner()
