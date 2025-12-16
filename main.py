import sys
import os
import asyncio
from fastapi import FastAPI

# ==========================================
# 🛡️ ANTI-CRASH SHIELD (یہ کوڈ ایپ بند ہونے سے روکے گا)
# ==========================================
def fake_exit(code=0):
    print(f"⚠️ WARNING: Library tried to crash app with code {code}, but I stopped it!")
    # ہم یہاں کچھ نہیں کریں گے، تاکہ ایپ چلتی رہے
    pass

# اصلی exit فنکشن کو اپنے والے سے بدل دیں
sys.exit = fake_exit

# ==========================================
# 🚑 EMERGENCY IMPORT FIX
# ==========================================
try:
    import quotexapi
    sys.modules['pyquotex'] = quotexapi
    import quotexapi.stable_api
    sys.modules['pyquotex.stable_api'] = quotexapi.stable_api
    from quotexapi.stable_api import Quotex
    print("✅ Successfully mapped quotexapi to pyquotex")
except ImportError as e:
    print(f"❌ Import Error: {e}")
    # Fallback
    try:
        from pyquotex.stable_api import Quotex
    except:
        print("CRITICAL: Quotex Library not found.")

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
EMAIL = "marslansalfias@gmail.com"
PASSWORD = "Arslan@786"

app = FastAPI()
client = Quotex(email=EMAIL, password=PASSWORD)
is_connected = False

# ==========================================
# 🔌 CONNECTION LOGIC (Improved)
# ==========================================
async def ensure_connection():
    global is_connected
    if is_connected: return True
    
    print(f"🔌 Connecting to Quotex as {EMAIL}...")
    try:
        # ہم connect کو try-except میں رکھیں گے
        check, reason = await client.connect()
        
        if check:
            print("✅ Connected Successfully!")
            is_connected = True
        else:
            print(f"❌ Connection Failed: {reason}")
            # اگر پاسورڈ غلط ہے تو یہاں پتا چل جائے گا
            if "auth" in str(reason).lower():
                print("⚠️ Check Email/Password!")
            is_connected = False
            
    except Exception as e:
        print(f"⚠️ Error during connection: {e}")
        is_connected = False
        
    return is_connected

# ==========================================
# 🛣️ API ROUTES
# ==========================================
@app.on_event("startup")
async def startup_event():
    # ایپ اسٹارٹ ہوتے ہی کنیکٹ کرنے کی کوشش
    await ensure_connection()

@app.get("/")
def home():
    status = "Connected 🟢" if is_connected else "Disconnected 🔴 (Check Logs)"
    return {"status": status, "account": EMAIL}

@app.get("/connect")
async def force_connect():
    """Manual Connection Trigger"""
    result = await ensure_connection()
    return {"connected": result}

@app.get("/get-candles")
async def get_candles_route(pair: str = "EURUSD", timeframe: int = 60):
    if not is_connected:
        await ensure_connection()
        if not is_connected:
            return {"status": "error", "message": "Login Failed. Check Server Logs."}

    import time
    candles = await client.get_candles(pair, int(time.time()), 3600, timeframe)
    
    if not candles:
        return {"status": "error", "message": "No data found"}
        
    formatted = [{"time": c['time'], "close": c['close']} for c in candles[-50:]]
    return {"pair": pair, "data": formatted}
