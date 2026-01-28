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
        self.data_api_url = "https://data-api.polymarket.com"  # Public API - no auth required
        self.api_key = Config.POLYMARKET_API_KEY

        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}'
            })

        logger.info("Polymarket API client initialized (using Data API for trades)")

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
    def get_trades_from_data_api(
        self,
        limit: int = 100,
        since_timestamp: Optional[int] = None,
        market_ids: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Get recent trades from Polymarket Data API (public, no auth required)

        Based on: https://data-api.polymarket.com/trades
        Documentation: https://gist.github.com/shaunlebron/0dd3338f7dea06b8e9f8724981bb13bf

        Args:
            limit: Number of trades to fetch (max 500)
            since_timestamp: Only trades after this timestamp (Unix timestamp in seconds)
            market_ids: Optional list of market condition IDs to filter by (supports CSV)

        Returns:
            List of trade dicts from Data API
        """
        try:
            url = f"{self.data_api_url}/trades"

            # Build parameters
            params = {
                'limit': min(limit, 500),  # Data API max is 500
            }

            # Add time filter if specified
            # Data API uses 'after' parameter for timestamp filtering
            if since_timestamp:
                params['after'] = since_timestamp

            # Add market filter if specified
            # Data API accepts comma-separated market IDs
            if market_ids:
                # Limit to reasonable number of markets to avoid URL length issues
                if len(market_ids) > 100:
                    logger.warning(f"Too many markets ({len(market_ids)}), limiting to first 100")
                    market_ids = market_ids[:100]
                params['market'] = ','.join(market_ids)
                logger.debug(f"Filtering trades for {len(market_ids)} markets")

            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()

            trades = response.json()

            if not isinstance(trades, list):
                logger.error(f"Unexpected response format: {type(trades)}")
                return []

            if market_ids:
                logger.info(f"Fetched {len(trades)} trades from {len(market_ids)} filtered markets")
            else:
                logger.info(f"Fetched {len(trades)} trades from Data API")

            return trades

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching trades from Data API: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in Data API query: {e}")
            return []

    @retry_with_backoff(max_retries=3, backoff_seconds=[1, 2, 4])
    def get_all_recent_trades(
        self,
        limit: int = 500,
        since_timestamp: Optional[int] = None,
        market_ids: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Get recent trades across all markets or specific markets

        Now uses Data API instead of CLOB API (which requires auth) or Subgraph (deprecated)

        Args:
            limit: Number of trades to fetch (max 500)
            since_timestamp: Only trades after this timestamp (Unix timestamp)
            market_ids: Optional list of market condition IDs to filter by

        Returns:
            List of trade dicts
        """
        # Use Data API - public endpoint, no auth required
        logger.info("Fetching trades from Polymarket Data API...")
        return self.get_trades_from_data_api(limit, since_timestamp, market_ids)

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

        Handles Data API format (primary), CLOB API format, and legacy Subgraph format

        Data API format (from https://data-api.polymarket.com/trades):
        - id: Trade ID
        - asset: Token contract address
        - conditionId: Market condition ID
        - size: Trade size in USDC (6 decimals)
        - price: Execution price (0-1)
        - side: BUY or SELL
        - timestamp: Unix timestamp (seconds)
        - user: Wallet address (optional field)
        - proxyWallet: Proxy wallet address

        Args:
            trade_raw: Raw trade data from API

        Returns:
            Parsed trade dict or None if invalid
        """
        try:
            # Extract trade ID
            trade_id = trade_raw.get('id') or trade_raw.get('trade_id')
            if not trade_id:
                logger.debug(f"❌ Parse failed: No trade ID found in {list(trade_raw.keys())}")
                return None

            # Extract wallet address
            # Data API: 'user' field (if available), otherwise 'proxyWallet'
            # Legacy: 'creator.id', 'taker_address', 'maker_address', 'address'
            wallet = None
            if 'user' in trade_raw:
                wallet = trade_raw['user']
            elif 'proxyWallet' in trade_raw:
                wallet = trade_raw['proxyWallet']
            elif 'creator' in trade_raw:
                # Legacy Subgraph format
                creator = trade_raw['creator']
                wallet = creator.get('id') if isinstance(creator, dict) else creator
            elif 'taker_address' in trade_raw:
                wallet = trade_raw['taker_address']
            elif 'maker_address' in trade_raw:
                wallet = trade_raw['maker_address']
            elif 'address' in trade_raw:
                wallet = trade_raw['address']

            if not wallet:
                logger.debug(f"❌ Parse failed for trade {trade_id}: No wallet address found. Available fields: {list(trade_raw.keys())}")
                return None

            # Extract bet size from Data API
            # Data API returns 'size' field already in USD (e.g., 5.36842 = $5.36)

            # Data API 'size' field is ALREADY in USD - no conversion needed!
            # Example: 'size': 5.36842 = $5.36 USD (not wei format)
            size_raw = trade_raw.get('size')
            if size_raw is not None:
                try:
                    bet_size_usd = float(size_raw)
                    if not hasattr(self, '_logged_size_conversion'):
                        logger.info(f"✅ Size parsing: {size_raw} → ${bet_size_usd} USD (direct, no conversion)")
                        self._logged_size_conversion = True
                except:
                    bet_size_usd = 0
            elif 'usdcSize' in trade_raw:
                # Alternative field name
                usdc_size = trade_raw.get('usdcSize')
                try:
                    bet_size_usd = float(usdc_size)
                except:
                    bet_size_usd = 0
            elif 'collateralAmount' in trade_raw:
                # Legacy Subgraph format (6 decimals)
                collateral_raw = trade_raw.get('collateralAmount', 0)
                try:
                    bet_size_usd = float(collateral_raw) / 1e6
                except:
                    bet_size_usd = 0
            else:
                bet_size_usd = 0
                logger.warning(f"Trade {trade_id}: No size field found!")

            # Extract price/probability
            # Data API: 'price' field (0-1 decimal)
            price_raw = trade_raw.get('price', 0)
            if price_raw:
                probability = float(price_raw)
                # If price is in basis points (>1), convert to decimal
                if probability > 1:
                    probability = probability / 10000
            elif 'outcomeTokensAmount' in trade_raw:
                # Legacy Subgraph: calculate from tokens/collateral
                outcome_tokens = float(trade_raw.get('outcomeTokensAmount', 0))
                collateral = float(trade_raw.get('collateralAmount', 1))
                if collateral > 0 and outcome_tokens > 0:
                    probability = min(collateral / outcome_tokens, 1.0)
                else:
                    probability = 0.5
            else:
                probability = 0.5

            # Extract market ID
            # Data API: 'conditionId' field
            market_id = trade_raw.get('conditionId')
            if not market_id:
                # Try other field names
                if 'fpmm' in trade_raw:
                    # Legacy Subgraph format
                    fpmm = trade_raw['fpmm']
                    condition = fpmm.get('condition', {}) if isinstance(fpmm, dict) else {}
                    market_id = condition.get('id') if isinstance(condition, dict) else None
                else:
                    market_id = (
                        trade_raw.get('market') or
                        trade_raw.get('market_id') or
                        trade_raw.get('asset_id')
                    )

            # Extract outcome/side
            # Data API: 'side' field (BUY/SELL)
            side = trade_raw.get('side', '').upper()
            if side in ['BUY', 'SELL']:
                outcome = 'YES' if side == 'BUY' else 'NO'
            elif 'outcome' in trade_raw:
                outcome = trade_raw['outcome']
            elif 'type' in trade_raw:
                # Legacy Subgraph format
                trade_type = trade_raw.get('type', '')
                outcome = 'YES' if trade_type == 'Buy' else 'NO'
            else:
                outcome = 'YES'  # Default

            # Extract timestamp
            # Data API: 'timestamp' field (Unix timestamp in seconds)
            ts_raw = trade_raw.get('timestamp') or trade_raw.get('creationTimestamp') or trade_raw.get('created_at')
            if ts_raw:
                try:
                    if isinstance(ts_raw, str):
                        # ISO format string
                        timestamp = datetime.fromisoformat(ts_raw.replace('Z', '+00:00'))
                    else:
                        # Unix timestamp
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

    def get_filtered_markets(
        self,
        high_risk_keywords: List[str],
        exclude_keywords: List[str],
        min_volume: float = 1000
    ) -> List[Dict]:
        """
        Get active markets filtered by category keywords

        Args:
            high_risk_keywords: Keywords to include (Politics, Business, Tech, etc.)
            exclude_keywords: Keywords to exclude (Sports, Crypto, etc.)
            min_volume: Minimum market volume in USD

        Returns:
            List of filtered market dicts with condition IDs
        """
        try:
            # Fetch active markets (fetch in batches if needed)
            all_markets = []
            offset = 0
            batch_size = 100

            while True:
                markets = self.get_markets(limit=batch_size, offset=offset, active=True)
                if not markets:
                    break
                all_markets.extend(markets)
                offset += batch_size

                # Stop if we got less than batch size (no more markets)
                if len(markets) < batch_size:
                    break

                # Safety limit: max 500 markets
                if len(all_markets) >= 500:
                    break

            logger.info(f"Fetched {len(all_markets)} total active markets")

            # Filter by keywords
            filtered_markets = []
            for market in all_markets:
                # Get market text fields
                question = market.get('question', '').lower()
                description = market.get('description', '').lower()
                title = market.get('title', question).lower()  # Some APIs use 'title' instead
                text = f"{question} {description} {title}"

                # Check exclusions first
                if any(keyword.lower() in text for keyword in exclude_keywords):
                    continue

                # Check inclusions
                if any(keyword.lower() in text for keyword in high_risk_keywords):
                    # Check volume threshold
                    volume = float(market.get('volume', 0))
                    if volume >= min_volume:
                        filtered_markets.append(market)

            logger.info(f"Filtered to {len(filtered_markets)} high-risk markets")
            return filtered_markets

        except Exception as e:
            logger.error(f"Error filtering markets: {e}")
            return []

    def scan_recent_trades(
        self,
        min_bet_size: float = 10000,
        lookback_seconds: int = 300,
        market_ids: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Scan for recent large trades, optionally filtered by markets

        Args:
            min_bet_size: Minimum bet size in USD
            lookback_seconds: How far back to look
            market_ids: Optional list of market condition IDs to filter by

        Returns:
            List of parsed trades meeting criteria
        """
        since_timestamp = int(time.time() - lookback_seconds)

        raw_trades = self.get_all_recent_trades(
            limit=500,
            since_timestamp=since_timestamp,
            market_ids=market_ids
        )

        # DEBUG: Log sample raw trade
        if raw_trades:
            import json
            logger.info(f"📊 Sample raw trade structure:")
            logger.info(json.dumps(raw_trades[0], indent=2))

        logger.info(f"🔍 FILTER DEBUG: Checking {len(raw_trades)} raw trades against MIN_BET_SIZE=${min_bet_size}")

        parsed_trades = []
        failed_parse = 0
        failed_size = 0

        for i, raw_trade in enumerate(raw_trades):
            trade = self.parse_trade(raw_trade)

            if not trade:
                failed_parse += 1
                continue

            # DEBUG: Log first 5 trades
            if i < 5:
                passes = trade['bet_size_usd'] >= min_bet_size
                logger.info(f"  Trade {i+1}: size=${trade['bet_size_usd']:.2f}, passes size filter? {'YES' if passes else 'NO'} (threshold=${min_bet_size})")

            if trade['bet_size_usd'] >= min_bet_size:
                parsed_trades.append(trade)
            else:
                failed_size += 1

        # Summary logging
        logger.info(f"📊 FILTER RESULTS:")
        logger.info(f"   - Total raw trades: {len(raw_trades)}")
        logger.info(f"   - Failed to parse: {failed_parse}")
        logger.info(f"   - Parsed successfully: {len(raw_trades) - failed_parse}")
        logger.info(f"   - Failed size filter (<${min_bet_size}): {failed_size}")
        logger.info(f"   - PASSED all filters: {len(parsed_trades)}")

        if market_ids:
            logger.info(f"Scanned {len(raw_trades)} trades from {len(market_ids)} filtered markets, found {len(parsed_trades)} meeting size criteria")
        else:
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
