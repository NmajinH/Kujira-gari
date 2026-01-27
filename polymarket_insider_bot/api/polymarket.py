"""
Polymarket API client for market and trade data
"""
import requests
import time
import sys
from typing import Dict, List, Optional
from datetime import datetime
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

logger = setup_logger('polymarket_api')

class PolymarketAPI:
    """Polymarket REST API client"""

    def __init__(self):
        self.rest_url = Config.POLYMARKET_REST_URL
        self.gamma_url = Config.POLYMARKET_GAMMA_URL
        self.subgraph_url = "https://api.thegraph.com/subgraphs/name/polymarket/matic-markets"
        self.api_key = Config.POLYMARKET_API_KEY

        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}'
            })

        logger.info("Polymarket API client initialized (using Subgraph for trades)")

    @retry_with_backoff(max_retries=3, backoff_seconds=[1, 2, 4])
    def get_markets(
        self,
        limit: int = 100,
        offset: int = 0,
        active: bool = True
    ) -> List[Dict]:
        """
        Get list of markets from Gamma API

        Args:
            limit: Number of markets to fetch
            offset: Offset for pagination
            active: Only active markets

        Returns:
            List of market dicts
        """
        try:
            params = {
                'limit': limit,
                'offset': offset,
                'active': str(active).lower()
            }

            url = f"{self.gamma_url}/markets"
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Handle different response formats
            if isinstance(data, list):
                markets = data
            elif isinstance(data, dict) and 'data' in data:
                markets = data['data']
            else:
                markets = []

            logger.debug(f"Fetched {len(markets)} markets")
            return markets

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching markets: {e}")
            raise

    @retry_with_backoff(max_retries=3, backoff_seconds=[1, 2, 4])
    def get_market_trades(
        self,
        market_id: str,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get recent trades for a market

        Args:
            market_id: Market/condition ID
            limit: Number of trades to fetch

        Returns:
            List of trade dicts
        """
        try:
            # Try CLOB API endpoint
            url = f"{self.rest_url}/trades"
            params = {
                'market': market_id,
                'limit': limit
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            trades = response.json()

            if not isinstance(trades, list):
                trades = []

            logger.debug(f"Fetched {len(trades)} trades for market {market_id}")
            return trades

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching trades for {market_id}: {e}")
            return []

    @retry_with_backoff(max_retries=3, backoff_seconds=[1, 2, 4])
    def get_trades_from_subgraph(
        self,
        limit: int = 100,
        since_timestamp: Optional[int] = None
    ) -> List[Dict]:
        """
        Get recent trades from Polymarket Subgraph (public, no auth required)

        Args:
            limit: Number of trades to fetch
            since_timestamp: Only trades after this timestamp

        Returns:
            List of trade dicts from Subgraph
        """
        try:
            # GraphQL query to get recent trades
            # The Subgraph tracks fpmmTrades (Fixed Product Market Maker trades)
            query = """
            query GetRecentTrades($limit: Int!, $timestamp: Int) {
              fpmmTrades(
                first: $limit,
                orderBy: creationTimestamp,
                orderDirection: desc,
                where: { creationTimestamp_gt: $timestamp }
              ) {
                id
                fpmm {
                  id
                  condition {
                    id
                  }
                }
                creator {
                  id
                }
                creationTimestamp
                collateralAmount
                outcomeTokensAmount
                type
              }
            }
            """

            variables = {
                "limit": min(limit, 1000),  # Subgraph has max 1000
                "timestamp": since_timestamp or 0
            }

            response = self.session.post(
                self.subgraph_url,
                json={'query': query, 'variables': variables},
                timeout=15
            )
            response.raise_for_status()

            data = response.json()

            if 'errors' in data:
                logger.error(f"Subgraph query errors: {data['errors']}")
                return []

            trades = data.get('data', {}).get('fpmmTrades', [])
            logger.info(f"Fetched {len(trades)} trades from Subgraph")

            return trades

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching trades from Subgraph: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in Subgraph query: {e}")
            return []

    @retry_with_backoff(max_retries=3, backoff_seconds=[1, 2, 4])
    def get_all_recent_trades(
        self,
        limit: int = 500,
        since_timestamp: Optional[int] = None
    ) -> List[Dict]:
        """
        Get recent trades across all markets

        Now uses Subgraph instead of CLOB API (which requires auth)

        Args:
            limit: Number of trades to fetch
            since_timestamp: Only trades after this timestamp

        Returns:
            List of trade dicts
        """
        # Use Subgraph instead of CLOB API
        logger.info("Fetching trades from Polymarket Subgraph...")
        return self.get_trades_from_subgraph(limit, since_timestamp)

    @retry_with_backoff(max_retries=3, backoff_seconds=[1, 2, 4])
    def get_market_by_id(self, market_id: str) -> Optional[Dict]:
        """
        Get market details by ID

        Args:
            market_id: Market ID

        Returns:
            Market dict or None
        """
        try:
            url = f"{self.gamma_url}/markets/{market_id}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            market = response.json()
            return market

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching market {market_id}: {e}")
            return None

    def parse_trade(self, trade_raw: Dict) -> Optional[Dict]:
        """
        Parse raw trade data into standardized format

        Handles both CLOB API format and Subgraph format

        Args:
            trade_raw: Raw trade data from API or Subgraph

        Returns:
            Parsed trade dict or None if invalid
        """
        try:
            # Detect format: Subgraph has 'fpmm' and 'creator', CLOB has 'taker_address'
            is_subgraph = 'fpmm' in trade_raw or 'creator' in trade_raw

            # Extract trade ID
            trade_id = trade_raw.get('id') or trade_raw.get('trade_id')
            if not trade_id:
                return None

            # Extract wallet address
            if is_subgraph:
                # Subgraph format: creator.id
                creator = trade_raw.get('creator', {})
                wallet = creator.get('id') if isinstance(creator, dict) else None
            else:
                # CLOB format: taker_address, maker_address, or address
                wallet = (
                    trade_raw.get('taker_address') or
                    trade_raw.get('maker_address') or
                    trade_raw.get('address')
                )

            if not wallet:
                logger.debug(f"Trade {trade_id}: No wallet address found")
                return None

            # Extract bet size
            if is_subgraph:
                # Subgraph format: collateralAmount in Wei (18 decimals)
                collateral_raw = trade_raw.get('collateralAmount', 0)
                try:
                    bet_size_usd = float(collateral_raw) / 1e6  # USDC has 6 decimals
                except:
                    bet_size_usd = 0
            else:
                # CLOB format: size or amount (usually 6 decimals)
                size_raw = (
                    trade_raw.get('size') or
                    trade_raw.get('amount') or
                    0
                )
                bet_size_usd = float(size_raw) / 1e6 if size_raw else 0

            # Extract price/probability
            if is_subgraph:
                # Subgraph: calculate from outcomeTokensAmount / collateralAmount
                outcome_tokens = float(trade_raw.get('outcomeTokensAmount', 0))
                collateral = float(trade_raw.get('collateralAmount', 1))
                if collateral > 0:
                    probability = min(collateral / outcome_tokens, 1.0) if outcome_tokens > 0 else 0.5
                else:
                    probability = 0.5  # Default if we can't calculate
            else:
                # CLOB format: price field
                price_raw = trade_raw.get('price', 0)
                probability = float(price_raw) if price_raw else 0

                # If price is in basis points (0-10000), convert to decimal
                if probability > 1:
                    probability = probability / 10000

            # Extract market ID
            if is_subgraph:
                # Subgraph format: fpmm.condition.id
                fpmm = trade_raw.get('fpmm', {})
                condition = fpmm.get('condition', {}) if isinstance(fpmm, dict) else {}
                market_id = condition.get('id') if isinstance(condition, dict) else None
            else:
                # CLOB format: market, market_id, or asset_id
                market_id = (
                    trade_raw.get('market') or
                    trade_raw.get('market_id') or
                    trade_raw.get('asset_id')
                )

            # Extract outcome (YES/NO)
            if is_subgraph:
                # Subgraph: type is BUY or SELL
                trade_type = trade_raw.get('type', '')
                outcome = 'YES' if trade_type == 'Buy' else 'NO'
            else:
                outcome = trade_raw.get('outcome') or trade_raw.get('side')

            # Timestamp
            if is_subgraph:
                # Subgraph: creationTimestamp (Unix timestamp)
                ts_raw = trade_raw.get('creationTimestamp')
                try:
                    timestamp = datetime.fromtimestamp(int(ts_raw)) if ts_raw else datetime.utcnow()
                except:
                    timestamp = datetime.utcnow()
            else:
                # CLOB: timestamp or created_at
                ts_raw = trade_raw.get('timestamp') or trade_raw.get('created_at')
                if ts_raw:
                    try:
                        if isinstance(ts_raw, str):
                            timestamp = datetime.fromisoformat(ts_raw.replace('Z', '+00:00'))
                        else:
                            timestamp = datetime.fromtimestamp(int(ts_raw))
                    except:
                        timestamp = datetime.utcnow()
                else:
                    timestamp = datetime.utcnow()

            return {
                'trade_id': str(trade_id),
                'wallet_address': wallet,
                'bet_size_usd': bet_size_usd,
                'probability': probability,
                'market_id': market_id,
                'outcome': outcome,
                'timestamp': timestamp
            }

        except Exception as e:
            logger.error(f"Error parsing trade: {e}")
            return None

    def scan_recent_trades(
        self,
        min_bet_size: float = 10000,
        lookback_seconds: int = 300
    ) -> List[Dict]:
        """
        Scan for recent large trades

        Args:
            min_bet_size: Minimum bet size in USD
            lookback_seconds: How far back to look

        Returns:
            List of parsed trades meeting criteria
        """
        since_timestamp = int(time.time() - lookback_seconds)

        raw_trades = self.get_all_recent_trades(
            limit=500,
            since_timestamp=since_timestamp
        )

        parsed_trades = []
        for raw_trade in raw_trades:
            trade = self.parse_trade(raw_trade)
            if trade and trade['bet_size_usd'] >= min_bet_size:
                parsed_trades.append(trade)

        logger.info(f"Scanned {len(raw_trades)} trades, found {len(parsed_trades)} meeting size criteria")

        return parsed_trades

    def get_market_price_history(
        self,
        market_id: str,
        hours: int = 2
    ) -> Optional[Dict]:
        """
        Get price history for price movement calculation

        For Phase 1: Return None (not critical)
        Phase 2: Implement price history analysis
        """
        # TODO: Implement price history
        return None
