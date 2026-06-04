# database.py - Completely Fixed (No Global Variable Issues)
import os
import datetime
import random
import string
import asyncio
import json
import tempfile
from typing import Optional, List, Dict, Any

# Try to import motor
try:
    from motor.motor_asyncio import AsyncIOMotorClient
    MOTOR_AVAILABLE = True
except ImportError:
    MOTOR_AVAILABLE = False
    print("⚠️ Motor not installed, using JSON storage only")

# ============ CONFIGURATION ============
MONGODB_URI = os.environ.get("MONGODB_URI", "")
USE_MONGODB = os.environ.get("USE_MONGODB", "false").lower() == "true"

# Validate MongoDB URI
if MONGODB_URI and "Tyr6hij:gufutihhh" in MONGODB_URI:
    USE_MONGODB = False

# Use temp directory for Railway (writable)
DB_DIR = os.environ.get("DB_DIR", tempfile.gettempdir())
_RAZOR_DB_FILE = os.path.join(DB_DIR, "razor_bot_data.json")

print(f"📁 Database file location: {_RAZOR_DB_FILE}")
print(f"📦 MongoDB Mode: {USE_MONGODB and MONGODB_URI and MOTOR_AVAILABLE}")

# Global clients
_mongo_client = None
_db = None
_json_cache = None
_json_cache_time = 0
_JSON_CACHE_TTL = 5

# ============ JSON STORAGE FUNCTIONS ============

def _get_db_file():
    """Get database file path"""
    return _RAZOR_DB_FILE

