"""
Database connection and operations
"""
from sqlalchemy import create_engine, desc, and_, func
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import json
import sys
from pathlib import Path

# Fix imports
if __package__:
    from .models import Base, FlaggedTrade, WalletProfile, MarketOutcome, AlertHistory, SystemHealth
    from ..config import Config
    from ..utils.logger import setup_logger
else:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from polymarket_insider_bot.database.models import Base, FlaggedTrade, WalletProfile, MarketOutcome, AlertHistory, SystemHealth
    from polymarket_insider_bot.config import Config
    from polymarket_insider_bot.utils.logger import setup_logger

logger = setup_logger('database')

class Database:
    """Database manager"""

    def __init__(self, db_path: str = None):
        """Initialize database connection"""
        self.db_path = db_path or Config.DATABASE_PATH
        self.engine = create_engine(f'sqlite:///{self.db_path}', echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create tables
        Base.metadata.create_all(self.engine)
        logger.info(f"Database initialized at {self.db_path}")

    @contextmanager
    def get_session(self) -> Session:
        """Context manager for database sessions"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()

    # Flagged Trades
    def save_flagged_trade(
        self,
        trade_id: str,
        wallet_address: str,
        market_id: str,
        market_name: str,
        bet_size_usd: float,
        probability: float,
        suspicion_score: int,
        alert_tier: str,
        flags: List[str],
        **kwargs
    ) -> Optional[FlaggedTrade]:
        """Save a flagged trade"""
        with self.get_session() as session:
            # Check if already exists
            existing = session.query(FlaggedTrade).filter_by(trade_id=trade_id).first()
            if existing:
                logger.warning(f"Trade {trade_id} already flagged")
                return existing

            trade = FlaggedTrade(
                trade_id=trade_id,
                wallet_address=wallet_address,
                market_id=market_id,
                market_name=market_name,
                bet_size_usd=bet_size_usd,
                probability=probability,
                suspicion_score=suspicion_score,
                alert_tier=alert_tier,
                flags=flags,
                timestamp=kwargs.get('timestamp', datetime.utcnow()),
                outcome=kwargs.get('outcome'),
                market_url=kwargs.get('market_url'),
                market_category=kwargs.get('market_category'),
                market_volume_usd=kwargs.get('market_volume_usd'),
                price_movement_2h=kwargs.get('price_movement_2h')
            )

            session.add(trade)
            session.flush()
            logger.info(f"Saved flagged trade {trade_id} with score {suspicion_score}")
            return trade

    def mark_alert_sent(self, trade_id: str):
        """Mark alert as sent for a trade"""
        with self.get_session() as session:
            trade = session.query(FlaggedTrade).filter_by(trade_id=trade_id).first()
            if trade:
                trade.alert_sent = True
                trade.alert_sent_at = datetime.utcnow()

    def get_unsent_alerts(self, min_score: int = 50) -> List[FlaggedTrade]:
        """Get trades that need alerts sent"""
        with self.get_session() as session:
            trades = session.query(FlaggedTrade).filter(
                and_(
                    FlaggedTrade.alert_sent == False,
                    FlaggedTrade.suspicion_score >= min_score
                )
            ).order_by(desc(FlaggedTrade.suspicion_score)).all()

            return [self._detach_trade(t) for t in trades]

    def _detach_trade(self, trade: FlaggedTrade) -> FlaggedTrade:
        """Detach trade from session for safe use"""
        return trade

    # Wallet Profiles
    def save_wallet_profile(self, profile: Dict[str, Any]) -> WalletProfile:
        """Save or update wallet profile"""
        with self.get_session() as session:
            wallet = session.query(WalletProfile).filter_by(
                wallet_address=profile['wallet_address']
            ).first()

            if wallet:
                # Update existing
                for key, value in profile.items():
                    if hasattr(wallet, key):
                        setattr(wallet, key, value)
                wallet.last_updated = datetime.utcnow()
            else:
                # Create new
                wallet = WalletProfile(**profile)
                session.add(wallet)

            session.flush()
            return wallet

    def get_wallet_profile(self, wallet_address: str) -> Optional[WalletProfile]:
        """Get wallet profile"""
        with self.get_session() as session:
            wallet = session.query(WalletProfile).filter_by(
                wallet_address=wallet_address
            ).first()
            return wallet

    # Market Outcomes
    def save_market_outcome(self, market_data: Dict[str, Any]) -> MarketOutcome:
        """Save or update market outcome"""
        with self.get_session() as session:
            market = session.query(MarketOutcome).filter_by(
                market_id=market_data['market_id']
            ).first()

            if market:
                for key, value in market_data.items():
                    if hasattr(market, key):
                        setattr(market, key, value)
            else:
                market = MarketOutcome(**market_data)
                session.add(market)

            session.flush()
            return market

    def increment_market_flag_count(self, market_id: str):
        """Increment flagged trade count for a market"""
        with self.get_session() as session:
            market = session.query(MarketOutcome).filter_by(market_id=market_id).first()
            if market:
                market.flagged_trade_count += 1
                if not market.first_flagged:
                    market.first_flagged = datetime.utcnow()
                market.last_flagged = datetime.utcnow()

    # Alert History
    def save_alert(
        self,
        alert_tier: str,
        wallet_address: str,
        market_id: str,
        trade_id: str,
        message: str,
        suspicion_score: int,
        sent_successfully: bool,
        error_message: str = None
    ):
        """Save alert history"""
        with self.get_session() as session:
            alert = AlertHistory(
                alert_tier=alert_tier,
                wallet_address=wallet_address,
                market_id=market_id,
                trade_id=trade_id,
                message=message,
                suspicion_score=suspicion_score,
                sent_successfully=sent_successfully,
                error_message=error_message
            )
            session.add(alert)

    def get_alerts_sent_today(self) -> int:
        """Count alerts sent today"""
        with self.get_session() as session:
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            count = session.query(AlertHistory).filter(
                AlertHistory.timestamp >= today
            ).count()
            return count

    # System Health
    def save_health_check(self, health_data: Dict[str, Any]):
        """Save system health check"""
        with self.get_session() as session:
            health = SystemHealth(**health_data)
            session.add(health)

    def get_latest_health(self) -> Optional[SystemHealth]:
        """Get most recent health check"""
        with self.get_session() as session:
            health = session.query(SystemHealth).order_by(
                desc(SystemHealth.timestamp)
            ).first()
            return health

    # Statistics
    def get_statistics(self) -> Dict[str, Any]:
        """Get bot statistics"""
        with self.get_session() as session:
            total_flagged = session.query(FlaggedTrade).count()
            critical_alerts = session.query(FlaggedTrade).filter(
                FlaggedTrade.alert_tier == 'CRITICAL'
            ).count()
            high_alerts = session.query(FlaggedTrade).filter(
                FlaggedTrade.alert_tier == 'HIGH'
            ).count()
            medium_alerts = session.query(FlaggedTrade).filter(
                FlaggedTrade.alert_tier == 'MEDIUM'
            ).count()

            unique_wallets = session.query(
                func.count(func.distinct(FlaggedTrade.wallet_address))
            ).scalar()

            unique_markets = session.query(
                func.count(func.distinct(FlaggedTrade.market_id))
            ).scalar()

            return {
                'total_flagged': total_flagged,
                'critical_alerts': critical_alerts,
                'high_alerts': high_alerts,
                'medium_alerts': medium_alerts,
                'unique_suspicious_wallets': unique_wallets,
                'unique_markets_flagged': unique_markets,
                'alerts_sent_today': self.get_alerts_sent_today()
            }
