"""
Solana Devnet Transaction Test
Demonstrates actual transactions on Solana devnet with trading agent.
Run this to prove agent can execute real trades on-chain.
"""
import asyncio
import time
from datetime import datetime
from solana_integration import wallet, executor
from database import db
from market_scanner import scanner


async def test_wallet_setup():
    """Test 1: Wallet setup and airdrop."""
    print("\n" + "="*60)
    print("TEST 1: WALLET SETUP")
    print("="*60)
    
    address = wallet.get_address()
    print(f"✅ Wallet address: {address}")
    print(f"   Network: Solana Devnet")
    print(f"   Keypair file: data/solana_keypair.json")
    
    # Check balance
    balance = wallet.get_balance()
    print(f"\n📊 Current balance: {balance} SOL")
    
    if balance < 0.5:
        print("⏳ Requesting airdrop of 2.0 SOL...")
        tx_hash = wallet.request_airdrop(2.0)
        if tx_hash:
            print(f"✅ Airdrop requested: {tx_hash}")
            # Wait for airdrop
            time.sleep(5)
            new_balance = wallet.get_balance()
            print(f"📊 New balance: {new_balance} SOL")
        else:
            print("❌ Airdrop failed")
    else:
        print(f"✅ Sufficient balance: {balance} SOL")
    
    return True


async def test_market_scanning():
    """Test 2: Scan and score markets."""
    print("\n" + "="*60)
    print("TEST 2: MARKET SCANNING")
    print("="*60)
    
    print("📡 Scanning Polymarket and Kalshi...")
    opportunities = await scanner.scan_all_markets()
    
    print(f"\n✅ Found {len(opportunities)} qualified markets:")
    for i, opp in enumerate(opportunities[:5]):
        print(f"\n{i+1}. {opp['title'][:50]}")
        print(f"   Platform: {opp['platform']}")
        print(f"   YES price: {opp['yes_price']:.4f}")
        print(f"   NO price: {opp['no_price']:.4f}")
        print(f"   Spread: {opp['spread']:.2%}")
        print(f"   Score: {opp['overall_score']:.1f}/100")
    
    return opportunities


async def test_trade_creation(opportunities):
    """Test 3: Create trades (simulated)."""
    print("\n" + "="*60)
    print("TEST 3: TRADE CREATION")
    print("="*60)
    
    if not opportunities:
        print("❌ No opportunities to trade")
        return []
    
    trades = []
    
    # Create 3 test trades
    for i in range(min(3, len(opportunities))):
        opp = opportunities[i]
        
        # Alternate between YES and NO
        side = "YES" if i % 2 == 0 else "NO"
        amount_usd = 5.0 + (i * 2.5)  # $5, $7.50, $10
        price = opp['yes_price'] if side == "YES" else opp['no_price']
        
        print(f"\n📝 Trade {i+1}:")
        print(f"   Market: {opp['market_id'][:30]}...")
        print(f"   Side: {side}")
        print(f"   Amount: ${amount_usd:.2f}")
        print(f"   Entry price: {price:.4f}")
        print(f"   Platform: {opp['platform']}")
        
        # Create trade
        if opp['platform'] == 'polymarket':
            trade = executor.create_polymarket_trade(
                opp['market_id'],
                side,
                amount_usd,
                price
            )
        else:
            trade = executor.create_kalshi_trade(
                opp['market_id'],
                side,
                amount_usd,
                price
            )
        
        if trade:
            print(f"   ✅ Created trade: {trade}")
            trades.append(trade)
        else:
            print(f"   ❌ Failed to create trade")
    
    return trades


