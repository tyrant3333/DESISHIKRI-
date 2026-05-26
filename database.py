# MongoDB Database - Complete Production Ready Storage
import os
import datetime
import random
import string
import asyncio
import json
import time
from typing import Optional, List, Dict, Any, Tuple
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure, OperationFailure

# ==================== CONFIGURATION ====================
MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb+srv://Tyr6hij:gufutihhh@cluster0.hdfqxfu.mongodb.net/?appName=Cluster0")
USE_MONGODB = bool(MONGODB_URI) and os.environ.get("USE_MONGODB", "true").lower() == "true"
DB_FILE = "razor_bot_data.json"
MAX_RETRIES = 3
RETRY_DELAY = 2

# ==================== GLOBAL VARIABLES ====================
_mongo_client: Optional[AsyncIOMotorClient] = None
_db = None
_json_cache = None
_json_cache_time = 0
_JSON_CACHE_TTL = 5
_mongo_available = None
_last_mongo_check = 0
_MONGO_CHECK_INTERVAL = 60

# ==================== MONGODB CONNECTION WITH RETRY ====================
async def get_mongo_db():
    global _mongo_client, _db, _mongo_available, _last_mongo_check
    
    if not USE_MONGODB or not MONGODB_URI:
        return None
    
    now = time.time()
    if _mongo_available is False and now - _last_mongo_check < _MONGO_CHECK_INTERVAL:
        return None
    
    if _mongo_client is None:
        for attempt in range(MAX_RETRIES):
            try:
                _mongo_client = AsyncIOMotorClient(
                    MONGODB_URI,
                    serverSelectionTimeoutMS=10000,
                    connectTimeoutMS=10000,
                    socketTimeoutMS=30000,
                    maxPoolSize=100,
                    minPoolSize=10,
                    maxIdleTimeMS=30000,
                    retryWrites=True,
                    retryReads=True,
                    w='majority'
                )
                _db = _mongo_client["razorbot"]
                await _mongo_client.admin.command('ping', serverSelectionTimeoutMS=5000)
                _mongo_available = True
                _last_mongo_check = now
                break
            except (ServerSelectionTimeoutError, ConnectionFailure, OperationFailure):
                _mongo_client = None
                _db = None
                _mongo_available = False
                _last_mongo_check = now
                if attempt == MAX_RETRIES - 1:
                    return None
                await asyncio.sleep(RETRY_DELAY)
            except Exception:
                _mongo_client = None
                _db = None
                _mongo_available = False
                return None
    return _db

# ==================== JSON STORAGE WITH CACHE ====================
def _load_json_db():
    global _json_cache, _json_cache_time
    now = time.time()
    if _json_cache and now - _json_cache_time < _JSON_CACHE_TTL:
        return _json_cache
    
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f:
                _json_cache = json.load(f)
        else:
            _json_cache = {"users": {}, "cards": [], "proxies": {}, "sites": {}, "plan_codes": {}}
    except:
        _json_cache = {"users": {}, "cards": [], "proxies": {}, "sites": {}, "plan_codes": {}}
    
    _json_cache_time = now
    return _json_cache

def _save_json_db(data):
    global _json_cache, _json_cache_time
    _json_cache = data
    _json_cache_time = time.time()
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
    except:
        pass

# ==================== USER FUNCTIONS ====================
async def ensure_user(user_id: int):
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
                    "created_at": datetime.datetime.now().isoformat(),
                    "updated_at": datetime.datetime.now().isoformat()
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
    db = await get_mongo_db()
    if db:
        try:
            user = await db.users.find_one({"_id": str(user_id)})
            if user:
                plan = user.get("plan", "Bronze")
                expiry = user.get("expiry")
                if expiry and plan != "Bronze":
                    try:
                        expiry_date = datetime.datetime.fromisoformat(expiry) if isinstance(expiry, str) else expiry
                        if expiry_date < datetime.datetime.now():
                            await db.users.update_one(
                                {"_id": str(user_id)},
                                {"$set": {"plan": "Bronze", "expiry": None, "updated_at": datetime.datetime.now().isoformat()}}
                            )
                            return "Bronze"
                    except:
                        pass
                return plan
        except:
            pass
    
    data = _load_json_db()
    return data["users"].get(str(user_id), {}).get("plan", "Bronze")