def _load_json_db() -> Dict:
    """Load JSON database with caching"""
    global _json_cache, _json_cache_time
    
    import time
    now = time.time()
    
    if _json_cache is not None and (now - _json_cache_time) < _JSON_CACHE_TTL:
        return _json_cache
    
    db_file = _get_db_file()
    
    try:
        if os.path.exists(db_file):
            with open(db_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {
                "users": {},
                "cards": [],
                "proxies": {},
                "sites": {},
                "plan_codes": {}
            }
        
        data.setdefault("users", {})
        data.setdefault("cards", [])
        data.setdefault("proxies", {})
        data.setdefault("sites", {})
        data.setdefault("plan_codes", {})
        
        _json_cache = data
        _json_cache_time = now
        return data
    except Exception as e:
        print(f"❌ Error loading JSON DB: {e}")
        return {
            "users": {},
            "cards": [],
            "proxies": {},
            "sites": {},
            "plan_codes": {}
        }

def _save_json_db(data: Dict) -> bool:
    """Save JSON database"""
    global _json_cache, _json_cache_time
    
    db_file = _get_db_file()
    
    try:
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        
        with open(db_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
        
        _json_cache = data
        _json_cache_time = time.time()
        return True
    except Exception as e:
        print(f"❌ Error saving JSON DB: {e}")
        return False

# ============ MONGODB FUNCTIONS ============

async def get_mongo_db():
    """Get MongoDB connection"""
    global _mongo_client, _db
    
    if not USE_MONGODB or not MOTOR_AVAILABLE or not MONGODB_URI:
        return None
    
    if _mongo_client is None:
        try:
            _mongo_client = AsyncIOMotorClient(
                MONGODB_URI,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=5000,
                retryWrites=False,
                maxPoolSize=10
            )
            await _mongo_client.admin.command('ping')
            _db = _mongo_client["razorbot"]
            print("✅ MongoDB connected!")
        except Exception as e:
            print(f"❌ MongoDB connection failed: {e}")
            _mongo_client = None
            _db = None
    return _db

# ============ USER FUNCTIONS ============

async def ensure_user(user_id: int):
    """Ensure user exists"""
    if USE_MONGODB and MOTOR_AVAILABLE:
        db = await get_mongo_db()
        if db:
            try:
                existing = await db.users.find_one({"_id": str(user_id)})
                if not existing:
                    await db.users.insert_one({
                        "_id": str(user_id),
                        "plan": "Bronze",
                        "expiry": None,
                        "banned": False,
                        "used_codes": [],
                        "created_at": datetime.datetime.now().isoformat()
                    })
                return
            except:
                pass
    
    data = _load_json_db()
    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {
            "plan": "Bronze", 
            "expiry": None, 
            "banned": False, 
            "used_codes": []
        }
        _save_json_db(data)

async def get_user_plan(user_id: int) -> str:
    """Get user's plan"""
    if USE_MONGODB and MOTOR_AVAILABLE:
        db = await get_mongo_db()
        if db:
            try:
                user = await db.users.find_one({"_id": str(user_id)})
                if user:
                    plan = user.get("plan", "Bronze")
                    expiry = user.get("expiry")
                    if expiry and plan != "Bronze":
                        if isinstance(expiry, str):
                            expiry_date = datetime.datetime.fromisoformat(expiry)
                        else:
                            expiry_date = expiry
                        if expiry_date < datetime.datetime.now():
                            await db.users.update_one(
                                {"_id": str(user_id)},
                                {"$set": {"plan": "Bronze", "expiry": None}}
                            )
                            return "Bronze"
                    return plan
            except:
                pass
    
    data = _load_json_db()
    user = data["users"].get(str(user_id), {})
    plan = user.get("plan", "Bronze")
    expiry = user.get("expiry")
    
    if expiry and plan != "Bronze":
        try:
            if isinstance(expiry, str):
                expiry_date = datetime.datetime.fromisoformat(expiry)
            else:
                expiry_date = expiry
            if expiry_date < datetime.datetime.now():
                user["plan"] = "Bronze"
                user["expiry"] = None
                data["users"][str(user_id)] = user
                _save_json_db(data)
                return "Bronze"
        except:
            pass
    
    return plan

async def set_user_plan(user_id: int, plan: str, days: int = 0):
    """Set user's plan"""
    expiry = None
    if days > 0:
        expiry = (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()
    
    if USE_MONGODB and MOTOR_AVAILABLE:
        db = await get_mongo_db()
        if db:
            try:
                await db.users.update_one(
                    {"_id": str(user_id)},
                    {"$set": {"plan": plan, "expiry": expiry}},
                    upsert=True
                )
                return
            except:
                pass
    
    data = _load_json_db()
    user = data["users"].get(str(user_id), {})
    user["plan"] = plan
    user["expiry"] = expiry
    user.setdefault("banned", False)
    user.setdefault("used_codes", [])
    data["users"][str(user_id)] = user
    _save_json_db(data)

async def is_premium_user(user_id: int) -> bool:
    """Check premium"""
    plan = await get_user_plan(user_id)
    return plan in ["Trial", "Core", "Elite", "Root", "X"]

async def is_banned_user(user_id: int) -> bool:
    """Check banned"""
    if USE_MONGODB and MOTOR_AVAILABLE:
        db = await get_mongo_db()
        if db:
            try:
                user = await db.users.find_one({"_id": str(user_id)})
                return user.get("banned", False) if user else False
            except:
                pass
    
    data = _load_json_db()
    return data["users"].get(str(user_id), {}).get("banned", False)

# ============ CARD FUNCTIONS ============

async def save_card_to_db(card: str, status: str, response: str, gateway: str, price: str):
    """Save card result"""
    card_data = {
        "card": card,
        "status": status,
        "response": response,
        "gateway": gateway,
        "price": price,
        "created_at": datetime.datetime.now().isoformat()
    }
    
    if USE_MONGODB and MOTOR_AVAILABLE:
        db = await get_mongo_db()
        if db:
            try:
                await db.cards.insert_one(card_data)
                return
            except:
                pass
    
    data = _load_json_db()
    data["cards"].append(card_data)
    if len(data["cards"]) > 10000:
        data["cards"] = data["cards"][-10000:]
    _save_json_db(data)

async def get_total_cards_count() -> int:
    """Total cards count"""
    if USE_MONGODB and MOTOR_AVAILABLE:
        db = await get_mongo_db()
        if db:
            try:
                return await db.cards.count_documents({})
            except:
                pass
    
    data = _load_json_db()
    return len(data["cards"])

async def get_charged_count() -> int:
    """Charged cards count"""
    if USE_MONGODB and MOTOR_AVAILABLE:
        db = await get_mongo_db()
        if db:
            try:
                return await db.cards.count_documents({"status": "CHARGED"})
            except:
                pass
    
    data = _load_json_db()
    return sum(1 for c in data["cards"] if c.get("status") == "CHARGED")

async def get_approved_count() -> int:
    """Approved cards count"""
    if USE_MONGODB and MOTOR_AVAILABLE:
        db = await get_mongo_db()
        if db:
            try:
                return await db.cards.count_documents({"status": "APPROVED"})
            except:
                pass
    
    data = _load_json_db()
    return sum(1 for c in data["cards"] if c.get("status") == "APPROVED")

# ============ PROXY FUNCTIONS ============

async def add_proxy_db(user_id: int, proxy_data: Dict):
    """Add proxy"""
    if USE_MONGODB and MOTOR_AVAILABLE:
        db = await get_mongo_db()
        if db:
            try:
                await db.proxies.update_one(
                    {"_id": str(user_id)},
                    {"$push": {"proxies": proxy_data}},
                    upsert=True
                )
                return
            except:
                pass
    
    data = _load_json_db()
    if str(user_id) not in data["proxies"]:
        data["proxies"][str(user_id)] = []
    data["proxies"][str(user_id)].append(proxy_data)
    _save_json_db(data)

async def get_all_user_proxies(user_id: int) -> List[Dict]:
    """Get all proxies"""
    if USE_MONGODB and MOTOR_AVAILABLE:
        db = await get_mongo_db()
        if db:
            try:
                user_proxies = await db.proxies.find_one({"_id": str(user_id)})
                return user_proxies.get("proxies", []) if user_proxies else []
            except:
                pass
    
    data = _load_json_db()
    return data["proxies"].get(str(user_id), [])

async def get_proxy_count(user_id: int) -> int:
    """Proxy count"""
    proxies = await get_all_user_proxies(user_id)
    return len(proxies)

async def get_random_proxy(user_id: int) -> Optional[Dict]:
    """Random proxy"""
    proxies = await get_all_user_proxies(user_id)
    return random.choice(proxies) if proxies else None

async def remove_proxy_by_index(user_id: int, index: int) -> Optional[Dict]:
    """Remove by index"""
    proxies = await get_all_user_proxies(user_id)
    if 0 <= index < len(proxies):
        removed = proxies.pop(index)
        
        if USE_MONGODB and MOTOR_AVAILABLE:
            db = await get_mongo_db()
            if db:
                try:
                    await db.proxies.update_one(
                        {"_id": str(user_id)},
                        {"$set": {"proxies": proxies}}
                    )
                    return removed
                except:
                    pass
        
        data = _load_json_db()
        data["proxies"][str(user_id)] = proxies
        _save_json_db(data)
        return removed
    return None

async def remove_proxy_by_url(user_id: int, proxy_url: str) -> bool:
    """Remove by URL"""
    proxies = await get_all_user_proxies(user_id)
    for i, p in enumerate(proxies):
        if p.get("proxy_url") == proxy_url:
            proxies.pop(i)
            
            if USE_MONGODB and MOTOR_AVAILABLE:
                db = await get_mongo_db()
                if db:
                    try:
                        await db.proxies.update_one(
                            {"_id": str(user_id)},
                            {"$set": {"proxies": proxies}}
                        )
                        return True
                    except:
                        pass
            
            data = _load_json_db()
            data["proxies"][str(user_id)] = proxies
            _save_json_db(data)
            return True
    return False

async def clear_all_proxies(user_id: int) -> int:
    """Clear all proxies"""
    proxies = await get_all_user_proxies(user_id)
    count = len(proxies)
    
    if USE_MONGODB and MOTOR_AVAILABLE:
        db = await get_mongo_db()
        if db:
            try:
                await db.proxies.update_one(
                    {"_id": str(user_id)},
                    {"$set": {"proxies": []}}
                )
                return count
            except:
                pass
    
    data = _load_json_db()
    data["proxies"][str(user_id)] = []
    _save_json_db(data)
    return count

# ============ SITE FUNCTIONS ============

async def add_site_db(user_id: int, site: str, gateway: str = "Unknown", price: str = "0") -> bool:
    """Add site"""
    if USE_MONGODB and MOTOR_AVAILABLE:
        db = await get_mongo_db()
        if db:
            try:
                await db.sites.update_one(
                    {"_id": str(user_id)},
                    {"$set": {f"sites.{site}": {"gateway": gateway, "price": price}}},
                    upsert=True
                )
                return True
            except:
                pass
    
    data = _load_json_db()
    if str(user_id) not in data["sites"]:
        data["sites"][str(user_id)] = {}
    data["sites"][str(user_id)][site] = {"gateway": gateway, "price": price}
    _save_json_db(data)
    return True

async def get_user_sites(user_id: int) -> List[str]:
    """Get all sites"""
    if USE_MONGODB and MOTOR_AVAILABLE:
        db = await get_mongo_db()
        if db:
            try:
                user_sites = await db.sites.find_one({"_id": str(user_id)})
                if user_sites and "sites" in user_sites:
                    return list(user_sites["sites"].keys())
                return []
            except:
                pass
    
    data = _load_json_db()
    sites_dict = data["sites"].get(str(user_id), {})
    return list(sites_dict.keys())

async def get_user_sites_with_info(user_id: int) -> List[Dict]:
    """Get sites with info"""
    if USE_MONGODB and MOTOR_AVAILABLE:
        db = await get_mongo_db()
        if db:
            try:
                user_sites = await db.sites.find_one({"_id": str(user_id)})
                if user_sites and "sites" in user_sites:
                    result = []
                    for site, info in user_sites["sites"].items():
                        if isinstance(info, dict):
                            result.append({
                                "site": site,
                                "gateway": info.get("gateway", "Unknown"),
                                "price": info.get("price", "0")
                            })
                        else:
                            result.append({
                                "site": site,
                                "gateway": "Unknown",
                                "price": "0"
                            })
                    return result
                return []
            except:
                pass
    
    data = _load_json_db()
    sites_data = data["sites"].get(str(user_id), {})
    result = []
    if isinstance(sites_data, dict):
        for site, info in sites_data.items():
            if isinstance(info, dict):
                result.append({
                    "site": site,
                    "gateway": info.get("gateway", "Unknown"),
                    "price": info.get("price", "0")
                })
            else:
                result.append({
                    "site": site,
                    "gateway": "Unknown",
                    "price": "0"
                })
    elif isinstance(sites_data, list):
        for site in sites_data:
            result.append({
                "site": site,
                "gateway": "Unknown",
                "price": "0"
            })
    return result

async def remove_site_db(user_id: int, site: str) -> bool:
    """Remove site"""
    if USE_MONGODB and MOTOR_AVAILABLE:
        db = await get_mongo_db()
        if db:
            try:
                await db.sites.update_one(
                    {"_id": str(user_id)},
                    {"$unset": {f"sites.{site}": ""}}
                )
                return True
            except:
                pass
    
    data = _load_json_db()
    sites_dict = data["sites"].get(str(user_id), {})
    if site in sites_dict:
        del sites_dict[site]
        data["sites"][str(user_id)] = sites_dict
        _save_json_db(data)
        return True
    return False

async def update_site_info(user_id: int, site: str, gateway: str, price: str) -> bool:
    """Update site info"""
    return await add_site_db(user_id, site, gateway, price)

# ============ PLAN CODE FUNCTIONS ============

PLAN_PREFIXES = {
    "trial": "SHOPIFY_TRIAL",
    "plan1": "SHOPIFY_CORE",
    "plan2": "SHOPIFY_ELITE",
    "plan3": "SHOPIFY_ROOT",
    "plan4": "SHOPIFY_X"
}

async def generate_plan_code(plan_key: str, count: int = 1) -> List[str]:
    """Generate codes"""
    prefix = PLAN_PREFIXES.get(plan_key, plan_key.upper())
    codes = []
    
    if USE_MONGODB and MOTOR_AVAILABLE:
        db = await get_mongo_db()
        if db:
            try:
                for _ in range(count):
                    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
                    code = f"{prefix}_{random_suffix}"
                    existing = await db.codes.find_one({"_id": code})
                    while existing:
                        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
                        code = f"{prefix}_{random_suffix}"
                        existing = await db.codes.find_one({"_id": code})
                    
                    await db.codes.insert_one({
                        "_id": code,
                        "plan": plan_key,
                        "created_at": datetime.datetime.now().isoformat(),
                        "used": False,
                        "used_by": None,
                        "used_at": None
                    })
                    codes.append(code)
                return codes
            except:
                pass
    
    data = _load_json_db()
    if "plan_codes" not in data:
        data["plan_codes"] = {}
    
    for _ in range(count):
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        code = f"{prefix}_{random_suffix}"
        while code in data["plan_codes"]:
            random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            code = f"{prefix}_{random_suffix}"
        
        data["plan_codes"][code] = {
            "plan": plan_key,
            "created_at": datetime.datetime.now().isoformat(),
            "used": False,
            "used_by": None,
            "used_at": None
        }
        codes.append(code)
    _save_json_db(data)
    return codes

async def redeem_plan_code(user_id: int, code: str) -> tuple:
    """Redeem code"""
    if USE_MONGODB and MOTOR_AVAILABLE:
        db = await get_mongo_db()
        if db:
            try:
                code_data = await db.codes.find_one({"_id": code})
                if not code_data:
                    return False, "invalid"
                if code_data.get("used", False):
                    return False, "used"
                
                plan_key = code_data.get("plan")
                from bot import PLANS
                if plan_key not in PLANS:
                    return False, "invalid"
                
                plan_info = PLANS[plan_key]
                user_plan = await get_user_plan(user_id)
                if user_plan != "Bronze":
                    return False, "has_plan"
                
                expiry = (datetime.datetime.now() + datetime.timedelta(days=plan_info["duration_days"])).isoformat()
                
                await db.users.update_one(
                    {"_id": str(user_id)},
                    {"$set": {"plan": plan_info["tier"], "expiry": expiry}}
                )
                
                await db.codes.update_one(
                    {"_id": code},
                    {"$set": {"used": True, "used_by": user_id, "used_at": datetime.datetime.now().isoformat()}}
                )
                
                return True, "success"
            except:
                pass
    
    data = _load_json_db()
    if code not in data.get("plan_codes", {}):
        return False, "invalid"
    
    code_data = data["plan_codes"][code]
    if code_data.get("used", False):
        return False, "used"
    
    plan_key = code_data.get("plan")
    from bot import PLANS
    if plan_key not in PLANS:
        return False, "invalid"
    
    plan_info = PLANS[plan_key]
    user_plan = await get_user_plan(user_id)
    if user_plan != "Bronze":
        return False, "has_plan"
    
    expiry = (datetime.datetime.now() + datetime.timedelta(days=plan_info["duration_days"])).isoformat()
    
    user = data["users"].get(str(user_id), {})
    data["users"][str(user_id)] = {
        "plan": plan_info["tier"],
        "expiry": expiry,
        "banned": user.get("banned", False),
        "used_codes": user.get("used_codes", []) + [code]
    }
    data["plan_codes"][code]["used"] = True
    data["plan_codes"][code]["used_by"] = user_id
    data["plan_codes"][code]["used_at"] = datetime.datetime.now().isoformat()
    _save_json_db(data)
    return True, "success"

def is_valid_code(code: str) -> bool:
    """Check valid code"""
    data = _load_json_db()
    code_data = data.get("plan_codes", {}).get(code)
    return code_data is not None and not code_data.get("used", False)

def get_code_info(code: str) -> Optional[Dict]:
    """Get code info"""
    data = _load_json_db()
    return data.get("plan_codes", {}).get(code)

async def remove_code(code: str) -> bool:
    """Remove code"""
    if USE_MONGODB and MOTOR_AVAILABLE:
        db = await get_mongo_db()
        if db:
            try:
                await db.codes.delete_one({"_id": code})
                return True
            except:
                pass
    
    data = _load_json_db()
    if code in data.get("plan_codes", {}):
        del data["plan_codes"][code]
        _save_json_db(data)
        return True
    return False

async def get_all_active_codes() -> Dict:
    """Get all active codes"""
    if USE_MONGODB and MOTOR_AVAILABLE:
        db = await get_mongo_db()
        if db:
            try:
                codes = {}
                cursor = db.codes.find({"used": False})
                async for doc in cursor:
                    codes[doc["_id"]] = doc
                return codes
            except:
                pass
    
    data = _load_json_db()
    codes = {}
    for code, info in data.get("plan_codes", {}).items():
        if not info.get("used", False):
            codes[code] = info
    return codes

async def get_all_codes() -> Dict:
    """Get all codes"""
    if USE_MONGODB and MOTOR_AVAILABLE:
        db = await get_mongo_db()
        if db:
            try:
                codes = {}
                cursor = db.codes.find({})
                async for doc in cursor:
                    codes[doc["_id"]] = doc
                return codes
            except:
                pass
    
    data = _load_json_db()
    return data.get("plan_codes", {})

# ============ STATISTICS FUNCTIONS ============

async def get_total_users() -> int:
    """Total users"""
    if USE_MONGODB and MOTOR_AVAILABLE:
        db = await get_mongo_db()
        if db:
            try:
                return await db.users.count_documents({})
            except:
                pass
    
    data = _load_json_db()
    return len(data["users"])

async def get_premium_count() -> int:
    """Premium count"""
    premium_plans = ["Trial", "Core", "Elite", "Root", "X"]
    
    if USE_MONGODB and MOTOR_AVAILABLE:
        db = await get_mongo_db()
        if db:
            try:
                return await db.users.count_documents({"plan": {"$in": premium_plans}})
            except:
                pass
    
    data = _load_json_db()
    return sum(1 for u in data["users"].values() if u.get("plan") in premium_plans)

async def get_all_premium_users() -> List[Dict]:
    """All premium users"""
    premium_plans = ["Trial", "Core", "Elite", "Root", "X"]
    result = []
    
    if USE_MONGODB and MOTOR_AVAILABLE:
        db = await get_mongo_db()
        if db:
            try:
                cursor = db.users.find({"plan": {"$in": premium_plans}})
                async for doc in cursor:
                    result.append({"user_id": int(doc["_id"]), "plan": doc.get("plan")})
                return result
            except:
                pass
    
    data = _load_json_db()
    for uid, udata in data["users"].items():
        if udata.get("plan") in premium_plans:
            result.append({"user_id": int(uid), "plan": udata.get("plan")})
    return result

async def get_total_sites_count() -> int:
    """Total sites"""
    if USE_MONGODB and MOTOR_AVAILABLE:
        db = await get_mongo_db()
        if db:
            try:
                total = 0
                cursor = db.sites.find({})
                async for doc in cursor:
                    total += len(doc.get("sites", {}))
                return total
            except:
                pass
    
    data = _load_json_db()
    total = 0
    for sites_dict in data["sites"].values():
        total += len(sites_dict)
    return total

async def get_users_with_sites() -> int:
    """Users with sites"""
    if USE_MONGODB and MOTOR_AVAILABLE:
        db = await get_mongo_db()
        if db:
            try:
                return await db.sites.count_documents({})
            except:
                pass
    
    data = _load_json_db()
    return len(data["sites"])

async def get_sites_per_user() -> List[Dict]:
    """Sites per user"""
    result = []
    
    if USE_MONGODB and MOTOR_AVAILABLE:
        db = await get_mongo_db()
        if db:
            try:
                cursor = db.sites.find({})
                async for doc in cursor:
                    result.append({"user_id": int(doc["_id"]), "cnt": len(doc.get("sites", {}))})
                return result
            except:
                pass
    
    data = _load_json_db()
    for uid, sites in data["sites"].items():
        result.append({"user_id": int(uid), "cnt": len(sites)})
    return result

async def get_all_sites_detail() -> List[Dict]:
    """All sites detail"""
    result = []
    
    if USE_MONGODB and MOTOR_AVAILABLE:
        db = await get_mongo_db()
        if db:
            try:
                cursor = db.sites.find({})
                async for doc in cursor:
                    uid = int(doc["_id"])
                    for site, info in doc.get("sites", {}).items():
                        result.append({
                            "user_id": uid,
                            "site": site,
                            "gateway": info.get("gateway", "Unknown"),
                            "price": info.get("price", "0")
                        })
                return result
            except:
                pass
    
    data = _load_json_db()
    for uid, sites_dict in data["sites"].items():
        for site, info in sites_dict.items():
            result.append({
                "user_id": int(uid),
                "site": site,
                "gateway": info.get("gateway", "Unknown"),
                "price": info.get("price", "0")
            })
    return result

# ============ INIT DATABASE ============

async def init_db():
    """Initialize database"""
    print("=" * 50)
    print("🔄 INITIALIZING DATABASE...")
    print("=" * 50)
    
    db_file = _get_db_file()
    
    try:
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        test_data = {"test": True}
        with open(db_file, 'w') as f:
            json.dump(test_data, f)
        os.remove(db_file)
        print(f"✅ JSON storage ready at: {db_file}")
    except Exception as e:
        print(f"❌ JSON storage error: {e}")
    
    if USE_MONGODB and MOTOR_AVAILABLE and MONGODB_URI:
        try:
            db = await get_mongo_db()
            if db:
                await db.users.create_index("_id")
                await db.cards.create_index("created_at")
                await db.codes.create_index("used")
                print("✅ MongoDB ready!")
        except Exception as e:
            print(f"⚠️ MongoDB not available: {e}")
    
    print("=" * 50)
    return True

# ============ JOIN CACHE ============

_joined_cache = set()

async def mark_user_joined(user_id: int):
    _joined_cache.add(user_id)

async def is_user_marked_joined(user_id: int) -> bool:
    return user_id in _joined_cache

async def remove_joined_mark(user_id: int):
    _joined_cache.discard(user_id)

# ============ GLOBAL SITES (Legacy) ============

async def add_global_site(site: str) -> bool:
    return True

async def get_global_sites() -> List[str]:
    return []

async def remove_global_site(site: str) -> bool:
    return True

# Database wrapper
class DatabaseWrapper:
    def __init__(self):
        self.users = {}
    
    async def find_one(self, collection, query):
        return None
    
    async def __getitem__(self, key):
        return self

db = DatabaseWrapper()

print(f"📁 Database file: {_RAZOR_DB_FILE}")
print(f"📦 MongoDB Mode: {USE_MONGODB and MONGODB_URI and MOTOR_AVAILABLE}")
