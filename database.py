# Simple JSON Database - No MongoDB Required!
import json
import os
import datetime
import random
import string
import asyncio
from pathlib import Path

# ====================== DATA STORAGE PATH CONFIGURATION ======================
# Railway persistent volume support
# Railway volume typically mounted at /app/data/ or use /data/
# Production ke liye Railway Volume ka path set karein

def get_db_path():
    """
    Returns the path for database file with proper persistence support
    Priority: 
    1. RAILWAY_VOLUME_MOUNT_PATH (Railway volume)
    2. RAILWAY_VOLUME_MOUNT (alternative)
    3. Custom DB_PATH environment variable
    4. Default /app/data/ (Railway recommended)
    5. Local directory as fallback
    """
    # Check for Railway volume mount (most persistent)
    railway_volume = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "")
    if railway_volume and os.path.exists(railway_volume):
        db_dir = os.path.join(railway_volume, "bot_data")
        os.makedirs(db_dir, exist_ok=True)
        return os.path.join(db_dir, "razor_bot_data.json")
    
    # Alternative Railway volume env
    railway_volume = os.environ.get("RAILWAY_VOLUME_MOUNT", "")
    if railway_volume and os.path.exists(railway_volume):
        db_dir = os.path.join(railway_volume, "bot_data")
        os.makedirs(db_dir, exist_ok=True)
        return os.path.join(db_dir, "razor_bot_data.json")
    
    # Custom DB_PATH environment variable
    custom_path = os.environ.get("DB_PATH", "")
    if custom_path:
        db_dir = os.path.dirname(custom_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        return custom_path
    
    # Default Railway recommended data directory
    if os.path.exists("/app/data"):
        return "/app/data/razor_bot_data.json"
    
    # Fallback to /data directory (Docker volumes)
    if os.path.exists("/data"):
        return "/data/razor_bot_data.json"
    
    # Local development - current directory
    return "razor_bot_data.json"

# Global DB path - set at startup
DB_FILE = get_db_path()
BACKUP_DIR = os.path.join(os.path.dirname(DB_FILE), "backups") if os.path.dirname(DB_FILE) else "backups"

# File write lock to prevent corruption
_file_lock = asyncio.Lock()

# ====================== DATABASE FUNCTIONS ======================

def _ensure_backup_dir():
    """Create backup directory if not exists"""
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
    except:
        pass

def _load_db():
    """Load database from JSON file with error handling"""
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Validate and fix corrupted structure
                if not isinstance(data, dict):
                    data = {"users": {}, "cards": [], "proxies": {}, "sites": {}, "plan_codes": {}}
                # Ensure all required keys exist
                required_keys = ["users", "cards", "proxies", "sites", "plan_codes"]
                for key in required_keys:
                    if key not in data:
                        data[key] = {} if key == "plan_codes" else ([] if key == "cards" else {})
                return data
    except json.JSONDecodeError:
        print(f"⚠️ Database file corrupted! Attempting recovery...")
        # Try to recover from backup
        recovered = _recover_from_backup()
        if recovered:
            return recovered
    except Exception as e:
        print(f"⚠️ Error loading database: {e}")
    
    # Return default structure
    return {"users": {}, "cards": [], "proxies": {}, "sites": {}, "plan_codes": {}}

def _recover_from_backup():
    """Recover database from latest backup"""
    _ensure_backup_dir()
    try:
        backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith("razor_bot_data_backup_")], reverse=True)
        if backups:
            latest_backup = os.path.join(BACKUP_DIR, backups[0])
            with open(latest_backup, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"✅ Database recovered from backup: {latest_backup}")
            # Save recovered data as current DB
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            return data
    except Exception as e:
        print(f"❌ Backup recovery failed: {e}")
    return None

def _create_backup(data):
    """Create a backup of current database"""
    _ensure_backup_dir()
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f"razor_bot_data_backup_{timestamp}.json")
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        
        # Clean old backups (keep last 10)
        try:
            backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith("razor_bot_data_backup_")])
            for old_backup in backups[:-10]:
                os.remove(os.path.join(BACKUP_DIR, old_backup))
        except:
            pass
    except Exception as e:
        print(f"⚠️ Backup creation failed: {e}")

