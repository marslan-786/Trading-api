import asyncio
from fastapi import FastAPI, HTTPException
# اب یہ لائن بغیر ایرر کے چلے گی کیونکہ فولڈر موجود ہے
from quotexapi.stable_api import Quotex 
import time

app = FastAPI()

# ==========================================
# ⚙️ USER CREDENTIALS
# ==========================================
EMAIL = "marslansalfias@gmail.com"
PASSWORD = "Arslan@786"

# Quotex Client Global
client = Quotex(email=EMAIL, password=PASSWORD)
is_connected = False

# ==========================================
# 🔌 CONNECTION LOGIC
# ==========================================
async def ensure_connection():
    global is_connected
    if not is_connected:
        print(f"🔌 Connecting to Quotex as {EMAIL}...")
        # کوٹیکس سرور سے کنیکٹ کریں
        check, reason = await client.connect()
        if check:
            print("✅ Connected Successfully!")
            is_connected = True
        else:
            print(f"❌ Connection Failed: {reason}")
            is_connected = False
    return is_connected

# ==========================================
# 🧠 INDICATOR LOGIC
# ==========================================
def calculate_indicators(prices):
    if len(prices) < 50: return None # کم از کم 50 کینڈلز چاہیے

    # EMA
    ema_50 = sum(prices[-50:]) / 50
    # اگر 200 کینڈلز نہیں ہیں تو جتنا ڈیٹا ہے اسی پر گزارہ کریں
    ema_200 = sum(prices[-200:]) / 200 if len(prices) >= 200 else ema_50 
    
    # RSI (14)
    gains, losses = [], []
    for i in range(-14, 0):
        try:
            change = prices[i] - prices[i-1]
            if change > 0: gains.append(change); losses.append(0)
            else: gains.append(0); losses.append(abs(change))
        except: pass
    
    avg_gain = sum(gains) / 14 if gains else 0
    avg_loss = sum(losses) / 14 if losses else 0
    rsi = 100 - (100 / (1 + avg_gain / avg_loss)) if avg_loss != 0 else 50

    return {"ema_50": ema_50, "ema_200": ema_200, "rsi": rsi}

def get_trade_decision(indicators):
    if not indicators: return "WAIT"
    
    ema_50 = indicators["ema_50"]
    ema_200 = indicators["ema_200"]
    rsi = indicators["rsi"]
    
    # CALL: EMA50 > EMA200 AND RSI 40-55
    if ema_50 > ema_200 and 40 < rsi < 55:
        return "CALL"
    
    # PUT: EMA50 < EMA200 AND RSI 45-60
    elif ema_50 < ema_200 and 45 < rsi < 60:
        return "PUT"
        
    return "HOLD"

# ==========================================
# 🛣️ API ROUTES
# ==========================================

@app.on_event("startup")
async def startup_event():
    await ensure_connection()

@app.get("/")
def home():
    return {"status": "Quotex API Online", "connected": is_connected}

@app.get("/get-candles")
async def get_candles_route(pair: str = "EURUSD", timeframe: int = 60):
    await ensure_connection()
    # اصلی کینڈلز لائیں
    candles = await client.get_candles(pair, int(time.time()), 3600, timeframe)
    
    if not candles:
        return {"status": "error", "message": "No data received"}
    
    # صرف ضروری ڈیٹا واپس کریں
    formatted = []
    for c in candles[-50:]: # آخری 50 کافی ہیں
        formatted.append({
            "time": c['time'],
            "close": c['close']
        })
        
    return {"pair": pair, "total": len(candles), "data": formatted}

@app.get("/live-signals")
async def live_signals_route(pair: str = "EURUSD"):
    await ensure_connection()
    # 200 کینڈلز لانے کی کوشش (3600 سیکنڈ پیچھے)
    candles = await client.get_candles(pair, int(time.time()), 12000, 60)
    
    if not candles:
        return {"status": "loading"}
        
    prices = [c['close'] for c in candles]
    indicators = calculate_indicators(prices)
    decision = get_trade_decision(indicators)
    
    return {
        "pair": pair,
        "signal": decision,
        "price": prices[-1],
        "analysis": {
            "rsi": round(indicators['rsi'], 2),
            "trend": "UP" if indicators['ema_50'] > indicators['ema_200'] else "DOWN"
        }
    }
