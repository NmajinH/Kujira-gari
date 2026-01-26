"""
Utility script to get Telegram chat ID

This script helps you find your Telegram chat ID so you can receive alerts.

Usage:
1. Message your bot on Telegram first (send any message like "hello")
2. Run: python -m polymarket_insider_bot.utils.get_chat_id
3. Copy the Chat ID to your .env file

Bot Token: 8523896394:AAETPrSCbHB58cyiqDU1PTlSObAsljczVvw
"""
import os
import sys
import requests
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

def get_chat_id():
    """Get chat ID from bot updates"""
    load_dotenv()

    token = os.getenv('TELEGRAM_BOT_TOKEN', '8523896394:AAETPrSCbHB58cyiqDU1PTlSObAsljczVvw')

    print("\n" + "="*60)
    print("  TELEGRAM CHAT ID FINDER")
    print("="*60 + "\n")

    print(f"Using bot token: {token[:20]}...")
    print()

    try:
        # Get bot info
        print("🔍 Connecting to Telegram...")
        response = requests.get(
            f"https://api.telegram.org/bot{token}/getMe",
            timeout=10
        )
        response.raise_for_status()
        bot_info = response.json()

        if not bot_info.get('ok'):
            print(f"❌ Bot error: {bot_info.get('description', 'Unknown error')}")
            print("\nCheck your TELEGRAM_BOT_TOKEN in .env")
            return None

        bot_username = bot_info['result']['username']
        print(f"✅ Connected to bot: @{bot_username}\n")

        # Get updates (messages sent to bot)
        print("🔍 Checking for messages...")
        print("   (Make sure you've messaged the bot first!)\n")

        response = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            timeout=10
        )
        response.raise_for_status()
        updates = response.json()

        if not updates.get('ok'):
            print(f"❌ API error: {updates.get('description', 'Unknown error')}")
            return None

        messages = updates.get('result', [])

        if not messages:
            print("❌ No messages found!\n")
            print("Steps to fix:")
            print("  1. Open Telegram")
            print(f"  2. Search for @{bot_username}")
            print("  3. Send any message to it (e.g., 'hello' or '/start')")
            print("  4. Run this script again\n")
            print("Or visit this URL in your browser:")
            print(f"  https://t.me/{bot_username}")
            return None

        # Get latest message
        latest_message = messages[-1]
        chat_id = latest_message['message']['chat']['id']
        username = latest_message['message']['chat'].get('username', 'Unknown')

        print("✅ Chat ID found!\n")
        print("="*60)
        print(f"  YOUR CHAT ID: {chat_id}")
        print("="*60 + "\n")

        print(f"Chat info:")
        print(f"  • Chat ID: {chat_id}")
        print(f"  • Username: @{username}")
        print(f"  • Bot: @{bot_username}")
        print()

        # Send confirmation message
        print("📤 Sending test message...")
        test_msg = f"✅ Chat ID found successfully!\n\nYour Chat ID: {chat_id}\n\nYou can now add this to your .env file and start the bot."

        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                'chat_id': chat_id,
                'text': test_msg
            },
            timeout=10
        )

        if response.json().get('ok'):
            print("✅ Test message sent!\n")
        else:
            print("⚠️  Could not send test message\n")

        # Instructions
        print("="*60)
        print("  NEXT STEPS")
        print("="*60 + "\n")

        print("1. Add this to your .env file:")
        print(f"   TELEGRAM_CHAT_ID={chat_id}\n")

        print("2. Your .env should look like:")
        print(f"   TELEGRAM_BOT_TOKEN={token}")
        print(f"   TELEGRAM_CHAT_ID={chat_id}")
        print("   POLYGON_RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY\n")

        print("3. Run the test suite:")
        print("   python -m polymarket_insider_bot.tests.test_api_connections\n")

        return chat_id

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {str(e)}")
        print("\nCheck your internet connection")
        return None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main entry point"""
    chat_id = get_chat_id()

    if chat_id:
        print("="*60)
        print("✅ SUCCESS - Chat ID retrieved!")
        print("="*60 + "\n")
        sys.exit(0)
    else:
        print("="*60)
        print("❌ FAILED - Could not get Chat ID")
        print("="*60 + "\n")
        sys.exit(1)

if __name__ == '__main__':
    main()
