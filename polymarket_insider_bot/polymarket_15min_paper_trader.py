#!/usr/bin/env python3
"""
Polymarket 15-Minute Paper Trading Bot

Scans for 15-min crypto prediction markets on Polymarket,
tracks BTC price via Binance WebSocket, and paper trades
opportunities when market price diverges from predicted outcome.

NO REAL TRADING - Paper mode only.
"""

import sys
import os
import time
import json
import csv
import threading
import requests
import websocket
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import deque

# Ensure we can import config from the same package
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

# Load .env from the same directory as this script
load_dotenv(Path(__file__).parent / '.env')

from config import Config


# ---------------------------------------------------------------------------
# Binance Price Tracker
# ---------------------------------------------------------------------------

class BinancePriceTracker:
    """Tracks real-time BTC/USDT price via Binance WebSocket."""

    WS_URL = "wss://stream.binance.com:9443/ws/btcusdt@trade"

    def __init__(self):
        self.current_price = None
        self.price_history = deque(maxlen=2000)
        self.ws = None
        self.running = False
        self._lock = threading.Lock()

    def start(self):
        """Start the WebSocket listener in a background thread."""
        self.running = True
        thread = threading.Thread(target=self._run_ws, daemon=True)
        thread.start()

    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()

    # -- WebSocket callbacks --------------------------------------------------

    def _run_ws(self):
        while self.running:
            try:
                self.ws = websocket.WebSocketApp(
                    self.WS_URL,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                    on_open=self._on_open,
                )
                self.ws.run_forever(ping_interval=30, ping_timeout=10)
            except Exception as e:
                print(f"[WS ERROR] {e}")

            if self.running:
                print("[WS] Reconnecting in 5s...")
                time.sleep(5)

    def _on_open(self, ws):
        print("[WS] Connected to Binance BTC/USDT stream")

    def _on_message(self, ws, message):
        data = json.loads(message)
        price = float(data["p"])
        ts = datetime.now(timezone.utc)
        with self._lock:
            self.current_price = price
            self.price_history.append((ts, price))

    def _on_error(self, ws, error):
        print(f"[WS ERROR] {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        print(f"[WS] Closed ({close_status_code})")

    # -- Public helpers -------------------------------------------------------

    def get_price(self):
        """Return current BTC price or None."""
        with self._lock:
            return self.current_price

    def get_price_change_pct(self, minutes=15):
        """Return % change in BTC price over the last *minutes* minutes."""
        with self._lock:
            if not self.price_history or self.current_price is None:
                return None

            cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
            oldest_price = None
            for ts, price in self.price_history:
                if ts >= cutoff:
                    oldest_price = price
                    break

            if oldest_price is None or oldest_price == 0:
                return None

            return ((self.current_price - oldest_price) / oldest_price) * 100


# ---------------------------------------------------------------------------
# Market Scanner
# ---------------------------------------------------------------------------

class MarketScanner:
    """Queries the Polymarket Gamma API for 15-minute crypto markets."""

    def __init__(self):
        self.gamma_url = Config.POLYMARKET_GAMMA_URL
        self.tracked_markets = {}  # condition_id -> parsed dict

    def scan_markets(self):
        """Fetch active markets and filter for 15-min crypto/BTC ones."""
        try:
            params = {
                "active": "true",
                "closed": "false",
                "limit": 100,
            }

            resp = requests.get(
                f"{self.gamma_url}/markets",
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            markets = resp.json()

            crypto_15min = []
            crypto_kw = ["btc", "bitcoin", "crypto"]
            time_kw = ["15 min", "15min", "15-min", "15 minute"]

            for mkt in markets:
                question = (mkt.get("question") or "").lower()
                description = (mkt.get("description") or "").lower()
                combined = question + " " + description

                is_crypto = any(kw in combined for kw in crypto_kw)
                is_15min = any(kw in combined for kw in time_kw)

                if is_crypto and is_15min:
                    crypto_15min.append(mkt)
                elif is_crypto and "price" in combined:
                    # Also pick up short-duration BTC price markets
                    end_str = mkt.get("end_date_iso") or mkt.get("endDate")
                    if end_str:
                        try:
                            end_dt = datetime.fromisoformat(
                                end_str.replace("Z", "+00:00")
                            )
                            secs_left = (
                                end_dt - datetime.now(timezone.utc)
                            ).total_seconds()
                            if 0 < secs_left < 1200:  # within 20 min
                                crypto_15min.append(mkt)
                        except (ValueError, TypeError):
                            pass

            # Update tracking dict
            for mkt in crypto_15min:
                cid = (
                    mkt.get("condition_id")
                    or mkt.get("conditionId")
                    or mkt.get("id")
                )
                if cid:
                    self.tracked_markets[cid] = self._parse_market(mkt)

            # Prune expired
            now = datetime.now(timezone.utc)
            expired = [
                cid
                for cid, m in self.tracked_markets.items()
                if m.get("end_time")
                and m["end_time"] < now - timedelta(minutes=5)
            ]
            for cid in expired:
                del self.tracked_markets[cid]

            return crypto_15min

        except requests.RequestException as e:
            print(f"[SCANNER ERROR] {e}")
            return []

    def _parse_market(self, mkt):
        """Normalise raw Gamma market data."""
        end_str = mkt.get("end_date_iso") or mkt.get("endDate") or ""
        end_time = None
        if end_str:
            try:
                end_time = datetime.fromisoformat(
                    end_str.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        outcomes = mkt.get("outcomes", [])
        raw_prices = mkt.get("outcomePrices", [])
        if isinstance(raw_prices, str):
            try:
                raw_prices = json.loads(raw_prices)
            except (json.JSONDecodeError, TypeError):
                raw_prices = []

        yes_price = None
        no_price = None
        try:
            if len(raw_prices) > 0:
                yes_price = float(raw_prices[0])
            if len(raw_prices) > 1:
                no_price = float(raw_prices[1])
        except (ValueError, TypeError, IndexError):
            pass

        return {
            "id": (
                mkt.get("condition_id")
                or mkt.get("conditionId")
                or mkt.get("id")
            ),
            "question": mkt.get("question", "Unknown"),
            "end_time": end_time,
            "yes_price": yes_price,
            "no_price": no_price,
            "outcomes": outcomes,
            "volume": mkt.get("volume", 0),
        }

    def get_expiring_markets(self, seconds_threshold=30):
        """Return tracked markets expiring within *seconds_threshold*."""
        now = datetime.now(timezone.utc)
        expiring = []
        for _cid, mkt in self.tracked_markets.items():
            if mkt.get("end_time"):
                secs = (mkt["end_time"] - now).total_seconds()
                if 0 < secs <= seconds_threshold:
                    mkt["time_left"] = secs
                    expiring.append(mkt)
        return expiring


# ---------------------------------------------------------------------------
# Telegram Notifier (sync – uses requests, no async needed)
# ---------------------------------------------------------------------------

class TelegramNotifier:
    """Sends alerts via the Telegram Bot HTTP API."""

    API_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self):
        self.token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.enabled = bool(self.token and self.chat_id)

        if not self.enabled:
            print(
                "[TELEGRAM] Alerts disabled – "
                "missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID"
            )
        else:
            print(f"[TELEGRAM] Alerts enabled (chat_id: {self.chat_id})")

    def send(self, message):
        """Send *message* (HTML) to the configured chat. Returns True on success."""
        if not self.enabled:
            return False
        try:
            resp = requests.post(
                self.API_URL.format(token=self.token),
                json={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=10,
            )
            resp.raise_for_status()
            print("[TELEGRAM] Alert sent")
            return True
        except Exception as e:
            print(f"[TELEGRAM ERROR] {e}")
            return False


# ---------------------------------------------------------------------------
# Paper Trade Logger (CSV)
# ---------------------------------------------------------------------------

CSV_HEADERS = [
    "timestamp",
    "market_id",
    "market_question",
    "predicted_winner",
    "entry_price",
    "btc_price",
    "btc_change_pct",
    "actual_winner",
    "profit",
    "result",
]


class PaperTradeLogger:
    """Appends paper trades to a CSV file and updates them on settlement."""

    def __init__(self, filepath="paper_trades.csv"):
        self.filepath = Path(filepath)
        self._ensure_csv()

    def _ensure_csv(self):
        if not self.filepath.exists():
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(self.filepath, "w", newline="") as f:
                csv.writer(f).writerow(CSV_HEADERS)

    def log_trade(
        self, timestamp, market_id, question, predicted_winner,
        entry_price, btc_price, btc_change_pct,
    ):
        with open(self.filepath, "a", newline="") as f:
            csv.writer(f).writerow([
                timestamp,
                market_id,
                question,
                predicted_winner,
                f"{entry_price:.4f}",
                f"{btc_price:.2f}",
                f"{btc_change_pct:.4f}",
                "",  # actual_winner (filled on settlement)
                "",  # profit
                "",  # result
            ])
        print(
            f"[TRADE] Logged {predicted_winner} on "
            f"'{question}' @ ${entry_price:.4f}"
        )

    def update_settlement(self, market_id, actual_winner):
        """Fill in actual_winner / profit / result for a settled market."""
        if not self.filepath.exists():
            return

        rows = []
        updated = False
        with open(self.filepath, "r", newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
            rows.append(header)
            for row in reader:
                if (
                    len(row) >= 10
                    and row[1] == market_id
                    and row[7] == ""
                ):
                    row[7] = actual_winner
                    predicted = row[3]
                    entry_price = float(row[4])
                    if predicted == actual_winner:
                        profit = 1.0 - entry_price
                        row[8] = f"{profit:.4f}"
                        row[9] = "WIN"
                    else:
                        row[8] = f"-{entry_price:.4f}"
                        row[9] = "LOSS"
                    updated = True
                rows.append(row)

        if updated:
            with open(self.filepath, "w", newline="") as f:
                csv.writer(f).writerows(rows)
            print(f"[SETTLEMENT] {market_id} -> winner={actual_winner}")


# ---------------------------------------------------------------------------
# Main Bot
# ---------------------------------------------------------------------------

class Polymarket15MinPaperTrader:
    """
    Orchestrates scanning, price tracking, opportunity detection,
    paper-trade logging, and Telegram alerts.
    """

    # Tunables
    BTC_CHANGE_THRESHOLD_PCT = 1.0   # min BTC % move to trigger
    MAX_WINNING_PRICE = 0.99         # only trade if price < this
    EXPIRY_WINDOW_SECONDS = 30       # how close to close we look
    TICK_INTERVAL = 5                # main-loop sleep (seconds)
    MARKET_SCAN_INTERVAL = 30        # re-fetch markets every N seconds

    def __init__(self):
        print("=" * 60)
        print("  POLYMARKET 15-MIN PAPER TRADING BOT")
        print("  Mode: PAPER TRADING ONLY - No real trades")
        print("=" * 60)

        self.price_tracker = BinancePriceTracker()
        self.scanner = MarketScanner()
        self.telegram = TelegramNotifier()
        self.trade_logger = PaperTradeLogger(
            filepath=Path(__file__).parent / "paper_trades.csv"
        )

        self.traded_markets = set()
        self.last_scan_time = 0
        self.opportunities_found = 0

    # -- lifecycle ------------------------------------------------------------

    def run(self):
        """Entry point – runs forever until Ctrl-C."""
        print("\n[START] Connecting to Binance BTC/USDT stream...")
        self.price_tracker.start()

        # Wait up to 30 s for the first price tick
        print("[START] Waiting for initial BTC price...")
        for _ in range(30):
            if self.price_tracker.get_price() is not None:
                break
            time.sleep(1)

        btc = self.price_tracker.get_price()
        if btc is not None:
            print(f"[START] BTC price: ${btc:,.2f}")
        else:
            print("[START] No price yet – continuing anyway")

        btc_str = f"${btc:,.2f}" if btc else "N/A"
        self.telegram.send(
            "<b>Paper Trading Bot Started</b>\n\n"
            f"Mode: Paper Trading Only\n"
            f"BTC: {btc_str}\n"
            f"Tick: {self.TICK_INTERVAL}s\n"
            f"BTC threshold: {self.BTC_CHANGE_THRESHOLD_PCT}%\n"
            f"Max winner price: ${self.MAX_WINNING_PRICE}"
        )

        print(f"\n[RUN] Polling every {self.TICK_INTERVAL}s  (Ctrl-C to stop)")
        print("-" * 60)

        try:
            while True:
                self._tick()
                time.sleep(self.TICK_INTERVAL)
        except KeyboardInterrupt:
            print("\n[STOP] Interrupted by user")
            self._summary()
            self.price_tracker.stop()

    # -- main loop body -------------------------------------------------------

    def _tick(self):
        now = time.time()
        btc = self.price_tracker.get_price()

        # Periodic market scan
        if now - self.last_scan_time >= self.MARKET_SCAN_INTERVAL:
            new_markets = self.scanner.scan_markets()
            self.last_scan_time = now
            n_tracked = len(self.scanner.tracked_markets)
            if new_markets:
                print(
                    f"[SCAN] {len(new_markets)} new 15-min crypto market(s) "
                    f"({n_tracked} tracked)"
                )
            else:
                print(f"[SCAN] No new markets ({n_tracked} tracked)")

        # Status line
        if btc is not None:
            chg = self.price_tracker.get_price_change_pct(15)
            chg_s = f"{chg:+.4f}%" if chg is not None else "n/a"
            print(
                f"[TICK] BTC ${btc:,.2f} | 15m {chg_s} | "
                f"markets {len(self.scanner.tracked_markets)} | "
                f"opps {self.opportunities_found}"
            )

        # Opportunity detection on expiring markets
        for mkt in self.scanner.get_expiring_markets(self.EXPIRY_WINDOW_SECONDS):
            self._evaluate(mkt, btc)

    # -- opportunity evaluation -----------------------------------------------

    def _evaluate(self, mkt, btc):
        mid = mkt["id"]
        if mid in self.traded_markets:
            return
        if btc is None:
            return

        chg = self.price_tracker.get_price_change_pct(15)
        if chg is None:
            print(f"[SKIP] Insufficient price history – '{mkt['question']}'")
            return

        if abs(chg) < self.BTC_CHANGE_THRESHOLD_PCT:
            print(
                f"[SKIP] BTC {chg:+.4f}% < {self.BTC_CHANGE_THRESHOLD_PCT}% "
                f"– '{mkt['question']}'"
            )
            return

        predicted = "YES" if chg > 0 else "NO"
        price = mkt.get("yes_price") if predicted == "YES" else mkt.get("no_price")

        if price is None:
            print(f"[SKIP] No price data – '{mkt['question']}'")
            return

        if price >= self.MAX_WINNING_PRICE:
            print(
                f"[SKIP] Winner ${price:.4f} >= ${self.MAX_WINNING_PRICE} "
                f"– '{mkt['question']}'"
            )
            return

        # ---------- opportunity found ----------
        self.opportunities_found += 1
        self.traded_markets.add(mid)
        tl = mkt.get("time_left", 0)
        pot_profit = 1.0 - price

        print("\n" + "=" * 60)
        print(f"  OPPORTUNITY #{self.opportunities_found}")
        print(f"  Market   : {mkt['question']}")
        print(f"  Winner   : {predicted}")
        print(f"  Entry    : ${price:.4f}")
        print(f"  BTC      : ${btc:,.2f}  ({chg:+.4f}%)")
        print(f"  Time left: {tl:.0f}s")
        print(f"  Profit   : ${pot_profit:.4f} / share")
        print("=" * 60 + "\n")

        # CSV
        self.trade_logger.log_trade(
            timestamp=datetime.now(timezone.utc).isoformat(),
            market_id=mid,
            question=mkt["question"],
            predicted_winner=predicted,
            entry_price=price,
            btc_price=btc,
            btc_change_pct=chg,
        )

        # Telegram
        self.telegram.send(
            f"<b>Paper Trade #{self.opportunities_found}</b>\n\n"
            f"<b>Market:</b> {mkt['question']}\n"
            f"<b>Predicted:</b> {predicted}\n"
            f"<b>Entry:</b> ${price:.4f}\n"
            f"<b>BTC:</b> ${btc:,.2f} ({chg:+.4f}%)\n"
            f"<b>Time left:</b> {tl:.0f}s\n"
            f"<b>Potential:</b> ${pot_profit:.4f}/share\n\n"
            f"<i>Paper trade only</i>"
        )

    # -- summary --------------------------------------------------------------

    def _summary(self):
        print("\n" + "=" * 60)
        print("  SESSION SUMMARY")
        print(f"  Opportunities : {self.opportunities_found}")
        print(f"  Markets tracked: {len(self.scanner.tracked_markets)}")
        btc = self.price_tracker.get_price()
        if btc is not None:
            print(f"  Final BTC     : ${btc:,.2f}")
        print(f"  Trade log     : {self.trade_logger.filepath}")
        print("=" * 60)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    bot = Polymarket15MinPaperTrader()
    bot.run()
