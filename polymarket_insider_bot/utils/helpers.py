"""
Utility helper functions
"""
import time
from typing import Callable, Any, Optional
from functools import wraps
from .logger import setup_logger

logger = setup_logger('helpers')

def retry_with_backoff(
    max_retries: int = 3,
    backoff_seconds: list = [1, 2, 4],
    exceptions: tuple = (Exception,)
):
    """
    Decorator to retry a function with exponential backoff

    Args:
        max_retries: Maximum number of retry attempts
        backoff_seconds: List of wait times between retries
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = backoff_seconds[min(attempt, len(backoff_seconds) - 1)]
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries}): {e}. "
                            f"Retrying in {wait_time}s..."
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} attempts: {e}"
                        )

            raise last_exception

        return wrapper
    return decorator

def truncate_address(address: str, chars: int = 6) -> str:
    """
    Truncate Ethereum address for display

    Args:
        address: Full Ethereum address
        chars: Number of characters to show on each end

    Returns:
        Truncated address like "0xSBet...4bf2"
    """
    if not address or len(address) < chars * 2:
        return address

    return f"{address[:chars]}...{address[-chars:]}"

def format_usd(amount: float) -> str:
    """Format USD amount with commas"""
    return f"${amount:,.0f}"

def format_percentage(value: float) -> str:
    """Format decimal as percentage"""
    return f"{value * 100:.1f}%"

def calculate_expected_profit(bet_size: float, odds: float) -> float:
    """
    Calculate expected profit from a bet

    Args:
        bet_size: Bet size in USD
        odds: Probability as decimal (e.g., 0.018 for 1.8%)

    Returns:
        Expected profit if bet wins
    """
    if odds <= 0 or odds >= 1:
        return 0

    return (bet_size / odds) - bet_size

def calculate_roi_multiplier(odds: float) -> float:
    """Calculate ROI multiplier (e.g., 5.5x)"""
    if odds <= 0 or odds >= 1:
        return 0

    return 1 / odds
