#!/usr/bin/env python3
"""
Test direct access to Polymarket Data API (no auth required)
"""
import requests
import json
from datetime import datetime

def test_data_api_trades():
    """Test the public Data API for trades"""
    print("="*60)
    print("Testing Polymarket Data API (Public Access)")
    print("="*60)

    base_url = "https://data-api.polymarket.com"

    # Test 1: Get recent trades (no filters)
    print("\n1. Fetching recent trades (no filters)...")
    try:
        url = f"{base_url}/trades"
        params = {
            'limit': 10,  # Get 10 recent trades
        }

        response = requests.get(url, params=params, timeout=10)
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            trades = response.json()
            print(f"   ✅ Success! Fetched {len(trades)} trades")

            if trades:
                print("\n   Sample trade:")
                trade = trades[0]
                print(json.dumps(trade, indent=2)[:800])

                # Show key fields
                print("\n   Key fields in trade:")
                print(f"   - Keys: {list(trade.keys())}")

                return True
        else:
            print(f"   ❌ Error: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False

def test_data_api_with_filters():
    """Test with various filters"""
    print("\n2. Testing with filters...")

    base_url = "https://data-api.polymarket.com/trades"

    # Try different parameter combinations
    test_params = [
        {'limit': 100},
        {'limit': 50, 'offset': 0},
        {'limit': 20, 'filterType': 'CASH', 'filterAmount': 1000},
    ]

    for i, params in enumerate(test_params):
        try:
            print(f"\n   Test {i+1}: {params}")
            response = requests.get(base_url, params=params, timeout=10)
            if response.status_code == 200:
                trades = response.json()
                print(f"   ✅ {len(trades)} trades fetched")
            else:
                print(f"   ❌ Status {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == '__main__':
    success = test_data_api_trades()
    test_data_api_with_filters()

    print("\n" + "="*60)
    if success:
        print("✅ Data API is accessible - ready to integrate!")
    else:
        print("❌ Data API access failed")
    print("="*60)
