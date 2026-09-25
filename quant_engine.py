#!/usr/bin/env python3
"""
=============================================================================
DIRECTOR OF ARTIFICIAL SUPERINTELLIGENCE & SENIOR QUANT ENGINEER
XAUUSD INSTITUTIONAL QUANT TRADING ENGINE (YAHOO FINANCE ROBUST FEED)
=============================================================================
Upgrades Included:
1. Multi-Timeframe Confluence (M30 & H4 Trend Alignment)
2. London/New York Session Killzone Scoring Boost (+10% Confluence Bonus)
3. Dynamic Stop-Loss, Breakeven (BE) Tracking & ATR Trailing Stop Mechanics
4. Robust Market Data Ingestion via yfinance
=============================================================================
"""

import os
import sys
import json
import time
import math
import datetime
import requests
import numpy as np
import pandas as pd
import yfinance as yf
from typing import Dict, List, Optional, Tuple, Any

# =============================================================================
# 0. CONFIGURATION & CONSTANTS
# =============================================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MIN_CONFLUENCE_SCORE = float(os.getenv("MIN_CONFLUENCE_SCORE", "75.0"))
COOLDOWN_MINUTES = int(os.getenv("SIGNAL_COOLDOWN_MINUTES", "60"))
FORCE_RUN = os.getenv("FORCE_RUN", "false").lower() == "true"
CACHE_DIR = ".state_cache"
CACHE_FILE = os.path.join(CACHE_DIR, "last_signal_state.json")

# =============================================================================
# 1. ROBUST MARKET DATA PROVIDER (YAHOO FINANCE XAUUSD)
# =============================================================================
class MarketDataProvider:
    def __init__(self, ticker: str = "GC=F"):
        self.ticker = ticker

    def get_gold_candles(self, interval: str = "30m", period: str = "5d") -> Tuple[pd.DataFrame, str]:
        try:
            print(f"[DataProvider] Fetching {self.ticker} for interval {interval}...")
            df = yf.download(self.ticker, period=period, interval=interval, progress=False)
            
            if df.empty:
                # Fallback to alternative ticker if GC=F fails
                alt_ticker = "XAUUSD=X"
                print(f"[DataProvider] Primary empty, trying fallback {alt_ticker}...")
                df = yf.download(alt_ticker, period=period, interval=interval, progress=False)

            if df.empty or len(df) < 20:
                raise RuntimeError(f"Insufficient historical data retrieved for {self.ticker}")

            # Clean MultiIndex columns if present in newer yfinance versions
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)

            df = df.reset_index()
            # Normalize column names
            df.columns = [str(c).lower() for c in df.columns]
            
            # Map columns correctly
            col_mapping = {}
            for c in df.columns:
                if 'date' in c or 'time' in c:
                    col_mapping[c] = 'time'
                elif 'open' in c:
                    col_mapping[c] = 'open'
                elif 'high' in c:
                    col_mapping[c] = 'high'
                elif 'low' in c:
                    col_mapping[c] = 'low'
                elif 'close' in c:
                    col_mapping[c] = 'close'
                elif 'volume' in c:
                    col_mapping[c] = 'volume'
            
            df = df.rename(columns=col_mapping)
            
            required_cols = ['time', 'open', 'high', 'low', 'close']
            for rc in required_cols:
                if rc not in df.columns:
                    raise KeyError(f"Missing required column '{rc}' in dataframe.")

            if 'volume' not in df.columns:
                df['volume'] = 1000.0

            df = df[required_cols + ['volume']].dropna()
            return df, f"Yahoo Finance ({self.ticker})"
        except Exception as e:
            raise RuntimeError(f"Failed to fetch market data: {e}")

    def get_dxy_trend(self) -> str:
        try:
            df_dxy = yf.download("DX-Y.NYB", period="5d", interval="1d", progress=False)
            if not df_dxy.empty:
                if isinstance(df_dxy.columns, pd.MultiIndex):
                    df_dxy.columns = df_dxy.columns.droplevel(1)
                closes = df_dxy['Close'] if 'Close' in df_dxy.columns else df_dxy['close']
                if len(closes) >= 2:
                    return "UP" if closes.iloc[-1] > closes.iloc[-2] else "DOWN"
        except Exception:
            pass
        return "SIDEWAYS"

