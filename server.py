import os
import json
import hmac
import hashlib
from urllib.parse import parse_qsl
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import database
import excel_parser

app = FastAPI(title="TikTok Leagues Telegram MiniApp API")

@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/api/") or path == "/" or path.endswith(".html") or path.endswith(".json"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]

def verify_telegram_init_data(init_data_raw: str, bot_token: str) -> dict:
    if not init_data_raw or not bot_token:
        return {"valid": False, "user": None}
        
    try:
        parsed_data = dict(parse_qsl(init_data_raw))
        received_hash = parsed_data.pop("hash", None)
        if not received_hash:
            return {"valid": False, "user": None}
            
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
        secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
        computed_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
        
        if computed_hash.lower() == received_hash.lower():
            user_json = parsed_data.get("user")
            user_data = json.loads(user_json) if user_json else None
            return {"valid": True, "user": user_data}
    except Exception as e:
        print(f"initData verification error: {e}")
        
    return {"valid": False, "user": None}

class VerifyRequest(BaseModel):
    initData: str = ""

@app.post("/api/verify")
async def verify_user_access(req: VerifyRequest):
    if not BOT_TOKEN:
        return {
            "authorized": True,
            "dev_mode": True,
            "user": {"id": 1, "first_name": "مستخدم تجريبي"},
            "subscription": {"is_active": True, "days_left": 30, "status": "active"}
        }
        
    res = verify_telegram_init_data(req.initData, BOT_TOKEN)
    if not res["valid"] or not res["user"]:
        return {
            "authorized": False,
            "reason": "invalid_session",
            "message": "جلسة التليجرام غير صالحة. يرجى فتح التطبيق من داخل بوت التليجرام."
        }
        
    user = res["user"]
    user_id = user["id"]
    
    database.get_or_create_user(
        user_id=user_id,
        username=user.get("username", ""),
        full_name=f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
        is_admin=(user_id in ADMIN_IDS)
    )
    
    sub = database.check_subscription(user_id, ADMIN_IDS)
    
    if sub["is_active"]:
        return {
            "authorized": True,
            "user": user,
            "subscription": sub
        }
    else:
        return {
            "authorized": False,
            "reason": "subscription_required",
            "user": user,
            "subscription": sub,
            "message": "عفواً، يتطلب الوصول لهذا التطبيق اشتراكاً مفعلاً. تواصل مع الأدمن أو استخدم كود التفعيل داخل البوت."
        }

@app.get("/api/leagues")
async def get_leagues_data():
    return excel_parser.get_current_leagues_data()

@app.post("/api/admin/upload")
async def admin_upload_excel(
    file: UploadFile = File(...),
    password: str = Form(None),
    initData: str = Form(None)
):
    is_authorized = False
    
    if password and password == ADMIN_PASSWORD:
        is_authorized = True
        
    if not is_authorized and initData and BOT_TOKEN:
        check = verify_telegram_init_data(initData, BOT_TOKEN)
        if check["valid"] and check["user"]:
            u_id = check["user"]["id"]
            if u_id in ADMIN_IDS:
                is_authorized = True
                
    if not is_authorized:
        raise HTTPException(status_code=403, detail="غير مصرح لك برفع البيانات - الأدمن فقط!")
        
    temp_dir = os.path.join(os.path.dirname(__file__), "data", "uploads")
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, file.filename)
    
    try:
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)
            
        parsed_result = excel_parser.parse_excel_file(temp_path)
        return {
            "success": True,
            "message": f"تم بنجاح تحديث بيانات {parsed_result['total_accounts']} حساب في {len(parsed_result['active_leagues'])} ليج!",
            "stats": {
                "total_accounts": parsed_result["total_accounts"],
                "active_leagues": parsed_result["active_leagues"],
                "total_earnings": parsed_result["total_earnings"],
                "total_diamonds": parsed_result["total_diamonds"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"خطأ أثناء معالجة الملف: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass


@app.post("/api/admin/clear")
async def admin_clear_data():
    clean_data = excel_parser.reset_leagues_data()
    return {
        "success": True,
        "message": "تم مسح وتصفير جميع بيانات الحسابات والليجات بنجاح من السيرفر!",
        "stats": clean_data
    }

@app.on_event("startup")
async def on_startup_run_bot():
    token = os.getenv("BOT_TOKEN", "8881972676:AAFbhVZWztH9JKit5EHXbPN2sSeJsGiJYlQ")
    if token:
        import asyncio
        try:
            from bot import start_bot
            asyncio.create_task(start_bot())
            print("🚀 Background Telegram Bot Polling task launched on startup.")
        except Exception as e:
            print(f"Error launching bot task: {e}")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")