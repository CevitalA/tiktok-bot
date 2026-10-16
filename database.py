import re
import os
import json
import secrets
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_FILE = os.path.join(DATA_DIR, "bot_database.json")

def _load_db() -> dict:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(DB_FILE):
        initial = {
            "users": {},
            "license_keys": {},
            "meta": {}
        }
        _save_db(initial)
        return initial
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"users": {}, "license_keys": {}, "meta": {}}

def _save_db(data: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def init_db():
    _load_db()

def get_or_create_user(user_id: int, username: str = "", full_name: str = "", is_admin: bool = False) -> dict:
    db = _load_db()
    uid = str(user_id)
    if uid not in db["users"]:
        db["users"][uid] = {
            "user_id": user_id,
            "username": username,
            "full_name": full_name,
            "is_admin": is_admin,
            "subscription_end": None,
            "status": "inactive",
            "created_at": datetime.now().isoformat()
        }
    else:
        db["users"][uid]["username"] = username
        db["users"][uid]["full_name"] = full_name
        if is_admin:
            db["users"][uid]["is_admin"] = True
            
    _save_db(db)
    return db["users"][uid]

def check_subscription(user_id: int, admin_ids: list = None) -> dict:
    if admin_ids and user_id in admin_ids:
        return {
            "is_active": True,
            "is_admin": True,
            "days_left": 9999,
            "hours_left": 23,
            "end_date": "غير محدود (أدمن)",
            "status": "admin"
        }
        
    db = _load_db()
    uid = str(user_id)
    user = db["users"].get(uid)
    
    if not user or not user.get("subscription_end"):
        return {
            "is_active": False,
            "is_admin": False,
            "days_left": 0,
            "hours_left": 0,
            "end_date": None,
            "status": "no_subscription"
        }
        
    try:
        end_date = datetime.fromisoformat(user["subscription_end"])
    except Exception:
        return {
            "is_active": False,
            "is_admin": False,
            "days_left": 0,
            "hours_left": 0,
            "end_date": None,
            "status": "no_subscription"
        }
        
    now = datetime.now()
    if end_date > now:
        remaining = end_date - now
        days_left = remaining.days
        hours_left = remaining.seconds // 3600
        return {
            "is_active": True,
            "is_admin": bool(user.get("is_admin")),
            "days_left": days_left,
            "hours_left": hours_left,
            "end_date": end_date.strftime("%Y-%m-%d %H:%M"),
            "status": "active"
        }
    else:
        return {
            "is_active": False,
            "is_admin": bool(user.get("is_admin")),
            "days_left": 0,
            "hours_left": 0,
            "end_date": end_date.strftime("%Y-%m-%d %H:%M"),
            "status": "expired"
        }

def add_subscription_days(user_id: int, days: int) -> str:
    db = _load_db()
    uid = str(user_id)
    now = datetime.now()
    
    if uid not in db["users"]:
        db["users"][uid] = {
            "user_id": user_id,
            "username": "",
            "full_name": "",
            "is_admin": False,
            "subscription_end": None,
            "status": "inactive",
            "created_at": now.isoformat()
        }
        
    current_end_str = db["users"][uid].get("subscription_end")
    if current_end_str:
        try:
            curr_dt = datetime.fromisoformat(current_end_str)
            start_from = curr_dt if curr_dt > now else now
        except Exception:
            start_from = now
    else:
        start_from = now
        
    new_end = start_from + timedelta(days=days)
    db["users"][uid]["subscription_end"] = new_end.isoformat()
    db["users"][uid]["status"] = "active"
    _save_db(db)
    return new_end.strftime("%Y-%m-%d %H:%M")

def remove_subscription(user_id: int):
    db = _load_db()
    uid = str(user_id)
    if uid in db["users"]:
        db["users"][uid]["subscription_end"] = None
        db["users"][uid]["status"] = "inactive"
        _save_db(db)

def generate_license_key(days: int, prefix: str = "TIK") -> str:
    token = secrets.token_hex(4).upper()
    key_code = f"{prefix}-{days}D-{token}"
    
    db = _load_db()
    db["license_keys"][key_code] = {
        "key_code": key_code,
        "days": days,
        "is_used": False,
        "used_by": None,
        "created_at": datetime.now().isoformat(),
        "used_at": None
    }
    _save_db(db)
    return key_code

def clean_license_key(raw_code: str) -> str:
    if not raw_code:
        return ""
    cleaned = raw_code.replace("•", "").replace("`", "").replace("'", "").replace('"', "").strip()
    match = re.search(r"([A-Za-z0-9]+-\d+D-[A-Za-z0-9]+)", cleaned, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return cleaned.upper()

def redeem_license_key(user_id: int, key_code: str) -> dict:
    key_code_cleaned = clean_license_key(key_code)
    db = _load_db()
    
    # Search key case-insensitively and cleanly
    target_key = None
    key_item = None
    for k, v in db.get("license_keys", {}).items():
        if k.upper() == key_code_cleaned:
            target_key = k
            key_item = v
            break
            
    if not key_item:
        return {
            "success": False,
            "message": f"❌ <b>الكود غير صحيح!</b>\nتأكد من نسخ الكود بدقة كما وصلك (مثال: <code>TIK-30D-XXXXXX</code>)."
        }
        
    if key_item.get("is_used"):
        used_at = key_item.get("used_at", "")[:10]
        return {
            "success": False,
            "message": f"⚠️ <b>هذا الكود تم استخدامه مسبقاً!</b>\nتم تفعيله بتاريخ: <code>{used_at}</code>."
        }
        
    days = key_item.get("days", 30)
    key_item["is_used"] = True
    key_item["used_by"] = user_id
    key_item["used_at"] = datetime.now().isoformat()
    
    _save_db(db)
    
    end_date_str = add_subscription_days(user_id, days)
    return {
        "success": True,
        "days": days,
        "end_date": end_date_str,
        "message": f"🎉 <b>تم تفعيل الاشتراك بنجاح يا بطل!</b>\n\n⏳ <b>المدة:</b> {days} يوم\n📅 <b>ينتهي في:</b> <code>{end_date_str}</code>\n\nيمكنك الآن فتح تطبيق الليجات مباشرة والاستمتاع بكافة المميزات! 🏆"
    }

def get_dashboard_stats() -> dict:
    db = _load_db()
    now = datetime.now()
    
    total_users = len(db["users"])
    active_users = 0
    for u in db["users"].values():
        sub_end = u.get("subscription_end")
        if sub_end:
            try:
                if datetime.fromisoformat(sub_end) > now:
                    active_users += 1
            except:
                pass
                
    unused_keys = sum(1 for k in db["license_keys"].values() if not k.get("is_used"))
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "unused_keys": unused_keys
    }

def list_all_users():
    db = _load_db()
    return list(db["users"].values())
