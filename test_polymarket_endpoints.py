"""
Test Polymarket API endpoints to find working trade data source

Run this to find which endpoints work:
python test_polymarket_endpoints.py
"""
import requests
import json

def test_endpoint(name, url, params=None):
    """Test an endpoint and show response"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print('='*60)

    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Response type: {type(data)}")

            if isinstance(data, list) and len(data) > 0:
                print(f"Items: {len(data)}")
                print("\nSample item:")
                print(json.dumps(data[0], indent=2)[:500])
            elif isinstance(data, dict):
                print(f"Keys: {list(data.keys())}")
                print("\nSample:")
                print(json.dumps(data, indent=2)[:500])

            return True
        else:
            print(f"Error: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"Exception: {e}")
        return False

# Test various Polymarket endpoints
endpoints = [
    ("Gamma Markets", "https://gamma-api.polymarket.com/markets", {"limit": 1}),
    ("Gamma Events", "https://gamma-api.polymarket.com/events", {"limit": 1}),
    ("Strapi Markets", "https://strapi-matic.poly.market/markets", {"_limit": 1}),
    ("Data API", "https://data-api.polymarket.com/trades", {"limit": 1}),
    ("CLOB Orderbook", "https://clob.polymarket.com/book", {"market": "any"}),
]

print("TESTING POLYMARKET API ENDPOINTS")
print("="*60)

results = {}
for name, url, params in endpoints:
    results[name] = test_endpoint(name, url, params)

print("\n" + "="*60)
print("SUMMARY")
print("="*60)
for name, success in results.items():
    status = "✅ WORKING" if success else "❌ FAILED"
    print(f"{status}: {name}")

print("\nNext: Use the working endpoint in polymarket.py")
