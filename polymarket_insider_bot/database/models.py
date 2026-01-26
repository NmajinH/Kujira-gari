"""
Database models for the insider trading bot
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class FlaggedTrade(Base):
    """Record of flagged suspicious trades"""
    __tablename__ = 'flagged_trades'

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(String(100), unique=True, nullable=False)
    wallet_address = Column(String(42), nullable=False, index=True)
    market_id = Column(String(100), nullable=False, index=True)
    market_name = Column(Text, nullable=False)
    market_url = Column(String(500))

    # Trade details
    bet_size_usd = Column(Float, nullable=False)
    probability = Column(Float, nullable=False)
    outcome = Column(String(10))  # YES/NO
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Scoring
    suspicion_score = Column(Integer, nullable=False, index=True)
    alert_tier = Column(String(10), nullable=False)  # CRITICAL/HIGH/MEDIUM
    flags = Column(JSON)  # List of red flags detected

    # Alert tracking
    alert_sent = Column(Boolean, default=False)
    alert_sent_at = Column(DateTime)

    # Additional context
    market_category = Column(String(50))
    market_volume_usd = Column(Float)
    price_movement_2h = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Indexes for common queries
    __table_args__ = (
        Index('idx_timestamp', 'timestamp'),
        Index('idx_score_tier', 'suspicion_score', 'alert_tier'),
    )

class WalletProfile(Base):
    """Wallet analysis profiles"""
    __tablename__ = 'wallet_profiles'

    wallet_address = Column(String(42), primary_key=True)

    # Basic metrics
    age_days = Column(Float)
    total_transactions = Column(Integer, default=0)
    polymarket_trades = Column(Integer, default=0)
    unique_markets = Column(Integer, default=0)
    total_volume_usd = Column(Float, default=0)

    # Funding analysis
    funding_source = Column(String(100))  # CEX name or "Unknown"
    last_cex_deposit = Column(DateTime)

    # Identity
    ens_domains = Column(JSON)  # List of ENS names

    # Timestamps
    first_seen = Column(DateTime, nullable=False)
    last_activity = Column(DateTime)
    last_updated = Column(DateTime, default=datetime.utcnow)

    # Flags
    is_suspicious = Column(Boolean, default=False)
    suspicion_notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_suspicious', 'is_suspicious'),
        Index('idx_age', 'age_days'),
    )

class MarketOutcome(Base):
    """Track market resolutions for accuracy measurement"""
    __tablename__ = 'market_outcomes'

    market_id = Column(String(100), primary_key=True)
    market_name = Column(Text, nullable=False)
    market_category = Column(String(50))

    # Market metadata
    created_at_market = Column(DateTime)
    resolution_date = Column(DateTime)
    resolved_date = Column(DateTime)
    outcome = Column(String(10))  # YES/NO/UNRESOLVED

    # Tracking
    flagged_trade_count = Column(Integer, default=0)
    our_prediction = Column(String(10))  # What our alerts suggested
    accuracy = Column(Boolean)  # Did we predict correctly?

    # Timestamps
    first_flagged = Column(DateTime)
    last_flagged = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class AlertHistory(Base):
    """History of sent alerts"""
    __tablename__ = 'alert_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_tier = Column(String(10), nullable=False)
    wallet_address = Column(String(42), nullable=False)
    market_id = Column(String(100), nullable=False)
    trade_id = Column(String(100), nullable=False)

    # Alert content
    message = Column(Text, nullable=False)
    suspicion_score = Column(Integer, nullable=False)

    # Delivery
    sent_successfully = Column(Boolean, default=False)
    error_message = Column(Text)

    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

class SystemHealth(Base):
    """System health check records"""
    __tablename__ = 'system_health'

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    status = Column(String(20))  # online/error/degraded
    uptime_seconds = Column(Integer)
    markets_tracked = Column(Integer)
    trades_scanned = Column(Integer)
    alerts_sent_today = Column(Integer)

    # API status
    polymarket_status = Column(Boolean)
    polygon_status = Column(Boolean)
    telegram_status = Column(Boolean)

    error_message = Column(Text)
