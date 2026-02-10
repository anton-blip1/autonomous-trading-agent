# GitHub Setup Instructions

## Option 1: Create Repo via GitHub Web UI (Recommended)

1. Go to https://github.com/new
2. Create repo: `autonomous-trading-agent` (public or private)
3. Run these commands locally:

```bash
cd /Users/faizan2/.openclaw/workspace/autonomous-trading-agent

# Add remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/autonomous-trading-agent.git

# Push code
git branch -M main
git push -u origin main
```

## Option 2: Use GitHub CLI

```bash
gh auth login
gh repo create autonomous-trading-agent --public --source=. --remote=origin --push
```

## What Gets Pushed (Safe)
✅ agent.py (core logic)
✅ market_scanner.py, solana_integration.py, telegram_bot.py
✅ database.py, config.py
✅ tests/ (test suite)
✅ .env.example (template - no secrets)
✅ .gitignore (security)
✅ README.md, BUILD_REPORT.md

## What Stays Local (Private)
🔒 .env (your API keys)
🔒 data/solana_keypair.json (your wallet)
🔒 data/trading.db (trade history)
🔒 venv/ (virtual environment)

---

**After pushing, you can add the remote and test:**

```bash
# Set API keys
cp .env.example .env
# Edit .env with your real API keys

# Run tests
python3 devnet_test.py

# Run agent
python3 agent.py
```