def _save_db(data):
    """Save database to JSON file with backup and locking"""
    try:
        # Create backup before saving (save old data if exists)
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                _create_backup(old_data)
            except:
                pass
        
        # Write new data atomically
        temp_file = f"{DB_FILE}.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        
        # Atomic rename (works on Unix/Linux)
        os.replace(temp_file, DB_FILE)
        
        # Log save confirmation (only for major changes)
        print(f"✅ Database saved: {DB_FILE} | Users: {len(data.get('users', {}))} | Cards: {len(data.get('cards', []))}")
        
    except Exception as e:
        print(f"❌ Error saving database: {e}")
        # Try direct save as fallback
        try:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            print(f"✅ Database saved (fallback): {DB_FILE}")
        except Exception as e2:
            print(f"❌ CRITICAL: Cannot save database: {e2}")

async def init_db():
    """Initialize database - ensure file exists and directories are ready"""
    # Ensure DB directory exists
    db_dir = os.path.dirname(DB_FILE)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    
    # Create backup directory
    _ensure_backup_dir()
    
    # Initialize if not exists
    if not os.path.exists(DB_FILE):
        default_data = {"users": {}, "cards": [], "proxies": {}, "sites": {}, "plan_codes": {}}
        _save_db(default_data)
    
    print(f"✅ JSON Database initialized at: {DB_FILE}")
    print(f"📁 Backup directory: {BACKUP_DIR}")
    return True

async def ensure_user(user_id):
    """Ensure user exists in database"""
    async with _file_lock:
        db = _load_db()
        user_str = str(user_id)
        if user_str not in db["users"]:
            db["users"][user_str] = {"plan": "Bronze", "expiry": None, "banned": False, "used_codes": []}
            _save_db(db)

async def get_user_plan(user_id):
    """Get user's plan with expiry check"""
    db = _load_db()
    user = db["users"].get(str(user_id), {})
    plan = user.get("plan", "Bronze")
    expiry = user.get("expiry")
    
    # Check if plan has expired
    if expiry and plan != "Bronze":
        try:
            if isinstance(expiry, str):
                expiry_date = datetime.datetime.fromisoformat(expiry)
            else:
                expiry_date = expiry
            
            if expiry_date < datetime.datetime.now():
                # Plan expired, reset to Bronze
                async with _file_lock:
                    db = _load_db()
                    db["users"][str(user_id)] = {"plan": "Bronze", "expiry": None, "banned": user.get("banned", False), "used_codes": user.get("used_codes", [])}
                    _save_db(db)
                return "Bronze"
        except:
            pass
    
    return plan

