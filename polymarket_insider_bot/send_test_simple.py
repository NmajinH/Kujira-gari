"""
Simple test alert sender using requests library only
"""
import requests
from datetime import datetime

TELEGRAM_BOT_TOKEN = "8523896394:AAETPrSCbHB58cyiqDU1PTlSObAsljczVvw"
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def get_chat_id():
    """Get chat ID from bot updates"""
    try:
        response = requests.get(f"{BASE_URL}/getUpdates", timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get('ok') or not data.get('result'):
            print("❌ No messages found!")
            print("\nPlease:")
            print("1. Open Telegram")
            print("2. Search for your bot")
            print("3. Send any message (e.g., 'hello')")
            print("4. Run this script again")
            return None

        # Get latest message
        updates = data['result']
        if not updates:
            print("❌ No updates found!")
            return None

        chat_id = updates[-1]['message']['chat']['id']
        print(f"✅ Found chat ID: {chat_id}")
        return chat_id

    except Exception as e:
        print(f"❌ Error getting chat ID: {e}")
        return None

def send_message(chat_id, text):
    """Send message via Telegram API"""
    try:
        payload = {
            'chat_id': chat_id,
            'text': text,
            'disable_web_page_preview': True
        }
        response = requests.post(f"{BASE_URL}/sendMessage", json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get('ok'):
            print("✅ Message sent successfully!")
            return True
        else:
            print(f"❌ Failed: {data.get('description')}")
            return False

    except Exception as e:
        print(f"❌ Error sending message: {e}")
        return False

def main():
    """Main function"""
    print("=" * 60)
    print("Telegram Bot Test - Sending Alert")
    print("=" * 60)
    print()

    # Test bot connection
    try:
        response = requests.get(f"{BASE_URL}/getMe", timeout=10)
        response.raise_for_status()
        bot_info = response.json()

        if bot_info.get('ok'):
            username = bot_info['result']['username']
            print(f"✅ Connected to bot: @{username}")
            print()
        else:
            print("❌ Bot connection failed")
            return
    except Exception as e:
        print(f"❌ Failed to connect to bot: {e}")
        return

    # Get chat ID
    print("🔍 Looking for your chat ID...")
    chat_id = get_chat_id()

    if not chat_id:
        return

    print()

    # Create test alert
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

    # Send test alert
    print("📤 Sending test alert...")
    success = send_message(chat_id, test_alert)

    print()
    print("=" * 60)

    if success:
        print("✅ SUCCESS!")
        print()
        print("Your Telegram bot is working correctly!")
        print(f"Your Chat ID: {chat_id}")
        print()
        print("To use the bot, create a .env file:")
        print(f"TELEGRAM_CHAT_ID={chat_id}")
        print("TELEGRAM_BOT_TOKEN=8523896394:AAETPrSCbHB58cyiqDU1PTlSObAsljczVvw")
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
