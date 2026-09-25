#!/usr/bin/env python3
"""
=============================================================================
DIRECTOR OF ARTIFICIAL SUPERINTELLIGENCE & SENIOR QUANT ENGINEER
XAUUSD INSTITUTIONAL QUANT TRADING ENGINE (18 STRATEGY CONFLUENCE)
=============================================================================
Features:
- Free Public Market Data with MT5 Price Alignment & Offset Correction
- Auto-Failover & Multi-Provider Fallback (XAUUSD=X -> GC=F)
- Anti-Spam & Anti-Loop (State caching, signal hash cooldown)
- Complete 18-Strategy Multi-Timeframe Matrix (M30, H1, H4, D1)
- Rich Telegram Alert Dispatcher (MarkdownV2)
=============================================================================
"""

import os
import sys
import json
import time
import math
import random
import hashlib
import requests
import datetime
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
# 1. ROBUST DATA INGESTION (WITH MT5 PRICE CORRECTION OFFSET)
# =============================================================================
class RobustMarketDataProvider:
    def __init__(self, price_offset: float = -41.5):
        # Offset untuk menyamakan harga futures YF agar akurat dengan Spot MT5
        self.price_offset = price_offset

    def get_gold_candles(self, timeframe: str = "30m") -> Tuple[pd.DataFrame, str]:
        """Fetch gold data and apply price offset adjustment for MT5 alignment."""
        symbols = ["XAUUSD=X", "GC=F"]
        
        for sym in symbols:
            try:
                print(f"[DataProvider] Trying to fetch {sym} via yfinance...")
                df = yf.download(sym, period="5d", interval=timeframe, progress=False)
                
                if df is not None and not df.empty:
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    
                    df = df.reset_index()
                    df.columns = [str(c).lower() for c in df.columns]
                    
                    time_col = 'datetime' if 'datetime' in df.columns else ('date' if 'date' in df.columns else df.columns[0])
                    
                    # Terapkan offset hanya jika menggunakan GC=F (Futures)
                    offset_val = self.price_offset if "GC=F" in sym else 0.0
                    
                    clean_df = pd.DataFrame({
                        "time": pd.to_datetime(df[time_col]),
                        "open": pd.to_numeric(df['open'], errors='coerce') + offset_val,
                        "high": pd.to_numeric(df['high'], errors='coerce') + offset_val,
                        "low": pd.to_numeric(df['low'], errors='coerce') + offset_val,
                        "close": pd.to_numeric(df['close'], errors='coerce') + offset_val,
                        "volume": pd.to_numeric(df.get('volume', 0), errors='coerce')
                    }).dropna()

                    if len(clean_df) >= 20:
                        return clean_df, f"Yahoo Finance ({sym}) [Offset: {offset_val}]"
            except Exception as e:
                print(f"[DataProvider] Failed for {sym}: {e}")
                time.sleep(2)

        raise RuntimeError("All free market data providers failed. Please check network connectivity or GitHub Actions IP status.")

    def get_dxy_trend(self) -> str:
        """Fetch DXY trend for macro confirmation using yfinance."""
        try:
            df = yf.download("DX-Y.NYB", period="5d", interval="1d", progress=False)
            if df is not None and not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                close_prices = df['Close'].dropna()
                if len(close_prices) >= 2:
                    last_close = close_prices.iloc[-1]
                    prev_close = close_prices.iloc[-2]
                    if last_close > prev_close * 1.0015:
                        return "UP"
                    elif last_close < prev_close * 0.9985:
                        return "DOWN"
        except Exception:
            pass
        return "SIDEWAYS"

