import os
import sys
import asyncio
from fastapi import FastAPI

# ==========================================
# 🛠️ AUTO-FIX FOLDER NAME (سب سے پہلے یہ چلے گا)
# ==========================================
# اگر 'quotexapi' نام کا فولڈر موجود ہے، تو اسے 'pyquotex' کر دو
if os.path.exists("quotexapi"):
    print("🔄 Found 'quotexapi', renaming to 'pyquotex'...")
    try:
        os.rename("quotexapi", "pyquotex")
        print("✅ Folder Renamed Successfully!")
    except Exception as e:
        print(f"⚠️ Rename failed (Might be in use or already done): {e}")

# ==========================================
# 📦 LIBRARIES IMPORT (نام ٹھیک ہونے کے بعد)
# ==========================================
try:
    # اب یہ لائن بغیر ایرر کے چلے گی
    from pyquotex.stable_api import Quotex
except ImportError as e:
    print("❌ CRITICAL ERROR: Library not found even after fix attempt.")
    print(f"Details: {e}")
    # اگر اب بھی نہ ملے تو ایپ بند کر دو تاکہ لاگز میں پتا چلے
    sys.exit(1)

# ==========================================
# ⚙️ CONFIGURATION & CREDENTIALS
# ==========================================
EMAIL = "marslansalfias@gmail.com"
PASSWORD = "Arslan@786"

app = FastAPI()
client = Quotex(email=EMAIL, password=PASSWORD)
is_connected = False

# ==========================================
# 🔌 CONNECTION LOGIC
# ==========================================
async def ensure_connection():
    global is_connected
    if not is_connected:
        print(f"🔌 Connecting to Quotex as {EMAIL}...")
        try:
            check, reason = await client.connect()
            if check:
                print("✅ Connected Successfully!")
                is_connected = True
            else:
                print(f"❌ Connection Failed: {reason}")
                is_connected = False
        except Exception as e:
            print(f"⚠️ Connection Error: {e}")
            is_connected = False
    return is_connected

# ==========================================
# 🧠 INDICATORS & LOGIC
# ==========================================
def calculate_indicators(prices):
    if len(prices) < 50: return None

    # EMA Calculation
    ema_50 = sum(prices[-50:]) / 50
    ema_200 = sum(prices[-200:]) / 200 if len(prices) >= 200 else ema_50
    
    # RSI Calculation (14)
    gains, losses = [], []
    for i in range(-14, 0):
        try:
            change = prices[i] - prices[i-1]
            if change > 0: gains.append(change); losses.append(0)
            else: gains.append(0); losses.append(abs(change))
        except: pass
    
    avg_gain = sum(gains) / 14 if gains else 0
    avg_loss = sum(losses) / 14 if losses else 0
    
    if avg_loss == 0: rsi = 100
    else: rsi = 100 - (100 / (1 + avg_gain / avg_loss))

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
    return {"status": "Quotex API Running", "connected": is_connected}

@app.get("/get-candles")
async def get_candles_route(pair: str = "EURUSD", timeframe: int = 60):
    await ensure_connection()
    import time
    # 3600 seconds = 1 hour history
    candles = await client.get_candles(pair, int(time.time()), 3600, timeframe)
    
    if not candles:
        return {"status": "error", "message": "No data received from Quotex"}
    
    formatted = []
    for c in candles[-50:]:
        formatted.append({"time": c['time'], "close": c['close']})
        
    return {"pair": pair, "total": len(candles), "data": formatted}

@app.get("/live-signals")
async def live_signals_route(pair: str = "EURUSD"):
    await ensure_connection()
    import time
    # Fetch enough candles for EMA 200
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
            "rsi": round(indicators['rsi'], 2) if indicators else 0,
            "ema_trend": "UP" if indicators and indicators['ema_50'] > indicators['ema_200'] else "DOWN"
        }
    }
