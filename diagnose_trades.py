#!/usr/bin/env python3
"""
DIAGNOSTIC SCRIPT - Run this on your machine to see what's wrong

This will:
1. Fetch real trades from Data API
2. Show the exact JSON structure
3. Test parse_trade() function
4. Identify why bet sizes are 0
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from polymarket_insider_bot.api.polymarket import PolymarketAPI
import json

def main():
    print("="*80)
    print("DIAGNOSTIC: Testing Data API and parse_trade()")
    print("="*80)

    api = PolymarketAPI()

    # Fetch 10 trades
    print("\n[1] Fetching 10 trades from Data API...")
    raw_trades = api.get_trades_from_data_api(limit=10)
    print(f"    Fetched: {len(raw_trades)} trades")

    if not raw_trades:
        print("    ❌ No trades returned - API might be down")
        return

    # Show first trade structure
    print("\n[2] First trade RAW JSON:")
    print(json.dumps(raw_trades[0], indent=2))

    # Test parsing on all trades
    print("\n[3] Testing parse_trade() on all fetched trades:")
    print("-"*80)

    parsed_count = 0
    failed_count = 0
    total_size = 0

    for i, raw_trade in enumerate(raw_trades):
        print(f"\nTrade {i+1}:")
        print(f"  Raw 'size' field: {raw_trade.get('size')}")
        print(f"  Raw 'size' type: {type(raw_trade.get('size'))}")

        parsed = api.parse_trade(raw_trade)

        if parsed:
            parsed_count += 1
            print(f"  ✅ Parsed successfully")
            print(f"     - bet_size_usd: ${parsed['bet_size_usd']:,.2f}")
            print(f"     - probability: {parsed['probability']:.4f}")
            print(f"     - wallet: {parsed['wallet_address'][:20]}...")
            total_size += parsed['bet_size_usd']
        else:
            failed_count += 1
            print(f"  ❌ Parsing FAILED")

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Parsed successfully: {parsed_count}/{len(raw_trades)}")
    print(f"Failed to parse: {failed_count}/{len(raw_trades)}")
    print(f"Average bet size: ${total_size/max(parsed_count,1):,.2f}")
    print(f"\nTrades >= $1,000: {sum(1 for t in raw_trades if api.parse_trade(t) and api.parse_trade(t)['bet_size_usd'] >= 1000)}")
    print(f"Trades >= $10,000: {sum(1 for t in raw_trades if api.parse_trade(t) and api.parse_trade(t)['bet_size_usd'] >= 10000)}")

    # Show all field names from first trade
    print("\n[4] All available fields in first trade:")
    for key in raw_trades[0].keys():
        value = raw_trades[0][key]
        if isinstance(value, (str, int, float, bool)):
            print(f"    {key}: {value}")
        else:
            print(f"    {key}: <{type(value).__name__}>")

if __name__ == '__main__':
    main()
