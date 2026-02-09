#!/usr/bin/env python3
"""
Polymarket BTC 15-Min Dual-Side Arbitrage Paper Trader

Strategy:
  Find BTC 15-min markets where YES + NO < $1.00.
  Buy BOTH sides = guaranteed $1.00 payout when one side wins.
  Profit = $1.00 - combined_cost per pair of shares.

Capital: $20,000 per opportunity.  Paper trading only.
"""

import sys
import time
import json
import csv
import requests
from datetime import datetime, timezone, timedelta, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from config import Config

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CAPITAL = 20_000.00          # dollars deployed per trade
ARB_THRESHOLD = 0.99         # enter when YES + NO < this
TICK_INTERVAL = 5            # seconds between ticks
MARKET_SCAN_INTERVAL = 30    # seconds between full API scans
SETTLEMENT_CHECK_DELAY = 60  # seconds after close before checking result
DAILY_SUMMARY_HOUR = 0       # UTC hour to print daily summary

CSV_PATH = Path(__file__).parent / "arbitrage_trades.csv"

CSV_HEADERS = [
    "entry_time",
    "market_id",
    "market_question",
    "yes_entry_price",
    "no_entry_price",
    "combined_cost_per_pair",
    "shares_bought",
    "total_invested",
    "settlement_time",
    "winning_side",
    "payout",
    "profit_usd",
    "profit_pct",
    "cumulative_profit",
    "account_balance",
]


# ---------------------------------------------------------------------------
# Telegram (sync, via requests)
# ---------------------------------------------------------------------------

