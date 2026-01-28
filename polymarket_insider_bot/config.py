"""
Configuration management for Polymarket Insider Bot
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

class Config:
    """Bot configuration from environment variables"""

    # Polymarket API
    POLYMARKET_API_KEY = os.getenv('POLYMARKET_API_KEY', '')
    POLYMARKET_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws"
    POLYMARKET_REST_URL = "https://clob.polymarket.com"
    POLYMARKET_GAMMA_URL = "https://gamma-api.polymarket.com"

    # Polygon RPC
    POLYGON_RPC_URL = os.getenv('POLYGON_RPC_URL', 'https://polygon-rpc.com')

    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

    # Database
    DATABASE_PATH = os.getenv('DATABASE_PATH', './data/bot.db')

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    # Scanning - TESTING MODE (ultra-sensitive)
    SCAN_INTERVAL_SECONDS = int(os.getenv('SCAN_INTERVAL_SECONDS', 60))  # 1 minute for fast testing
    MIN_BET_SIZE_USD = float(os.getenv('MIN_BET_SIZE_USD', 50))  # $50 to catch almost everything
    MAX_PROBABILITY = float(os.getenv('MAX_PROBABILITY', 0.95))  # 95% - accept nearly any odds

    # Alert Configuration - TESTING MODE (alert on everything)
    MIN_ALERT_SCORE = int(os.getenv('MIN_ALERT_SCORE', 1))  # Score of 1+ triggers alerts
    BATCH_MEDIUM_ALERTS = os.getenv('BATCH_MEDIUM_ALERTS', 'false').lower() == 'true'

    # Market filters
    MIN_MARKET_VOLUME_USD = 10000
    MAX_MARKET_DAYS_UNTIL_EXPIRY = 90

    # Wallet analysis thresholds
    NEW_WALLET_AGE_DAYS = 7
    LOW_TRADE_COUNT = 10
    FRESH_FUNDING_HOURS = 48

    # High-risk market keywords (for category filtering)
    HIGH_RISK_KEYWORDS = [
        # Politics & Geopolitics
        'election', 'president', 'prime minister', 'senate', 'congress',
        'vote', 'ballot', 'campaign', 'cabinet', 'minister', 'governor',
        'coup', 'regime', 'sanctions', 'military', 'war', 'conflict',
        'diplomatic', 'treaty', 'impeach', 'resign',

        # Business & Corporate
        'earnings', 'revenue', 'profit', 'ebitda', 'eps',
        'acquisition', 'merger', 'buyout', 'ipo', 'delisting',
        'ceo', 'cfo', 'executive', 'board', 'chairman',
        'bankrupt', 'restructur', 'layoff', 'shutdown',

        # Tech
        'launch', 'release', 'announce', 'unveil',
        'model', 'api', 'feature', 'product',
        'apple', 'google', 'microsoft', 'meta', 'amazon', 'tesla',
        'openai', 'anthropic', 'nvidia',

        # Awards & Appointments
        'nobel', 'oscar', 'grammy', 'emmy', 'appointment',
        'nomination', 'nominate', 'award', 'winner',

        # Regulatory
        'sec', 'fda', 'approve', 'approval', 'regulation',
        'court', 'ruling', 'verdict', 'judge', 'legal',
        'lawsuit', 'settlement', 'indictment', 'trial'
    ]

    # Exclude keywords (filter out sports/crypto/entertainment)
    EXCLUDE_KEYWORDS = [
        # Sports
        'football', 'basketball', 'soccer', 'baseball', 'cricket',
        'tennis', 'golf', 'ufc', 'boxing', 'nfl', 'nba', 'mlb',
        'nhl', 'fifa', 'super bowl', 'world cup', 'olympics',
        'championship', 'playoff', 'quarterback', 'touchdown',

        # Crypto price predictions
        'bitcoin', 'btc', 'ethereum', 'eth', 'crypto price',
        'coin price', 'will btc hit', 'will eth hit',

        # General entertainment (unless awards-related)
        'movie box office', 'album sales', 'streaming',
        'youtube views', 'tiktok', 'instagram followers'
    ]

    # Retry configuration
    MAX_RETRIES = 3
    RETRY_BACKOFF_SECONDS = [1, 2, 4]

    # Rate limiting
    MAX_RPC_REQUESTS_PER_SECOND = 20  # Conservative for free tier

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []

        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN is required")

        if not cls.TELEGRAM_CHAT_ID:
            errors.append("TELEGRAM_CHAT_ID is required (run utils/get_chat_id.py to obtain)")

        if not cls.POLYGON_RPC_URL:
            errors.append("POLYGON_RPC_URL is required")

        if errors:
            raise ValueError(f"Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))

        # Create data directory if needed
        db_dir = Path(cls.DATABASE_PATH).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        return True

# Validate config on import
if __name__ != '__main__':
    try:
        Config.validate()
    except ValueError:
        # Don't fail on import, let main.py handle it
        pass
