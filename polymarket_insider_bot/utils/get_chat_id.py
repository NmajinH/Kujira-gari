"""
Utility script to get Telegram chat ID

Usage:
1. Message your bot on Telegram first (send any message)
2. Run: python -m polymarket_insider_bot.utils.get_chat_id
"""
import os
import sys
from telegram import Bot
from dotenv import load_dotenv

def main():
    """Get chat ID from bot updates"""
    load_dotenv()

    token = os.getenv('TELEGRAM_BOT_TOKEN')

    if not token:
        print("❌ Error: TELEGRAM_BOT_TOKEN not found in .env file")
        print("\nPlease add your bot token to .env:")
        print("TELEGRAM_BOT_TOKEN=your_token_here")
        sys.exit(1)

    try:
        bot = Bot(token=token)

        print("🔍 Checking for messages...")
        print("(Make sure you've sent a message to the bot first!)")
        print()

        updates = bot.get_updates()

        if not updates:
            print("❌ No messages found!")
            print("\nSteps to fix:")
            print("1. Open Telegram")
            print("2. Search for your bot")
            print("3. Send any message to it (e.g., '/start' or 'hello')")
            print("4. Run this script again")
            sys.exit(1)

        # Get latest update
        latest_update = updates[-1]
        chat_id = latest_update.message.chat_id

        print("✅ Success!")
        print(f"\nYour Chat ID: {chat_id}")
        print("\nAdd this to your .env file:")
        print(f"TELEGRAM_CHAT_ID={chat_id}")
        print()

        # Test sending a message
        bot.send_message(
            chat_id=chat_id,
            text="✅ Chat ID found successfully!\n\nYou can now start the bot."
        )

        print("✅ Test message sent to your Telegram!")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
