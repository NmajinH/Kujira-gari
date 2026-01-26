"""
Send a test alert to verify Telegram bot connection

This script will:
1. Get your chat ID automatically (if you've messaged the bot)
2. Send a test CRITICAL alert with sample data
3. Verify the bot is working
"""
import sys
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError

# Bot token
TELEGRAM_BOT_TOKEN = "8523896394:AAETPrSCbHB58cyiqDU1PTlSObAsljczVvw"

def get_chat_id():
    """Get chat ID from bot updates"""
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        updates = bot.get_updates()

        if not updates:
            print("❌ No messages found!")
            print("\nPlease:")
            print("1. Open Telegram")
            print("2. Search for your bot")
            print("3. Send any message (e.g., 'hello')")
            print("4. Run this script again")
            return None

        chat_id = updates[-1].message.chat_id
        print(f"✅ Found chat ID: {chat_id}")
        return chat_id

    except Exception as e:
        print(f"❌ Error getting chat ID: {e}")
        return None

def send_test_alert(bot, chat_id):
    """Send a test CRITICAL alert"""

    test_alert = """🚨 CRITICAL ALERT - TEST MESSAGE (Score: 95/100)

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

⏰ Detected: {timestamp} UTC

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 This is a TEST ALERT to verify your bot is working!
✅ If you received this, your Polymarket Insider Detection Bot is properly configured!
""".format(timestamp=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))

    try:
        bot.send_message(
            chat_id=chat_id,
            text=test_alert,
            disable_web_page_preview=True
        )
        print("\n✅ Test alert sent successfully!")
        print(f"✅ Check your Telegram for the message")
        return True

    except TelegramError as e:
        print(f"\n❌ Failed to send message: {e}")
        return False

def main():
    """Main function"""
    print("=" * 60)
    print("Telegram Bot Test - Sending Alert")
    print("=" * 60)
    print()

    # Connect to bot
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        bot_info = bot.get_me()
        print(f"✅ Connected to bot: @{bot_info.username}")
        print()
    except Exception as e:
        print(f"❌ Failed to connect to bot: {e}")
        sys.exit(1)

    # Get chat ID
    print("🔍 Looking for your chat ID...")
    chat_id = get_chat_id()

    if not chat_id:
        sys.exit(1)

    print()

    # Send test alert
    print("📤 Sending test alert...")
    success = send_test_alert(bot, chat_id)

    print()
    print("=" * 60)

    if success:
        print("✅ SUCCESS!")
        print()
        print("Your Telegram bot is working correctly!")
        print(f"Your Chat ID: {chat_id}")
        print()
        print("Add this to your .env file:")
        print(f"TELEGRAM_CHAT_ID={chat_id}")
        print()
        print("Then you can start the bot with:")
        print("  python -m polymarket_insider_bot.main")
    else:
        print("❌ FAILED")
        print()
        print("Please check:")
        print("- Bot token is correct")
        print("- You have messaged the bot on Telegram")
        print("- Your internet connection is working")

    print("=" * 60)

if __name__ == '__main__':
    main()