class TelegramNotifier:
    API_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self):
        self.token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.enabled = bool(self.token and self.chat_id)
        if self.enabled:
            print(f"[TELEGRAM] Enabled (chat {self.chat_id})")
        else:
            print("[TELEGRAM] Disabled – missing token or chat_id")

    def send(self, msg):
        if not self.enabled:
            return False
        try:
            resp = requests.post(
                self.API_URL.format(token=self.token),
                json={
                    "chat_id": self.chat_id,
                    "text": msg,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=10,
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            print(f"[TELEGRAM ERROR] {e}")
            return False


# ---------------------------------------------------------------------------
# CSV P&L Logger
# ---------------------------------------------------------------------------

class TradeLog:
    """Append-only CSV with in-place settlement updates."""

    def __init__(self, path=CSV_PATH):
        self.path = Path(path)
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", newline="") as f:
                csv.writer(f).writerow(CSV_HEADERS)

    # -- helpers to compute running totals ------------------------------------

    def _read_all(self):
        rows = []
        with open(self.path, "r", newline="") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            for row in reader:
                rows.append(row)
        return rows

    def _cumulative_profit(self):
        total = 0.0
        for row in self._read_all():
            if len(row) >= 12 and row[11]:  # profit_usd column
                try:
                    total += float(row[11])
                except ValueError:
                    pass
        return total

    # -- write ----------------------------------------------------------------

    def log_entry(self, market_id, question, yes_price, no_price,
                  combined, shares, invested):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with open(self.path, "a", newline="") as f:
            csv.writer(f).writerow([
                now,                          # entry_time
                market_id,                    # market_id
                question,                     # market_question
                f"{yes_price:.4f}",           # yes_entry_price
                f"{no_price:.4f}",            # no_entry_price
                f"{combined:.4f}",            # combined_cost_per_pair
                f"{shares:.2f}",              # shares_bought
                f"{invested:.2f}",            # total_invested
                "",                           # settlement_time
                "",                           # winning_side
                "",                           # payout
                "",                           # profit_usd
                "",                           # profit_pct
                "",                           # cumulative_profit
                "",                           # account_balance
            ])

    def settle(self, market_id, winning_side):
        """Fill settlement columns for the given market_id."""
        if not self.path.exists():
            return None

        rows = []
        header = None
        settled_profit = None

        with open(self.path, "r", newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
            rows_data = list(reader)

        # First pass: compute cumulative profit from already-settled rows
        cum = 0.0
        for r in rows_data:
            if len(r) >= 14 and r[13]:
                try:
                    cum = float(r[13])
                except ValueError:
                    pass

        updated = False
        for row in rows_data:
            if len(row) >= 15 and row[1] == market_id and row[8] == "":
                shares = float(row[6])
                invested = float(row[7])
                payout = shares * 1.0
                profit = payout - invested
                profit_pct = (profit / invested) * 100 if invested else 0.0
                cum += profit

                row[8] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                row[9] = winning_side
                row[10] = f"{payout:.2f}"
                row[11] = f"{profit:.2f}"
                row[12] = f"{profit_pct:.4f}"
                row[13] = f"{cum:.2f}"
                row[14] = f"{CAPITAL + cum:.2f}"
                settled_profit = profit
                updated = True

        if updated:
            with open(self.path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(header)
                w.writerows(rows_data)

        return settled_profit

    def get_stats(self):
        """Return aggregate stats from the CSV."""
        rows = self._read_all()
        total_trades = len(rows)
        settled = [r for r in rows if len(r) >= 12 and r[11]]
        wins = 0
        total_profit = 0.0
        profits = []
        best_profit = 0.0
        best_pct = 0.0

        for r in settled:
            try:
                p = float(r[11])
            except ValueError:
                continue
            total_profit += p
            profits.append(p)
            if p > 0:
                wins += 1
            if p > best_profit:
                best_profit = p
                try:
                    best_pct = float(r[12])
                except ValueError:
                    best_pct = 0.0

        avg_profit = total_profit / len(profits) if profits else 0.0
        return {
            "total_trades": total_trades,
            "settled": len(settled),
            "wins": wins,
            "total_profit": total_profit,
            "avg_profit": avg_profit,
            "best_profit": best_profit,
            "best_pct": best_pct,
            "roi_pct": (total_profit / CAPITAL) * 100 if CAPITAL else 0.0,
        }


# ---------------------------------------------------------------------------
# Market Scanner
# ---------------------------------------------------------------------------

class ArbitrageScanner:
    """Queries Gamma API for active BTC 15-min markets and their prices."""

    def __init__(self):
        self.gamma_url = Config.POLYMARKET_GAMMA_URL
        self.tracked = {}  # id -> parsed market dict

    def scan(self):
        """Fetch markets, filter for 15-min BTC, return new matches."""
        try:
            resp = requests.get(
                f"{self.gamma_url}/markets",
                params={"active": "true", "closed": "false", "limit": 100},
                timeout=15,
            )
            resp.raise_for_status()
            markets = resp.json()
        except requests.RequestException as e:
            print(f"[SCANNER ERROR] {e}")
            return []

        crypto_kw = ["btc", "bitcoin", "crypto"]
        time_kw = ["15 min", "15min", "15-min", "15 minute"]
        found = []

        for raw in markets:
            q = (raw.get("question") or "").lower()
            d = (raw.get("description") or "").lower()
            blob = q + " " + d

            is_crypto = any(k in blob for k in crypto_kw)
            is_15 = any(k in blob for k in time_kw)

            keep = False
            if is_crypto and is_15:
                keep = True
            elif is_crypto and "price" in blob:
                end_s = raw.get("end_date_iso") or raw.get("endDate")
                if end_s:
                    try:
                        end = datetime.fromisoformat(end_s.replace("Z", "+00:00"))
                        left = (end - datetime.now(timezone.utc)).total_seconds()
                        if 0 < left < 1200:
                            keep = True
                    except (ValueError, TypeError):
                        pass

            if keep:
                parsed = self._parse(raw)
                if parsed:
                    self.tracked[parsed["id"]] = parsed
                    found.append(parsed)

        # prune expired (>5 min past close)
        now = datetime.now(timezone.utc)
        gone = [
            k for k, v in self.tracked.items()
            if v["end_time"] and v["end_time"] < now - timedelta(minutes=5)
        ]
        for k in gone:
            del self.tracked[k]

        return found

    def refresh_prices(self, market_id):
        """Re-fetch a single market's prices from the API."""
        try:
            resp = requests.get(
                f"{self.gamma_url}/markets/{market_id}",
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                parsed = self._parse(data)
                if parsed:
                    self.tracked[parsed["id"]] = parsed
                    return parsed
        except requests.RequestException:
            pass
        return self.tracked.get(market_id)

    def check_resolution(self, market_id):
        """Check if a market has resolved.  Returns winning side or None."""
        try:
            resp = requests.get(
                f"{self.gamma_url}/markets/{market_id}",
                timeout=10,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()

            # Check various resolution indicators
            if data.get("resolved") or data.get("closed"):
                outcomes = data.get("outcomes", [])
                prices = data.get("outcomePrices", [])
                if isinstance(prices, str):
                    try:
                        prices = json.loads(prices)
                    except (json.JSONDecodeError, TypeError):
                        prices = []

                # After resolution the winning side has price ~1.0
                if len(prices) >= 2:
                    try:
                        p0 = float(prices[0])
                        p1 = float(prices[1])
                        if p0 > 0.9:
                            return "YES"
                        if p1 > 0.9:
                            return "NO"
                    except (ValueError, TypeError):
                        pass

                # Fallback: check resolved_to or winner fields
                winner = data.get("winner") or data.get("resolved_to")
                if winner:
                    return str(winner).upper()

            return None
        except requests.RequestException:
            return None

    def _parse(self, raw):
        mid = (
            raw.get("condition_id")
            or raw.get("conditionId")
            or raw.get("id")
        )
        if not mid:
            return None

        end_s = raw.get("end_date_iso") or raw.get("endDate") or ""
        end_time = None
        if end_s:
            try:
                end_time = datetime.fromisoformat(end_s.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        raw_prices = raw.get("outcomePrices", [])
        if isinstance(raw_prices, str):
            try:
                raw_prices = json.loads(raw_prices)
            except (json.JSONDecodeError, TypeError):
                raw_prices = []

        yes_p = None
        no_p = None
        try:
            if len(raw_prices) > 0:
                yes_p = float(raw_prices[0])
            if len(raw_prices) > 1:
                no_p = float(raw_prices[1])
        except (ValueError, TypeError):
            pass

        return {
            "id": mid,
            "question": raw.get("question", "Unknown"),
            "end_time": end_time,
            "yes_price": yes_p,
            "no_price": no_p,
            "volume": raw.get("volume", 0),
        }


# ---------------------------------------------------------------------------
# Main Bot
# ---------------------------------------------------------------------------

class ArbitragePaperTrader:
    """
    Main loop: scan -> detect arb -> paper-enter -> track -> settle -> report.
    """

    def __init__(self):
        print("=" * 62)
        print("  POLYMARKET BTC 15-MIN ARBITRAGE PAPER TRADER")
        print(f"  Capital: ${CAPITAL:,.0f}  |  Threshold: YES+NO < ${ARB_THRESHOLD}")
        print("  Mode: PAPER TRADING ONLY")
        print("=" * 62)

        self.scanner = ArbitrageScanner()
        self.telegram = TelegramNotifier()
        self.log = TradeLog()

        self.entered = {}       # market_id -> entry dict (unsettled)
        self.cumulative_pnl = 0.0
        self.trade_count = 0
        self.last_scan = 0
        self.day_trades = 0
        self.day_profit = 0.0
        self.current_day = date.today()
        self._daily_summary_sent = False

    # -- lifecycle ------------------------------------------------------------

    def run(self):
        startup_msg = (
            "<b>Arbitrage Paper Trader Started</b>\n\n"
            f"Capital: ${CAPITAL:,.0f}\n"
            f"Threshold: YES+NO &lt; ${ARB_THRESHOLD}\n"
            f"Scan interval: {TICK_INTERVAL}s\n"
            "Mode: Paper trading only"
        )
        self.telegram.send(startup_msg)
        print(f"\n[RUN] Polling every {TICK_INTERVAL}s  (Ctrl-C to stop)")
        print("-" * 62)

        try:
            while True:
                self._tick()
                time.sleep(TICK_INTERVAL)
        except KeyboardInterrupt:
            print("\n[STOP] Interrupted")
            self._print_weekly_report()
            self.telegram.send(self._weekly_report_text())

    # -- main loop body -------------------------------------------------------

    def _tick(self):
        now_ts = time.time()
        now_utc = datetime.now(timezone.utc)

        # -- daily rollover ---------------------------------------------------
        today = date.today()
        if today != self.current_day:
            self._print_daily_summary()
            self._send_daily_summary()
            self.day_trades = 0
            self.day_profit = 0.0
            self.current_day = today
            self._daily_summary_sent = False

        # -- periodic market scan ---------------------------------------------
        if now_ts - self.last_scan >= MARKET_SCAN_INTERVAL:
            new = self.scanner.scan()
            self.last_scan = now_ts
            n = len(self.scanner.tracked)
            if new:
                print(f"[SCAN] {len(new)} market(s) found ({n} tracked)")
            else:
                print(f"[SCAN] No new markets ({n} tracked)")

        # -- check for arbitrage entries --------------------------------------
        for mid, mkt in list(self.scanner.tracked.items()):
            if mid in self.entered:
                continue  # already in this one

            yes = mkt.get("yes_price")
            no = mkt.get("no_price")
            if yes is None or no is None:
                continue

            combined = yes + no
            if combined >= ARB_THRESHOLD:
                continue

            # --- ENTRY ---
            self._enter(mkt, yes, no, combined)

        # -- check pending settlements ---------------------------------------
        for mid in list(self.entered.keys()):
            entry = self.entered[mid]
            if entry["end_time"] is None:
                continue
            secs_since_close = (now_utc - entry["end_time"]).total_seconds()
            if secs_since_close < SETTLEMENT_CHECK_DELAY:
                continue  # wait a bit after close

            winner = self.scanner.check_resolution(mid)
            if winner:
                self._settle(mid, winner)

        # -- status line ------------------------------------------------------
        open_count = len(self.entered)
        print(
            f"[TICK] Tracked: {len(self.scanner.tracked)} | "
            f"Open: {open_count} | "
            f"Trades: {self.trade_count} | "
            f"P&L: ${self.cumulative_pnl:+,.2f}"
        )

    # -- entry ----------------------------------------------------------------

    def _enter(self, mkt, yes_price, no_price, combined):
        mid = mkt["id"]
        shares = CAPITAL / combined
        expected_profit = shares * (1.0 - combined)
        expected_pct = ((1.0 - combined) / combined) * 100

        self.entered[mid] = {
            "id": mid,
            "question": mkt["question"],
            "yes_price": yes_price,
            "no_price": no_price,
            "combined": combined,
            "shares": shares,
            "invested": CAPITAL,
            "expected_profit": expected_profit,
            "end_time": mkt.get("end_time"),
            "entry_time": datetime.now(timezone.utc),
        }
        self.trade_count += 1
        self.day_trades += 1

        self.log.log_entry(
            market_id=mid,
            question=mkt["question"],
            yes_price=yes_price,
            no_price=no_price,
            combined=combined,
            shares=shares,
            invested=CAPITAL,
        )

        print()
        print("=" * 62)
        print(f"  ENTERED ARBITRAGE  (Trade #{self.trade_count})")
        print(f"  Market : {mkt['question']}")
        print(f"  YES: ${yes_price:.3f} | NO: ${no_price:.3f} | "
              f"Combined: ${combined:.4f}")
        print(f"  Shares : {shares:,.2f} pairs (${CAPITAL:,.0f} deployed)")
        print(f"  Expected profit: ${expected_profit:,.2f} "
              f"({expected_pct:.2f}%)")
        print("=" * 62)
        print()

        self.telegram.send(
            f"<b>ENTERED ARBITRAGE</b>  (#{self.trade_count})\n\n"
            f"<b>Market:</b> {mkt['question']}\n"
            f"YES: ${yes_price:.3f} | NO: ${no_price:.3f} | "
            f"Combined: ${combined:.4f}\n"
            f"Shares: {shares:,.2f} pairs (${CAPITAL:,.0f})\n"
            f"Expected profit: ${expected_profit:,.2f} ({expected_pct:.2f}%)"
        )

    # -- settlement -----------------------------------------------------------

    def _settle(self, mid, winning_side):
        entry = self.entered.pop(mid, None)
        if entry is None:
            return

        payout = entry["shares"] * 1.0
        profit = payout - entry["invested"]
        profit_pct = (profit / entry["invested"]) * 100

        self.cumulative_pnl += profit
        self.day_profit += profit

        self.log.settle(mid, winning_side)

        print()
        print("=" * 62)
        if profit >= 0:
            print("  SETTLED - PROFIT!")
        else:
            print("  SETTLED - LOSS")
        print(f"  Market : {entry['question']}")
        print(f"  Winner : {winning_side}")
        print(f"  Payout : ${payout:,.2f} | Cost: ${entry['invested']:,.2f}")
        print(f"  Profit : ${profit:+,.2f} ({profit_pct:+.2f}%)")
        print(f"  Cumulative P&L: ${self.cumulative_pnl:+,.2f}")
        print("=" * 62)
        print()

        self.telegram.send(
            f"<b>SETTLED {'- PROFIT!' if profit >= 0 else '- LOSS'}</b>\n\n"
            f"<b>Market:</b> {entry['question']}\n"
            f"<b>Winner:</b> {winning_side}\n"
            f"Payout: ${payout:,.2f} | Cost: ${entry['invested']:,.2f}\n"
            f"<b>Profit: ${profit:+,.2f} ({profit_pct:+.2f}%)</b>\n"
            f"Cumulative P&L: ${self.cumulative_pnl:+,.2f}"
        )

    # -- daily summary --------------------------------------------------------

    def _print_daily_summary(self):
        avg = self.day_profit / self.day_trades if self.day_trades else 0.0
        roi = (self.day_profit / CAPITAL) * 100
        monthly = self.day_profit * 30

        print()
        print("*" * 62)
        print(f"  DAY SUMMARY  ({self.current_day})")
        print(f"  Capital       : ${CAPITAL:,.0f}")
        print(f"  Trades        : {self.day_trades}")
        print(f"  Total profit  : ${self.day_profit:+,.2f}")
        print(f"  Avg per trade : ${avg:+,.2f}")
        print(f"  ROI today     : {roi:+.2f}%")
        print(f"  Projected mo. : ${monthly:+,.0f} ({roi * 30:+.1f}%)")
        print("*" * 62)
        print()

    def _send_daily_summary(self):
        avg = self.day_profit / self.day_trades if self.day_trades else 0.0
        roi = (self.day_profit / CAPITAL) * 100
        monthly = self.day_profit * 30

        self.telegram.send(
            f"<b>DAY SUMMARY ({self.current_day})</b>\n\n"
            f"Capital: ${CAPITAL:,.0f}\n"
            f"Trades: {self.day_trades}\n"
            f"Total profit: ${self.day_profit:+,.2f}\n"
            f"Avg/trade: ${avg:+,.2f}\n"
            f"ROI today: {roi:+.2f}%\n"
            f"Projected monthly: ${monthly:+,.0f} ({roi * 30:+.1f}%)"
        )

    # -- weekly report --------------------------------------------------------

    def _weekly_report_text(self):
        stats = self.log.get_stats()
        days_running = max(
            1,
            (datetime.now(timezone.utc).date() - self.current_day).days + 1
        )
        trades_per_day = stats["settled"] / days_running if days_running else 0
        monthly_proj = (stats["total_profit"] / days_running) * 30

        return (
            "<b>WEEKLY REPORT</b>\n\n"
            f"Starting capital: ${CAPITAL:,.0f}\n"
            f"Total trades: {stats['total_trades']}\n"
            f"Settled: {stats['settled']}\n"
            f"Wins: {stats['wins']}\n"
            f"Total profit: ${stats['total_profit']:+,.2f}\n"
            f"ROI: {stats['roi_pct']:+.2f}%\n"
            f"Avg profit/trade: ${stats['avg_profit']:+,.2f}\n"
            f"Trades/day: {trades_per_day:.1f}\n"
            f"Best trade: ${stats['best_profit']:+,.2f} "
            f"({stats['best_pct']:+.2f}%)\n"
            f"Projected monthly: ${monthly_proj:+,.0f}"
        )

    def _print_weekly_report(self):
        stats = self.log.get_stats()
        days_running = max(
            1,
            (datetime.now(timezone.utc).date() - self.current_day).days + 1
        )
        trades_per_day = stats["settled"] / days_running if days_running else 0
        monthly_proj = (stats["total_profit"] / days_running) * 30

        print()
        print("#" * 62)
        print("  WEEKLY REPORT")
        print("#" * 62)
        print(f"  Starting capital  : ${CAPITAL:,.0f}")
        print(f"  Total trades      : {stats['total_trades']}")
        print(f"  Settled           : {stats['settled']}")
        print(f"  Wins              : {stats['wins']}")
        print(f"  Total profit      : ${stats['total_profit']:+,.2f}")
        print(f"  ROI               : {stats['roi_pct']:+.2f}%")
        print(f"  Avg profit/trade  : ${stats['avg_profit']:+,.2f}")
        print(f"  Trades/day        : {trades_per_day:.1f}")
        print(f"  Best trade        : ${stats['best_profit']:+,.2f} "
              f"({stats['best_pct']:+.2f}%)")
        print(f"  Projected monthly : ${monthly_proj:+,.0f}")
        print(f"  Account balance   : ${CAPITAL + stats['total_profit']:,.2f}")
        print("#" * 62)
        print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    bot = ArbitragePaperTrader()
    bot.run()