async def set_user_plan(user_id: int, plan: str, days: int = 0):
    db = await get_mongo_db()
    if db:
        try:
            expiry = None
            if days > 0:
                expiry = (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()
            await db.users.update_one(
                {"_id": str(user_id)},
                {
                    "$set": {
                        "plan": plan, 
                        "expiry": expiry,
                        "updated_at": datetime.datetime.now().isoformat()
                    }
                },
                upsert=True
            )
            return
        except:
            pass
    
    data = _load_json_db()
    expiry = None
    if days > 0:
        expiry = (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()
    user = data["users"].get(str(user_id), {})
    data["users"][str(user_id)] = {
        "plan": plan, 
        "expiry": expiry, 
        "banned": user.get("banned", False), 
        "used_codes": user.get("used_codes", [])
    }
    _save_json_db(data)

async def is_premium_user(user_id: int) -> bool:
    plan = await get_user_plan(user_id)
    return plan in ["Trial", "Core", "Elite", "Root", "X"]

async def is_banned_user(user_id: int) -> bool:
    db = await get_mongo_db()
    if db:
        try:
            user = await db.users.find_one({"_id": str(user_id)})
            return user.get("banned", False) if user else False
        except:
            pass
    
    data = _load_json_db()
    return data["users"].get(str(user_id), {}).get("banned", False)

async def ban_user(user_id: int):
    db = await get_mongo_db()
    if db:
        try:
            await db.users.update_one(
                {"_id": str(user_id)},
                {"$set": {"banned": True, "updated_at": datetime.datetime.now().isoformat()}},
                upsert=True
            )
            return
        except:
            pass
    
    data = _load_json_db()
    if str(user_id) in data["users"]:
        data["users"][str(user_id)]["banned"] = True
    else:
        data["users"][str(user_id)] = {"plan": "Bronze", "expiry": None, "banned": True, "used_codes": []}
    _save_json_db(data)

async def unban_user(user_id: int):
    db = await get_mongo_db()
    if db:
        try:
            await db.users.update_one(
                {"_id": str(user_id)},
                {"$set": {"banned": False, "updated_at": datetime.datetime.now().isoformat()}},
                upsert=True
            )
            return
        except:
            pass
    
    data = _load_json_db()
    if str(user_id) in data["users"]:
        data["users"][str(user_id)]["banned"] = False
    _save_json_db(data)

async def get_user_expiry(user_id: int) -> Optional[str]:
    db = await get_mongo_db()
    if db:
        try:
            user = await db.users.find_one({"_id": str(user_id)})
            return user.get("expiry") if user else None
        except:
            pass
    data = _load_json_db()
    return data["users"].get(str(user_id), {}).get("expiry")

# ==================== CARD FUNCTIONS ====================
async def save_card_to_db(card: str, status: str, response: str, gateway: str, price: str):
    db = await get_mongo_db()
    if db:
        try:
            await db.cards.insert_one({
                "card": card,
                "status": status,
                "response": response[:500],
                "gateway": gateway,
                "price": price,
                "created_at": datetime.datetime.now().isoformat()
            })
            return
        except:
            pass
    
    data = _load_json_db()
    data["cards"].append({
        "card": card, 
        "status": status, 
        "response": response[:500],
        "gateway": gateway, 
        "price": price, 
        "created_at": datetime.datetime.now().isoformat()
    })
    _save_json_db(data)

async def get_total_cards_count() -> int:
    db = await get_mongo_db()
    if db:
        try:
            return await db.cards.count_documents({})
        except:
            pass
    data = _load_json_db()
    return len(data["cards"])

async def get_charged_count() -> int:
    db = await get_mongo_db()
    if db:
        try:
            return await db.cards.count_documents({"status": "CHARGED"})
        except:
            pass
    data = _load_json_db()
    return sum(1 for c in data["cards"] if c.get("status") == "CHARGED")

async def get_approved_count() -> int:
    db = await get_mongo_db()
    if db:
        try:
            return await db.cards.count_documents({"status": "APPROVED"})
        except:
            pass
    data = _load_json_db()
    return sum(1 for c in data["cards"] if c.get("status") == "APPROVED")

async def get_cards_by_status(status: str, limit: int = 100) -> List[Dict]:
    db = await get_mongo_db()
    if db:
        try:
            cursor = db.cards.find({"status": status}).sort("created_at", -1).limit(limit)
            return await cursor.to_list(length=limit)
        except:
            pass
    data = _load_json_db()
    return [c for c in data["cards"] if c.get("status") == status][:limit]

# ==================== PROXY FUNCTIONS ====================
async def add_proxy_db(user_id: int, proxy_data: Dict):
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
    proxies = await get_all_user_proxies(user_id)
    return len(proxies)

async def get_random_proxy(user_id: int) -> Optional[Dict]:
    proxies = await get_all_user_proxies(user_id)
    return random.choice(proxies) if proxies else None

async def remove_proxy_by_index(user_id: int, index: int) -> Optional[Dict]:
    proxies = await get_all_user_proxies(user_id)
    if 0 <= index < len(proxies):
        removed = proxies.pop(index)
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
    proxies = await get_all_user_proxies(user_id)
    for i, p in enumerate(proxies):
        if p.get("proxy_url") == proxy_url:
            proxies.pop(i)
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
    proxies = await get_all_user_proxies(user_id)
    count = len(proxies)
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

# ==================== SITE FUNCTIONS ====================
async def add_site_db(user_id: int, site: str, gateway: str = "Unknown", price: str = "0") -> bool:
    db = await get_mongo_db()
    if db:
        try:
            await db.sites.update_one(
                {"_id": str(user_id)},
                {"$set": {f"sites.{site}": {"gateway": gateway, "price": price, "added_at": datetime.datetime.now().isoformat()}}},
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
                        result.append({"site": site, "gateway": "Unknown", "price": "0"})
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
                result.append({"site": site, "gateway": "Unknown", "price": "0"})
    elif isinstance(sites_data, list):
        for site in sites_data:
            result.append({"site": site, "gateway": "Unknown", "price": "0"})
    return result

async def remove_site_db(user_id: int, site: str) -> bool:
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
        _save_json_db(data)
        return True
    return False

async def update_site_info(user_id: int, site: str, gateway: str, price: str) -> bool:
    return await add_site_db(user_id, site, gateway, price)

# ==================== PLAN CODE FUNCTIONS ====================
PLAN_PREFIXES = {
    "trial": "SHOPIFY_TRIAL",
    "plan1": "SHOPIFY_CORE",
    "plan2": "SHOPIFY_ELITE",
    "plan3": "SHOPIFY_ROOT",
    "plan4": "SHOPIFY_X"
}

async def generate_plan_code(plan_key: str, count: int = 1) -> List[str]:
    prefix = PLAN_PREFIXES.get(plan_key, plan_key.upper())
    codes = []
    db = await get_mongo_db()
    
    if db:
        try:
            for _ in range(count):
                while True:
                    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
                    code = f"{prefix}_{random_suffix}"
                    existing = await db.codes.find_one({"_id": code})
                    if not existing:
                        break
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
        while True:
            random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            code = f"{prefix}_{random_suffix}"
            if code not in data["plan_codes"]:
                break
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

async def redeem_plan_code(user_id: int, code: str) -> Tuple[bool, str]:
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
                {"$set": {"plan": plan_info["tier"], "expiry": expiry, "updated_at": datetime.datetime.now().isoformat()}}
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
    
    from bot import PLANS
    plan_key = code_data.get("plan")
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
    data = _load_json_db()
    code_data = data.get("plan_codes", {}).get(code)
    if code_data:
        return not code_data.get("used", False)
    return False

def get_code_info(code: str) -> Optional[Dict]:
    data = _load_json_db()
    return data.get("plan_codes", {}).get(code)

async def remove_code(code: str) -> bool:
    db = await get_mongo_db()
    if db:
        try:
            result = await db.codes.delete_one({"_id": code})
            return result.deleted_count > 0
        except:
            pass
    
    data = _load_json_db()
    if code in data.get("plan_codes", {}):
        del data["plan_codes"][code]
        _save_json_db(data)
        return True
    return False

async def get_all_active_codes() -> Dict:
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

async def get_code_usage_stats() -> Dict:
    db = await get_mongo_db()
    if db:
        try:
            total = await db.codes.count_documents({})
            used = await db.codes.count_documents({"used": True})
            active = total - used
            return {"total": total, "used": used, "active": active}
        except:
            pass
    
    data = _load_json_db()
    codes = data.get("plan_codes", {})
    total = len(codes)
    used = sum(1 for c in codes.values() if c.get("used", False))
    return {"total": total, "used": used, "active": total - used}

# ==================== STATISTICS FUNCTIONS ====================
async def get_total_users() -> int:
    db = await get_mongo_db()
    if db:
        try:
            return await db.users.count_documents({})
        except:
            pass
    data = _load_json_db()
    return len(data["users"])

async def get_premium_count() -> int:
    db = await get_mongo_db()
    if db:
        try:
            return await db.users.count_documents({"plan": {"$in": ["Trial", "Core", "Elite", "Root", "X"]}})
        except:
            pass
    data = _load_json_db()
    return sum(1 for u in data["users"].values() if u.get("plan") in ["Trial", "Core", "Elite", "Root", "X"])

async def get_all_premium_users() -> List[Dict]:
    db = await get_mongo_db()
    if db:
        try:
            result = []
            cursor = db.users.find({"plan": {"$in": ["Trial", "Core", "Elite", "Root", "X"]}})
            async for doc in cursor:
                result.append({"user_id": int(doc["_id"]), "plan": doc.get("plan"), "expiry": doc.get("expiry")})
            return result
        except:
            pass
    
    data = _load_json_db()
    result = []
    for uid, udata in data["users"].items():
        if udata.get("plan") in ["Trial", "Core", "Elite", "Root", "X"]:
            result.append({"user_id": int(uid), "plan": udata.get("plan"), "expiry": udata.get("expiry")})
    return result

async def get_total_sites_count() -> int:
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
    db = await get_mongo_db()
    if db:
        try:
            return await db.sites.count_documents({})
        except:
            pass
    data = _load_json_db()
    return len(data["sites"])

async def get_sites_per_user() -> List[Dict]:
    db = await get_mongo_db()
    if db:
        try:
            result = []
            cursor = db.sites.find({})
            async for doc in cursor:
                result.append({"user_id": int(doc["_id"]), "cnt": len(doc.get("sites", {}))})
            return result
        except:
            pass
    
    data = _load_json_db()
    return [{"user_id": int(uid), "cnt": len(sites)} for uid, sites in data["sites"].items()]

async def get_all_sites_detail() -> List[Dict]:
    db = await get_mongo_db()
    if db:
        try:
            result = []
            cursor = db.sites.find({})
            async for doc in cursor:
                uid = int(doc["_id"])
                for site, info in doc.get("sites", {}).items():
                    result.append({
                        "user_id": uid,
                        "site": site,
                        "gateway": info.get("gateway", "Unknown") if isinstance(info, dict) else "Unknown",
                        "price": info.get("price", "0") if isinstance(info, dict) else "0"
                    })
            return result
        except:
            pass
    
    data = _load_json_db()
    result = []
    for uid, sites_dict in data["sites"].items():
        for site, info in sites_dict.items():
            result.append({
                "user_id": int(uid),
                "site": site,
                "gateway": info.get("gateway", "Unknown") if isinstance(info, dict) else "Unknown",
                "price": info.get("price", "0") if isinstance(info, dict) else "0"
            })
    return result

async def get_daily_stats() -> Dict:
    today = datetime.datetime.now().date().isoformat()
    db = await get_mongo_db()
    if db:
        try:
            today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            cards_today = await db.cards.count_documents({"created_at": {"$gte": today_start}})
            charged_today = await db.cards.count_documents({"status": "CHARGED", "created_at": {"$gte": today_start}})
            return {"date": today, "cards": cards_today, "charged": charged_today}
        except:
            pass
    
    data = _load_json_db()
    cards_today = sum(1 for c in data["cards"] if c.get("created_at", "").startswith(today))
    charged_today = sum(1 for c in data["cards"] if c.get("status") == "CHARGED" and c.get("created_at", "").startswith(today))
    return {"date": today, "cards": cards_today, "charged": charged_today}

# ==================== DATABASE INITIALIZATION ====================
async def init_db() -> bool:
    db = await get_mongo_db()
    if db:
        try:
            await db.users.create_index("_id")
            await db.users.create_index("plan")
            await db.users.create_index("expiry")
            await db.cards.create_index("created_at")
            await db.cards.create_index("status")
            await db.codes.create_index("used")
            await db.codes.create_index("_id")
            await db.proxies.create_index("_id")
            await db.sites.create_index("_id")
            return True
        except:
            return False
    return True

# ==================== BACKUP FUNCTIONS ====================
async def backup_to_json() -> Optional[str]:
    db = await get_mongo_db()
    if db:
        try:
            backup_data = {}
            users = await db.users.find({}).to_list(length=None)
            cards = await db.cards.find({}).to_list(length=None)
            codes = await db.codes.find({}).to_list(length=None)
            proxies = await db.proxies.find({}).to_list(length=None)
            sites = await db.sites.find({}).to_list(length=None)
            
            backup_data["users"] = {u["_id"]: u for u in users}
            backup_data["cards"] = cards
            backup_data["plan_codes"] = {c["_id"]: c for c in codes}
            backup_data["proxies"] = {p["_id"]: p for p in proxies}
            backup_data["sites"] = {s["_id"]: s for s in sites}
            
            backup_file = f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=2, default=str, ensure_ascii=False)
            return backup_file
        except:
            pass
    return None

async def restore_from_json(file_path: str) -> bool:
    db = await get_mongo_db()
    if not db:
        return False
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if "users" in data:
            for uid, user_data in data["users"].items():
                await db.users.update_one({"_id": uid}, {"$set": user_data}, upsert=True)
        
        if "cards" in data:
            await db.cards.delete_many({})
            for card in data["cards"]:
                await db.cards.insert_one(card)
        
        if "plan_codes" in data:
            await db.codes.delete_many({})
            for code, code_data in data["plan_codes"].items():
                await db.codes.insert_one(code_data)
        
        return True
    except:
        return False

# ==================== HEALTH CHECK ====================
async def is_mongo_healthy() -> bool:
    db = await get_mongo_db()
    if db:
        try:
            await db.command('ping')
            return True
        except:
            pass
    return False

async def get_db_status() -> Dict:
    mongo_ok = await is_mongo_healthy()
    json_ok = os.path.exists(DB_FILE)
    return {
        "mongo": mongo_ok,
        "json": json_ok,
        "active_storage": "mongodb" if mongo_ok else "json" if json_ok else "none"
    }

# ==================== JOIN CACHE ====================
_joined_cache = set()

async def mark_user_joined(user_id: int):
    _joined_cache.add(user_id)

async def is_user_marked_joined(user_id: int) -> bool:
    return user_id in _joined_cache

async def remove_joined_mark(user_id: int):
    _joined_cache.discard(user_id)

# ==================== GLOBAL SITES ====================
async def add_global_site(site: str) -> bool:
    return True

async def get_global_sites() -> List[str]:
    return []

async def remove_global_site(site: str) -> bool:
    return True

# ==================== DATABASE WRAPPER FOR COMPATIBILITY ====================
class DatabaseWrapper:
    def __init__(self):
        self.users = {}
    
    async def find_one(self, collection, query):
        return None
    
    async def __getitem__(self, key):
        return self

db = DatabaseWrapper()
