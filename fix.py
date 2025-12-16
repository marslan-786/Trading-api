import os

# 1. فولڈر کا نام تبدیل کریں (quotexapi -> pyquotex)
if os.path.exists("quotexapi"):
    print("🔄 Renaming folder 'quotexapi' to 'pyquotex'...")
    os.rename("quotexapi", "pyquotex")
    print("✅ Folder Renamed!")
else:
    print("ℹ️ Folder 'quotexapi' not found (Maybe already renamed).")

# 2. main.py کو اپڈیٹ کریں
try:
    with open("main.py", "r") as f:
        content = f.read()
    
    # پرانے امپورٹ کو نئے سے بدلیں
    if "from quotexapi.stable_api" in content:
        print("🔄 Fixing main.py imports...")
        new_content = content.replace("from quotexapi.stable_api", "from pyquotex.stable_api")
        
        with open("main.py", "w") as f:
            f.write(new_content)
        print("✅ main.py Fixed!")
    else:
        print("ℹ️ main.py already looks correct.")
        
except FileNotFoundError:
    print("❌ main.py not found!")

print("\n🚀 FIX COMPLETE! Now Redeploy.")
