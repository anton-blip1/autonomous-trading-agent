"""
Insight Engine - Generate market analysis using Groq LLM
Shared insights (same for all users)
"""

import json
import asyncio
from typing import Optional, Dict
from datetime import datetime, timedelta
from groq import Groq

from config import Config
from database import db


class InsightEngine:
    """Generate market insights using Groq LLM."""
    
    def __init__(self):
        self.groq_client = Groq(api_key=Config.GROQ_API_KEY)
        self.model = Config.GROQ_MODEL
        self.cache_ttl = Config.INSIGHT_CACHE_TTL_SECONDS
        self.insights_cache = {}
    
    async def generate_insight(self, market: Dict) -> Dict:
        """
        Generate insight for a market using Groq.
        
        Args:
            market: Market data {id, title, description, current_price, ...}
        
        Returns:
            Insight {market_id, fair_value, opportunity_pct, confidence, reasoning}
        """
        
        market_id = market.get('market_id') or market.get('id')
        
        # Check if insight already cached (within TTL)
        cached = self.insights_cache.get(market_id)
        if cached:
            expires_at = cached.get('expires_at')
            if expires_at and datetime.now() < expires_at:
                print(f"[INSIGHT] Using cached insight for {market_id}")
                return cached
        
        # Check database cache
        db_insight = await db.get_insight(market_id)
        if db_insight:
            if db_insight.get('expires_at') and datetime.now() < db_insight['expires_at']:
                print(f"[INSIGHT] Using DB cached insight for {market_id}")
                self.insights_cache[market_id] = db_insight
                return db_insight
        
        print(f"[INSIGHT] Generating new insight for {market_id}...")
        
        # Use Groq to analyze market
        try:
            prompt = self._build_prompt(market)
            
            response = self.groq_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.5,
                max_tokens=500
            )
            
            response_text = response.choices[0].message.content
            
            # Parse JSON response
            try:
                analysis = json.loads(response_text)
            except:
                # Fallback if response isn't valid JSON
                analysis = {
                    'fair_value': market.get('current_price', 0.5),
                    'confidence': 0.3,
                    'reasoning': response_text[:200]
                }
            
            # Build insight
            current_price = market.get('current_price', 0.5)
            fair_value = analysis.get('fair_value', current_price)
            
            insight = {
                'market_id': market_id,
                'fair_value': fair_value,
                'opportunity_pct': ((fair_value - current_price) / current_price * 100) if current_price > 0 else 0,
                'confidence': analysis.get('confidence', 0.5),
                'reasoning': analysis.get('reasoning', '')[:500],
                'generated_at': datetime.now(),
                'expires_at': datetime.now() + timedelta(seconds=self.cache_ttl)
            }
            
            # Cache in memory
            self.insights_cache[market_id] = insight
            
            # Store in database
            await db.store_insight(insight)
            
            print(f"[INSIGHT] Generated: {market_id} (Fair: {fair_value:.0%}, Opp: {insight['opportunity_pct']:+.1f}%)")
            
            return insight
        
        except Exception as e:
            print(f"[INSIGHT] Error generating insight: {e}")
            
            # Fallback insight (no analysis)
            return {
                'market_id': market_id,
                'fair_value': market.get('current_price', 0.5),
                'opportunity_pct': 0,
                'confidence': 0,
                'reasoning': 'Analysis unavailable',
                'generated_at': datetime.now(),
                'expires_at': datetime.now() + timedelta(seconds=60)
            }
    
    def _build_prompt(self, market: Dict) -> str:
        """Build prompt for Groq market analysis."""
        
        title = market.get('title', 'Unknown')
        description = market.get('description', '')
        current_price = market.get('current_price', 0.5)
        platform = market.get('platform', 'unknown')
        
        prompt = f"""Analyze this prediction market and provide your best estimate of its fair value.

**Market:** {title}
**Platform:** {platform}
**Current Price:** {current_price:.1%}
**Description:** {description}

Based on available information, what is the FAIR VALUE (true probability) of this market?

Respond ONLY in JSON format with NO markdown:
{{
  "fair_value": 0.XX,
  "confidence": 0.XX,
  "reasoning": "Your brief explanation (1-2 sentences)"
}}

Rules:
- fair_value: Your estimate of true probability (0.0 to 1.0)
- confidence: How confident you are (0.0 to 1.0)
- reasoning: Why you think this

Example: {{"fair_value": 0.42, "confidence": 0.75, "reasoning": "NOAA forecast shows 60% rain probability, market at 35% is undervalued by historical pattern"}}"""
        
        return prompt
    
    async def get_insights_for_markets(self, markets: list) -> list:
        """Get insights for multiple markets (parallel)."""
        
        tasks = [self.generate_insight(market) for market in markets]
        insights = await asyncio.gather(*tasks)
        return insights
    
    async def get_top_opportunities(self, markets: list, min_opportunity: float = 0.05) -> list:
        """
        Get markets with best trading opportunities.
        
        Args:
            markets: List of markets
            min_opportunity: Minimum opportunity % (e.g., 0.05 = 5%)
        
        Returns:
            Sorted list of opportunities
        """
        
        insights = await self.get_insights_for_markets(markets)
        
        # Filter by opportunity
        opportunities = [
            insight for insight in insights
            if abs(insight.get('opportunity_pct', 0)) >= min_opportunity * 100
        ]
        
        # Sort by opportunity (largest first)
        opportunities.sort(
            key=lambda x: abs(x.get('opportunity_pct', 0)),
            reverse=True
        )
        
        return opportunities


# Global instance
insight_engine = InsightEngine()