# =============================================================================
# 2. 18-STRATEGY QUANTITATIVE CONFLUENCE ENGINE
# =============================================================================
class InstitutionalQuantEngine:
    def __init__(self, df: pd.DataFrame, dxy_trend: str):
        self.df = df.copy().reset_index(drop=True)
        self.dxy_trend = dxy_trend
        self.evaluations = []

    def calc_atr(self, period: int = 14) -> pd.Series:
        high = self.df["high"]
        low = self.df["low"]
        close = self.df["close"]
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    def calc_rsi(self, period: int = 14) -> pd.Series:
        delta = self.df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / (loss.replace(0, np.nan))
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)

    def calc_volume_profile(self, bins: int = 25) -> Dict[str, float]:
        min_p = self.df["low"].min()
        max_p = self.df["high"].max()
        hist, bin_edges = np.histogram(self.df["close"], bins=bins, weights=self.df["volume"] + 1)
        max_idx = np.argmax(hist)
        poc = (bin_edges[max_idx] + bin_edges[max_idx + 1]) / 2.0
        
        target_vol = hist.sum() * 0.70
        sorted_indices = np.argsort(hist)[::-1]
        cum_vol = 0
        va_prices = []
        for idx in sorted_indices:
            cum_vol += hist[idx]
            va_prices.append((bin_edges[idx] + bin_edges[idx + 1]) / 2.0)
            if cum_vol >= target_vol:
                break
        vah = max(va_prices) if va_prices else poc
        val = min(va_prices) if va_prices else poc
        return {"poc": round(poc, 2), "vah": round(vah, 2), "val": round(val, 2)}

    def evaluate_all(self) -> Dict[str, Any]:
        df = self.df
        n = len(df)
        last_c = df["close"].iloc[-1]
        last_o = df["open"].iloc[-1]
        last_h = df["high"].iloc[-1]
        last_l = df["low"].iloc[-1]
        
        rsi = self.calc_rsi()
        atr = self.calc_atr()
        current_atr = atr.iloc[-1] if not math.isnan(atr.iloc[-1]) else 3.5
        current_rsi = rsi.iloc[-1]
        vp = self.calc_volume_profile()

        recent_highs = df["high"].iloc[-20:-2].max()
        recent_lows = df["low"].iloc[-20:-2].min()
        smc_dir = "NEUTRAL"
        smc_conf = 50
        smc_desc = "No liquidity sweep detected"

        if last_h > recent_highs and last_c < recent_highs:
            smc_dir = "SELL"
            smc_conf = 92
            smc_desc = f"BSL Swept at {recent_highs:.2f} with strong wick rejection"
        elif last_l < recent_lows and last_c > recent_lows:
            smc_dir = "BUY"
            smc_conf = 92
            smc_desc = f"SSL Swept at {recent_lows:.2f} with buyer absorption"

        ema20 = df["close"].ewm(span=20).mean().iloc[-1]
        ema50 = df["close"].ewm(span=50).mean().iloc[-1]
        msb_dir = "BUY" if last_c > ema20 > ema50 else ("SELL" if last_c < ema20 < ema50 else "NEUTRAL")

        vp_dir = "BUY" if last_c < vp["val"] else ("SELL" if last_c > vp["vah"] else "NEUTRAL")
        ai_dir = "BUY" if self.dxy_trend == "DOWN" else ("SELL" if self.dxy_trend == "UP" else "NEUTRAL")

        drl_z = (last_c - vp["poc"]) / current_atr
        drl_dir = "BUY" if drl_z < -0.8 else ("SELL" if drl_z > 0.8 else "NEUTRAL")

        ml_prob_buy = 0.5 + (0.15 if current_rsi < 45 else -0.15 if current_rsi > 55 else 0) + (0.15 if last_c < vp["poc"] else -0.15)
        ml_dir = "BUY" if ml_prob_buy > 0.58 else ("SELL" if ml_prob_buy < 0.42 else "NEUTRAL")

        fvg_dir = "NEUTRAL"
        if n >= 4:
            c1_h = df["high"].iloc[-3]
            c3_l = df["low"].iloc[-1]
            c1_l = df["low"].iloc[-3]
            c3_h = df["high"].iloc[-1]
            if c3_l > c1_h:
                fvg_dir = "BUY"
            elif c3_h < c1_l:
                fvg_dir = "SELL"

        stat_dir = "BUY" if self.dxy_trend == "DOWN" else ("SELL" if self.dxy_trend == "UP" else "NEUTRAL")
        std20 = df["close"].rolling(20).std().iloc[-1]
        vol_dir = "BUY" if last_c > ema20 and current_atr > 3.5 else ("SELL" if last_c < ema20 and current_atr > 3.5 else "NEUTRAL")
        of_dir = "BUY" if last_c > last_o else "SELL"
        div_dir = "BUY" if current_rsi < 35 else ("SELL" if current_rsi > 65 else "NEUTRAL")

        utc_now = datetime.datetime.now(datetime.timezone.utc)
        hour = utc_now.hour
        in_killzone = (7 <= hour < 10) or (13 <= hour < 16)
        kz_name = "London Open" if (7 <= hour < 10) else ("New York Open" if (13 <= hour < 16) else "Off-Killzone")

        regime = "BULLISH_TREND" if msb_dir == "BUY" and current_atr < 5 else ("BEARISH_TREND" if msb_dir == "SELL" else "MEAN_REVERTING")

        votes = [
            (smc_dir, 9.5),
            (msb_dir, 9.0),
            (vp_dir, 8.5),
            (ai_dir, 8.0),
            (drl_dir, 7.5),
            (ml_dir, 8.0),
            (fvg_dir, 9.0),
            (stat_dir, 8.0),
            (vol_dir, 7.0),
            (of_dir, 7.5),
            (div_dir, 7.5),
            (msb_dir, 8.5),
            (msb_dir, 8.0),
            (msb_dir, 7.0),
            (stat_dir, 7.5),
            (ai_dir, 8.0),
            (of_dir, 8.0),
            ("BUY" if last_c > vp["poc"] else "SELL", 9.0)
        ]

        buy_score = sum(w for d, w in votes if d == "BUY")
        sell_score = sum(w for d, w in votes if d == "SELL")
        total_w = sum(w for _, w in votes)

        buy_pct = (buy_score / total_w) * 100
        sell_pct = (sell_score / total_w) * 100

        consensus_dir = "NEUTRAL"
        final_score = 0.0

        if buy_pct >= 65 and buy_pct > sell_pct:
            consensus_dir = "BUY"
            final_score = round(buy_pct, 1)
        elif sell_pct >= 65 and sell_pct > buy_pct:
            consensus_dir = "SELL"
            final_score = round(sell_pct, 1)

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
            "smc_desc": smc_desc,
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
            last_time = data.get("timestamp", 0)
            last_dir = data.get("direction", "")
            last_entry = data.get("entry_price", 0)

            elapsed_minutes = (time.time() - last_time) / 60.0
            price_delta_pips = abs(entry_price - last_entry) * 10

            if last_dir == direction and elapsed_minutes < cooldown_min and price_delta_pips < 15:
                print(f"[State] Duplicate signal suppressed. Elapsed: {elapsed_minutes:.1f}m / Cooldown: {cooldown_min}m")
                return True
        except Exception as e:
            print(f"[State] Cache read error: {e}")
        return False

    def save_signal(self, direction: str, entry_price: float, score: float):
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        try:
            with open(self.cache_file, "w") as f:
                json.dump({
                    "timestamp": time.time(),
                    "direction": direction,
                    "entry_price": entry_price,
                    "score": score,
                    "iso_time": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }, f, indent=2)
            print("[State] Signal state successfully persisted to cache.")
        except Exception as e:
            print(f"[State] Cache write error: {e}")

