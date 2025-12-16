import sys
import os
import asyncio
from fastapi import FastAPI

# ==========================================
# 🛡️ 1. ANTI-CRASH SYSTEM (CRITICAL)
# ==========================================
# یہ کوڈ لائبریری کو ایپ بند کرنے سے روکے گا
def fake_exit(code=0):
    print(f"⚠️ LIBRARY TRIED TO CRASH WITH CODE {code} - IGNORED!")
    pass

sys.exit = fake_exit

# ==========================================
# 🛠️ 2. FOLDER NAME FIX
# ==========================================
try:
    import quotexapi
    sys.modules['pyquotex'] = quotexapi
    import quotexapi.stable_api
    sys.modules['pyquotex.stable_api'] = quotexapi.stable_api
    from quotexapi.stable_api import Quotex
    print("✅ Library Mapped Successfully")
except ImportError:
    try:
        from pyquotex.stable_api import Quotex
    except:
        print("❌ Critical: Quotex Library not found.")

# ==========================================
# ⚙️ GLOBAL VARIABLES
# ==========================================
app = FastAPI()

# ڈیفالٹ اکاؤنٹ (اگر آپ چاہیں تو یہاں لکھیں، ورنہ API سے سیٹ کریں)
current_email = "marslansalfias@gmail.com"
current_password = "Arslan@786"

# گلوبل کلائنٹ
client = None
is_connected = False

# ==========================================
# 🔌 CONNECTION ENGINE
# ==========================================
async def connect_client(email, password):
    global client, is_connected, current_email, current_password
    
    print(f"🔄 Attempting Login for: {email}...")
    
    # اگر پہلے سے کوئی کلائنٹ ہے تو اسے بند کریں
    if client:
        try:
            client.api.close()
        except: pass
    
    # نیا کلائنٹ بنائیں
    client = Quotex(email=email, password=password)
    
    try:
        # کنیکٹ کرنے کی کوشش
        check, reason = await client.connect()
        
        if check:
            print(f"✅ Login Successful for {email}!")
            is_connected = True
            current_email = email
            current_password = password # صرف میموری میں محفوظ رہے گا
            return True, "Connected Successfully"
        else:
            print(f"❌ Login Failed: {reason}")
            is_connected = False
            return False, f"Login Failed: {reason}"
            
    except Exception as e:
        print(f"⚠️ Exception during login: {e}")
        is_connected = False
        return False, str(e)

# ==========================================
# 🛣️ API ROUTES
# ==========================================

@app.on_event("startup")
async def startup_event():
    # سرور چلتے وقت ہم کوشش کریں گے، لیکن اگر فیل ہو تو سرور بند نہیں ہوگا
    print("🚀 Server Starting...")
    try:
        await connect_client(current_email, current_password)
    except:
        print("⚠️ Startup Login Failed (Server is still running, use /login endpoint)")

@app.get("/")
def home():
    status = "🟢 Connected" if is_connected else "🔴 Disconnected"
    return {
        "status": status,
        "current_account": current_email,
        "message": "Use /login to switch accounts"
    }

# 👇👇👇 یہ ہے آپ کا نیا فیچر 👇👇👇
@app.get("/login")
async def login_route(email: str, password: str):
    """
    اس API کو کال کر کے آپ نیا اکاؤنٹ لاگ ان کر سکتے ہیں۔
    Example: /login?email=new@gmail.com&password=12345
    """
    success, message = await connect_client(email, password)
    
    return {
        "success": success,
        "email": email,
        "message": message,
        "status": "Connected" if success else "Failed"
    }

@app.get("/get-candles")
async def get_candles_route(pair: str = "EURUSD", timeframe: int = 60):
    if not is_connected:
        return {"status": "error", "message": "Bot is disconnected. Please use /login first."}

    import time
    try:
        candles = await client.get_candles(pair, int(time.time()), 3600, timeframe)
        if not candles:
            return {"status": "error", "message": "No data found"}
            
        formatted = [{"time": c['time'], "close": c['close']} for c in candles[-50:]]
        return {"pair": pair, "data": formatted}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/live-signals")
async def live_signals_route(pair: str = "EURUSD"):
    if not is_connected:
        return {"status": "error", "message": "Disconnected"}
        
    # ... (باقی سگنل کوڈ وہی رہے گا) ...
    # صرف ٹیسٹنگ کے لیے ابھی یہ واپس کر رہے ہیں:
    return {"status": "Online", "pair": pair}