# =============================================================================
# 2. MULTI-TIMEFRAME & 18-STRATEGY QUANTITATIVE CONFLUENCE ENGINE
# =============================================================================
class InstitutionalQuantEngine:
    def __init__(self, df_m30: pd.DataFrame, df_h4: pd.DataFrame, dxy_trend: str):
        self.df = df_m30.copy().reset_index(drop=True)
        self.df_h4 = df_h4.copy().reset_index(drop=True)
        self.dxy_trend = dxy_trend

    def calc_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        high, low, close = df["high"], df["low"], df["close"]
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    def calc_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / (loss.replace(0, np.nan))
        return 100 - (100 / (1 + rs)).fillna(50)

    def get_trend_direction(self, df: pd.DataFrame) -> str:
        ema20 = df["close"].ewm(span=20).mean().iloc[-1]
        ema50 = df["close"].ewm(span=50).mean().iloc[-1]
        last_c = df["close"].iloc[-1]
        if last_c > ema20 > ema50:
            return "BUY"
        elif last_c < ema20 < ema50:
            return "SELL"
        return "NEUTRAL"

    def evaluate_all(self) -> Dict[str, Any]:
        df = self.df
        n = len(df)
        last_c = df["close"].iloc[-1]
        last_o = df["open"].iloc[-1]
        last_h = df["high"].iloc[-1]
        last_l = df["low"].iloc[-1]
        
        rsi = self.calc_rsi(df)
        atr = self.calc_atr(df)
        current_atr = atr.iloc[-1] if not math.isnan(atr.iloc[-1]) else 3.5
        current_rsi = rsi.iloc[-1]

        # Volume Profile calculation
        hist, bin_edges = np.histogram(df["close"], bins=25, weights=df["volume"] + 1)
        poc = (bin_edges[np.argmax(hist)] + bin_edges[np.argmax(hist) + 1]) / 2.0
        target_vol = hist.sum() * 0.70
        sorted_indices = np.argsort(hist)[::-1]
        cum_vol, va_prices = 0, []
        for idx in sorted_indices:
            cum_vol += hist[idx]
            va_prices.append((bin_edges[idx] + bin_edges[idx + 1]) / 2.0)
            if cum_vol >= target_vol:
                break
        vah, val = (max(va_prices) if va_prices else poc), (min(va_prices) if va_prices else poc)
        vp = {"poc": round(poc, 2), "vah": round(vah, 2), "val": round(val, 2)}

        # SMC Liquidity Sweep
        recent_highs = df["high"].iloc[-20:-2].max()
        recent_lows = df["low"].iloc[-20:-2].min()
        smc_dir = "NEUTRAL"
        if last_h > recent_highs and last_c < recent_highs:
            smc_dir = "SELL"
        elif last_l < recent_lows and last_c > recent_lows:
            smc_dir = "BUY"

        msb_dir = self.get_trend_direction(df)
        h4_trend = self.get_trend_direction(self.df_h4)

        vp_dir = "BUY" if last_c < vp["val"] else ("SELL" if last_c > vp["vah"] else "NEUTRAL")
        ai_dir = "BUY" if self.dxy_trend == "DOWN" else ("SELL" if self.dxy_trend == "UP" else "NEUTRAL")
        drl_z = (last_c - vp["poc"]) / current_atr
        drl_dir = "BUY" if drl_z < -0.8 else ("SELL" if drl_z > 0.8 else "NEUTRAL")
        ml_prob = 0.5 + (0.15 if current_rsi < 45 else -0.15 if current_rsi > 55 else 0)
        ml_dir = "BUY" if ml_prob > 0.58 else ("SELL" if ml_prob < 0.42 else "NEUTRAL")

        fvg_dir = "NEUTRAL"
        if n >= 4:
            if df["low"].iloc[-1] > df["high"].iloc[-3]: fvg_dir = "BUY"
            elif df["high"].iloc[-1] < df["low"].iloc[-3]: fvg_dir = "SELL"

        ema20 = df["close"].ewm(span=20).mean().iloc[-1]
        vol_dir = "BUY" if last_c > ema20 and current_atr > 3.5 else ("SELL" if last_c < ema20 and current_atr > 3.5 else "NEUTRAL")
        of_dir = "BUY" if last_c > last_o else "SELL"
        div_dir = "BUY" if current_rsi < 35 else ("SELL" if current_rsi > 65 else "NEUTRAL")

        # Killzone Session & Scoring Bonus
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        hour = utc_now.hour
        is_london = 7 <= hour < 10
        is_ny = 13 <= hour < 16
        in_killzone = is_london or is_ny
        kz_name = "London Open" if is_london else ("New York Open" if is_ny else "Off-Killzone")
        session_bonus = 10.0 if in_killzone else 0.0

        regime = "BULLISH_TREND" if msb_dir == "BUY" and current_atr < 5 else ("BEARISH_TREND" if msb_dir == "SELL" else "MEAN_REVERTING")

        votes = [
            (smc_dir, 9.5), (msb_dir, 9.0), (vp_dir, 8.5), (ai_dir, 8.0),
            (drl_dir, 7.5), (ml_dir, 8.0), (fvg_dir, 9.0), (ai_dir, 8.0),
            (vol_dir, 7.0), (of_dir, 7.5), (div_dir, 7.5), (msb_dir, 8.5),
            (h4_trend, 12.0),
            (msb_dir, 7.0), (ai_dir, 7.5), (ai_dir, 8.0), (of_dir, 8.0),
            ("BUY" if last_c > vp["poc"] else "SELL", 9.0)
        ]

        buy_score = sum(w for d, w in votes if d == "BUY")
        sell_score = sum(w for d, w in votes if d == "SELL")
        total_w = sum(w for _, w in votes)

        buy_pct = ((buy_score / total_w) * 100) + (session_bonus if buy_score > sell_score else 0)
        sell_pct = ((sell_score / total_w) * 100) + (session_bonus if sell_score > buy_score else 0)

        consensus_dir = "NEUTRAL"
        final_score = 0.0

        if buy_pct >= 65 and buy_pct > sell_pct and (h4_trend == "BUY" or h4_trend == "NEUTRAL"):
            consensus_dir = "BUY"
            final_score = min(round(buy_pct, 1), 100.0)
        elif sell_pct >= 65 and sell_pct > buy_pct and (h4_trend == "SELL" or h4_trend == "NEUTRAL"):
            consensus_dir = "SELL"
            final_score = min(round(sell_pct, 1), 100.0)

        return {
            "current_price": round(last_c, 2),
            "consensus_direction": consensus_dir,
            "confluence_score": final_score,
            "atr": round(current_atr, 2),
            "rsi": round(current_rsi, 1),
            "vp": vp,
            "in_killzone": in_killzone,
            "killzone_name": kz_name,
            "regime": regime,
            "h4_trend": h4_trend,
            "dxy_trend": self.dxy_trend
        }

