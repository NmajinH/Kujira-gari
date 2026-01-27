"""
Wallet profiling and analysis
"""
import sys
from typing import Dict, Optional, List
from datetime import datetime
from pathlib import Path

# Fix imports
if __package__:
    from ..api.polygon import PolygonRPC
    from ..database.db import Database
    from ..config import Config
    from ..utils.logger import setup_logger
else:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from polymarket_insider_bot.api.polygon import PolygonRPC
    from polymarket_insider_bot.database.db import Database
    from polymarket_insider_bot.config import Config
    from polymarket_insider_bot.utils.logger import setup_logger

logger = setup_logger('wallet_analyzer')

class WalletAnalyzer:
    """Analyzes wallet behavior and history"""

    def __init__(self, polygon_rpc: PolygonRPC, database: Database):
        """
        Initialize wallet analyzer

        Args:
            polygon_rpc: Polygon RPC client
            database: Database instance
        """
        self.rpc = polygon_rpc
        self.db = database

    def get_or_create_profile(
        self,
        wallet_address: str,
        force_refresh: bool = False,
        score_tier: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Get wallet profile from database or create new one

        Args:
            wallet_address: Wallet address
            force_refresh: Force refresh from blockchain
            score_tier: Alert tier for tiered analysis depth

        Returns:
            Wallet profile dict
        """
        # Check database first
        if not force_refresh:
            existing = self.db.get_wallet_profile(wallet_address)
            if existing:
                # Check if profile is recent (< 1 hour old)
                age = (datetime.utcnow() - existing.last_updated).total_seconds() / 3600
                if age < 1:
                    logger.debug(f"Using cached wallet profile for {wallet_address}")
                    return self._wallet_to_dict(existing)

        # Build new profile from blockchain
        logger.info(f"Building new wallet profile for {wallet_address}")
        profile = self.rpc.build_wallet_profile(wallet_address, score_tier)

        # Save to database
        self.db.save_wallet_profile(profile)

        return profile

    def analyze_wallet_for_trade(
        self,
        wallet_address: str,
        trade_data: Dict,
        preliminary_score: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Analyze wallet specifically for a suspicious trade

        Args:
            wallet_address: Wallet address
            trade_data: Trade information
            preliminary_score: Preliminary score to determine analysis depth

        Returns:
            Enhanced wallet profile
        """
        # Determine analysis tier
        score_tier = None
        if preliminary_score:
            if preliminary_score >= 90:
                score_tier = 'CRITICAL'
            elif preliminary_score >= 70:
                score_tier = 'HIGH'
            elif preliminary_score >= 50:
                score_tier = 'MEDIUM'

        # Get wallet profile
        profile = self.get_or_create_profile(wallet_address, score_tier=score_tier)

        # Add Polymarket-specific analysis
        profile = self._analyze_polymarket_activity(profile, trade_data)

        return profile

    def _analyze_polymarket_activity(
        self,
        profile: Dict,
        current_trade: Dict
    ) -> Dict:
        """
        Analyze Polymarket trading patterns

        For Phase 1: Use database records
        For Phase 2: Could query Polymarket subgraph directly
        """
        wallet_address = profile['wallet_address']

        # Query historical trades from our database
        with self.db.get_session() as session:
            from ..database.models import FlaggedTrade

            # Get all flagged trades for this wallet
            previous_flags = session.query(FlaggedTrade).filter_by(
                wallet_address=wallet_address
            ).all()

            # Count unique markets
            unique_markets = set()
            total_volume = 0
            trade_count = len(previous_flags)

            for trade in previous_flags:
                unique_markets.add(trade.market_id)
                total_volume += trade.bet_size_usd

            # Add current trade
            trade_count += 1
            unique_markets.add(current_trade.get('market_id', ''))
            total_volume += current_trade.get('bet_size_usd', 0)

            profile['polymarket_trades'] = trade_count
            profile['unique_markets'] = len(unique_markets)
            profile['total_volume_usd'] = total_volume
            profile['last_activity'] = datetime.utcnow()

        return profile

    def _wallet_to_dict(self, wallet_obj) -> Dict:
        """Convert SQLAlchemy wallet object to dict"""
        return {
            'wallet_address': wallet_obj.wallet_address,
            'age_days': wallet_obj.age_days,
            'total_transactions': wallet_obj.total_transactions,
            'polymarket_trades': wallet_obj.polymarket_trades,
            'unique_markets': wallet_obj.unique_markets,
            'total_volume_usd': wallet_obj.total_volume_usd,
            'funding_source': wallet_obj.funding_source,
            'last_cex_deposit': wallet_obj.last_cex_deposit,
            'ens_domains': wallet_obj.ens_domains,
            'first_seen': wallet_obj.first_seen,
            'last_activity': wallet_obj.last_activity,
            'is_suspicious': wallet_obj.is_suspicious
        }

    def mark_suspicious(
        self,
        wallet_address: str,
        reason: str
    ):
        """
        Mark wallet as suspicious

        Args:
            wallet_address: Wallet address
            reason: Reason for flagging
        """
        with self.db.get_session() as session:
            from ..database.models import WalletProfile

            wallet = session.query(WalletProfile).filter_by(
                wallet_address=wallet_address
            ).first()

            if wallet:
                wallet.is_suspicious = True
                wallet.suspicion_notes = reason
                logger.info(f"Marked wallet {wallet_address} as suspicious: {reason}")

    def get_wallet_history_summary(self, wallet_address: str) -> str:
        """
        Generate human-readable wallet history summary

        Args:
            wallet_address: Wallet address

        Returns:
            Formatted summary string
        """
        profile = self.get_or_create_profile(wallet_address)

        lines = [
            f"Wallet: {wallet_address[:10]}...{wallet_address[-8:]}",
            f"Age: {profile.get('age_days', 0):.1f} days",
            f"Total Transactions: {profile.get('total_transactions', 0)}",
            f"Polymarket Trades: {profile.get('polymarket_trades', 0)}",
            f"Unique Markets: {profile.get('unique_markets', 0)}",
            f"Total Volume: ${profile.get('total_volume_usd', 0):,.0f}"
        ]

        if profile.get('funding_source'):
            lines.append(f"Funding: {profile['funding_source']}")

        if profile.get('last_cex_deposit'):
            hours_ago = (datetime.utcnow() - profile['last_cex_deposit']).total_seconds() / 3600
            lines.append(f"Last CEX Deposit: {hours_ago:.0f}h ago")

        return "\n".join(lines)
