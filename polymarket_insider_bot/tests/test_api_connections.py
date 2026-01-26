"""
API Connection Tests

Tests real connectivity to:
- Telegram Bot API
- Polymarket API
- Polygon RPC

Run this FIRST before running the main bot to verify all APIs work.

Usage: python -m polymarket_insider_bot.tests.test_api_connections
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import requests
from web3 import Web3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8523896394:AAETPrSCbHB58cyiqDU1PTlSObAsljczVvw')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
POLYGON_RPC_URL = os.getenv('POLYGON_RPC_URL', 'https://polygon-rpc.com')
POLYMARKET_API_URL = "https://gamma-api.polymarket.com"

def print_header():
    """Print test header"""
    print("\n" + "="*60)
    print("  API CONNECTION TESTS")
    print("="*60 + "\n")

def print_result(service, success, message):
    """Print test result"""
    icon = "✅" if success else "❌"
    print(f"{icon} {service}: {message}")

def test_telegram_connection():
    """Test Telegram Bot API connection"""
    print("Testing Telegram Bot...")

    try:
        # Test bot connection
        response = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe",
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        if not data.get('ok'):
            print_result("Telegram", False, f"API error: {data.get('description', 'Unknown error')}")
            return False

        bot_username = data['result']['username']

        # Try to send test message if chat ID is configured
        if TELEGRAM_CHAT_ID:
            try:
                test_msg = "🧪 API Connection Test - Your bot is working!"
                response = requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={
                        'chat_id': TELEGRAM_CHAT_ID,
                        'text': test_msg
                    },
                    timeout=10
                )
                response.raise_for_status()

                if response.json().get('ok'):
                    print_result("Telegram", True, f"Connected to @{bot_username} - Test message sent!")
                    return True
                else:
                    print_result("Telegram", False, f"Connected to @{bot_username} but couldn't send message")
                    return False
            except Exception as e:
                print_result("Telegram", False, f"Connected to @{bot_username} but send failed: {str(e)}")
                return False
        else:
            print_result("Telegram", True, f"Connected to @{bot_username} (no Chat ID to test sending)")
            print("   ℹ️  Set TELEGRAM_CHAT_ID in .env to test message sending")
            return True

    except requests.exceptions.RequestException as e:
        print_result("Telegram", False, f"Connection failed: {str(e)}")
        return False
    except Exception as e:
        print_result("Telegram", False, f"Unexpected error: {str(e)}")
        return False

def test_polymarket_connection():
    """Test Polymarket API connection"""
    print("\nTesting Polymarket API...")

    try:
        # Fetch active markets
        response = requests.get(
            f"{POLYMARKET_API_URL}/markets",
            params={'limit': 10, 'active': 'true'},
            timeout=15
        )
        response.raise_for_status()
        data = response.json()

        # Handle different response formats
        if isinstance(data, list):
            markets = data
        elif isinstance(data, dict) and 'data' in data:
            markets = data['data']
        else:
            print_result("Polymarket", False, "Unexpected response format")
            return False

        market_count = len(markets)

        if market_count > 0:
            print_result("Polymarket", True, f"Connected - Found {market_count} active markets")

            # Show sample market
            sample = markets[0]
            market_name = sample.get('question') or sample.get('title', 'Unknown')
            print(f"   ℹ️  Sample market: \"{market_name[:60]}...\"")
            return True
        else:
            print_result("Polymarket", False, "Connected but no markets found")
            return False

    except requests.exceptions.RequestException as e:
        print_result("Polymarket", False, f"Connection failed: {str(e)}")
        return False
    except Exception as e:
        print_result("Polymarket", False, f"Unexpected error: {str(e)}")
        return False

def test_polygon_rpc_connection():
    """Test Polygon RPC connection"""
    print("\nTesting Polygon RPC...")

    try:
        # Connect to RPC
        w3 = Web3(Web3.HTTPProvider(POLYGON_RPC_URL))

        if not w3.is_connected():
            print_result("Polygon RPC", False, "Cannot connect to RPC endpoint")
            print(f"   ℹ️  RPC URL: {POLYGON_RPC_URL}")
            return False

        # Get latest block
        block_number = w3.eth.block_number

        # Test querying a wallet (Polymarket contract address)
        test_address = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"  # Polymarket CLOB
        balance = w3.eth.get_balance(test_address)

        print_result("Polygon RPC", True, f"Connected - Block #{block_number:,}")
        print(f"   ℹ️  RPC Provider: {POLYGON_RPC_URL}")
        return True

    except Exception as e:
        print_result("Polygon RPC", False, f"Connection failed: {str(e)}")
        print(f"   ℹ️  RPC URL: {POLYGON_RPC_URL}")
        return False

def check_environment():
    """Check environment variables"""
    print("Checking environment variables...")

    issues = []

    if not TELEGRAM_BOT_TOKEN:
        issues.append("TELEGRAM_BOT_TOKEN not set")

    if not TELEGRAM_CHAT_ID:
        issues.append("TELEGRAM_CHAT_ID not set (optional but recommended)")

    if not POLYGON_RPC_URL:
        issues.append("POLYGON_RPC_URL not set")

    if issues:
        print("⚠️  Configuration issues:")
        for issue in issues:
            print(f"   - {issue}")
        print("\nCheck your .env file")
        return False

    print("✅ Environment variables configured\n")
    return True

def run_all_tests():
    """Run all connection tests"""
    print_header()

    # Check environment
    env_ok = check_environment()
    if not env_ok:
        print("\n" + "="*60)
        print("⚠️  Fix environment variables before running tests")
        print("="*60 + "\n")
        return False

    # Run tests
    results = {
        'telegram': test_telegram_connection(),
        'polymarket': test_polymarket_connection(),
        'polygon': test_polygon_rpc_connection()
    }

    # Summary
    print("\n" + "="*60)
    passed = sum(results.values())
    total = len(results)

    if passed == total:
        print("✅ ALL TESTS PASSED - Ready to run bot!")
        print("="*60 + "\n")
        print("Next steps:")
        print("  1. Run: python -m polymarket_insider_bot.tests.test_telegram_alerts")
        print("  2. Run: python -m polymarket_insider_bot.tests.test_polymarket_live_data")
        print("  3. Run: python -m polymarket_insider_bot.main")
        print()
        return True
    else:
        print(f"❌ {total - passed}/{total} TESTS FAILED")
        print("="*60 + "\n")

        if not results['telegram']:
            print("Telegram failed:")
            print("  - Check TELEGRAM_BOT_TOKEN in .env")
            print("  - Get Chat ID: python -m polymarket_insider_bot.utils.get_chat_id")
            print()

        if not results['polymarket']:
            print("Polymarket failed:")
            print("  - Check your internet connection")
            print("  - Polymarket API may be temporarily down")
            print()

        if not results['polygon']:
            print("Polygon RPC failed:")
            print("  - Check POLYGON_RPC_URL in .env")
            print("  - Get free RPC from alchemy.com")
            print("  - Try public RPC: https://polygon-rpc.com")
            print()

        return False

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
