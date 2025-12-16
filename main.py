import os
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
import random 

# اگر اصلی لائبریری استعمال کرنی ہے تو نیچے والی لائن ان-کمنٹ کریں
# from quotexapi.stable_api import Quotex 

app = FastAPI()

# ================================
# 1. TIMEFRAME MAPPING
# ================================
TIME_MAP = {
    "5s": 5, "10s": 10, "15s": 15, "30s": 30,
    "1m": 60, "2m": 120, "3m": 180, "5m": 300,
    "10m": 600, "15m": 900, "30m": 1800,
    "1h": 3600, "4h": 14400, "1d": 86400
}

# ================================
# 2. TRADE LOGIC CONSTANTS
# ================================
EMA_SHORT_PERIOD = 50
EMA_LONG_PERIOD = 200
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26

# ================================
# 3. ANALYSIS LOGIC
# ================================
def analyze_market_logic(close_prices):
    if len(close_prices) < EMA_LONG_PERIOD:
        return {"decision": "HOLD", "reason": "Insufficient Data", "details": {}}

    # EMA Calculation
    ema_short = sum(close_prices[-EMA_SHORT_PERIOD:]) / EMA_SHORT_PERIOD
    ema_long = sum(close_prices[-EMA_LONG_PERIOD:]) / EMA_LONG_PERIOD
    trend = "UP" if ema_short > ema_long else "DOWN"
    
    # RSI Calculation
    gains = []
    losses = []
    for i in range(-RSI_PERIOD, 0):
        change = close_prices[i] - close_prices[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
            
    avg_gain = sum(gains) / RSI_PERIOD if gains else 0
    avg_loss = sum(losses) / RSI_PERIOD if losses else 0
    
    if avg_loss == 0:
        rsi = 100
    else:
        rsi = 100 - (100 / (1 + avg_gain / avg_loss))

    # MACD Calculation
    short_ema_macd = sum(close_prices[-MACD_FAST:]) / MACD_FAST
    long_ema_macd = sum(close_prices[-MACD_SLOW:]) / MACD_SLOW
    macd_val = short_ema_macd - long_ema_macd

    # REPORT
    details = {
        "trend": trend,
        "rsi": round(rsi, 2),
        "macd": round(macd_val, 5),
        "ema_50": round(ema_short, 5),
        "ema_200": round(ema_long, 5)
    }

    # DECISION
    final_signal = "HOLD"
    reason = "Market is choppy."

    if ema_short > ema_long and 40 < rsi < 55 and macd_val > 0:
        final_signal = "CALL"
        reason = "Strong UP trend with healthy momentum."
    
    elif ema_short < ema_long and 45 < rsi < 60 and macd_val < 0:
        final_signal = "PUT"
        reason = "Strong DOWN trend with selling pressure."

    return {
        "decision": final_signal,
        "reason": reason,
        "details": details
    }

# ================================
# 4. DATA FETCHING
# ================================
async def fetch_candles(pair: str, timeframe_str: str):
    seconds = TIME_MAP.get(timeframe_str)
    if not seconds: raise ValueError("Invalid Timeframe")

    # --- REAL QUOTEX CODE (Uncomment on Railway) ---
    # EMAIL = os.getenv("QUOTEX_EMAIL")
    # PASS = os.getenv("QUOTEX_PASSWORD")
    # client = Quotex(email=EMAIL, password=PASS)
    # ... (connection logic) ...
    
    # --- FAKE DATA FOR TEST ---
    base = 1.34150
    return [base + (random.uniform(-0.0005, 0.0005)) for _ in range(300)]

# ================================
# 5. API ENDPOINT
# ================================
class SignalRequest(BaseModel):
    pair: str
    timeframe: str

@app.get("/")
def home():
    return {"status": "Online", "message": "Signal API is running on Railway!"}

@app.post("/generate-signal")
async def get_signal(request: SignalRequest):
    try:
        prices = await fetch_candles(request.pair, request.timeframe)
        result = analyze_market_logic(prices)
        
        return {
            "market_analysis": {
                "pair": request.pair,
                "timeframe": request.timeframe,
                "current_price": prices[-1],
                "logic_breakdown": result["reason"],
                "indicators": result["details"]
            },
            "final_decision": {
                "signal": result["decision"],
                "action": "TRADE NOW" if result["decision"] != "HOLD" else "WAIT"
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ================================
# 6. SERVER STARTUP
# ================================
if __name__ == "__main__":
    # یہ لائن ریلوے کے لیے بہت ضروری ہے
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
