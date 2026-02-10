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
from groq import Groq

from config import (
    GROQ_API_KEY,
    GROQ_MODEL,
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
from blockchain_integration import SolanaWallet, PolygonWallet, TradeExecutor, executor
from wormhole_bridge import bridge


class AutonomousAgent:
    """Main trading agent powered by Claude with tool use."""

    def __init__(self):
        # Use Groq for faster, free inference
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = GROQ_MODEL  # mixtral-8x7b-32768
        self.bankroll = INITIAL_BANKROLL_USD
        self.trades_executed = 0
        self.trades_successful = 0
        self.session_pnl = 0.0
        
        # Define tools for agent use
        self.tools = self._define_tools()
        
        print(f"[AGENT] Initialized with bankroll: ${self.bankroll}")
        print(f"[AGENT] Model: {self.model} (via Groq API)")
        print(f"[AGENT] Groq provides free, fast inference - no Anthropic dependency")

    def _define_tools(self) -> List[Dict]:
        """Define tools that Groq can use (OpenAI format)."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_market_data",
                    "description": "Fetch current market data for a specific market",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "market_id": {"type": "string", "description": "Market ID to fetch"}
                        },
                        "required": ["market_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_kelly_position",
                    "description": "Calculate position size using Kelly Criterion",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "bankroll": {"type": "number", "description": "Available bankroll in USD"},
                            "win_probability": {"type": "number", "description": "Probability of winning (0-1)"},
                            "win_payoff": {"type": "number", "description": "Payoff if win (e.g., 2.0)"},
                            "loss_payoff": {"type": "number", "description": "Payoff if loss (e.g., 0.0)"}
                        },
                        "required": ["bankroll", "win_probability", "win_payoff", "loss_payoff"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "evaluate_market_edge",
                    "description": "Evaluate if a market has sufficient edge to trade",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "market_id": {"type": "string"},
                            "fair_value": {"type": "number", "description": "True probability (0-1)"},
                            "market_price": {"type": "number", "description": "Current market price (0-1)"},
                            "confidence": {"type": "number", "description": "Confidence in estimate (0-1)"}
                        },
                        "required": ["market_id", "fair_value", "market_price", "confidence"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "place_trade",
                    "description": "Execute a trade on Solana/Polygon devnet",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "market_id": {"type": "string"},
                            "side": {"type": "string", "enum": ["YES", "NO"]},
                            "amount_usd": {"type": "number"},
                            "entry_price": {"type": "number"},
                            "chain": {"type": "string", "enum": ["solana", "polygon"], "description": "Target blockchain"}
                        },
                        "required": ["market_id", "side", "amount_usd", "entry_price", "chain"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_portfolio_status",
                    "description": "Get current portfolio status and open positions",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            }
        ]

    def _log_bridge_failure(self, bridge_tx: Dict) -> None:
        """Log a failed bridge transaction."""
        try:
            db.log_event("bridge_failed", details={
                "from_chain": bridge_tx.get("from_chain"),
                "to_chain": bridge_tx.get("to_chain"),
                "amount_usd": bridge_tx.get("amount_usd"),
                "tx_hash": bridge_tx.get("tx_hash")
            })
            print(f"[AGENT] Bridge failure logged: {bridge_tx.get('tx_hash')}")
        except Exception as e:
            print(f"[AGENT ERROR] Failed to log bridge failure: {e}")

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
            chain = tool_input.get("chain", "solana")
            
            if not ENABLE_LIVE_TRADING:
                return json.dumps({"status": "simulated", "message": "Trading disabled for testing", "chain": chain})
            
            # Route trade based on chain with auto-bridging
            trade = None
            bridge_executed = False
            bridge_cost = 0
            
            if chain == "polygon":
                # Check Polygon wallet balance
                poly_balance = executor.polygon_wallet.get_balance()
                if poly_balance < amount_usd:
                    # Need to bridge from Solana to Polygon
                    bridge_needed = amount_usd - poly_balance
                    print(f"[AGENT] Insufficient USDC on Polygon ({poly_balance}). Attempting bridge from Solana...")
                    
                    # Check Solana balance
                    sol_balance = executor.solana_wallet.get_balance()
                    if sol_balance > 1.0:  # Need at least 1 SOL for gas
                        # Execute bridge
                        bridge_tx_hash = bridge.execute_bridge(
                            executor.solana_wallet,
                            executor.polygon_wallet.get_address(),
                            bridge_needed,
                            "solana",
                            "polygon"
                        )
                        
                        if bridge_tx_hash:
                            # Wait for bridge confirmation
                            confirmed = bridge.wait_for_confirmation(bridge_tx_hash, "solana", timeout=60)
                            if confirmed:
                                bridge_executed = True
                                bridge_cost = bridge.estimate_bridge_cost(bridge_needed, "solana", "polygon")
                                print(f"[AGENT] Bridge successful: {bridge_tx_hash}")
                                
                                # Log bridge transaction
                                db.add_bridge_transaction({
                                    "from_chain": "solana",
                                    "to_chain": "polygon",
                                    "amount_usd": bridge_needed,
                                    "tx_hash": bridge_tx_hash,
                                    "status": "confirmed",
                                    "cost_usd": bridge_cost
                                })
                            else:
                                # Bridge timed out, try fallback
                                print(f"[AGENT] Bridge timeout. Attempting fallback...")
                                bridge.handle_timeout(bridge_tx_hash, lambda tx: self._log_bridge_failure(tx))
                    else:
                        print(f"[AGENT] Insufficient SOL balance for bridging: {sol_balance}")
                        return json.dumps({"status": "failed", "error": "Insufficient liquidity on both chains"})
                
                # Create Polygon trade
                trade = executor.create_polygon_trade(market_id, side, amount_usd, entry_price)
                
            else:  # solana
                # Check Solana balance (sufficient SOL for gas)
                sol_balance = executor.solana_wallet.get_balance()
                if sol_balance < 0.1:
                    print(f"[AGENT] Insufficient SOL for gas. Requesting airdrop...")
                    executor.solana_wallet.request_airdrop(2.0)
                
                # Create Solana trade
                trade = executor.create_solana_trade(market_id, side, amount_usd, entry_price)
            
            if trade:
                # Add chain metadata
                trade["chain"] = chain
                trade["bridge_executed"] = bridge_executed
                trade["bridge_cost"] = bridge_cost
                
                tx_hash = executor.submit_trade(trade)
                if tx_hash:
                    self.trades_executed += 1
                    
                    # Log trade to database
                    db.add_trade({
                        "market_id": market_id,
                        "side": side,
                        "amount_usd": amount_usd,
                        "entry_price": entry_price,
                        "tx_hash": tx_hash,
                        "status": "submitted",
                        "chain": chain
                    })
                    
                    return json.dumps({
                        "status": "submitted",
                        "tx_hash": tx_hash,
                        "chain": chain,
                        "amount_usd": amount_usd,
                        "bridge_executed": bridge_executed,
                        "bridge_cost": bridge_cost
                    })
            
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
        
        # Agentic loop using Groq (compatible with Anthropic tool_use)
        decision_log = []
        loop_iteration = 0
        max_iterations = 10  # Prevent infinite loops
        
        while loop_iteration < max_iterations:
            loop_iteration += 1
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=2048,
                system=system_prompt,
                tools=self.tools,
                tool_choice="auto",
                messages=messages
            )
            
            # Handle Groq response (OpenAI-compatible format)
            choice = response.choices[0]
            
            if choice.finish_reason == "stop":
                # Agent is done reasoning
                if choice.message.content:
                    decision_log.append(choice.message.content)
                break
            
            elif choice.finish_reason == "tool_calls":
                # Agent wants to use tools
                if choice.message.content:
                    decision_log.append(choice.message.content)
                
                # Add assistant message to history
                messages.append({
                    "role": "assistant",
                    "content": choice.message.content,
                    "tool_calls": choice.message.tool_calls if hasattr(choice.message, 'tool_calls') else []
                })
                
                # Process each tool call
                if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                    for tool_call in choice.message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_input = json.loads(tool_call.function.arguments)
                        tool_id = tool_call.id
                        
                        print(f"[AGENT] Groq called tool: {tool_name}")
                        result = self._process_tool_call(tool_name, tool_input)
                        decision_log.append(f"Tool {tool_name} → {result[:150]}")
                        
                        # Add tool result
                        messages.append({
                            "role": "tool",
                            "content": result,
                            "tool_call_id": tool_id
                        })
            else:
                # Unexpected finish reason
                print(f"[AGENT] Unexpected finish reason: {choice.finish_reason}")
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
    
    # Check dual wallet status
    wallet_status = executor.get_dual_wallet_status()
    print(f"\n[WALLET] Dual Wallet Status:")
    print(f"  Solana: {wallet_status['solana']['address'][:16]}... ({wallet_status['solana']['balance_sol']:.2f} SOL)")
    print(f"  Polygon: {wallet_status['polygon']['address'][:16]}... ({wallet_status['polygon']['balance_usdc']:.2f} USDC)")
    
    # Request Solana airdrop if needed
    if wallet_status['solana']['balance_sol'] < 0.5:
        print("[WALLET] Requesting Solana airdrop...")
        executor.solana_wallet.request_airdrop(2.0)
    
    # Request Polygon faucet if needed
    if wallet_status['polygon']['balance_usdc'] < 100:
        print("[WALLET] Requesting Polygon Mumbai USDC faucet...")
        executor.polygon_wallet.request_faucet(100.0)
    
    # Run agent loop
    await agent.run_main_loop()


if __name__ == "__main__":
    asyncio.run(main())
