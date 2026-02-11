# Scope Clarification - All Markets, Strategies Later

## Architecture (Revised)

### Layer 1: Market Discovery (Comprehensive)
- **Kalshi:** ALL active markets (weather, sports, economics, etc.)
- **Polymarket:** ALL active markets (politics, crypto, sports, events, etc.)
- **No artificial filtering** at discovery level
- All users see same market universe

### Layer 2: Shared Insights (Per Market)
- Groq analyzes each market for fair value
- Categorization for browsing (weather, crypto, politics, sports, economics)
- Shared reasoning across all users

### Layer 3: Strategies (Per User, Built Later)
- **Strategy 1:** Weather Arbitrage (Kalshi weather markets)
- **Strategy 2:** Sentiment Analysis (Polymarket events)
- **Strategy 3:** Crypto Momentum (Polymarket crypto markets)
- Users browse ALL markets, choose which to apply strategies to

## Browsing Flow

```
/browse
  → Shows markets page by page (mixed platforms + categories)
  → All 5-10 markets on each page
  → Categories are metadata (not filters)
  → User picks a market → /trade
```

## Why This Approach

1. **Maximum discovery:** Users see everything available
2. **Flexible strategies:** Build decision logic after browsing
3. **No constraints:** Kalshi weather + sports + econ + Polymarket politics + crypto + sports
4. **Better UX:** Explore first, filter later

## Current Status

✅ Market scanner fetches all platforms (no category filtering)
✅ Browse handler shows all markets (category=None)
✅ Database supports any market type
✅ Mock data includes weather, crypto, politics, sports

## Next: Build Strategies

Strategies will be applied at trade approval level:
- User browses, sees a market
- User clicks /trade on that market
- Bot suggests strategy (or manual override)
- User approves → execute with encrypted key

This means strategies don't limit discovery—they enhance decision-making.
