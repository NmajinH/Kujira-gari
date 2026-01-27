"""
Market categorization and filtering logic
"""
import sys
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from pathlib import Path

# Fix imports
if __package__:
    from ..config import Config
    from ..utils.logger import setup_logger
else:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from polymarket_insider_bot.config import Config
    from polymarket_insider_bot.utils.logger import setup_logger

logger = setup_logger('market_analyzer')

class MarketAnalyzer:
    """Analyzes and categorizes Polymarket markets"""

    def __init__(self):
        self.high_risk_keywords = [kw.lower() for kw in Config.HIGH_RISK_CATEGORIES]

    def is_high_risk_category(self, market_name: str, market_description: str = "") -> bool:
        """
        Check if market is in a high-risk category for insider trading

        Args:
            market_name: Market title
            market_description: Market description (optional)

        Returns:
            True if market is high-risk category
        """
        text = f"{market_name} {market_description}".lower()

        for keyword in self.high_risk_keywords:
            if keyword in text:
                logger.debug(f"Market '{market_name}' matched keyword: {keyword}")
                return True

        return False

    def categorize_market(self, market_name: str, market_description: str = "") -> Optional[str]:
        """
        Determine market category

        Returns category name or None if not in high-risk categories
        """
        text = f"{market_name} {market_description}".lower()

        # Politics & Geopolitics
        politics_keywords = [
            'election', 'president', 'prime minister', 'senate', 'congress',
            'vote', 'ballot', 'campaign', 'cabinet', 'minister', 'governor',
            'coup', 'regime', 'sanctions', 'military', 'war', 'diplomatic'
        ]
        if any(kw in text for kw in politics_keywords):
            return "Politics & Geopolitics"

        # Business & Corporate
        business_keywords = [
            'earnings', 'revenue', 'profit', 'ebitda', 'eps',
            'acquisition', 'merger', 'buyout', 'ipo', 'ceo', 'cfo',
            'bankrupt', 'layoff'
        ]
        if any(kw in text for kw in business_keywords):
            return "Business & Corporate"

        # Tech
        tech_keywords = [
            'launch', 'release', 'announce', 'model', 'api', 'feature',
            'apple', 'google', 'microsoft', 'meta', 'amazon', 'tesla',
            'openai', 'anthropic', 'nvidia'
        ]
        if any(kw in text for kw in tech_keywords):
            return "Tech"

        # Awards & Appointments
        awards_keywords = [
            'nobel', 'oscar', 'grammy', 'emmy', 'appointment',
            'nomination', 'award'
        ]
        if any(kw in text for kw in awards_keywords):
            return "Awards & Appointments"

        # Regulatory
        regulatory_keywords = [
            'sec', 'fda', 'approve', 'regulation', 'court', 'ruling',
            'verdict', 'lawsuit', 'settlement', 'indictment'
        ]
        if any(kw in text for kw in regulatory_keywords):
            return "Regulatory"

        return None

    def should_monitor_market(
        self,
        market_name: str,
        market_volume_usd: float,
        end_date: Optional[datetime] = None,
        market_description: str = ""
    ) -> Dict[str, any]:
        """
        Determine if market should be monitored

        Returns:
            dict with 'should_monitor' boolean and 'reason' string
        """
        # Check volume threshold
        if market_volume_usd < Config.MIN_MARKET_VOLUME_USD:
            return {
                'should_monitor': False,
                'reason': f'Volume too low (${market_volume_usd:,.0f} < ${Config.MIN_MARKET_VOLUME_USD:,.0f})'
            }

        # Check expiry date
        if end_date:
            days_until_expiry = (end_date - datetime.utcnow()).days
            if days_until_expiry > Config.MAX_MARKET_DAYS_UNTIL_EXPIRY:
                return {
                    'should_monitor': False,
                    'reason': f'Too far in future ({days_until_expiry} days)'
                }
            if days_until_expiry < 0:
                return {
                    'should_monitor': False,
                    'reason': 'Market already expired'
                }

        # Check if high-risk category
        if not self.is_high_risk_category(market_name, market_description):
            return {
                'should_monitor': False,
                'reason': 'Not in high-risk category'
            }

        category = self.categorize_market(market_name, market_description)

        return {
            'should_monitor': True,
            'reason': f'High-risk category: {category}',
            'category': category
        }

    def extract_market_info(self, market_data: Dict) -> Dict:
        """
        Extract relevant market information from API response

        Args:
            market_data: Raw market data from Polymarket API

        Returns:
            Cleaned market info dict
        """
        try:
            # Handle different API response formats
            market_id = market_data.get('id') or market_data.get('condition_id')
            question = market_data.get('question') or market_data.get('title', '')
            description = market_data.get('description', '')

            # Volume can be in different fields
            volume = (
                market_data.get('volume') or
                market_data.get('volume_usd') or
                market_data.get('volumeNum', 0)
            )

            # Parse end date
            end_date_str = market_data.get('end_date') or market_data.get('endDate')
            end_date = None
            if end_date_str:
                try:
                    end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                except:
                    pass

            return {
                'market_id': market_id,
                'market_name': question,
                'description': description,
                'volume_usd': float(volume) if volume else 0,
                'end_date': end_date,
                'url': f"https://polymarket.com/event/{market_data.get('slug', market_id)}"
            }

        except Exception as e:
            logger.error(f"Error extracting market info: {e}")
            return None