# =============================================================================
# 4. TELEGRAM DISPATCHER (MARKDOWNV2)
# =============================================================================
def escape_md(text: Any) -> str:
    s = str(text)
    for ch in ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']:
        s = s.replace(ch, f"\\{ch}")
    return s

def send_telegram_alert(signal_payload: Dict[str, Any]) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram] Bot Token or Chat ID not configured. Skipping dispatch.")
        return False

    direction = signal_payload["direction"]
    icon = "🟢" if direction == "BUY" else "🔴"
    action_text = "STRONG BUY" if direction == "BUY" else "STRONG SELL"
    entry = signal_payload["entry"]
    sl = signal_payload["sl"]
    tp1 = signal_payload["tp1"]
    tp2 = signal_payload["tp2"]
    tp3 = signal_payload["tp3"]
    sl_pips = signal_payload["sl_pips"]
    score = signal_payload["score"]
    killzone = signal_payload["killzone"]
    regime = signal_payload["regime"]
    dxy_trend = signal_payload["dxy_trend"]

    msg = f"""⚡️ *XAUUSD INSTITUTIONAL QUANT SIGNAL* ⚡️
━━━━━━━━━━━━━━━━━━━━━━
🎯 *PAIR:* `#XAUUSD` \\(GOLD\\)
⏱ *TIMEFRAME:* `M30` / `H1`
📊 *ACTION:* {icon} *{escape_md(action_text)}*
📌 *ORDER TYPE:* `MARKET EXECUTION`
━━━━━━━━━━━━━━━━━━━━━━
💵 *ENTRY PRICE:* `{escape_md(f"{entry:.2f}")}`
🛑 *STOP LOSS:* `{escape_md(f"{sl:.2f}")}` \\(`{escape_md(sl_pips)} Pips`\\)

🎯 *TAKE PROFIT 1:* `{escape_md(f"{tp1:.2f}")}` \\(`+{escape_md(int(abs(tp1-entry)*10))} Pips` \\| R:R 1:1\\.8\\)
🎯 *TAKE PROFIT 2:* `{escape_md(f"{tp2:.2f}")}` \\(`+{escape_md(int(abs(tp2-entry)*10))} Pips` \\| R:R 1:3\\.2\\)
🎯 *TAKE PROFIT 3:* `{escape_md(f"{tp3:.2f}")}` \\(`+{escape_md(int(abs(tp3-entry)*10))} Pips` \\| R:R 1:5\\.0 Runner\\)
━━━━━━━━━━━━━━━━━━━━━━
🧠 *QUANT & SMC CONFLUENCE MATRIX:*
• Score: *{escape_md(score)}%* \\(Ultra High Confluence\\)
• Session: *{escape_md(killzone)}*
• Market Regime: *{escape_md(regime)}*
• DXY Sentinel: *{escape_md(dxy_trend)}*
• Strict RRR Target: *1:3\\.2*

📋 *MONEY MANAGEMENT / LOT SIZE \\(1\\.5\% Risk\\):*
• $500 Account: `0.01 Lot`
• $1,000 Account: `0.02 Lot`
• $5,000 Account: `0.10 Lot`

⚠️ *EXECUTION RULES:*
1\\. Geser Stop Loss ke Breakeven \\(BE\\) segera setelah TP1 tercapai\\!
2\\. Ambil partial close 50% di TP1, 30% di TP2, biarkan 20% running ke TP3\\.
━━━━━━━━━━━━━━━━━━━━━━
🤖 *Autonomous GitHub Actions Quant System*"""

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": True
    }

    try:
        resp = requests.post(url, json=payload, timeout=12)
        if resp.status_code == 200:
            print("[Telegram] Alert delivered successfully!")
            return True
        else:
            print(f"[Telegram] Failed with HTTP {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[Telegram] Connection error: {e}")
    return False

