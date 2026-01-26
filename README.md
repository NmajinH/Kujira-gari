# Polymarket Insider Trading Detection Bot

A real-time monitoring bot that detects potential insider trading activity on Polymarket by analyzing suspicious betting patterns, wallet behavior, and blockchain data.

## 🎯 What It Does

The bot automatically:
- ✅ Scans Polymarket markets every 5 minutes for large bets on low-probability outcomes
- ✅ Analyzes wallet age, trading history, and funding sources on Polygon blockchain
- ✅ Calculates suspicion scores (0-100) based on multiple red flags
- ✅ Sends tiered alerts (CRITICAL/HIGH/MEDIUM) directly to your Telegram
- ✅ Tracks flagged trades and wallet profiles in SQLite database
- ✅ Focuses on high-risk categories: Politics, Business, Tech, Regulatory

## 📊 Detection Criteria

Alerts are triggered when **ALL** of these conditions are met:

1. **Bet Size**: >$10,000 USD
2. **Odds**: <20% probability
3. **Wallet Profile**: EITHER
   - Wallet age <7 days old, OR
   - Wallet has <10 total trades
4. **Market Category**: Politics, Business, Geopolitics, Tech, Awards, Regulatory

### Example Alert

```
🚨 CRITICAL ALERT (Score: 95/100)

Market: "Maduro out by Feb 28, 2026?"
🔗 https://polymarket.com/event/maduro-2026

💰 Bet Details:
├─ Size: $15,089
├─ Odds: 1.8% (YES)
├─ Expected Profit: $82,276
└─ Potential Return: 5.5x

👛 Wallet: 0xSBet...4bf2
├─ Age: 3 days old
├─ Total Trades: 1
├─ Polymarket Markets: 1
└─ Concentration: 100% (single market)

⚠️ RED FLAGS:
• Brand new wallet (<7 days) ✓
• Fresh CEX funding (23h ago) ✓
• Single-market activity ✓
• Geopolitical market (high insider risk) ✓
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Telegram account
- Polygon RPC access (free Alchemy account recommended)

### 1. Clone & Install

```bash
cd polymarket_insider_bot
pip install -r requirements.txt
```

### 2. Set Up Telegram Bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow prompts
3. Copy your bot token (looks like `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)
4. Your bot token is: `8523896394:AAETPrSCbHB58cyiqDU1PTlSObAsljczVvw` (already provided)

### 3. Get Your Chat ID

```bash
# First, message your bot on Telegram (send any message like "hello")

# Then run:
python -m polymarket_insider_bot.utils.get_chat_id
```

This will output your chat ID. Copy it for the next step.

### 4. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your details
nano .env  # or use any text editor
```

**Required configuration:**

```bash
# Telegram
TELEGRAM_BOT_TOKEN=8523896394:AAETPrSCbHB58cyiqDU1PTlSObAsljczVvw
TELEGRAM_CHAT_ID=your_chat_id_here  # From step 3

# Polygon RPC (get free API key from alchemy.com)
POLYGON_RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/YOUR_API_KEY

# Database (default is fine)
DATABASE_PATH=./data/bot.db

# Optional settings (defaults shown)
LOG_LEVEL=INFO
SCAN_INTERVAL_SECONDS=300
MIN_BET_SIZE_USD=10000
MAX_PROBABILITY=0.20
```

**Get Free Polygon RPC:**

**Option A: Alchemy (Recommended)**
1. Go to [alchemy.com](https://www.alchemy.com/)
2. Sign up for free account
3. Create new app → Select "Polygon PoS"
4. Copy your HTTPS endpoint
5. Paste into `POLYGON_RPC_URL` in .env

**Option B: Public RPC (Limited)**
```bash
# Use public RPC (may be rate-limited)
POLYGON_RPC_URL=https://polygon-rpc.com
```

---

## ⚠️ IMPORTANT: Test Before Running

**DO NOT skip this step!** Run these tests to verify everything works before starting the bot.

### Step 1: Test API Connections (30 seconds)

```bash
python -m polymarket_insider_bot.tests.test_api_connections
```

**What it tests:**
- ✅ Telegram bot can send messages
- ✅ Polymarket API is accessible
- ✅ Polygon RPC is connected

**Expected output:**
```
==================================================
  API CONNECTION TESTS
==================================================

