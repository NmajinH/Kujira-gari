"""
Telegram bot client for sending alerts
"""
from telegram import Bot
from telegram.error import TelegramError
import asyncio
import sys
from typing import Dict, Optional
from pathlib import Path

# Fix imports
if __package__:
    from ..config import Config
    from ..utils.logger import setup_logger
    from ..utils.helpers import retry_with_backoff
    from .formatter import AlertFormatter
else:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from polymarket_insider_bot.config import Config
    from polymarket_insider_bot.utils.logger import setup_logger
    from polymarket_insider_bot.utils.helpers import retry_with_backoff
    from polymarket_insider_bot.alerts.formatter import AlertFormatter

logger = setup_logger('telegram')

class TelegramAlertBot:
    """Telegram bot for sending alerts"""

    def __init__(self, token: str = None, chat_id: str = None):
        """
        Initialize Telegram bot

        Args:
            token: Bot token
            chat_id: Chat ID to send messages to
        """
        self.token = token or Config.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or Config.TELEGRAM_CHAT_ID

        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not configured")

        if not self.chat_id:
            logger.warning("TELEGRAM_CHAT_ID not configured - alerts won't be sent")

        self.bot = Bot(token=self.token)
        self.formatter = AlertFormatter()

        logger.info(f"Telegram bot initialized (chat_id: {self.chat_id})")

    @retry_with_backoff(
        max_retries=3,
        backoff_seconds=[1, 2, 4],
        exceptions=(TelegramError,)
    )
    async def send_message(self, message: str, parse_mode: str = None) -> bool:
        """
        Send message to configured chat

        Args:
            message: Message text
            parse_mode: Parse mode (Markdown, HTML, or None)

        Returns:
            True if sent successfully
        """
        if not self.chat_id:
            logger.error("Cannot send message: TELEGRAM_CHAT_ID not configured")
            return False

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode,
                disable_web_page_preview=True
            )
            logger.info("Telegram message sent successfully")
            return True

        except TelegramError as e:
            logger.error(f"Failed to send Telegram message: {e}")
            raise

    async def send_alert(
        self,
        alert_tier: str,
        trade_data: Dict,
        analysis: Dict,
        wallet_profile: Dict,
        market_info: Dict
    ) -> bool:
        """
        Send formatted alert

        Args:
            alert_tier: CRITICAL, HIGH, or MEDIUM
            trade_data: Trade information
            analysis: Analysis results
            wallet_profile: Wallet profile
            market_info: Market metadata

        Returns:
            True if sent successfully
        """
        try:
            message = self.formatter.format_alert(
                alert_tier=alert_tier,
                trade_data=trade_data,
                analysis=analysis,
                wallet_profile=wallet_profile,
                market_info=market_info
            )

            success = await self.send_message(message)

            if success:
                logger.info(f"Sent {alert_tier} alert for trade {trade_data.get('trade_id')}")

            return success

        except Exception as e:
            logger.error(f"Error sending alert: {e}")
            return False

    async def send_error_alert(
        self,
        error_type: str,
        error_message: str,
        context: str = ""
    ) -> bool:
        """
        Send error alert

        Args:
            error_type: Error type
            error_message: Error message
            context: Additional context

        Returns:
            True if sent successfully
        """
        try:
            message = self.formatter.format_error_alert(
                error_type, error_message, context
            )
            return await self.send_message(message)

        except Exception as e:
            logger.error(f"Failed to send error alert: {e}")
            return False

    async def send_health_check(self, health_data: Dict) -> bool:
        """
        Send health check message

        Args:
            health_data: Health check data

        Returns:
            True if sent successfully
        """
        try:
            message = self.formatter.format_health_check(health_data)
            return await self.send_message(message)

        except Exception as e:
            logger.error(f"Failed to send health check: {e}")
            return False

    async def test_connection(self) -> bool:
        """
        Test Telegram bot connection

        Returns:
            True if connection works
        """
        try:
            bot_info = await self.bot.get_me()
            logger.info(f"Connected to Telegram bot: @{bot_info.username}")

            if self.chat_id:
                test_msg = f"✅ Bot connection test successful!\n\nBot: @{bot_info.username}\nChat ID: {self.chat_id}"
                self.send_message(test_msg)

            return True

        except TelegramError as e:
            logger.error(f"Telegram connection test failed: {e}")
            return False

    def get_chat_id_from_updates(self) -> Optional[str]:
        """
        Get chat ID from recent messages (helper for setup)

        Returns:
            Chat ID if found
        """
        try:
            updates = self.bot.get_updates()

            if updates:
                latest_update = updates[-1]
                chat_id = latest_update.message.chat_id
                logger.info(f"Found chat ID from updates: {chat_id}")
                return str(chat_id)
            else:
                logger.warning("No updates found. Send a message to the bot first.")
                return None

        except TelegramError as e:
            logger.error(f"Error getting updates: {e}")
            return None
