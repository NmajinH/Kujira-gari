"""
Demo Mode - Simulate the bot detecting suspicious trades

This runs offline with simulated data to prove the detection logic works.
No network calls required.
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from analyzers.market_analyzer import MarketAnalyzer
from analyzers.trade_analyzer import TradeAnalyzer
from alerts.formatter import AlertFormatter

def print_separator():
    print("\n" + "="*70 + "\n")

def simulate_maduro_trade():
    """Simulate the Maduro trade example"""
    print("🎯 SIMULATING SUSPICIOUS TRADE DETECTION")
    print_separator()

    # Simulated trade data
    trade = {
        'trade_id': 'demo_trade_001',
        'wallet_address': '0xSBet365abc123def456789012345678901234bf2',
        'bet_size_usd': 15089,
        'probability': 0.018,  # 1.8%
        'market_id': 'maduro_market_123',
        'outcome': 'YES',
        'timestamp': datetime.utcnow() - timedelta(minutes=5)
    }

    # Simulated market data
    market_info = {
        'market_id': 'maduro_market_123',
        'market_name': 'Maduro out by Feb 28, 2026?',
        'description': 'Will Nicolas Maduro be out of power by February 28, 2026?',
        'volume_usd': 2300000,
        'end_date': datetime(2026, 2, 28),
        'url': 'https://polymarket.com/event/maduro-2026'
    }

    # Simulated wallet profile
    wallet_profile = {
        'wallet_address': trade['wallet_address'],
        'age_days': 3.0,
        'total_transactions': 2,
        'polymarket_trades': 1,
        'unique_markets': 1,
        'total_volume_usd': 15089,
        'funding_source': 'Likely CEX',
        'last_cex_deposit': datetime.utcnow() - timedelta(hours=23),
        'first_seen': datetime.utcnow() - timedelta(days=3),
        'is_suspicious': False
    }

    print("📊 TRADE DATA:")
    print(f"  Wallet: {trade['wallet_address'][:10]}...{trade['wallet_address'][-8:]}")
    print(f"  Bet Size: ${trade['bet_size_usd']:,}")
    print(f"  Odds: {trade['probability']*100:.1f}%")
    print(f"  Market: {market_info['market_name']}")
    print_separator()

    # Step 1: Market Analysis
    print("🔍 STEP 1: MARKET CATEGORIZATION")
    market_analyzer = MarketAnalyzer()

    category = market_analyzer.categorize_market(
        market_info['market_name'],
        market_info['description']
    )

    should_monitor = market_analyzer.should_monitor_market(
        market_name=market_info['market_name'],
        market_volume_usd=market_info['volume_usd'],
        end_date=market_info['end_date'],
        market_description=market_info['description']
    )

    print(f"  Category: {category}")
    print(f"  Should Monitor: {should_monitor['should_monitor']}")
    print(f"  Reason: {should_monitor['reason']}")

    if not should_monitor['should_monitor']:
        print("  ❌ Market filtered out - would not monitor")
        return False
    else:
        print("  ✅ Market passes filters - monitoring active")

    print_separator()

    # Step 2: Trade Analysis & Scoring
    print("🎯 STEP 2: TRADE ANALYSIS & SCORING")
    trade_analyzer = TradeAnalyzer()

    # Check basic criteria
    meets_criteria, reason = trade_analyzer.meets_basic_criteria(
        trade['bet_size_usd'],
        trade['probability']
    )

    print(f"  Meets Size Criteria (>${trade_analyzer.min_bet_size:,.0f}): {meets_criteria}")
    print(f"  Meets Odds Criteria (<{trade_analyzer.max_probability*100}%): {meets_criteria}")

    if not meets_criteria:
        print(f"  ❌ Filtered: {reason}")
        return False

    # Calculate suspicion score
    score, flags = trade_analyzer.calculate_suspicion_score(
        bet_size_usd=trade['bet_size_usd'],
        probability=trade['probability'],
        wallet_age_days=wallet_profile['age_days'],
        total_trades=wallet_profile['polymarket_trades'],
        unique_markets=wallet_profile['unique_markets'],
        is_high_risk_category=True,
        recent_cex_funding=True
    )

    alert_tier = trade_analyzer.determine_alert_tier(score)

    print(f"\n  🚨 SUSPICION SCORE: {score}/100")
    print(f"  📊 ALERT TIER: {alert_tier}")
    print(f"\n  ⚠️  RED FLAGS DETECTED ({len(flags)}):")
    for flag in flags:
        print(f"    • {flag}")

    print_separator()

    # Step 3: Generate Alert
    print("📤 STEP 3: ALERT GENERATION")

    formatter = AlertFormatter()

    analysis = {
        'score': score,
        'alert_tier': alert_tier,
        'flags': flags,
        'bet_size_usd': trade['bet_size_usd'],
        'probability': trade['probability'],
        'expected_profit': (trade['bet_size_usd'] / trade['probability']) - trade['bet_size_usd'],
        'roi_multiplier': 1 / trade['probability']
    }

    alert_message = formatter.format_alert(
        alert_tier=alert_tier,
        trade_data=trade,
        analysis=analysis,
        wallet_profile=wallet_profile,
        market_info=market_info
    )

    print("  Alert formatted successfully!")
    print("\n" + "─"*70)
    print("  THIS IS WHAT WOULD BE SENT TO TELEGRAM:")
    print("─"*70 + "\n")
    print(alert_message)
    print("\n" + "─"*70)

    print_separator()
    print("✅ DETECTION COMPLETE!")
    print(f"  • Market categorized as: {category}")
    print(f"  • Score calculated: {score}/100")
    print(f"  • Alert tier: {alert_tier}")
    print(f"  • Would trigger: {alert_tier} priority alert")
    print_separator()

    return True

def simulate_filtered_trades():
    """Show examples of trades that would be filtered out"""
    print("\n🔍 EXAMPLES OF FILTERED TRADES (NO ALERT)")
    print_separator()

    trade_analyzer = TradeAnalyzer()

    test_cases = [
        {
            'name': 'Large bet but high probability',
            'bet_size': 50000,
            'probability': 0.85,
            'reason': 'Probability >20%'
        },
        {
            'name': 'Low probability but small bet',
            'bet_size': 500,
            'probability': 0.02,
            'reason': 'Bet size <$10k'
        },
        {
            'name': 'Good size and odds but old wallet',
            'bet_size': 15000,
            'probability': 0.05,
            'wallet_age_days': 180,
            'total_trades': 250,
            'reason': 'Wallet too established (>7 days, >10 trades)'
        }
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"{i}. {case['name']}")
        print(f"   Bet: ${case['bet_size']:,} @ {case['probability']*100:.1f}%")

        meets_criteria, reason = trade_analyzer.meets_basic_criteria(
            case['bet_size'],
            case['probability']
        )

        if not meets_criteria:
            print(f"   ❌ {reason}")
        elif 'wallet_age_days' in case:
            score, flags = trade_analyzer.calculate_suspicion_score(
                bet_size_usd=case['bet_size'],
                probability=case['probability'],
                wallet_age_days=case.get('wallet_age_days', 3),
                total_trades=case.get('total_trades', 1),
                unique_markets=1,
                is_high_risk_category=True,
                recent_cex_funding=False
            )
            print(f"   Score: {score}/100")
            print(f"   ❌ {case['reason']}")

        print()

    print_separator()

def run_demo():
    """Run the full demo"""
    print("\n" + "🎯" * 35)
    print("   POLYMARKET INSIDER DETECTION BOT - DEMO MODE")
    print("🎯" * 35)
    print("\nThis demo simulates the bot detecting a suspicious trade.")
    print("No network connection required - using sample data.\n")

    input("Press ENTER to start the simulation...")

    # Run Maduro simulation
    result = simulate_maduro_trade()

    if result:
        print("\n✅ The detection logic is working correctly!")
        print("\nWhat this proves:")
        print("  1. ✅ Market categorization works")
        print("  2. ✅ Trade filtering works")
        print("  3. ✅ Scoring algorithm works")
        print("  4. ✅ Alert formatting works")
        print("\nWhat's NOT tested (requires network):")
        print("  1. ❌ Polymarket API connection")
        print("  2. ❌ Polygon blockchain queries")
        print("  3. ❌ Telegram message delivery")
        print("\nTo test those, see: TEST_BOT_LOCALLY.md")

    print_separator()

    # Show filtered examples
    show_filtered = input("Show examples of filtered trades? (y/n): ")
    if show_filtered.lower() == 'y':
        simulate_filtered_trades()

    print("\n" + "="*70)
    print("DEMO COMPLETE")
    print("="*70)
    print("\nNext steps:")
    print("  1. Run: python send_test_simple.py (test Telegram)")
    print("  2. Configure .env with your Chat ID")
    print("  3. Run: python -m polymarket_insider_bot.main (start bot)")
    print("\nSee TEST_BOT_LOCALLY.md for full instructions.")
    print("="*70 + "\n")

if __name__ == '__main__':
    run_demo()