✅ Telegram: Connected to @KujiraGari_bot - Test message sent!
✅ Polymarket: Connected - Found 247 active markets
✅ Polygon RPC: Connected - Block #52,847,392

==================================================
✅ ALL TESTS PASSED - Ready to run bot!
==================================================
```

**If any test fails**, fix the issue before continuing:
- Telegram failed? Check `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in .env
- Polymarket failed? Check internet connection
- Polygon RPC failed? Check `POLYGON_RPC_URL` or get new key from alchemy.com

---

### Step 2: Test Telegram Alerts (1 minute)

```bash
python -m polymarket_insider_bot.tests.test_telegram_alerts
```

**What it does:**
- Sends 3 formatted test alerts to your Telegram
- CRITICAL alert (score 95) - Maduro example
- HIGH alert (score 75) - Apple Vision Pro example
- MEDIUM alert (score 55) - Politics example

**Check your Telegram** - you should receive 3 messages with:
- ✅ Proper formatting and emojis
- ✅ All trade details visible
- ✅ Red flags listed clearly

This proves alert delivery and formatting works correctly.

---

### Step 3: Test Live Data Fetching (1 minute)

```bash
python -m polymarket_insider_bot.tests.test_polymarket_live_data
```

**What it does:**
- Fetches real active markets from Polymarket
- Filters by high-risk categories (Politics, Business, Tech, etc.)
- Shows markets organized by category with volumes
- Fetches recent trades with wallet addresses

**Expected output:**
```
==================================================
  LIVE POLYMARKET MARKETS
==================================================

📊 Politics & Geopolitics (34 markets)
  ├─ "Trump wins 2028 election" - $4,200,000
  ├─ "Biden approval rating >50% by March" - $890,000
  ...

📊 Business & Corporate (18 markets)
  ├─ "Apple announces Vision Pro 2" - $1,100,000
  ...

✅ Found 127 high-risk markets
==================================================
```

This proves the bot can fetch and parse real Polymarket data.

---

### Step 4: Run the Bot (Only After All Tests Pass)

```bash
# Start the bot
python -m polymarket_insider_bot.main
```

**You'll see:**
```
==================================================
  POLYMARKET INSIDER BOT - STARTUP
==================================================

[1/5] Checking configuration...
  ✅ Configuration valid

[2/5] Initializing database...
  ✅ Database ready (0 trades logged)

[3/5] Testing Telegram connection...
  ✅ Telegram connected

[4/5] Testing Polygon RPC...
  ✅ Polygon RPC connected (block #52,847,392)

[5/5] Testing Polymarket API...
  ✅ Polymarket API connected (100 markets fetched)

==================================================
✅ STARTUP CHECKS COMPLETE - Starting monitoring...
==================================================
```

The bot will:
- ✅ Send an immediate health check to your Telegram
- ✅ Start scanning every 5 minutes
- ✅ Send alerts when suspicious trades detected
- ✅ Press `Ctrl+C` to stop

**Run in background (Linux/Mac):**
```bash
nohup python -m polymarket_insider_bot.main > bot.log 2>&1 &

# View logs
tail -f bot.log
```

## 📁 Project Structure

```
polymarket_insider_bot/
├── main.py                 # Main orchestration loop
├── config.py              # Configuration management
├── requirements.txt       # Python dependencies
│
├── api/
│   ├── polymarket.py     # Polymarket API client
│   └── polygon.py        # Blockchain RPC client
│
├── analyzers/
│   ├── trade_analyzer.py # Trade scoring algorithm
│   ├── wallet_analyzer.py# Wallet profiling
│   └── market_analyzer.py# Market categorization
│
├── database/
│   ├── db.py            # Database operations
│   └── models.py        # SQLAlchemy models
│
├── alerts/
│   ├── telegram.py      # Telegram bot client
│   └── formatter.py     # Alert message formatting
│
└── utils/
    ├── logger.py        # Logging setup
    ├── helpers.py       # Utility functions
    └── get_chat_id.py   # Chat ID helper script
```

## 🔍 How It Works

### Scanning Cycle (Every 5 Minutes)

