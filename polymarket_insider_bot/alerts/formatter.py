"""
Alert message formatting
"""
from typing import Dict
from datetime import datetime
from ..utils.helpers import truncate_address, format_usd, format_percentage

class AlertFormatter:
    """Formats alert messages for Telegram"""

    @staticmethod
    def format_critical_alert(
        trade_data: Dict,
        analysis: Dict,
        wallet_profile: Dict,
        market_info: Dict
    ) -> str:
        """
        Format CRITICAL alert (90-100 score) - Full detail

        Args:
            trade_data: Trade information
            analysis: Analysis results with score and flags
            wallet_profile: Wallet profile data
            market_info: Market metadata

        Returns:
            Formatted message string
        """
        score = analysis['score']
        bet_size = analysis['bet_size_usd']
        prob = analysis['probability']
        expected_profit = analysis['expected_profit']
        roi = analysis['roi_multiplier']

        market_name = market_info.get('market_name', 'Unknown Market')
        market_url = market_info.get('url', '')
        market_category = market_info.get('category', 'Unknown')
        market_volume = market_info.get('volume_usd', 0)

        wallet_addr = wallet_profile.get('wallet_address', '')
        wallet_age = wallet_profile.get('age_days', 0)
        wallet_trades = wallet_profile.get('polymarket_trades', 0)
        wallet_markets = wallet_profile.get('unique_markets', 0)
        funding_source = wallet_profile.get('funding_source', 'Unknown')
        last_cex_deposit = wallet_profile.get('last_cex_deposit')

        # Calculate concentration
        concentration = 100
        if wallet_markets > 0 and wallet_trades > 0:
            concentration = (1 - (wallet_markets / wallet_trades)) * 100

        msg = f"""🚨 CRITICAL ALERT (Score: {score}/100)

Market: "{market_name}"
🔗 {market_url}

💰 Bet Details:
├─ Size: {format_usd(bet_size)}
├─ Odds: {format_percentage(prob)} ({trade_data.get('outcome', 'YES')})
├─ Expected Profit: {format_usd(expected_profit)}
└─ Potential Return: {roi:.1f}x

👛 Wallet: {truncate_address(wallet_addr, 6)}
├─ Age: {wallet_age:.1f} days old
├─ Total Trades: {wallet_trades}
├─ Polymarket Markets: {wallet_markets}
└─ Concentration: {concentration:.0f}% {"(single market)" if wallet_markets == 1 else ""}

⚠️ RED FLAGS:"""

        # Add flags
        for flag in analysis['flags']:
            msg += f"\n• {flag} ✓"

        # Add funding info if available
        if funding_source and funding_source != 'Unknown':
            msg += f"\n• Funding: {funding_source} ✓"

        if last_cex_deposit:
            hours_ago = (datetime.utcnow() - last_cex_deposit).total_seconds() / 3600
            msg += f"\n• Fresh CEX funding ({hours_ago:.0f}h ago) ✓"

        msg += f"""

📊 Market Context:
├─ Category: {market_category}
├─ Volume: {format_usd(market_volume)}
└─ Resolution: {market_info.get('end_date', 'Unknown')}

⏰ Detected: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

        return msg

    @staticmethod
    def format_high_alert(
        trade_data: Dict,
        analysis: Dict,
        wallet_profile: Dict,
        market_info: Dict
    ) -> str:
        """
        Format HIGH alert (70-89 score) - Abbreviated format

        Args:
            trade_data: Trade information
            analysis: Analysis results
            wallet_profile: Wallet profile
            market_info: Market metadata

        Returns:
            Formatted message string
        """
        score = analysis['score']
        bet_size = analysis['bet_size_usd']
        prob = analysis['probability']
        roi = analysis['roi_multiplier']

        market_name = market_info.get('market_name', 'Unknown')
        market_url = market_info.get('url', '')

        wallet_addr = wallet_profile.get('wallet_address', '')
        wallet_age = wallet_profile.get('age_days', 0)
        wallet_trades = wallet_profile.get('polymarket_trades', 0)

        msg = f"""⚠️ HIGH ALERT (Score: {score}/100)

Market: "{market_name}"
🔗 {market_url}

💰 {format_usd(bet_size)} @ {format_percentage(prob)} ({trade_data.get('outcome', 'YES')})
    Potential: {roi:.1f}x return

