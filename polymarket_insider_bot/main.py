"""
Main orchestration for Polymarket Insider Trading Detection Bot
"""
import time
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict
from pathlib import Path

# Fix imports to work when running directly or as module
if __name__ == '__main__':
    # Running directly: python main.py
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from polymarket_insider_bot.config import Config
    from polymarket_insider_bot.utils.logger import setup_logger
    from polymarket_insider_bot.database.db import Database
    from polymarket_insider_bot.api.polymarket import PolymarketAPI
    from polymarket_insider_bot.api.polygon import PolygonRPC
    from polymarket_insider_bot.analyzers.market_analyzer import MarketAnalyzer
    from polymarket_insider_bot.analyzers.trade_analyzer import TradeAnalyzer
    from polymarket_insider_bot.analyzers.wallet_analyzer import WalletAnalyzer
    from polymarket_insider_bot.alerts.telegram import TelegramAlertBot
else:
    # Running as module: python -m polymarket_insider_bot.main
    from .config import Config
    from .utils.logger import setup_logger
    from .database.db import Database
    from .api.polymarket import PolymarketAPI
    from .api.polygon import PolygonRPC
    from .analyzers.market_analyzer import MarketAnalyzer
    from .analyzers.trade_analyzer import TradeAnalyzer
    from .analyzers.wallet_analyzer import WalletAnalyzer
    from .alerts.telegram import TelegramAlertBot

logger = setup_logger('main', Config.LOG_LEVEL)

