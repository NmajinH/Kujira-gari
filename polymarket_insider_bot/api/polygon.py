"""
Polygon blockchain RPC client for wallet analysis
"""
from web3 import Web3
import sys
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from pathlib import Path

# Fix imports
if __package__:
    from ..config import Config
    from ..utils.logger import setup_logger
    from ..utils.helpers import retry_with_backoff
else:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from polymarket_insider_bot.config import Config
    from polymarket_insider_bot.utils.logger import setup_logger
    from polymarket_insider_bot.utils.helpers import retry_with_backoff

logger = setup_logger('polygon_rpc')

# Known CEX deposit addresses on Polygon (add more as needed)
KNOWN_CEX_ADDRESSES = {
    '0x...(sample)': 'Coinbase',
    # More would be added here - this is a sample
}

class PolygonRPC:
    """Polygon blockchain RPC client"""

    def __init__(self, rpc_url: str = None):
        """Initialize Web3 connection"""
        self.rpc_url = rpc_url or Config.POLYGON_RPC_URL
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))

        if not self.w3.is_connected():
            logger.error("Failed to connect to Polygon RPC")
            raise ConnectionError(f"Cannot connect to Polygon RPC: {self.rpc_url}")

        logger.info(f"Connected to Polygon RPC")

    @retry_with_backoff(max_retries=3, backoff_seconds=[1, 2, 4])
    def get_wallet_age(self, address: str) -> Optional[float]:
        """
        Get wallet age in days

        Args:
            address: Wallet address

        Returns:
            Age in days or None if error
        """
        try:
            # Get current block
            current_block = self.w3.eth.block_number

            # Binary search for first transaction
            # Start by checking if address has any transactions
            latest_nonce = self.w3.eth.get_transaction_count(address)

            if latest_nonce == 0:
                # No transactions, wallet might be brand new
                # Check if it has any balance
                balance = self.w3.eth.get_balance(address)
                if balance == 0:
                    logger.debug(f"Wallet {address} has no activity")
                    return None

                # Has balance but no outgoing tx - estimate as very new
                return 0.01  # < 1 day

            # For wallets with transactions, estimate based on current state
            # This is a simplified approach - full history would require archive node
            # For Phase 1, we'll use heuristics

            # Get recent transactions to estimate age
            # Note: This is approximate without archive node access
            logger.debug(f"Wallet {address} has {latest_nonce} transactions")

            # For Phase 1, return a conservative estimate
            # If nonce is low, wallet is likely newer
            if latest_nonce < 5:
                return 3.0  # Estimate ~3 days for low-activity wallets
            elif latest_nonce < 20:
                return 15.0  # Estimate ~15 days
            else:
                return 30.0  # Estimate ~30+ days

            # TODO Phase 2: Implement proper historical lookup with archive node

        except Exception as e:
            logger.error(f"Error getting wallet age for {address}: {e}")
            return None

    @retry_with_backoff(max_retries=3, backoff_seconds=[1, 2, 4])
    def get_transaction_count(self, address: str) -> int:
        """Get total transaction count for address"""
        try:
            count = self.w3.eth.get_transaction_count(address)
            return count
        except Exception as e:
            logger.error(f"Error getting transaction count for {address}: {e}")
            return 0

    @retry_with_backoff(max_retries=3, backoff_seconds=[1, 2, 4])
    def get_balance(self, address: str) -> float:
        """Get wallet balance in MATIC"""
        try:
            balance_wei = self.w3.eth.get_balance(address)
            balance_matic = self.w3.from_wei(balance_wei, 'ether')
            return float(balance_matic)
        except Exception as e:
            logger.error(f"Error getting balance for {address}: {e}")
            return 0.0

    def analyze_funding_source(
        self,
        address: str,
        depth: int = 1
    ) -> Dict[str, any]:
        """
        Analyze wallet funding source

        Args:
            address: Wallet address
            depth: How many hops to trace back (1 for Phase 1)

        Returns:
            Funding analysis dict
        """
        try:
            # For Phase 1: Simple heuristic approach
            # Full transaction history requires archive node or indexer

            result = {
                'funding_source': 'Unknown',
                'last_cex_deposit': None,
                'is_likely_cex_funded': False
            }

            # Check transaction count as proxy for funding pattern
            tx_count = self.get_transaction_count(address)

            # Low tx count with balance = likely funded from CEX
            balance = self.get_balance(address)

            if tx_count < 5 and balance > 0:
                result['is_likely_cex_funded'] = True
                result['funding_source'] = 'Likely CEX'
                # Estimate recent funding
                result['last_cex_deposit'] = datetime.utcnow() - timedelta(days=1)

            logger.debug(f"Funding analysis for {address}: {result['funding_source']}")

            return result

            # TODO Phase 2: Implement proper transaction history parsing

        except Exception as e:
            logger.error(f"Error analyzing funding for {address}: {e}")
            return {
                'funding_source': 'Error',
                'last_cex_deposit': None,
                'is_likely_cex_funded': False
            }

    def check_ens_domain(self, address: str) -> List[str]:
        """
        Check for ENS domains (requires mainnet, not Polygon)

        For Phase 1: Return empty list (not critical)
        Phase 2: Implement ENS lookup on Ethereum mainnet
        """
        # TODO: Implement ENS lookup
        return []

    def build_wallet_profile(
        self,
        address: str,
        score_tier: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Build comprehensive wallet profile based on suspicion score

        Args:
            address: Wallet address
            score_tier: Alert tier (MEDIUM/HIGH/CRITICAL) for tiered analysis

        Returns:
            Wallet profile dict
        """
        profile = {
            'wallet_address': address,
            'first_seen': datetime.utcnow()
        }

        try:
            # Always get basic metrics
            profile['total_transactions'] = self.get_transaction_count(address)
            profile['age_days'] = self.get_wallet_age(address) or 0

            # For MEDIUM scores (50-69): Light check only
            if score_tier == 'MEDIUM':
                logger.debug(f"Light wallet check for {address}")
                return profile

            # For HIGH scores (70-89): Add funding analysis
            if score_tier in ['HIGH', 'CRITICAL']:
                funding = self.analyze_funding_source(address)
                profile.update(funding)

            # For CRITICAL scores (90-100): Deep dive
            if score_tier == 'CRITICAL':
                profile['ens_domains'] = self.check_ens_domain(address)
                profile['balance_matic'] = self.get_balance(address)

            logger.info(f"Built wallet profile for {address} (tier: {score_tier})")

            return profile

        except Exception as e:
            logger.error(f"Error building wallet profile for {address}: {e}")
            return profile
