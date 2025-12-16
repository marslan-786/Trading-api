import asyncio
from fastapi import FastAPI, HTTPException
from quotexapi.stable_api import Quotex
import time

app = FastAPI()

# ==========================================
# ⚙️ USER CREDENTIALS (REAL ACCOUNT)
# ==========================================
EMAIL = "marslansalfias@gmail.com"
PASSWORD = "Arslan@786"

# Quotex Client
client = Quotex(email=EMAIL, password=PASSWORD)
is_connected = False

# ==========================================
# 🔌 CONNECTION LOGIC
# ==========================================
async def ensure_connection():
    global is_connected
    if not is_connected:
        print(f"🔌 Connecting to Quotex as {EMAIL}...")
        check, reason = await client.connect()
        if check:
            print("✅ Connected Successfully!")
            is_connected = True
        else:
            print(f"❌ Connection Failed: {reason}")
            is_connected = False
    return is_connected

# ==========================================
# 🧠 INDICATOR LOGIC (HELPER FUNCTIONS)
# ==========================================
def calculate_indicators(prices):
    if len(prices) < 200:
        return None

    # 1. EMA Calculation
    ema_50 = sum(prices[-50:]) / 50
    ema_200 = sum(prices[-200:]) / 200
    
    # 2. RSI Calculation (14)
    gains, losses = [], []
    for i in range(-14, 0):
        change = prices[i] - prices[i-1]
        if change > 0: gains.append(change); losses.append(0)
        else: gains.append(0); losses.append(abs(change))
    
    avg_gain = sum(gains) / 14 if gains else 0
    avg_loss = sum(losses) / 14 if losses else 0
    
    if avg_loss == 0: rsi = 100
    else: rsi = 100 - (100 / (1 + avg_gain / avg_loss))

    # 3. MACD (12, 26)
    short_ema = sum(prices[-12:]) / 12
    long_ema = sum(prices[-26:]) / 26
    macd = short_ema - long_ema
    
    return {"ema_50": ema_50, "ema_200": ema_200, "rsi": rsi, "macd": macd}

def get_trade_decision(indicators):
    if not indicators: return "WAIT"
    
    ema_50 = indicators["ema_50"]
    ema_200 = indicators["ema_200"]
    rsi = indicators["rsi"]
    macd = indicators["macd"]
    
    # YOUR LOGIC
    # CALL: EMA50 > EMA200 + RSI(40-55) + MACD > 0
    if ema_50 > ema_200 and 40 < rsi < 55 and macd > 0:
        return "CALL"
    
    # PUT: EMA50 < EMA200 + RSI(45-60) + MACD < 0
    elif ema_50 < ema_200 and 45 < rsi < 60 and macd < 0:
        return "PUT"
        
    return "HOLD"

# ==========================================
# 🛣️ API ROUTES (ENDPOINTS)
# ==========================================

@app.on_event("startup")
async def startup_event():
    await ensure_connection()

@app.get("/")
def home():
    return {"status": "Online", "connected": is_connected, "endpoints": ["/get-candles", "/get-signal", "/live-signals"]}

# --- ROUTE 1: GET CANDLES (RAW DATA) ---
@app.get("/get-candles")
async def get_candles_route(pair: str = "EURUSD", timeframe: int = 60):
    """
    timeframe: 60 (1 min), 300 (5 min)
    Returns: Raw Candle Data (Open, Close, High, Low)
    """
    await ensure_connection()
    
    # Quotex API returns candles as objects
    candles = await client.get_candles(pair, int(timeframe))
    
    if not candles:
        return {"status": "error", "message": "No data found"}
    
    # Format data for user
    formatted_data = []
    for c in candles[-50:]: # آخری 50 کینڈلز دکھائیں تاکہ رسپونس بھاری نہ ہو
        formatted_data.append({
            "time": c['time'],
            "open": c['open'],
            "close": c['close'],
            "high": c['high'],
            "low": c['low']
        })
        
    return {
        "pair": pair,
        "timeframe": timeframe,
        "total_candles": len(candles),
        "latest_candles": formatted_data
    }

# --- ROUTE 2: GET SIGNAL (SIMPLE DECISION) ---
@app.get("/get-signal")
async def get_signal_route(pair: str = "EURUSD", timeframe: int = 60):
    await ensure_connection()
    
    # ہمیں لوجک کے لیے کم از کم 250 کینڈلز چاہیے
    candles = await client.get_candles(pair, int(timeframe))
    if not candles or len(candles) < 200:
        return {"signal": "WAIT", "reason": "Not enough data"}
        
    prices = [c['close'] for c in candles]
    indicators = calculate_indicators(prices)
    decision = get_trade_decision(indicators)
    
    return {
        "pair": pair,
        "signal": decision,
        "current_price": prices[-1]
    }

# --- ROUTE 3: LIVE SIGNALS (DETAILED ANALYSIS) ---
@app.get("/live-signals")
async def live_signals_route(pair: str = "EURUSD"):
    """
    یہ روٹ مکمل تجزیہ دے گا (RSI, EMA ویلیوز کے ساتھ)
    ڈیفالٹ ٹائم فریم 1 منٹ (60) رکھا ہے
    """
    await ensure_connection()
    
    candles = await client.get_candles(pair, 60)
    if not candles or len(candles) < 200:
        return {"status": "loading", "message": "Fetching candle history..."}
        
    prices = [c['close'] for c in candles]
    indicators = calculate_indicators(prices)
    decision = get_trade_decision(indicators)
    
    return {
        "pair": pair,
        "timeframe": "1m",
        "final_signal": decision,
        "market_data": {
            "price": prices[-1],
            "rsi": round(indicators['rsi'], 2),
            "ema_50": round(indicators['ema_50'], 5),
            "ema_200": round(indicators['ema_200'], 5),
            "macd": round(indicators['macd'], 6),
            "trend": "UP" if indicators['ema_50'] > indicators['ema_200'] else "DOWN"
        }
    }
