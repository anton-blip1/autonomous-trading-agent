"""
Core Trading Agent - Claude-powered decision making loop.
Main orchestrator that:
1. Fetches markets
2. Analyzes opportunities
3. Makes trading decisions via Claude
4. Executes trades via Solana
5. Learns from outcomes
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional
from anthropic import Anthropic

from config import (
    ANTHROPIC_API_KEY,
    MIN_EDGE_PERCENT,
    MIN_CONFIDENCE,
    AUTO_EXEC_THRESHOLD_USD,
    APPROVAL_THRESHOLD_USD,
    SCAN_INTERVAL_SECONDS,
    KELLY_FRACTION,
    INITIAL_BANKROLL_USD,
    ENABLE_LIVE_TRADING,
)
from market_scanner import scanner
from database import db
from solana_integration import wallet, executor


class AutonomousAgent:
    """Main trading agent powered by Claude with tool use."""

    def __init__(self):
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
        self.model = "claude-haiku-4-5"
        self.bankroll = INITIAL_BANKROLL_USD
        self.trades_executed = 0
        self.trades_successful = 0
        self.session_pnl = 0.0
        
        # Define Claude tools
        self.tools = self._define_tools()
        
        print(f"[AGENT] Initialized with bankroll: ${self.bankroll}")
        print(f"[AGENT] Model: {self.model}")

    def _define_tools(self) -> List[Dict]:
        """Define tools that Claude can use."""
        return [
            {
                "name": "get_market_data",
                "description": "Fetch current market data for a specific market",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "market_id": {"type": "string", "description": "Market ID to fetch"}
                    },
                    "required": ["market_id"]
                }
            },
            {
                "name": "calculate_kelly_position",
                "description": "Calculate position size using Kelly Criterion",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "bankroll": {"type": "number", "description": "Available bankroll in USD"},
                        "win_probability": {"type": "number", "description": "Probability of winning (0-1)"},
                        "win_payoff": {"type": "number", "description": "Payoff if win (e.g., 2.0 = double)"},
                        "loss_payoff": {"type": "number", "description": "Payoff if loss (e.g., 0.0 = lose all)"}
                    },
                    "required": ["bankroll", "win_probability", "win_payoff", "loss_payoff"]
                }
            },
            {
                "name": "evaluate_market_edge",
                "description": "Evaluate if a market has sufficient edge to trade",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "market_id": {"type": "string"},
                        "fair_value": {"type": "number", "description": "True probability (0-1)"},
                        "market_price": {"type": "number", "description": "Current market price (0-1)"},
                        "confidence": {"type": "number", "description": "Confidence in estimate (0-1)"}
                    },
                    "required": ["market_id", "fair_value", "market_price", "confidence"]
                }
            },
            {
                "name": "place_trade",
                "description": "Execute a trade on Solana devnet",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "market_id": {"type": "string"},
                        "side": {"type": "string", "enum": ["YES", "NO"]},
                        "amount_usd": {"type": "number"},
                        "entry_price": {"type": "number"}
                    },
                    "required": ["market_id", "side", "amount_usd", "entry_price"]
                }
            },
            {
                "name": "get_portfolio_status",
                "description": "Get current portfolio status and open positions",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]

    def _process_tool_call(self, tool_name: str, tool_input: Dict) -> str:
        """Process Claude's tool calls."""
        
        if tool_name == "get_market_data":
            market_id = tool_input["market_id"]
            market = scanner.get_market_by_id(market_id)
            if market:
                return json.dumps(market)
            return json.dumps({"error": "Market not found"})
        
        elif tool_name == "calculate_kelly_position":
            bankroll = tool_input["bankroll"]
            p_win = tool_input["win_probability"]
            b_win = tool_input["win_payoff"]
            b_loss = tool_input["loss_payoff"]
            
            # Kelly Criterion: f = (b*p - (1-p)) / b
            if b_win == 0:
                kelly_fraction = 0
            else:
                kelly_fraction = (b_win * p_win - (1 - p_win)) / b_win
            
            # Use fractional Kelly for safety
            kelly_fraction = max(0, kelly_fraction * KELLY_FRACTION)
            position_size = bankroll * kelly_fraction
            
            return json.dumps({
                "kelly_fraction": kelly_fraction,
                "position_size_usd": position_size,
                "bankroll": bankroll
            })
        
        elif tool_name == "evaluate_market_edge":
            fair_value = tool_input["fair_value"]
            market_price = tool_input["market_price"]
            confidence = tool_input["confidence"]
            
            edge_percent = abs(fair_value - market_price) * 100
            
            has_edge = edge_percent >= MIN_EDGE_PERCENT and confidence >= MIN_CONFIDENCE
            
            return json.dumps({
                "edge_percent": edge_percent,
                "confidence": confidence,
                "has_edge": has_edge,
                "recommendation": "BUY" if fair_value > market_price else "SELL" if fair_value < market_price else "HOLD"
            })
        
        elif tool_name == "place_trade":
            market_id = tool_input["market_id"]
            side = tool_input["side"]
            amount_usd = tool_input["amount_usd"]
            entry_price = tool_input["entry_price"]
            
            if not ENABLE_LIVE_TRADING:
                return json.dumps({"status": "simulated", "message": "Trading disabled for testing"})
            
            # Execute trade
            if side == "YES":
                trade = executor.create_polymarket_trade(market_id, side, amount_usd, entry_price)
            else:
                trade = executor.create_polymarket_trade(market_id, side, amount_usd, entry_price)
            
            if trade:
                tx_hash = executor.submit_trade(trade)
                self.trades_executed += 1
                return json.dumps({"status": "submitted", "tx_hash": tx_hash, "trade": trade})
            
            return json.dumps({"status": "failed", "error": "Could not create trade"})
        
        elif tool_name == "get_portfolio_status":
            positions = db.get_open_positions()
            recent_trades = db.get_recent_trades(5)
            
            return json.dumps({
                "bankroll": self.bankroll,
                "open_positions": len(positions) if positions else 0,
                "trades_executed": self.trades_executed,
                "session_pnl_usd": self.session_pnl
            })
        
        return json.dumps({"error": "Unknown tool"})

    async def analyze_and_decide(self, opportunities: List[Dict]) -> str:
        """Have Claude analyze opportunities and make trading decisions."""
        
        if not opportunities:
            return "No qualifying opportunities found."
        
        # Prepare market context for Claude
        market_context = json.dumps(opportunities[:10], indent=2)  # Top 10
        
        system_prompt = """You are an autonomous trading agent for prediction markets.
Your job is to:
1. Analyze market opportunities
2. Identify trades with sufficient edge
3. Use tools to make trading decisions
4. Execute trades when appropriate

Trading Rules:
- Minimum 3% edge required
- Minimum 65% confidence
- Use Kelly Criterion for position sizing
- Auto-execute trades under $5
- Request approval for $5-50 trades
- Reject trades over $50 without approval

You have access to tools to:
- Get detailed market data
- Calculate optimal position sizes
- Evaluate market edges
- Place trades
- Check portfolio status"""
        
        user_message = f"""Current market opportunities:

{market_context}

Please analyze these opportunities and decide which ones to trade.
For promising opportunities:
1. Use evaluate_market_edge to confirm edge
2. Use calculate_kelly_position to size position
3. Use place_trade to execute if you have high confidence

Focus on finding 1-3 high-conviction trades."""
        
        messages = [{"role": "user", "content": user_message}]
        
        # Agentic loop
        decision_log = []
        while True:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=system_prompt,
                tools=self.tools,
                messages=messages
            )
            
            # Check if Claude is done or needs to use tools
            if response.stop_reason == "end_turn":
                # Extract final response
                for block in response.content:
                    if hasattr(block, 'text'):
                        decision_log.append(block.text)
                break
            
            elif response.stop_reason == "tool_use":
                # Process tool calls
                for block in response.content:
                    if hasattr(block, 'text'):
                        decision_log.append(block.text)
                    
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        tool_use_id = block.id
                        
                        print(f"[AGENT] Claude called tool: {tool_name}")
                        result = self._process_tool_call(tool_name, tool_input)
                        decision_log.append(f"Tool {tool_name} result: {result[:200]}")
                        
                        # Add tool result back to messages
                        messages.append({"role": "assistant", "content": response.content})
                        messages.append({
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_use_id,
                                    "content": result
                                }
                            ]
                        })
            else:
                break
        
        return "\n".join(decision_log)

    async def run_main_loop(self):
        """Main agent loop: scan → analyze → decide → execute."""
        print("[AGENT] Starting main trading loop...")
        iteration = 0
        
        while True:
            iteration += 1
            timestamp = datetime.now().isoformat()
            print(f"\n{'='*60}")
            print(f"[ITERATION {iteration}] {timestamp}")
            print(f"Bankroll: ${self.bankroll:.2f} | Trades: {self.trades_executed}")
            print(f"{'='*60}")
            
            try:
                # 1. Scan markets
                print("[AGENT] Scanning markets...")
                opportunities = await scanner.scan_all_markets()
                
                if opportunities:
                    # 2. Analyze and decide
                    print(f"[AGENT] Analyzing {len(opportunities)} opportunities...")
                    decision = await self.analyze_and_decide(opportunities)
                    
                    # Log decision
                    print("[AGENT] Decision made:")
                    print(decision[:500])
                    db.log_event("decisions_made", details={"opportunities": len(opportunities)})
                else:
                    print("[AGENT] No opportunities found")
                
            except Exception as e:
                print(f"[AGENT ERROR] {e}")
                import traceback
                traceback.print_exc()
            
            # Wait before next iteration
            print(f"[AGENT] Waiting {SCAN_INTERVAL_SECONDS}s before next scan...")
            await asyncio.sleep(SCAN_INTERVAL_SECONDS)


async def main():
    """Main entry point."""
    agent = AutonomousAgent()
    
    # Check wallet status
    balance = wallet.get_balance()
    print(f"\n[WALLET] Balance: {balance} SOL")
    if balance < 0.5:
        print("[WALLET] Requesting airdrop...")
        wallet.request_airdrop(2.0)
    
    # Run agent loop
    await agent.run_main_loop()


if __name__ == "__main__":
    asyncio.run(main())
