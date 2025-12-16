import os
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import asyncio
import random

# ================================
# 1. SETUP & CONFIGURATION
# ================================
app = FastAPI(title="Quotex Signal API", version="2.0")

# Timeframe Map (Minutes -> Seconds)
TIME_MAP = {
    "5s": 5, "10s": 10, "15s": 15, "30s": 30,
    "1m": 60, "2m": 120, "3m": 180, "5m": 300,
    "10m": 600, "15m": 900, "30m": 1800,
    "1h": 3600, "4h": 14400, "1d": 86400
}

# Trade Logic Constants
EMA_SHORT = 50
EMA_LONG = 200
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26

# ================================
# 2. HELPER FUNCTIONS (Logic & Data)
# ================================

async def fetch_candles_from_broker(pair: str, timeframe_str: str, count: int = 300):
    """
    Simulates fetching data. Replace random logic with actual 'pyquotex' calls later.
    """
    seconds = TIME_MAP.get(timeframe_str)
    if not seconds:
        raise ValueError(f"Invalid Timeframe: {timeframe_str}")

    # --- اصلی کوڈ یہاں آئے گا (جب لائبریری لگ جائے گی) ---
    # client = Quotex(email=..., password=...)
    # ... code to fetch 'count' candles ...
    
    # --- فرضی ڈیٹا (Fake Data for Testing) ---
    # ہم تھوڑا رینڈم ڈیٹا بنا رہے ہیں تاکہ سگنلز بدلتے ہوئے نظر آئیں
    base_price = 1.3400
    volatility = 0.0005 if "s" in timeframe_str else 0.0020
    
    prices = []
    current = base_price
    for _ in range(count):
        change = random.uniform(-volatility, volatility)
        current += change
        prices.append(round(current, 6))
    
    return prices

def calculate_signal(close_prices):
    """
    آپ کا ٹریڈ برین (Trade Brain)
    """
    if len(close_prices) < EMA_LONG:
        return "WAIT", "Not enough data"

    # 1. EMA
    ema_short = sum(close_prices[-EMA_SHORT:]) / EMA_SHORT
    ema_long = sum(close_prices[-EMA_LONG:]) / EMA_LONG
    trend = "UP" if ema_short > ema_long else "DOWN"

    # 2. RSI
    gains, losses = [], []
    for i in range(-RSI_PERIOD, 0):
        change = close_prices[i] - close_prices[i-1]
        if change > 0: gains.append(change); losses.append(0)
        else: gains.append(0); losses.append(abs(change))
    
    avg_gain = sum(gains) / RSI_PERIOD if gains else 0
    avg_loss = sum(losses) / RSI_PERIOD if losses else 0
    rsi = 100 if avg_loss == 0 else 100 - (100 / (1 + avg_gain / avg_loss))

    # 3. MACD
    short_ema_macd = sum(close_prices[-MACD_FAST:]) / MACD_FAST
    long_ema_macd = sum(close_prices[-MACD_SLOW:]) / MACD_SLOW
    macd = short_ema_macd - long_ema_macd

    # 4. DECISION
    signal = "HOLD"
    reason = "Market condition unclear"
    
    if ema_short > ema_long and 40 < rsi < 55 and macd > 0:
        signal = "CALL"
        reason = "Uptrend + Good Momentum"
    elif ema_short < ema_long and 45 < rsi < 60 and macd < 0:
        signal = "PUT"
        reason = "Downtrend + Selling Pressure"

    return signal, reason, {
        "rsi": round(rsi, 2),
        "macd": round(macd, 6),
        "ema50": round(ema_short, 5),
        "ema200": round(ema_long, 5),
        "trend": trend
    }

# ================================
# 3. API ENDPOINTS (The New Stuff)
# ================================

@app.get("/")
def home():
    return {"message": "Quotex Signal API is Live", "endpoints": ["/live-signals", "/generate-signal", "/get-candles"]}

# --- 1. LIVE SIGNALS (سارے ٹائم فریمز کا ایک ساتھ نظارہ) ---
@app.get("/live-signals")
async def get_live_market_overview(pair: str = Query(..., description="e.g. EURUSD")):
    """
    یہ تمام اہم ٹائم فریمز (1m, 5m, 15m, 30m) کا لائیو اسٹیٹس بتائے گا۔
    """
    timeframes_to_check = ["1m", "5m", "15m", "30m"]
    report = {}
    
    for tf in timeframes_to_check:
        try:
            prices = await fetch_candles_from_broker(pair, tf)
            sig, reason, indicators = calculate_signal(prices)
            report[tf] = {
                "signal": sig,
                "action": "TRADE" if sig != "HOLD" else "WAIT",
                "trend": indicators["trend"],
                "rsi": indicators["rsi"]
            }
        except Exception as e:
            report[tf] = {"error": str(e)}

    return {
        "pair": pair,
        "market_snapshot": report,
        "summary": "This is a live overview of multiple timeframes."
    }

# --- 2. GENERATE SIGNAL (GET Request - آسان طریقہ) ---
@app.get("/generate-signal")
async def generate_signal_get(pair: str, timeframe: str):
    """
    براؤزر میں سیدھا لنک لکھ کر سگنل حاصل کریں:
    /generate-signal?pair=EURUSD&timeframe=1m
    """
    try:
        prices = await fetch_candles_from_broker(pair, timeframe)
        sig, reason, indicators = calculate_signal(prices)
        
        return {
            "pair": pair,
            "timeframe": timeframe,
            "final_signal": sig,
            "logic_reason": reason,
            "indicators": indicators,
            "current_price": prices[-1]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- 3. GET CANDLES (ڈیٹا چیک کرنے کے لیے) ---
@app.get("/get-candles")
async def get_raw_candles(pair: str, timeframe: str, count: int = 200):
    """
    پچھلی 200 کینڈلز کا ڈیٹا دیکھنے کے لیے تاکہ تسلی ہو جائے کہ ڈیٹا صحیح آ رہا ہے۔
    """
    try:
        prices = await fetch_candles_from_broker(pair, timeframe, count)
        return {
            "pair": pair,
            "timeframe": timeframe,
            "total_candles": len(prices),
            "latest_price": prices[-1],
            "oldest_price": prices[0],
            "data_preview": prices # یہ پوری لسٹ دکھائے گا
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- 4. GENERATE SIGNAL (POST Request - پرانا طریقہ) ---
class SignalRequest(BaseModel):
    pair: str
    timeframe: str

@app.post("/generate-signal")
async def generate_signal_post(request: SignalRequest):
    return await generate_signal_get(request.pair, request.timeframe)

# ================================
# 4. STARTUP (Railway Requirement)
# ================================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
