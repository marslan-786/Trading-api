import sys
import subprocess

# Auto-Install Logic
try:
    from quotexapi.stable_api import Quotex
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "git+https://github.com/cleitonleonel/pyquotex.git"])
    from quotexapi.stable_api import Quotex

import asyncio
from fastapi import FastAPI, HTTPException
import time

app = FastAPI()

# CREDENTIALS
EMAIL = "marslansalfias@gmail.com"
PASSWORD = "Arslan@786"

client = Quotex(email=EMAIL, password=PASSWORD)
is_connected = False

async def ensure_connection():
    global is_connected
    if not is_connected:
        print(f"🔌 Connecting to Quotex...")
        check, reason = await client.connect()
        if check:
            print("✅ Connected!")
            is_connected = True
        else:
            print(f"❌ Failed: {reason}")
            is_connected = False
    return is_connected

def calculate_indicators(prices):
    if len(prices) < 200: return None
    ema_50 = sum(prices[-50:]) / 50
    ema_200 = sum(prices[-200:]) / 200
    
    gains, losses = [], []
    for i in range(-14, 0):
        change = prices[i] - prices[i-1]
        if change > 0: gains.append(change); losses.append(0)
        else: gains.append(0); losses.append(abs(change))
    
    avg_gain = sum(gains) / 14 if gains else 0
    avg_loss = sum(losses) / 14 if losses else 0
    rsi = 100 - (100 / (1 + avg_gain / avg_loss)) if avg_loss != 0 else 50

    short_ema = sum(prices[-12:]) / 12
    long_ema = sum(prices[-26:]) / 26
    macd = short_ema - long_ema
    
    return {"ema_50": ema_50, "ema_200": ema_200, "rsi": rsi, "macd": macd}

def get_trade_decision(indicators):
    if not indicators: return "WAIT"
    ema_50, ema_200, rsi, macd = indicators["ema_50"], indicators["ema_200"], indicators["rsi"], indicators["macd"]
    
    if ema_50 > ema_200 and 40 < rsi < 55 and macd > 0: return "CALL"
    elif ema_50 < ema_200 and 45 < rsi < 60 and macd < 0: return "PUT"
    return "HOLD"

@app.on_event("startup")
async def startup_event():
    await ensure_connection()

@app.get("/")
def home():
    return {"status": "Online", "connected": is_connected}

@app.get("/get-candles")
async def get_candles_route(pair: str = "EURUSD", timeframe: int = 60):
    await ensure_connection()
    candles = await client.get_candles(pair, int(timeframe))
    if not candles: return {"status": "error", "message": "No data"}
    
    formatted = [{"time": c['time'], "close": c['close']} for c in candles[-50:]]
    return {"pair": pair, "total_candles": len(candles), "data": formatted}

@app.get("/get-signal")
async def get_signal_route(pair: str = "EURUSD", timeframe: int = 60):
    await ensure_connection()
    candles = await client.get_candles(pair, int(timeframe))
    if not candles or len(candles) < 200: return {"signal": "WAIT", "reason": "No Data"}
    
    prices = [c['close'] for c in candles]
    indicators = calculate_indicators(prices)
    decision = get_trade_decision(indicators)
    
    return {"pair": pair, "signal": decision, "price": prices[-1]}

@app.get("/live-signals")
async def live_signals_route(pair: str = "EURUSD"):
    await ensure_connection()
    candles = await client.get_candles(pair, 60)
    if not candles or len(candles) < 200: return {"status": "loading"}
    
    prices = [c['close'] for c in candles]
    indicators = calculate_indicators(prices)
    decision = get_trade_decision(indicators)
    
    return {
        "pair": pair,
        "final_signal": decision,
        "market_data": {
            "price": prices[-1],
            "rsi": round(indicators['rsi'], 2),
            "ema_50": round(indicators['ema_50'], 5),
            "ema_200": round(indicators['ema_200'], 5),
            "trend": "UP" if indicators['ema_50'] > indicators['ema_200'] else "DOWN"
        }
    }
