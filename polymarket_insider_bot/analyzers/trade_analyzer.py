"""
Trade analysis and suspicion scoring
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from ..config import Config
from ..utils.logger import setup_logger

logger = setup_logger('trade_analyzer')

class TradeAnalyzer:
    """Analyzes individual trades for suspicious patterns"""

    def __init__(self):
        self.min_bet_size = Config.MIN_BET_SIZE_USD
        self.max_probability = Config.MAX_PROBABILITY

    def meets_basic_criteria(
        self,
        bet_size_usd: float,
        probability: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if trade meets basic filtering criteria

        Returns:
            (meets_criteria, reason_if_not)
        """
        if bet_size_usd < self.min_bet_size:
            return False, f"Bet size ${bet_size_usd:,.0f} below threshold"

        if probability >= self.max_probability:
            return False, f"Probability {probability*100:.1f}% above threshold"

        return True, None

    def calculate_suspicion_score(
        self,
        bet_size_usd: float,
        probability: float,
        wallet_age_days: Optional[float],
        total_trades: Optional[int],
        unique_markets: Optional[int] = None,
        is_high_risk_category: bool = False,
        recent_cex_funding: bool = False
    ) -> Tuple[int, List[str]]:
        """
        Calculate suspicion score (0-100) and identify red flags

        Args:
            bet_size_usd: Size of bet in USD
            probability: Probability of outcome (0-1)
            wallet_age_days: Age of wallet in days
            total_trades: Total number of Polymarket trades
            unique_markets: Number of unique markets traded
            is_high_risk_category: Is market in high-risk category
            recent_cex_funding: Has CEX funding within 48h

        Returns:
            (score, list_of_flags)
        """
        score = 0
        flags = []

        # Bet size scoring (0-30 points)
        if bet_size_usd > 50000:
            score += 30
            flags.append(f"Massive bet size (${bet_size_usd:,.0f})")
        elif bet_size_usd > 30000:
            score += 25
            flags.append(f"Very large bet (${bet_size_usd:,.0f})")
        elif bet_size_usd > 20000:
            score += 20
            flags.append(f"Large bet (${bet_size_usd:,.0f})")
        elif bet_size_usd > 10000:
            score += 15
            flags.append(f"Significant bet (${bet_size_usd:,.0f})")

        # Probability anomaly (0-30 points)
        prob_pct = probability * 100
        if probability < 0.02:
            score += 30
            flags.append(f"Extreme longshot ({prob_pct:.1f}%)")
        elif probability < 0.05:
            score += 25
            flags.append(f"Very low odds ({prob_pct:.1f}%)")
        elif probability < 0.10:
            score += 20
            flags.append(f"Low probability ({prob_pct:.1f}%)")
        elif probability < 0.20:
            score += 15
            flags.append(f"Below 20% odds ({prob_pct:.1f}%)")

        # Wallet freshness (0-25 points)
        if wallet_age_days is not None:
            if wallet_age_days < 1:
                score += 25
                flags.append(f"Brand new wallet (<1 day old)")
            elif wallet_age_days < 3:
                score += 20
                flags.append(f"Very fresh wallet ({wallet_age_days:.1f} days)")
            elif wallet_age_days < 7:
                score += 15
                flags.append(f"New wallet ({wallet_age_days:.1f} days)")

        # Low trade count (0-25 points, alternative to age)
        if total_trades is not None:
            if total_trades < 5:
                score += 20
                flags.append(f"Very low activity ({total_trades} trades)")
            elif total_trades < 10:
                score += 15
                flags.append(f"Low activity ({total_trades} trades)")

        # Market concentration (0-15 points)
        if unique_markets is not None and total_trades is not None and total_trades > 0:
            if unique_markets == 1:
                score += 15
                flags.append("Single market activity (100% concentration)")
            else:
                concentration = (1 - (unique_markets / total_trades)) * 100
                if concentration > 80:
                    score += 10
                    flags.append(f"High market concentration ({concentration:.0f}%)")

        # High-risk category bonus (0-10 points)
        if is_high_risk_category:
            score += 10
            flags.append("High-risk category (politics/business/regulatory)")

        # Fresh funding bonus (0-10 points)
        if recent_cex_funding:
            score += 10
            flags.append("Recent CEX funding (<48h)")

        # Cap at 100
        score = min(score, 100)

        logger.debug(f"Trade score: {score}/100 with {len(flags)} flags")

        return score, flags

    def determine_alert_tier(self, score: int) -> str:
        """
        Determine alert tier based on score

        Returns:
            CRITICAL, HIGH, MEDIUM, or None
        """
        if score >= 90:
            return "CRITICAL"
        elif score >= 70:
            return "HIGH"
        elif score >= 50:
            return "MEDIUM"
        else:
            return None

    def analyze_trade(
        self,
        trade_data: Dict,
        wallet_profile: Optional[Dict] = None,
        market_category: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Perform complete trade analysis

        Args:
            trade_data: Trade information
            wallet_profile: Wallet analysis (optional)
            market_category: Market category (optional)

        Returns:
            Analysis result dict or None if doesn't meet criteria
        """
        bet_size_usd = trade_data.get('bet_size_usd', 0)
        probability = trade_data.get('probability', 1.0)

        # Basic criteria check
        meets_criteria, reason = self.meets_basic_criteria(bet_size_usd, probability)
        if not meets_criteria:
            logger.debug(f"Trade filtered out: {reason}")
            return None

        # Extract wallet info
        wallet_age_days = None
        total_trades = None
        unique_markets = None
        recent_cex_funding = False

        if wallet_profile:
            wallet_age_days = wallet_profile.get('age_days')
            total_trades = wallet_profile.get('polymarket_trades')
            unique_markets = wallet_profile.get('unique_markets')

            # Check for recent CEX funding
            last_cex_deposit = wallet_profile.get('last_cex_deposit')
            if last_cex_deposit:
                hours_since_funding = (datetime.utcnow() - last_cex_deposit).total_seconds() / 3600
                recent_cex_funding = hours_since_funding < Config.FRESH_FUNDING_HOURS

        # Wallet criteria check
        wallet_meets_criteria = False
        if wallet_age_days is not None and wallet_age_days < Config.NEW_WALLET_AGE_DAYS:
            wallet_meets_criteria = True
        elif total_trades is not None and total_trades < Config.LOW_TRADE_COUNT:
            wallet_meets_criteria = True

        if not wallet_meets_criteria and wallet_profile is not None:
            logger.debug("Trade filtered: wallet doesn't meet age/trade criteria")
            return None

        # Calculate score
        is_high_risk = market_category is not None
        score, flags = self.calculate_suspicion_score(
            bet_size_usd=bet_size_usd,
            probability=probability,
            wallet_age_days=wallet_age_days,
            total_trades=total_trades,
            unique_markets=unique_markets,
            is_high_risk_category=is_high_risk,
            recent_cex_funding=recent_cex_funding
        )

        # Determine alert tier
        alert_tier = self.determine_alert_tier(score)

        if not alert_tier:
            logger.debug(f"Trade score {score} below alert threshold")
            return None

        return {
            'score': score,
            'alert_tier': alert_tier,
            'flags': flags,
            'bet_size_usd': bet_size_usd,
            'probability': probability,
            'expected_profit': (bet_size_usd / probability) - bet_size_usd if probability > 0 else 0,
            'roi_multiplier': 1 / probability if probability > 0 else 0
        }

    def format_trade_summary(self, analysis: Dict, trade_data: Dict) -> str:
        """
        Generate human-readable trade summary

        Args:
            analysis: Analysis results
            trade_data: Original trade data

        Returns:
            Formatted summary string
        """
        lines = [
            f"Score: {analysis['score']}/100 ({analysis['alert_tier']})",
            f"Bet: ${analysis['bet_size_usd']:,.0f} @ {analysis['probability']*100:.1f}%",
            f"Potential Return: {analysis['roi_multiplier']:.1f}x (${analysis['expected_profit']:,.0f} profit)",
            f"\nRed Flags ({len(analysis['flags'])}):"
        ]

        for flag in analysis['flags']:
            lines.append(f"  • {flag}")

        return "\n".join(lines)