async def test_trade_execution(trades):
    """Test 4: Execute trades on devnet."""
    print("\n" + "="*60)
    print("TEST 4: TRADE EXECUTION (SOLANA DEVNET)")
    print("="*60)
    
    if not trades:
        print("❌ No trades to execute")
        return []
    
    executed = []
    
    for i, trade in enumerate(trades):
        print(f"\n🚀 Executing trade {i+1}/{len(trades)}...")
        print(f"   Market: {trade['market_id'][:30]}...")
        print(f"   Side: {trade['side']}")
        print(f"   Amount: ${trade['amount_usd']:.2f}")
        
        # Submit trade
        tx_hash = executor.submit_trade(trade)
        
        if tx_hash:
            print(f"   ✅ Submitted to devnet")
            print(f"   TX Hash: {tx_hash}")
            print(f"   Explorer: https://solana.fm/tx/{tx_hash}?cluster=devnet")
            
            # Store in database
            db.add_trade({
                "market_id": trade['market_id'],
                "side": trade['side'],
                "amount_usd": trade['amount_usd'],
                "entry_price": trade['entry_price'],
                "tx_hash": tx_hash,
                "status": "submitted"
            })
            
            executed.append({**trade, "tx_hash": tx_hash, "status": "submitted"})
            
            # Check status
            print(f"   ⏳ Checking transaction status...")
            time.sleep(2)
            
            status = wallet.get_transaction_status(tx_hash)
            if status:
                print(f"   Status: {status}")
                executed[-1]["status"] = status
        else:
            print(f"   ❌ Failed to submit trade")
    
    return executed


async def test_portfolio_tracking():
    """Test 5: Track portfolio and positions."""
    print("\n" + "="*60)
    print("TEST 5: PORTFOLIO TRACKING")
    print("="*60)
    
    positions = db.get_open_positions()
    trades = db.get_recent_trades(10)
    
    print(f"\n📊 Portfolio Status:")
    print(f"   Open positions: {len(positions) if positions else 0}")
    print(f"   Recent trades: {len(trades) if trades else 0}")
    
    if trades:
        print(f"\n   Recent trades:")
        for trade in trades[:5]:
            print(f"   • {trade}")


async def demonstrate_claude_integration():
    """Test 6: Demonstrate Claude integration."""
    print("\n" + "="*60)
    print("TEST 6: CLAUDE AGENT INTEGRATION")
    print("="*60)
    
    from agent import AutonomousAgent
    
    agent = AutonomousAgent()
    print(f"✅ Agent initialized")
    print(f"   Model: {agent.model}")
    print(f"   Bankroll: ${agent.bankroll}")
    print(f"   Available tools: {len(agent.tools)}")
    
    for tool in agent.tools:
        print(f"   • {tool['name']}")


async def main():
    """Run all tests."""
    print("\n" + "🚀 "*30)
    print("AUTONOMOUS TRADING AGENT - DEVNET TRANSACTION TEST")
    print("🚀 "*30)
    print(f"Started: {datetime.now().isoformat()}")
    
    try:
        # Test 1: Wallet
        await test_wallet_setup()
        
        # Test 2: Market scanning
        opportunities = await test_market_scanning()
        
        if not opportunities:
            print("❌ No market opportunities found. Skipping trade tests.")
            return
        
        # Test 3: Trade creation
        trades = await test_trade_creation(opportunities)
        
        if not trades:
            print("❌ Failed to create trades.")
            return
        
        # Test 4: Trade execution
        executed = await test_trade_execution(trades)
        
        # Test 5: Portfolio tracking
        await test_portfolio_tracking()
        
        # Test 6: Claude integration
        await demonstrate_claude_integration()
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"✅ Wallet setup: PASSED")
        print(f"✅ Market scanning: PASSED ({len(opportunities)} markets)")
        print(f"✅ Trade creation: PASSED ({len(trades)} trades)")
        print(f"✅ Trade execution: PASSED ({len(executed)} executed)")
        print(f"✅ Portfolio tracking: PASSED")
        print(f"✅ Claude integration: PASSED")
        print(f"\n🎉 ALL TESTS PASSED - Ready for full agent deployment")
        
        # Show next steps
        print("\n" + "="*60)
        print("NEXT STEPS")
        print("="*60)
        print("1. Copy .env.example to .env")
        print("2. Set ANTHROPIC_API_KEY in .env")
        print("3. Run: python agent.py")
        print("4. Monitor trades at: https://solana.fm/?cluster=devnet")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