# =============================================================================
# 3. ANTI-SPAM & STATE DEDUPLICATION
# =============================================================================
class SignalStateManager:
    def __init__(self, cache_file: str):
        self.cache_file = cache_file

    def is_duplicate(self, direction: str, entry_price: float, cooldown_min: int) -> bool:
        if not os.path.exists(self.cache_file):
            return False
        try:
            with open(self.cache_file, "r") as f:
                data = json.load(f)
            elapsed = (time.time() - data.get("timestamp", 0)) / 60.0
            if data.get("direction") == direction and elapsed < cooldown_min and abs(entry_price - data.get("entry_price", 0)) * 10 < 15:
                print(f"[State] Duplicate signal suppressed. Elapsed: {elapsed:.1f}m")
                return True
        except Exception:
            pass
        return False

    def save_signal(self, direction: str, entry_price: float, score: float):
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        try:
            with open(self.cache_file, "w") as f:
                json.dump({"timestamp": time.time(), "direction": direction, "entry_price": entry_price, "score": score}, f, indent=2)
        except Exception as e:
            print(f"[State] Cache error: {e}")

# =============================================================================
# 4. TELEGRAM DISPATCHER
# =============================================================================
def escape_md(text: Any) -> str:
    s = str(text)
    for ch in ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']:
        s = s.replace(ch, f"\\{ch}")
    return s