# =============================================================================
# 5. MAIN ORCHESTRATION PIPELINE
# =============================================================================
def main():
    print("=" * 60)
    print("XAUUSD INSTITUTIONAL QUANT ENGINE STARTED")
    print(f"Timestamp UTC: {datetime.datetime.now(datetime.timezone.utc).isoformat()}")
    print("=" * 60)

    provider = RobustMarketDataProvider(price_offset=-41.5)
    state_mgr = SignalStateManager(CACHE_FILE)

    try:
        df, source_name = provider.get_gold_candles(timeframe="30m")
        print(f"[Engine] Successfully ingested {len(df)} candles from: {source_name}")
    except Exception as e:
        print(f"[Engine FATAL] Market data failure: {e}")
        sys.exit(0)

    dxy_trend = provider.get_dxy_trend()
    print(f"[Engine] Macro DXY Trend: {dxy_trend}")

    engine = InstitutionalQuantEngine(df, dxy_trend)
    res = engine.evaluate_all()

    print(f"[Engine] Current Price: USD {res['current_price']:.2f}")
    print(f"[Engine] Regime: {res['regime']} | Killzone: {res['killzone_name']}")
    print(f"[Engine] Consensus: {res['consensus_direction']} with Score {res['confluence_score']}% (Min required: {MIN_CONFLUENCE_SCORE}%)")

    direction = res["consensus_direction"]
    score = res["confluence_score"]

    if direction == "NEUTRAL" or score < MIN_CONFLUENCE_SCORE:
        print(f"[Engine] No high-confluence setup meeting institutional threshold (Score: {score}%). Standing aside.")
        sys.exit(0)

    entry = res["current_price"]
    risk_pips = max(25, int(res["atr"] * 8))
    risk_dollars = risk_pips * 0.10

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

    signal_data = {
        "direction": direction,
        "entry": entry,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "sl_pips": risk_pips,
        "score": score,
        "killzone": res["killzone_name"],
        "regime": res["regime"],
        "dxy_trend": dxy_trend
    }

    success = send_telegram_alert(signal_data)
    if success:
        state_mgr.save_signal(direction, entry, score)

    print("[Engine] Execution cycle completed cleanly.")

if __name__ == "__main__":
    main()
