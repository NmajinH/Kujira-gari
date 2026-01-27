#!/usr/bin/env python3
"""
Test REAL Data API access and parse_trade() function
This will show us the actual data format and verify parsing works
"""
import requests
import json
from datetime import datetime

def test_data_api_access():
    """Test if Data API is accessible and returns real trade data"""
    print("="*80)
    print("TESTING POLYMARKET DATA API - LIVE ACCESS")
    print("="*80)

    url = "https://data-api.polymarket.com/trades"

    print(f"\n[1] Testing endpoint: {url}")
    print("    Parameters: limit=10")

    try:
        response = requests.get(url, params={'limit': 10}, timeout=15)
        print(f"    Status Code: {response.status_code}")

        if response.status_code != 200:
            print(f"    ❌ FAILED: {response.text[:200]}")
            return None

        trades = response.json()
        print(f"    ✅ SUCCESS: Fetched {len(trades)} trades")

        return trades

    except Exception as e:
        print(f"    ❌ EXCEPTION: {e}")
        return None

def analyze_trade_structure(trades):
    """Analyze the actual structure of returned trades"""
    if not trades:
        print("\n❌ No trades to analyze")
        return

    print("\n" + "="*80)
    print("ANALYZING TRADE DATA STRUCTURE")
    print("="*80)

    print(f"\n[2] Total trades returned: {len(trades)}")
    print(f"    Type: {type(trades)}")

    if len(trades) > 0:
        first_trade = trades[0]
        print(f"\n[3] First trade structure:")
        print(f"    Type: {type(first_trade)}")
        print(f"    Keys: {list(first_trade.keys())}")

        print(f"\n[4] Full first trade (formatted):")
        print(json.dumps(first_trade, indent=2)[:1500])

        # Analyze critical fields
        print(f"\n[5] Critical field analysis:")

        # Trade ID
        trade_id = first_trade.get('id')
        print(f"    ✓ Trade ID: {trade_id}")

        # Wallet address
        user = first_trade.get('user')
        proxy = first_trade.get('proxyWallet')
        print(f"    ✓ User: {user}")
        print(f"    ✓ ProxyWallet: {proxy}")

        # Bet size (THIS IS THE CRITICAL ONE)
        size = first_trade.get('size')
        print(f"    ✓ Size (raw): {size}")
        print(f"    ✓ Size (type): {type(size)}")

        if size:
            try:
                size_float = float(size)
                size_usd = size_float / 1e6
                print(f"    ✓ Size (converted): ${size_usd:,.2f} USD")
            except:
                print(f"    ❌ Size conversion FAILED")

        # Price/probability
        price = first_trade.get('price')
        print(f"    ✓ Price: {price}")

        # Market ID
        condition_id = first_trade.get('conditionId')
        print(f"    ✓ ConditionId: {condition_id}")

        # Side
        side = first_trade.get('side')
        print(f"    ✓ Side: {side}")

        # Timestamp
        timestamp = first_trade.get('timestamp')
        print(f"    ✓ Timestamp: {timestamp}")

        # Show 3 more trades for pattern verification
        print(f"\n[6] Analyzing size field across multiple trades:")
        for i, trade in enumerate(trades[:5]):
            size = trade.get('size')
            try:
                size_usd = float(size) / 1e6
                print(f"    Trade {i+1}: size={size} → ${size_usd:,.2f} USD")
            except:
                print(f"    Trade {i+1}: size={size} → CONVERSION FAILED")

def test_parse_trade_function(trades):
    """Test the actual parse_trade() function from the bot"""
    if not trades:
        print("\n❌ No trades to test parsing")
        return

    print("\n" + "="*80)
    print("TESTING PARSE_TRADE() FUNCTION")
    print("="*80)

    # Import the actual parse_trade function from the bot
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent))
        from polymarket_insider_bot.api.polymarket import PolymarketAPI

        api = PolymarketAPI()

        print(f"\n[7] Testing parse_trade() on {len(trades[:5])} trades:")

        successful = 0
        failed = 0

        for i, trade_raw in enumerate(trades[:5]):
            parsed = api.parse_trade(trade_raw)

            if parsed:
                successful += 1
                print(f"\n    ✅ Trade {i+1} parsed successfully:")
                print(f"       - Trade ID: {parsed['trade_id']}")
                print(f"       - Wallet: {parsed['wallet_address'][:10]}...")
                print(f"       - Bet Size: ${parsed['bet_size_usd']:,.2f} USD")
                print(f"       - Probability: {parsed['probability']:.2%}")
                print(f"       - Market ID: {parsed['market_id'][:20] if parsed['market_id'] else 'None'}...")
                print(f"       - Outcome: {parsed['outcome']}")
                print(f"       - Timestamp: {parsed['timestamp']}")
            else:
                failed += 1
                print(f"\n    ❌ Trade {i+1} parsing FAILED")

        print(f"\n[8] Parsing Summary:")
        print(f"    ✅ Successful: {successful}/5")
        print(f"    ❌ Failed: {failed}/5")

        # Test filtering by size
        print(f"\n[9] Testing size filtering (>= $1,000 USD):")
        large_trades = []
        for trade_raw in trades:
            parsed = api.parse_trade(trade_raw)
            if parsed and parsed['bet_size_usd'] >= 1000:
                large_trades.append(parsed)

        print(f"    Found {len(large_trades)} trades >= $1,000 USD out of {len(trades)} total")

        if large_trades:
            print(f"\n    Sample large trades:")
            for trade in large_trades[:3]:
                print(f"    - ${trade['bet_size_usd']:,.2f} @ {trade['probability']:.2%} odds")

        return successful, failed

    except Exception as e:
        print(f"\n❌ Error testing parse_trade(): {e}")
        import traceback
        traceback.print_exc()
        return 0, 5

def main():
    """Run all tests"""

    # Step 1: Access Data API
    trades = test_data_api_access()

    if not trades:
        print("\n" + "="*80)
        print("❌ DATA API ACCESS FAILED - Cannot proceed with further tests")
        print("="*80)
        return

    # Step 2: Analyze structure
    analyze_trade_structure(trades)

    # Step 3: Test parsing
    test_parse_trade_function(trades)

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

if __name__ == '__main__':
    main()