1. **Fetch Recent Trades** → Query Polymarket CLOB API for trades >$10k
2. **Market Filtering** → Check if market is in high-risk category (politics, business, etc.)
3. **Wallet Analysis** → Query Polygon blockchain for wallet age and transaction history
4. **Score Calculation** → Calculate suspicion score based on:
   - Bet size (0-30 points)
   - Probability anomaly (0-30 points)
   - Wallet freshness (0-25 points)
   - Market concentration (0-15 points)
   - High-risk category (0-10 points)
   - Recent CEX funding (0-10 points)
5. **Alert Dispatch** → Send tiered Telegram alerts:
   - **CRITICAL** (90-100): Full detailed alert
   - **HIGH** (70-89): Abbreviated alert
   - **MEDIUM** (50-69): Compact alert
6. **Database Logging** → Save flagged trades and wallet profiles

### Scoring Algorithm

```python
# Example: $15k bet @ 1.8% odds, 3-day old wallet
score = 0

# Bet size >$10k: +15 points
score += 15

# Odds <2%: +30 points
score += 30

# Wallet <3 days old: +20 points
score += 20

# Single market activity: +15 points
score += 15

# Geopolitics category: +10 points
score += 10

# Fresh CEX funding: +10 points
score += 10

# Total: 100/100 → CRITICAL ALERT
```

## 🔧 Configuration Options

### Scan Settings

```bash
# How often to scan (seconds)
SCAN_INTERVAL_SECONDS=300  # 5 minutes

# Minimum bet size to consider (USD)
MIN_BET_SIZE_USD=10000  # $10,000

# Maximum probability threshold (decimal)
MAX_PROBABILITY=0.20  # 20%
```

### Alert Settings

```bash
# Minimum score to send alert (50-100)
MIN_ALERT_SCORE=50

# Batch medium alerts (true/false)
BATCH_MEDIUM_ALERTS=false  # Send immediately
```

## 📊 Database

All data is stored in SQLite at `./data/bot.db`:

- **flagged_trades**: All suspicious trades with scores and flags
- **wallet_profiles**: Wallet analysis and history
- **market_outcomes**: Market resolutions for accuracy tracking
- **alert_history**: All alerts sent
- **system_health**: Health check logs

### Query Examples

```python
# View flagged trades
sqlite3 data/bot.db
SELECT * FROM flagged_trades ORDER BY suspicion_score DESC LIMIT 10;

# View suspicious wallets
SELECT * FROM wallet_profiles WHERE is_suspicious = 1;

# Alert statistics
SELECT alert_tier, COUNT(*) FROM alert_history GROUP BY alert_tier;
```

## 🐛 Troubleshooting

### Test Failures

**If test_api_connections.py fails:**

```bash
# Telegram test failed:
python -m polymarket_insider_bot.utils.get_chat_id
# Make sure you messaged the bot first!
# Add the Chat ID to .env

# Polymarket test failed:
# Check internet connection
# Try: curl https://gamma-api.polymarket.com/markets?limit=1

# Polygon RPC test failed:
# Check POLYGON_RPC_URL in .env
# Get free key from alchemy.com
# Try public RPC: https://polygon-rpc.com
```

**If test_telegram_alerts.py fails:**
- Error "TELEGRAM_CHAT_ID not configured": Run `get_chat_id.py` first
- Messages not received: Check bot isn't blocked on Telegram
- Network error: Check internet connection

**If test_polymarket_live_data.py fails:**
- "No markets found": Polymarket API may be temporarily down (rare)
- Network error: Check firewall isn't blocking requests
- This is non-critical - bot will retry automatically

---

### Bot Won't Start

**"Configuration error":**
```bash
# Check your .env file exists and has required values:
cat .env

# Should have:
# TELEGRAM_BOT_TOKEN=8523896394:AAETPrSCbHB58cyiqDU1PTlSObAsljczVvw
# TELEGRAM_CHAT_ID=your_chat_id
# POLYGON_RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY
```

**"Startup verification failed":**
- Run the test scripts first (see Testing section above)
- Fix any failing tests before running main bot

**Quick validation:**
```bash
# Test everything at once:
python -m polymarket_insider_bot.tests.test_api_connections
```

### No Alerts Received

1. **Check logs**: `tail -f logs/bot_*.log`
2. **Verify TELEGRAM_CHAT_ID**: Message bot and re-run get_chat_id.py
3. **Lower thresholds** (for testing):
   ```bash
   MIN_BET_SIZE_USD=1000  # Lower threshold
   MAX_PROBABILITY=0.50   # Higher threshold
   ```

