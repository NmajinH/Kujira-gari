"""
Setup validation script

Tests all components to ensure bot is configured correctly.

Usage: python -m polymarket_insider_bot.test_setup
"""
import sys
from datetime import datetime

def test_imports():
    """Test all imports work"""
    print("🔍 Testing imports...")
    try:
        from . import config
        from .database import db, models
        from .api import polymarket, polygon
        from .analyzers import market_analyzer, trade_analyzer, wallet_analyzer
        from .alerts import telegram, formatter
        from .utils import logger, helpers
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_config():
    """Test configuration"""
    print("\n🔍 Testing configuration...")
    try:
        from .config import Config

        print(f"  Telegram Bot Token: {'✅ Set' if Config.TELEGRAM_BOT_TOKEN else '❌ Missing'}")
        print(f"  Telegram Chat ID: {'✅ Set' if Config.TELEGRAM_CHAT_ID else '❌ Missing (run get_chat_id.py)'}")
        print(f"  Polygon RPC URL: {'✅ Set' if Config.POLYGON_RPC_URL else '❌ Missing'}")
        print(f"  Database Path: {Config.DATABASE_PATH}")
        print(f"  Scan Interval: {Config.SCAN_INTERVAL_SECONDS}s")
        print(f"  Min Bet Size: ${Config.MIN_BET_SIZE_USD:,.0f}")

        Config.validate()
        print("✅ Configuration valid")
        return True

    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_database():
    """Test database initialization"""
    print("\n🔍 Testing database...")
    try:
        from .database.db import Database

        db = Database()
        stats = db.get_statistics()

        print(f"  Database created at: {db.db_path}")
        print(f"  Total flagged trades: {stats['total_flagged']}")
        print("✅ Database initialized")
        return True

    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def test_polygon_rpc():
    """Test Polygon RPC connection"""
    print("\n🔍 Testing Polygon RPC...")
    try:
        from .api.polygon import PolygonRPC

        rpc = PolygonRPC()

        if rpc.w3.is_connected():
            block = rpc.w3.eth.block_number
            print(f"  Connected to Polygon")
            print(f"  Current block: {block:,}")
            print("✅ Polygon RPC working")
            return True
        else:
            print("❌ Cannot connect to Polygon RPC")
            return False

    except Exception as e:
        print(f"❌ Polygon RPC error: {e}")
        return False

def test_telegram():
    """Test Telegram bot"""
    print("\n🔍 Testing Telegram...")
    try:
        from .alerts.telegram import TelegramAlertBot

        bot = TelegramAlertBot()

        if bot.test_connection():
            print("✅ Telegram bot working")
            print("  (Check your Telegram for test message)")
            return True
        else:
            print("❌ Telegram connection failed")
            return False

    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return False

def test_polymarket_api():
    """Test Polymarket API"""
    print("\n🔍 Testing Polymarket API...")
    try:
        from .api.polymarket import PolymarketAPI

        api = PolymarketAPI()

        # Try to fetch markets
        markets = api.get_markets(limit=5)

        if markets:
            print(f"  Fetched {len(markets)} markets")
            print(f"  Example market: {markets[0].get('question', 'N/A')[:60]}...")
            print("✅ Polymarket API working")
            return True
        else:
            print("⚠️  Polymarket API returned no markets (may be temporary)")
            return True  # Don't fail, could be temporary

    except Exception as e:
        print(f"❌ Polymarket API error: {e}")
        return False

def test_scoring():
    """Test scoring algorithm"""
    print("\n🔍 Testing scoring algorithm...")
    try:
        from .analyzers.trade_analyzer import TradeAnalyzer

        analyzer = TradeAnalyzer()

        # Test case: Maduro example
        score, flags = analyzer.calculate_suspicion_score(
            bet_size_usd=15089,
            probability=0.018,
            wallet_age_days=3,
            total_trades=1,
            unique_markets=1,
            is_high_risk_category=True,
            recent_cex_funding=True
        )

        print(f"  Test case (Maduro scenario):")
        print(f"  Score: {score}/100")
        print(f"  Tier: {analyzer.determine_alert_tier(score)}")
        print(f"  Flags: {len(flags)}")

        if score >= 90:
            print("✅ Scoring algorithm working correctly")
            return True
        else:
            print(f"⚠️  Score {score} lower than expected (should be 90+)")
            return False

    except Exception as e:
        print(f"❌ Scoring error: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Polymarket Insider Bot - Setup Validation")
    print("=" * 60)
    print()

    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("Database", test_database),
        ("Polygon RPC", test_polygon_rpc),
        ("Telegram", test_telegram),
        ("Polymarket API", test_polymarket_api),
        ("Scoring Algorithm", test_scoring),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} test crashed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    print()
    print(f"Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Bot is ready to run.")
        print("\nStart the bot with:")
        print("  python -m polymarket_insider_bot.main")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
        return 1

def main():
    """Entry point"""
    sys.exit(run_all_tests())

if __name__ == '__main__':
    main()