class InsiderDetectionBot:
    """Main bot orchestrator"""

    def __init__(self):
        """Initialize bot components"""
        logger.info("Initializing Polymarket Insider Detection Bot...")

        try:
            # Validate configuration
            Config.validate()

            # Initialize components
            self.db = Database()
            self.polymarket = PolymarketAPI()
            self.polygon_rpc = PolygonRPC()
            self.telegram = TelegramAlertBot()

            # Initialize analyzers
            self.market_analyzer = MarketAnalyzer()
            self.trade_analyzer = TradeAnalyzer()
            self.wallet_analyzer = WalletAnalyzer(self.polygon_rpc, self.db)

            # State tracking
            self.start_time = datetime.utcnow()
            self.trades_scanned = 0
            self.alerts_sent = 0
            self.last_scan_time = None
            self.markets_cache = {}

            logger.info("Bot initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise

    def scan_and_analyze(self):
        """
        Main scanning loop iteration:
        DEBUG MODE: Fetch ALL trades without market filtering to test Data API

        1. Fetch recent trades (NO FILTERING)
        2. Analyze and send alerts
        """
        logger.info("Starting scan cycle...")

        try:
            # DEBUG: Skip market filtering completely
            logger.info("⚠️  DEBUG MODE: Fetching ALL trades without market filtering")

            # Get recent trades from ALL markets (no filtering)
            lookback_seconds = Config.SCAN_INTERVAL_SECONDS
            trades = self.polymarket.scan_recent_trades(
                min_bet_size=Config.MIN_BET_SIZE_USD,
                lookback_seconds=lookback_seconds,
                market_ids=None  # DEBUG: No market filter
            )

            logger.info(f"Found {len(trades)} trades meeting size criteria")

            for trade in trades:
                self.process_trade(trade)

            self.last_scan_time = datetime.utcnow()

            logger.info(f"Scan cycle completed. Processed {len(trades)} trades.")

        except Exception as e:
            logger.error(f"Error in scan cycle: {e}")
            self.handle_scan_error(e)

    def process_trade(self, trade: Dict):
        """
        Process individual trade

        Args:
            trade: Parsed trade data
        """
        try:
            trade_id = trade.get('trade_id')
            market_id = trade.get('market_id')

            logger.debug(f"Processing trade {trade_id}")

            # Check if already processed
            with self.db.get_session() as session:
                from .database.models import FlaggedTrade
                existing = session.query(FlaggedTrade).filter_by(trade_id=trade_id).first()
                if existing:
                    logger.debug(f"Trade {trade_id} already processed")
                    return

            # Get market info
            market_info = self.get_market_info(market_id)
            if not market_info:
                logger.warning(f"Could not fetch market info for {market_id}")
                return

            # Check if market should be monitored
            should_monitor = self.market_analyzer.should_monitor_market(
                market_name=market_info['market_name'],
                market_volume_usd=market_info.get('volume_usd', 0),
                end_date=market_info.get('end_date'),
                market_description=market_info.get('description', '')
            )

            if not should_monitor['should_monitor']:
                logger.debug(f"Market {market_id} filtered: {should_monitor['reason']}")
                return

            market_category = should_monitor.get('category')
            logger.info(f"Processing trade in high-risk market: {market_info['market_name']}")

            # Get wallet profile (light check first)
            wallet_address = trade.get('wallet_address')
            wallet_profile = self.wallet_analyzer.get_or_create_profile(
                wallet_address,
                score_tier='MEDIUM'  # Start with light check
            )

            # Analyze trade
            analysis = self.trade_analyzer.analyze_trade(
                trade_data=trade,
                wallet_profile=wallet_profile,
                market_category=market_category
            )

            if not analysis:
                logger.debug(f"Trade {trade_id} did not meet suspicion criteria")
                self.trades_scanned += 1
                return

            # Trade is suspicious! Get deeper wallet profile if needed
            alert_tier = analysis['alert_tier']
            if alert_tier in ['HIGH', 'CRITICAL']:
                logger.info(f"Trade {trade_id} flagged as {alert_tier} - performing deeper wallet analysis")
                wallet_profile = self.wallet_analyzer.analyze_wallet_for_trade(
                    wallet_address,
                    trade,
                    preliminary_score=analysis['score']
                )

                # Recalculate score with enhanced wallet data
                analysis = self.trade_analyzer.analyze_trade(
                    trade_data=trade,
                    wallet_profile=wallet_profile,
                    market_category=market_category
                )

            # Save to database
            self.save_flagged_trade(trade, analysis, market_info, market_category)

            # Send alert
            self.send_alert(trade, analysis, wallet_profile, market_info, alert_tier)

            self.trades_scanned += 1

        except Exception as e:
            logger.error(f"Error processing trade {trade.get('trade_id')}: {e}")

    def get_market_info(self, market_id: str) -> Dict:
        """
        Get market information (with caching)

        Args:
            market_id: Market ID

        Returns:
            Market info dict
        """
        # Check cache
        if market_id in self.markets_cache:
            return self.markets_cache[market_id]

        # Fetch from API
        market_raw = self.polymarket.get_market_by_id(market_id)
        if not market_raw:
            return None

        # Extract info
        market_info = self.market_analyzer.extract_market_info(market_raw)

        # Cache it
        self.markets_cache[market_id] = market_info

        return market_info

    def save_flagged_trade(
        self,
        trade: Dict,
        analysis: Dict,
        market_info: Dict,
        market_category: str
    ):
        """
        Save flagged trade to database

        Args:
            trade: Trade data
            analysis: Analysis results
            market_info: Market information
            market_category: Market category
        """
        try:
            self.db.save_flagged_trade(
                trade_id=trade['trade_id'],
                wallet_address=trade['wallet_address'],
                market_id=trade['market_id'],
                market_name=market_info['market_name'],
                bet_size_usd=analysis['bet_size_usd'],
                probability=analysis['probability'],
                suspicion_score=analysis['score'],
                alert_tier=analysis['alert_tier'],
                flags=analysis['flags'],
                timestamp=trade['timestamp'],
                outcome=trade.get('outcome'),
                market_url=market_info.get('url'),
                market_category=market_category,
                market_volume_usd=market_info.get('volume_usd')
            )

            # Update market flag count
            self.db.increment_market_flag_count(trade['market_id'])

            logger.info(f"Saved flagged trade {trade['trade_id']} to database")

        except Exception as e:
            logger.error(f"Error saving flagged trade: {e}")

    def send_alert(
        self,
        trade: Dict,
        analysis: Dict,
        wallet_profile: Dict,
        market_info: Dict,
        alert_tier: str
    ):
        """
        Send Telegram alert

        Args:
            trade: Trade data
            analysis: Analysis results
            wallet_profile: Wallet profile
            market_info: Market info
            alert_tier: Alert tier
        """
        try:
            # Check if we should batch MEDIUM alerts
            if alert_tier == 'MEDIUM' and Config.BATCH_MEDIUM_ALERTS:
                logger.info("MEDIUM alert will be batched (not yet implemented)")
                # TODO: Implement batching
                return

            # Send alert
            success = self.telegram.send_alert(
                alert_tier=alert_tier,
                trade_data=trade,
                analysis=analysis,
                wallet_profile=wallet_profile,
                market_info=market_info
            )

            # Save alert history
            self.db.save_alert(
                alert_tier=alert_tier,
                wallet_address=trade['wallet_address'],
                market_id=trade['market_id'],
                trade_id=trade['trade_id'],
                message="Alert sent",
                suspicion_score=analysis['score'],
                sent_successfully=success
            )

            if success:
                self.alerts_sent += 1
                self.db.mark_alert_sent(trade['trade_id'])

        except Exception as e:
            logger.error(f"Error sending alert: {e}")

    def handle_scan_error(self, error: Exception):
        """
        Handle scan errors

        Args:
            error: Exception that occurred
        """
        error_msg = f"Scan error: {str(error)}"
        logger.error(error_msg)

        # Send error alert to Telegram
        try:
            self.telegram.send_error_alert(
                error_type="Scan Error",
                error_message=str(error),
                context="Error occurred during market scanning cycle"
            )
        except:
            logger.error("Failed to send error alert")

    def run_health_check(self):
        """Perform and report health check"""
        try:
            uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()

            health_data = {
                'status': 'online',
                'uptime_seconds': int(uptime_seconds),
                'markets_tracked': len(self.markets_cache),
                'last_scan': self.last_scan_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_scan_time else 'Never',
                'trades_scanned': self.trades_scanned,
                'alerts_sent_today': self.db.get_alerts_sent_today(),
                'polymarket_status': True,
                'polygon_status': self.polygon_rpc.w3.is_connected(),
                'telegram_status': True
            }

            # Save to database
            self.db.save_health_check(health_data)

            # Send to Telegram
            self.telegram.send_health_check(health_data)

            logger.info("Health check completed and sent")

        except Exception as e:
            logger.error(f"Health check failed: {e}")

    def verify_startup(self):
        """
        Verify all systems are ready before starting monitoring

        Returns:
            bool: True if all checks pass
        """
        print("\n" + "="*60)
        print("  POLYMARKET INSIDER BOT - STARTUP")
        print("="*60 + "\n")

        # Check 1: Configuration
        print("[1/5] Checking configuration...")
        try:
            Config.validate()
            print("  ✅ Configuration valid\n")
        except ValueError as e:
            print(f"  ❌ Configuration error: {e}\n")
            print("Please check your .env file")
            print("Run: python -m polymarket_insider_bot.utils.get_chat_id")
            return False

        # Check 2: Database
        print("[2/5] Initializing database...")
        try:
            stats = self.db.get_statistics()
            print(f"  ✅ Database ready ({stats['total_flagged']} trades logged)\n")
        except Exception as e:
            print(f"  ❌ Database error: {e}\n")
            return False

        # Check 3: Telegram
        print("[3/5] Testing Telegram connection...")
        try:
            if self.telegram.test_connection():
                print("  ✅ Telegram connected\n")
            else:
                print("  ⚠️  Telegram connection issue (will continue)\n")
        except Exception as e:
            print(f"  ⚠️  Telegram error: {e} (will continue)\n")

        # Check 4: Polygon RPC
        print("[4/5] Testing Polygon RPC...")
        try:
            if self.polygon_rpc.w3.is_connected():
                block = self.polygon_rpc.w3.eth.block_number
                print(f"  ✅ Polygon RPC connected (block #{block:,})\n")
            else:
                print("  ❌ Cannot connect to Polygon RPC\n")
                print("Check POLYGON_RPC_URL in .env")
                return False
        except Exception as e:
            print(f"  ❌ Polygon RPC error: {e}\n")
            return False

        # Check 5: Polymarket
        print("[5/5] Testing Polymarket API...")
        try:
            markets = self.polymarket.get_markets(limit=5)
            if markets:
                print(f"  ✅ Polymarket API connected ({len(markets)} markets fetched)\n")
            else:
                print("  ⚠️  Polymarket returned no markets (may be temporary)\n")
        except Exception as e:
            print(f"  ⚠️  Polymarket API issue: {e} (will continue)\n")

        print("="*60)
        print("✅ STARTUP CHECKS COMPLETE - Starting monitoring...")
        print("="*60)
        print()
        return True

    def run(self):
        """Main bot loop"""
        logger.info("Starting Polymarket Insider Detection Bot")

        # Run startup verification
        if not self.verify_startup():
            print("\n❌ Startup verification failed!")
            print("\nTroubleshooting:")
            print("  1. Run: python -m polymarket_insider_bot.tests.test_api_connections")
            print("  2. Check your .env file")
            print("  3. Get Chat ID: python -m polymarket_insider_bot.utils.get_chat_id")
            print()
            sys.exit(1)

        logger.info(f"Scan interval: {Config.SCAN_INTERVAL_SECONDS}s")
        logger.info(f"Min bet size: ${Config.MIN_BET_SIZE_USD:,.0f}")
        logger.info(f"Max probability: {Config.MAX_PROBABILITY * 100}%")

        # Initial health check
        self.run_health_check()

        # Main loop
        cycle_count = 0
        try:
            while True:
                cycle_count += 1
                logger.info(f"\n{'='*50}")
                logger.info(f"Scan Cycle #{cycle_count}")
                logger.info(f"{'='*50}")

                self.scan_and_analyze()

                # Health check every hour
                if cycle_count % (3600 // Config.SCAN_INTERVAL_SECONDS) == 0:
                    self.run_health_check()

                # Wait for next cycle
                logger.info(f"Waiting {Config.SCAN_INTERVAL_SECONDS}s until next scan...")
                time.sleep(Config.SCAN_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            logger.info("\nBot stopped by user")
        except Exception as e:
            logger.error(f"Bot crashed: {e}")
            self.telegram.send_error_alert(
                error_type="Bot Crash",
                error_message=str(e),
                context="Bot encountered fatal error and stopped"
            )
            raise


def main():
    """Entry point"""
    print("\n" + "🎯"*30)
    print("   POLYMARKET INSIDER TRADING DETECTION BOT")
    print("🎯"*30 + "\n")

    try:
        bot = InsiderDetectionBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("Bot stopped by user (Ctrl+C)")
        print("="*60 + "\n")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print("\n" + "="*60)
        print(f"❌ FATAL ERROR: {e}")
        print("="*60 + "\n")
        print("Check logs for details:")
        print("  tail -f logs/bot_*.log")
        print()
        sys.exit(1)


if __name__ == '__main__':
    main()