async def set_user_plan(user_id, plan, days=0):
    """Set user's plan with expiry"""
    async with _file_lock:
        db = _load_db()
        expiry = None
        if days > 0:
            expiry = (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()
        
        # Preserve used_codes when updating plan
        user = db["users"].get(str(user_id), {})
        used_codes = user.get("used_codes", [])
        
        db["users"][str(user_id)] = {"plan": plan, "expiry": expiry, "banned": user.get("banned", False), "used_codes": used_codes}
        _save_db(db)

async def is_premium_user(user_id):
    """Check if user has premium plan"""
    plan = await get_user_plan(user_id)
    return plan in ["Trial", "Core", "Elite", "Root", "X"]

async def is_banned_user(user_id):
    """Check if user is banned"""
    db = _load_db()
    return db["users"].get(str(user_id), {}).get("banned", False)

async def save_card_to_db(card, status, response, gateway, price):
    """Save card check result to database"""
    async with _file_lock:
        db = _load_db()
        db["cards"].append({
            "card": card, "status": status, "response": response,
            "gateway": gateway, "price": price, "created_at": datetime.datetime.now().isoformat()
        })
        _save_db(db)

async def get_total_cards_count():
    """Get total cards in database"""
    db = _load_db()
    return len(db["cards"])

async def get_charged_count():
    """Get count of charged cards"""
    db = _load_db()
    return sum(1 for c in db["cards"] if c.get("status") == "CHARGED")

async def get_approved_count():
    """Get count of approved cards"""
    db = _load_db()
    return sum(1 for c in db["cards"] if c.get("status") == "APPROVED")

async def add_proxy_db(user_id, proxy_data):
    """Add proxy for user"""
    async with _file_lock:
        db = _load_db()
        user_str = str(user_id)
        if user_str not in db["proxies"]:
            db["proxies"][user_str] = []
        db["proxies"][user_str].append(proxy_data)
        _save_db(db)

async def get_all_user_proxies(user_id):
    """Get all proxies for user"""
    db = _load_db()
    return db["proxies"].get(str(user_id), [])

async def get_proxy_count(user_id):
    """Get proxy count for user"""
    db = _load_db()
    return len(db["proxies"].get(str(user_id), []))

async def get_random_proxy(user_id):
    """Get random proxy for user"""
    proxies = await get_all_user_proxies(user_id)
    return random.choice(proxies) if proxies else None

async def remove_proxy_by_index(user_id, index):
    """Remove proxy by index"""
    async with _file_lock:
        db = _load_db()
        proxies = db["proxies"].get(str(user_id), [])
        if 0 <= index < len(proxies):
            removed = proxies.pop(index)
            _save_db(db)
            return removed
    return None

async def remove_proxy_by_url(user_id, proxy_url):
    """Remove proxy by URL"""
    async with _file_lock:
        db = _load_db()
        proxies = db["proxies"].get(str(user_id), [])
        for i, p in enumerate(proxies):
            if p.get("proxy_url") == proxy_url:
                proxies.pop(i)
                _save_db(db)
                return True
    return False

async def clear_all_proxies(user_id):
    """Clear all proxies for user"""
    async with _file_lock:
        db = _load_db()
        count = len(db["proxies"].get(str(user_id), []))
        db["proxies"][str(user_id)] = []
        _save_db(db)
        return count

# ============ SITE MANAGEMENT ============

async def add_site_db(user_id, site, gateway="Unknown", price="0"):
    """Add site with gateway and price info"""
    async with _file_lock:
        db = _load_db()
        user_str = str(user_id)
        if user_str not in db["sites"]:
            db["sites"][user_str] = {}
        
        db["sites"][user_str][site] = {"gateway": gateway, "price": price}
        _save_db(db)
        return True

async def get_user_sites(user_id):
    """Get all sites for user (returns list of site names)"""
    db = _load_db()
    sites_dict = db["sites"].get(str(user_id), {})
    return list(sites_dict.keys())

async def get_user_sites_with_info(user_id):
    """Get all sites with gateway and price info"""
    db = _load_db()
    sites_data = db["sites"].get(str(user_id), {})
    
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

async def remove_site_db(user_id, site):
    """Remove site for user"""
    async with _file_lock:
        db = _load_db()
        sites_dict = db["sites"].get(str(user_id), {})
        if site in sites_dict:
            del sites_dict[site]
            _save_db(db)
            return True
    return False

async def update_site_info(user_id, site, gateway, price):
    """Update gateway and price for existing site"""
    async with _file_lock:
        db = _load_db()
        user_str = str(user_id)
        if user_str not in db["sites"]:
            db["sites"][user_str] = {}
        db["sites"][user_str][site] = {"gateway": gateway, "price": price}
        _save_db(db)
        return True

# ============ PLAN CODE SYSTEM ============

async def generate_plan_code(plan_key, count=1):
    """Generate unique codes for a plan - returns list of codes"""
    async with _file_lock:
        db = _load_db()
        codes = []
        
        plan_prefixes = {
            "trial": "SHOPIFY_TRIAL",
            "plan1": "SHOPIFY_CORE",
            "plan2": "SHOPIFY_ELITE",
            "plan3": "SHOPIFY_ROOT",
            "plan4": "SHOPIFY_X"
        }
        
        prefix = plan_prefixes.get(plan_key, plan_key.upper())
        
        if "plan_codes" not in db:
            db["plan_codes"] = {}
        
        for _ in range(count):
            random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            code = f"{prefix}_{random_suffix}"
            
            while code in db["plan_codes"]:
                random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
                code = f"{prefix}_{random_suffix}"
            
            db["plan_codes"][code] = {
                "plan": plan_key,
                "created_at": datetime.datetime.now().isoformat(),
                "used": False,
                "used_by": None,
                "used_at": None
            }
            codes.append(code)
        
        _save_db(db)
        return codes

async def redeem_plan_code(user_id, code):
    """Redeem a plan code for a user"""
    async with _file_lock:
        db = _load_db()
        
        if code not in db.get("plan_codes", {}):
            return False, "invalid"
        
        code_data = db["plan_codes"][code]
        
        if code_data.get("used", False):
            return False, "used"
        
        plan_key = code_data.get("plan")
        
        from bot import PLANS
        if plan_key not in PLANS:
            return False, "invalid"
        
        plan_info = PLANS[plan_key]
        
        # Check if user already has a plan (import async)
        # We'll reload user data after lock release, for now check basic
        user_plan = db["users"].get(str(user_id), {}).get("plan", "Bronze")
        if user_plan != "Bronze":
            # Need to reload after lock, so return error
            return False, "has_plan"
        
        # Update user plan
        expiry = (datetime.datetime.now() + datetime.timedelta(days=plan_info["duration_days"])).isoformat()
        user = db["users"].get(str(user_id), {})
        used_codes = user.get("used_codes", [])
        
        db["users"][str(user_id)] = {
            "plan": plan_info["tier"],
            "expiry": expiry,
            "banned": user.get("banned", False),
            "used_codes": used_codes
        }
        
        # Mark code as used
        db["plan_codes"][code]["used"] = True
        db["plan_codes"][code]["used_by"] = user_id
        db["plan_codes"][code]["used_at"] = datetime.datetime.now().isoformat()
        
        # Add to user's used codes
        if "used_codes" not in db["users"][str(user_id)]:
            db["users"][str(user_id)]["used_codes"] = []
        db["users"][str(user_id)]["used_codes"].append(code)
        
        _save_db(db)
        return True, "success"

def is_valid_code(code):
    """Check if a code is valid and not used"""
    db = _load_db()
    code_data = db.get("plan_codes", {}).get(code)
    if not code_data:
        return False
    return not code_data.get("used", False)

def get_code_info(code):
    """Get information about a code"""
    db = _load_db()
    return db.get("plan_codes", {}).get(code)

async def remove_code(code):
    """Remove a code from the database"""
    async with _file_lock:
        db = _load_db()
        if code in db.get("plan_codes", {}):
            del db["plan_codes"][code]
            _save_db(db)
            return True
    return False

async def get_all_active_codes():
    """Get all active (unused) codes"""
    db = _load_db()
    codes = {}
    for code, data in db.get("plan_codes", {}).items():
        if not data.get("used", False):
            codes[code] = data
    return codes

async def get_all_codes():
    """Get all codes (used and unused)"""
    db = _load_db()
    return db.get("plan_codes", {})

# ============ STATISTICS ============

async def get_total_users():
    """Get total number of users"""
    db = _load_db()
    return len(db["users"])

async def get_premium_count():
    """Get count of premium users"""
    db = _load_db()
    return sum(1 for u in db["users"].values() if u.get("plan") in ["Trial", "Core", "Elite", "Root", "X"])

async def get_all_premium_users():
    """Get list of all premium users"""
    db = _load_db()
    result = []
    for uid, data in db["users"].items():
        if data.get("plan") in ["Trial", "Core", "Elite", "Root", "X"]:
            result.append({"user_id": int(uid), "plan": data.get("plan")})
    return result

async def get_total_sites_count():
    """Get total sites across all users"""
    db = _load_db()
    total = 0
    for sites_dict in db["sites"].values():
        total += len(sites_dict)
    return total

async def get_users_with_sites():
    """Get count of users who have sites"""
    db = _load_db()
    return len(db["sites"])

async def get_sites_per_user():
    """Get sites count per user"""
    db = _load_db()
    return [{"user_id": int(uid), "cnt": len(sites)} for uid, sites in db["sites"].items()]

async def get_all_sites_detail():
    """Get detailed sites information"""
    db = _load_db()
    result = []
    for uid, sites_dict in db["sites"].items():
        for site, info in sites_dict.items():
            result.append({
                "user_id": int(uid), 
                "site": site, 
                "gateway": info.get("gateway", "Unknown"),
                "price": info.get("price", "0")
            })
    return result

# ============ JOIN CACHE ============

_joined_cache = set()

async def mark_user_joined(user_id):
    """Mark user as joined (temporary cache)"""
    _joined_cache.add(user_id)

async def is_user_marked_joined(user_id):
    """Check if user is marked as joined"""
    return user_id in _joined_cache

async def remove_joined_mark(user_id):
    """Remove joined mark from user"""
    _joined_cache.discard(user_id)

# ============ GLOBAL SITES ============
# These functions are for backward compatibility

async def add_global_site(site):
    """Add global site (placeholder)"""
    return True

async def get_global_sites():
    """Get global sites (placeholder)"""
    return []

async def remove_global_site(site):
    """Remove global site (placeholder)"""
    return True

# ============ DATABASE WRAPPER ============

class DatabaseWrapper:
    def __init__(self):
        self.users = {}
    
    async def find_one(self, collection, query):
        """Find one user in database"""
        if collection == "users":
            user_id = query.get("user_id")
            if user_id:
                db_data = _load_db()
                user_data = db_data["users"].get(str(user_id))
                if user_data:
                    expiry = user_data.get("expiry")
                    if expiry and isinstance(expiry, str):
                        try:
                            user_data["expiry"] = datetime.datetime.fromisoformat(expiry)
                        except:
                            pass
                    return user_data
        return None
    
    async def __getitem__(self, key):
        return self

db = DatabaseWrapper()

# Print DB path on startup for debugging
print(f"📂 DATABASE PATH: {DB_FILE}")
print(f"📁 BACKUP PATH: {BACKUP_DIR}")