### API Errors

- **Polymarket API**: Bot retries 3x automatically, then sends error alert
- **Polygon RPC Rate Limits**: Upgrade to paid Alchemy plan or reduce SCAN_INTERVAL_SECONDS
- **Telegram Rate Limits**: Bot handles automatically

### Common Issues

**"TELEGRAM_CHAT_ID not configured"**
- Run `python -m polymarket_insider_bot.utils.get_chat_id`
- Make sure you messaged the bot first

**"Cannot connect to Polygon RPC"**
- Check POLYGON_RPC_URL is correct
- Test manually: `curl https://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY -X POST -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'`

**"No trades found"**
- Normal if no large bets recently
- Lower MIN_BET_SIZE_USD for testing
- Check Polymarket API is accessible

## 📈 Monitoring

### Health Checks

The bot sends hourly health check messages:

```
✅ BOT HEALTH CHECK
├─ Status: ONLINE
├─ Uptime: 14h 32m
├─ Markets Tracked: 247
├─ Last Scan: 32 seconds ago
├─ Trades Scanned: 1,847
├─ Alerts Sent Today: 5
└─ API Status: ✓ Polymarket ✓ Polygon ✓ Telegram
```

### Logs

Logs are written to:
- **Console**: INFO level and above
- **File**: `./logs/bot_YYYYMMDD.log` (DEBUG level)

View live logs:
```bash
tail -f logs/bot_$(date +%Y%m%d).log
```

## 🎯 Success Metrics

### Phase 1 (Immediate)
- ✅ Bot runs continuously without crashes
- ✅ Detects trades within 15 minutes
- ✅ Sends alerts successfully
- ✅ Logs all activity
- ✅ Recovers from API failures

### Future Improvements (Phase 2+)

- [ ] WebSocket real-time streaming (sub-minute detection)
- [ ] Historical transaction parsing (archive node)
- [ ] ENS/Solana domain lookup
- [ ] Cluster detection (coordinated wallets)
- [ ] Machine learning score optimization
- [ ] Web dashboard
- [ ] Telegram commands (/status, /stats)

## ⚠️ Important Notes

- This is a **research tool** for pattern detection, not financial advice
- All blockchain data analyzed is public
- Expect 40-60% false positive rate initially (acceptable trade-off)
- Bot is designed to catch every potential insider (prefer false positives)
- Optimized for high-impact trades (>$10k on <5% odds)

## 📚 Technical Details

### API Endpoints Used

**Polymarket:**
- REST API: `https://clob.polymarket.com`
- Gamma API: `https://gamma-api.polymarket.com`
- Markets: `GET /markets`
- Trades: `GET /trades`

**Polygon:**
- RPC: Alchemy/Infura HTTPS endpoint
- Methods: `eth_getTransactionCount`, `eth_getBalance`, `eth_blockNumber`

### Rate Limits

- **Polymarket**: ~60 req/min (free)
- **Alchemy Free**: 25 req/s (~2M/month)
- **Telegram**: 30 msg/s per chat

### Performance

- **Memory**: ~50-100MB
- **CPU**: Minimal (<5% on scan cycles)
- **Disk**: ~10MB/week for database
- **Network**: ~1-5MB/hour

## 🤝 Contributing

This is a personal research project. Feel free to fork and modify!

## 📄 License

MIT License - Use at your own risk

## 🔗 Resources

- [Polymarket API Docs](https://docs.polymarket.com/)
- [Web3.py Documentation](https://web3py.readthedocs.io/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Alchemy Documentation](https://docs.alchemy.com/)

## Sources

- [WSS Overview - Polymarket Documentation](https://docs.polymarket.com/developers/CLOB/websocket/wss-overview)
- [Polymarket Real-Time Data Client](https://github.com/Polymarket/real-time-data-client)
- [Alchemy vs Infura Comparison](https://drpc.org/blog/alchemy-vs-infura/)
- [Top Ethereum RPC Providers 2025](https://chainstack.com/top-ethereum-rpc-providers-for-2025/)
- [List of RPC Node Providers on Polygon](https://www.alchemy.com/dapps/list-of/rpc-node-providers-on-polygon)

---

**Built for detecting potential insider trading patterns on Polymarket prediction markets.**

For issues or questions, check logs first: `tail -f logs/bot_*.log`