👛 {truncate_address(wallet_addr, 6)}
    Age: {wallet_age:.1f}d | Trades: {wallet_trades}

⚠️ Flags: {', '.join(analysis['flags'][:3])}{"..." if len(analysis['flags']) > 3 else ""}

⏰ {datetime.utcnow().strftime('%H:%M:%S')} UTC
━━━━━━━━━━━━━━━━━━━━"""

        return msg

    @staticmethod
    def format_medium_alert(
        trade_data: Dict,
        analysis: Dict,
        wallet_profile: Dict,
        market_info: Dict
    ) -> str:
        """
        Format MEDIUM alert (50-69 score) - Compact format

        Args:
            trade_data: Trade information
            analysis: Analysis results
            wallet_profile: Wallet profile
            market_info: Market metadata

        Returns:
            Formatted message string
        """
        score = analysis['score']
        bet_size = analysis['bet_size_usd']
        prob = analysis['probability']

        market_name = market_info.get('market_name', 'Unknown')[:60]
        wallet_addr = wallet_profile.get('wallet_address', '')

        msg = f"""📊 MEDIUM (Score: {score}/100)

{market_name}...
💰 {format_usd(bet_size)} @ {format_percentage(prob)}
👛 {truncate_address(wallet_addr, 4)} | {wallet_profile.get('wallet_age', 0):.0f}d old

⏰ {datetime.utcnow().strftime('%H:%M')} UTC
━━━━━━━━━━━━━━"""

        return msg

    @staticmethod
    def format_alert(
        alert_tier: str,
        trade_data: Dict,
        analysis: Dict,
        wallet_profile: Dict,
        market_info: Dict
    ) -> str:
        """
        Format alert based on tier

        Args:
            alert_tier: CRITICAL, HIGH, or MEDIUM
            trade_data: Trade information
            analysis: Analysis results
            wallet_profile: Wallet profile
            market_info: Market metadata

        Returns:
            Formatted message
        """
        if alert_tier == 'CRITICAL':
            return AlertFormatter.format_critical_alert(
                trade_data, analysis, wallet_profile, market_info
            )
        elif alert_tier == 'HIGH':
            return AlertFormatter.format_high_alert(
                trade_data, analysis, wallet_profile, market_info
            )
        elif alert_tier == 'MEDIUM':
            return AlertFormatter.format_medium_alert(
                trade_data, analysis, wallet_profile, market_info
            )
        else:
            return "Unknown alert tier"

    @staticmethod
    def format_error_alert(error_type: str, error_message: str, context: str = "") -> str:
        """
        Format error alert for system issues

        Args:
            error_type: Type of error (API, Network, etc.)
            error_message: Error message
            context: Additional context

        Returns:
            Formatted error message
        """
        msg = f"""⚠️ SYSTEM ERROR: {error_type}

{error_message}

{context}

Retried 3x. Please investigate.

⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"""

        return msg

    @staticmethod
    def format_health_check(health_data: Dict) -> str:
        """
        Format health check message

        Args:
            health_data: Health check data

        Returns:
            Formatted health message
        """
        status_emoji = "✅" if health_data.get('status') == 'online' else "⚠️"

        uptime_seconds = health_data.get('uptime_seconds', 0)
        uptime_hours = uptime_seconds // 3600
        uptime_mins = (uptime_seconds % 3600) // 60

        msg = f"""{status_emoji} BOT HEALTH CHECK
├─ Status: {health_data.get('status', 'Unknown').upper()}
├─ Uptime: {uptime_hours}h {uptime_mins}m
├─ Markets Tracked: {health_data.get('markets_tracked', 0)}
├─ Last Scan: {health_data.get('last_scan', 'N/A')}
├─ Trades Scanned: {health_data.get('trades_scanned', 0):,}
├─ Alerts Sent Today: {health_data.get('alerts_sent_today', 0)}
└─ API Status: {"✓" if health_data.get('polymarket_status') else "✗"} Polymarket {"✓" if health_data.get('polygon_status') else "✗"} Polygon {"✓" if health_data.get('telegram_status') else "✗"} Telegram"""

        if health_data.get('error_message'):
            msg += f"\n\n⚠️ Error: {health_data['error_message']}"

        return msg
