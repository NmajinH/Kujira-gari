#!/usr/bin/env python3
"""
Test the official py-clob-client library to see if we can fetch trades
"""
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds
import json

def test_clob_trades():
    """Test if we can fetch trades without authentication"""
    print("="*60)
    print("Testing Official Polymarket CLOB Client")
    print("="*60)

    # Try without credentials first (public access)
    try:
        print("\n1. Testing without authentication...")
        client = ClobClient("https://clob.polymarket.com")

        # Try to get trades
        print("   Fetching recent trades...")
        trades = client.get_trades()

        if trades:
            print(f"   ✅ Success! Fetched {len(trades)} trades")
            print("\n   Sample trade:")
            print(json.dumps(trades[0], indent=2)[:500])
            return True
        else:
            print("   ⚠️  No trades returned")
            return False

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_clob_markets():
    """Test if we can fetch markets"""
    try:
        print("\n2. Testing market data access...")
        client = ClobClient("https://clob.polymarket.com")

        # Try to get markets
        print("   Fetching markets...")
        markets = client.get_markets()

        if markets:
            print(f"   ✅ Success! Fetched {len(markets)} markets")
            return True
        else:
            print("   ⚠️  No markets returned")
            return False

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def inspect_client_methods():
    """Show available methods in the client"""
    print("\n3. Available methods in ClobClient:")
    client = ClobClient("https://clob.polymarket.com")

    methods = [m for m in dir(client) if not m.startswith('_') and callable(getattr(client, m))]
    for method in sorted(methods):
        print(f"   - {method}")

if __name__ == '__main__':
    test_clob_trades()
    test_clob_markets()
    inspect_client_methods()

    print("\n" + "="*60)
    print("Test Complete")
    print("="*60)