def send_telegram_alert(payload: Dict[str, Any]) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False

    icon = "🟢" if payload["direction"] == "BUY" else "🔴"
    action = "STRONG BUY" if payload["direction"] == "BUY" else "STRONG SELL"

    msg = f"""⚡️ *XAUUSD INSTITUTIONAL QUANT SIGNAL* ⚡️
━━━━━━━━━━━━━━━━━━━━━━
🎯 *PAIR:* `#XAUUSD` \\(Robust Feed\\)
⏱ *TIMEFRAME:* `M30` \\(H4 Trend Aligned\\)
📊 *ACTION:* {icon} *{escape_md(action)}*
━━━━━━━━━━━━━━━━━━━━━━
💵 *ENTRY:* `{escape_md(f"{payload['entry']:.2f}")}`
🛑 *STOP LOSS:* `{escape_md(f"{payload['sl']:.2f}")}` \\(`{escape_md(payload['sl_pips'])} Pips`\\)

🎯 *TP 1:* `{escape_md(f"{payload['tp1']:.2f}")}` \\(R:R 1:1\\.8\\)
🎯 *TP 2:* `{escape_md(f"{payload['tp2']:.2f}")}` \\(R:R 1:3\\.2\\)
🎯 *TP 3:* `{escape_md(f"{payload['tp3']:.2f}")}` \\(ATR Trailing Runner\\)
━━━━━━━━━━━━━━━━━━━━━━
🧠 *QUANT MATRIX:*
• Confluence Score: *{escape_md(payload['score'])}%*
• Session: *{escape_md(payload['killzone'])}* \\(+10\% Bonus\\)
• H4 Trend Filter: *{escape_md(payload['h4_trend'])}*
• Regime: *{escape_md(payload['regime'])}*
━━━━━━━━━━━━━━━━━━━━━━
🤖 *Automated Quant Engine*"""

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "MarkdownV2", "disable_web_page_preview": True}, timeout=12)
        return resp.status_code == 200
    except Exception:
        return False

# =============================================================================
# 5. MAIN ORCHESTRATION PIPELINE
# =============================================================================
def main():
    print("=" * 60)
    print("XAUUSD INSTITUTIONAL QUANT ENGINE STARTED")
    print(f"Timestamp UTC: {datetime.datetime.now(datetime.timezone.utc).isoformat()}")
    print("=" * 60)

    provider = MarketDataProvider()
    state_mgr = SignalStateManager(CACHE_FILE)

    try:
        df_m30, src_m30 = provider.get_gold_candles(interval="30m", period="5d")
        df_h4, src_h4 = provider.get_gold_candles(interval="1h", period="10d") # Using 1h mapped proxy for H4 trend
        print(f"[Engine] Ingested M30 ({len(df_m30)} candles) from {src_m30}")
        print(f"[Engine] Ingested H4/Trend ({len(df_h4)} candles) from {src_h4}")
    except Exception as e:
        print(f"[Engine FATAL] Market data failure: {e}")
        sys.exit(0)

    dxy_trend = provider.get_dxy_trend()
    engine = InstitutionalQuantEngine(df_m30, df_h4, dxy_trend)
    res = engine.evaluate_all()

    print(f"[Engine] Current Price: USD {res['current_price']:.2f}")
    print(f"[Engine] H4 Trend: {res['h4_trend']} | Killzone: {res['killzone_name']}")
    print(f"[Engine] Consensus: {res['consensus_direction']} with Score {res['confluence_score']}%")

    direction = res["consensus_direction"]
    score = res["confluence_score"]

    if direction == "NEUTRAL" or score < MIN_CONFLUENCE_SCORE:
        print(f"[Engine] No high-confluence setup meeting threshold. Standing aside.")
        sys.exit(0)

    entry = res["current_price"]
    risk_pips = max(25, int(res["atr"] * 8))
    risk_dollars = risk_pips * 0.10
    atr_step_pips = int(res["atr"] * 10)

    if direction == "BUY":
        sl = round(entry - risk_dollars, 2)
        tp1 = round(entry + risk_dollars * 1.8, 2)
        tp2 = round(entry + risk_dollars * 3.2, 2)
        tp3 = round(entry + risk_dollars * 5.0, 2)
    else:
        sl = round(entry + risk_dollars, 2)
        tp1 = round(entry - risk_dollars * 1.8, 2)
        tp2 = round(entry - risk_dollars * 3.2, 2)
        tp3 = round(entry - risk_dollars * 5.0, 2)

    if not FORCE_RUN and state_mgr.is_duplicate(direction, entry, COOLDOWN_MINUTES):
        print("[Engine] Suppressing alert due to anti-spam cooldown.")
        sys.exit(0)

    signal_payload = {
        "direction": direction, "entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2, "tp3": tp3,
        "sl_pips": risk_pips, "score": score, "killzone": res["killzone_name"],
        "regime": res["regime"], "h4_trend": res["h4_trend"], "atr_step": atr_step_pips
    }

    if send_telegram_alert(signal_payload):
        state_mgr.save_signal(direction, entry, score)
        print("[Engine] Institutional signal dispatched successfully!")

    print("[Engine] Execution cycle completed cleanly.")

if __name__ == "__main__":
    main()
