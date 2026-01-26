# How to Test Your Telegram Bot Connection

## The Issue

I cannot send test messages from this environment due to network restrictions. However, I've prepared everything you need to test the bot on your local machine.

---

## Quick Test (3 Steps)

### Step 1: Message Your Bot

1. Open Telegram
2. Search for your bot (using the token: `8523896394:AAETPrSCbHB58cyiqDU1PTlSObAsljczVvw`)
3. Send any message like "hello" or "test"

### Step 2: Run the Test Script

Download the repository and run:

```bash
cd polymarket_insider_bot
python send_test_simple.py
```

### Step 3: Check Telegram

You should receive a **CRITICAL ALERT** test message that looks like this:

```
🚨 CRITICAL ALERT - TEST MESSAGE (Score: 95/100)

Market: "Maduro out by Feb 28, 2026?"
🔗 https://polymarket.com/event/maduro-2026

💰 Bet Details:
├─ Size: $15,089
├─ Odds: 1.8% (YES)
├─ Expected Profit: $82,276
└─ Potential Return: 5.5x

👛 Wallet: 0xSBet365...4bf2
├─ Age: 3 days old
├─ Total Trades: 1
├─ Polymarket Markets: 1
└─ Concentration: 100% (single market)

⚠️ RED FLAGS:
• Brand new wallet (<7 days) ✓
• Fresh CEX funding (23h ago) ✓
• Single-market activity ✓
• Geopolitical market (high insider risk) ✓

📊 Market Context:
├─ Category: Politics & Geopolitics
├─ Volume: $2,300,000
└─ Resolution: Feb 28, 2026

⏰ Detected: 2026-01-26 20:15:32 UTC

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 This is a TEST ALERT to verify your bot is working!
✅ If you received this, your Polymarket Insider Detection Bot is properly configured!
```

---

## Alternative: Manual Test via Browser

If you want to test RIGHT NOW without downloading anything:

### 1. First, get your Chat ID:

Open this URL in your browser (replace the token if different):
```
https://api.telegram.org/bot8523896394:AAETPrSCbHB58cyiqDU1PTlSObAsljczVvw/getUpdates
```

Look for `"chat":{"id":XXXXXXXXX` - that's your chat ID.

### 2. Then send a test message:

Open this URL (replace YOUR_CHAT_ID with the number from step 1):
```
https://api.telegram.org/bot8523896394:AAETPrSCbHB58cyiqDU1PTlSObAsljczVvw/sendMessage?chat_id=YOUR_CHAT_ID&text=Test%20message%20from%20bot!
```

You should see:
```json
{"ok":true,"result":{"message_id":...}}
```

And receive the message in Telegram!

---

## Using cURL (For Power Users)

If you have curl installed:

```bash
# Get your chat ID
curl "https://api.telegram.org/bot8523896394:AAETPrSCbHB58cyiqDU1PTlSObAsljczVvw/getUpdates"

# Send a test message (replace YOUR_CHAT_ID)
curl -X POST "https://api.telegram.org/bot8523896394:AAETPrSCbHB58cyiqDU1PTlSObAsljczVvw/sendMessage" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": YOUR_CHAT_ID, "text": "🎯 Test alert from bot!"}'
```

---

## What to Expect

✅ **Success looks like:**
```
✅ Connected to bot: @your_bot_name
✅ Found chat ID: 123456789
✅ Message sent successfully!

Your Chat ID: 123456789
```

❌ **Failure looks like:**
```
❌ No messages found!

Please:
1. Open Telegram
2. Search for your bot
3. Send any message (e.g., 'hello')
4. Run this script again
```

---

## Next Steps After Successful Test

Once you confirm the bot is working:

1. **Create .env file:**
```bash
cd polymarket_insider_bot
cp .env.example .env
nano .env
```

2. **Add your Chat ID:**
```bash
TELEGRAM_CHAT_ID=your_chat_id_here  # From test output
TELEGRAM_BOT_TOKEN=8523896394:AAETPrSCbHB58cyiqDU1PTlSObAsljczVvw
POLYGON_RPC_URL=https://polygon-rpc.com  # Or your Alchemy URL
```

3. **Start the bot:**
```bash
python -m polymarket_insider_bot.main
```

You'll immediately receive a health check message!

---

## Troubleshooting

### "Bot not found"
- The token might be incorrect
- The bot might have been deleted by BotFather

### "No messages found"
- You need to message the bot FIRST on Telegram
- Then run the test script

### "Unauthorized"
- Check the bot token is correct
- Make sure there are no extra spaces

### "Chat not found"
- The chat ID might be wrong
- Make sure you got the ID from the /getUpdates response

---

## Files Included

I've created two test scripts for you:

1. **send_test_simple.py** - Uses only `requests` library (simpler)
2. **send_test_alert.py** - Uses `python-telegram-bot` library (more features)

Both do the same thing - send a test alert to verify connectivity.

---

**Ready to test?** Just run:
```bash
python polymarket_insider_bot/send_test_simple.py
```

(After messaging your bot on Telegram first!)
