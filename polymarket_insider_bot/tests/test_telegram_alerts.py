"""
Telegram Alert Tests

Sends sample alerts to your Telegram to verify:
- Alert formatting is correct
- Message delivery works
- All alert tiers display properly

Run this AFTER test_api_connections.py passes.

Usage: python -m polymarket_insider_bot.tests.test_telegram_alerts
"""
import sys
import os
from pathlib import Path
import time
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8523896394:AAETPrSCbHB58cyiqDU1PTlSObAsljczVvw')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

def send_telegram_message(text):
    """Send message to Telegram"""
    if not TELEGRAM_CHAT_ID:
        print("❌ TELEGRAM_CHAT_ID not configured in .env")
        print("   Run: python -m polymarket_insider_bot.utils.get_chat_id")
        return False

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                'chat_id': TELEGRAM_CHAT_ID,
                'text': text,
                'disable_web_page_preview': True
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        if data.get('ok'):
            return True
        else:
            print(f"❌ Telegram API error: {data.get('description', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"❌ Failed to send message: {str(e)}")
        return False

def format_critical_alert():
    """Format CRITICAL alert (score 95)"""
    return """🚨 CRITICAL ALERT - TEST (Score: 95/100)

Market: "Maduro out by Feb 28, 2026?"
🔗 https://polymarket.com/event/maduro-2026

💰 Bet Details:
├─ Size: $15,089
├─ Odds: 1.8% (YES)
├─ Expected Profit: $823,189
└─ Potential Return: 55.6x

👛 Wallet: 0xSBet365a...01234bf2
├─ Age: 3.0 days old
├─ Total Trades: 1
├─ Polymarket Markets: 1
└─ Concentration: 100% (single market)

⚠️ RED FLAGS:
• Massive bet ($15,089) ✓
• Extreme longshot (1.8%) ✓
• New wallet (3.0 days) ✓
• Very low activity (1 trades) ✓
• Single market activity ✓
• High-risk category (geopolitics) ✓
• Recent CEX funding (<48h) ✓

📊 Market Context:
├─ Category: Politics & Geopolitics
├─ Volume: $2,300,000
└─ Resolution: Feb 28, 2026

⏰ Detected: """ + datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S') + """ UTC

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 This is a TEST ALERT
"""

def format_high_alert():
    """Format HIGH alert (score 75)"""
    return """⚠️ HIGH ALERT - TEST (Score: 75/100)

Market: "Apple announces Vision Pro 2 by June 2026"
🔗 https://polymarket.com/event/apple-vision-pro-2

💰 Bet Details:
├─ Size: $22,500
├─ Odds: 8.5% (YES)
├─ Expected Profit: $242,059
└─ Potential Return: 11.8x

👛 Wallet: 0xTech987...def456gh
├─ Age: 5.5 days old
├─ Total Trades: 3
├─ Polymarket Markets: 2
└─ Concentration: 67% (focused)

⚠️ RED FLAGS:
• Large bet ($22,500) ✓
• Very low odds (8.5%) ✓
• New wallet (5.5 days) ✓
• Low activity (3 trades) ✓
• High-risk category (tech) ✓

📊 Market Context:
├─ Category: Tech
├─ Volume: $1,450,000
└─ Resolution: Jun 30, 2026

⏰ Detected: """ + datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S') + """ UTC

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 This is a TEST ALERT
"""

def format_medium_alert():
    """Format MEDIUM alert (score 55)"""
    return """📊 MEDIUM ALERT - TEST (Score: 55/100)

Market: "Trump DOJ charges Biden family member"
🔗 https://polymarket.com/event/trump-doj-charges

💰 Bet Details:
├─ Size: $12,800
├─ Odds: 18.2% (YES)
├─ Expected Profit: $58,549
└─ Potential Return: 5.5x

👛 Wallet: 0xPolitix...789abc12
├─ Age: 6.2 days old
├─ Total Trades: 8
├─ Polymarket Markets: 5
└─ Concentration: 62% (moderate)

⚠️ RED FLAGS:
• Significant bet ($12,800) ✓
• Below 20% odds (18.2%) ✓
• New wallet (6.2 days) ✓
• Low activity (8 trades) ✓
• High-risk category (politics) ✓

📊 Market Context:
├─ Category: Politics
├─ Volume: $890,000
└─ Resolution: Mar 15, 2026

⏰ Detected: """ + datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S') + """ UTC

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 This is a TEST ALERT
"""

def send_all_test_alerts():
    """Send all three alert types"""
    print("\n" + "="*60)
    print("  TELEGRAM ALERT TESTS")
    print("="*60 + "\n")

    if not TELEGRAM_CHAT_ID:
        print("❌ TELEGRAM_CHAT_ID not configured")
        print("\nTo get your Chat ID:")
        print("  1. Message your bot on Telegram")
        print("  2. Run: python -m polymarket_insider_bot.utils.get_chat_id")
        print("  3. Add Chat ID to .env file")
        print()
        return False

    print(f"Sending test alerts to Chat ID: {TELEGRAM_CHAT_ID}")
    print()

    # Test 1: CRITICAL Alert
    print("[1/3] Sending CRITICAL alert (score 95)...")
    if send_telegram_message(format_critical_alert()):
        print("✅ CRITICAL alert sent")
    else:
        print("❌ CRITICAL alert failed")
        return False

    time.sleep(2)  # Delay between messages

    # Test 2: HIGH Alert
    print("\n[2/3] Sending HIGH alert (score 75)...")
    if send_telegram_message(format_high_alert()):
        print("✅ HIGH alert sent")
    else:
        print("❌ HIGH alert failed")
        return False

    time.sleep(2)  # Delay between messages

    # Test 3: MEDIUM Alert
    print("\n[3/3] Sending MEDIUM alert (score 55)...")
    if send_telegram_message(format_medium_alert()):
        print("✅ MEDIUM alert sent")
    else:
        print("❌ MEDIUM alert failed")
        return False

    # Summary
    print("\n" + "="*60)
    print("✅ ALL ALERTS SENT SUCCESSFULLY!")
    print("="*60 + "\n")
    print("📱 Check your Telegram for 3 test messages")
    print()
    print("Verify:")
    print("  • Formatting looks correct")
    print("  • Emojis display properly")
    print("  • All information is readable")
    print("  • Different tiers are distinguishable")
    print()
    print("Next step:")
    print("  python -m polymarket_insider_bot.tests.test_polymarket_live_data")
    print()

    return True

if __name__ == '__main__':
    success = send_all_test_alerts()
    sys.exit(0 if success else 1)
