import re
import random
import string
import uuid

from utils.constants import USER_AGENTS, TLS_PROFILES, get_random_browser_profile


# Per-user persistent fingerprints (muid stays same per machine)
_user_fingerprints = {}


def _detect_browser_info(ua: str) -> dict:
    """Extract browser name, version, and platform from user agent string."""
    info = {"browser": "Chrome", "version": "131", "platform": "Windows"}

    # Detect platform
    if "Macintosh" in ua or "Mac OS X" in ua:
        info["platform"] = "macOS"
    elif "Linux" in ua:
        info["platform"] = "Linux"
    else:
        info["platform"] = "Windows"

    # Detect browser + version
    if "Edg/" in ua:
        info["browser"] = "Edge"
        m = re.search(r'Edg/(\d+)', ua)
        if m: info["version"] = m.group(1)
    elif "OPR/" in ua:
        info["browser"] = "Opera"
        m = re.search(r'Chrome/(\d+)', ua)
        if m: info["version"] = m.group(1)
    elif "Firefox/" in ua:
        info["browser"] = "Firefox"
        m = re.search(r'Firefox/(\d+)', ua)
        if m: info["version"] = m.group(1)
    elif "Safari/" in ua and "Chrome" not in ua:
        info["browser"] = "Safari"
        m = re.search(r'Version/(\d+)', ua)
        if m: info["version"] = m.group(1)
    else:
        info["browser"] = "Chrome"
        m = re.search(r'Chrome/(\d+)', ua)
        if m: info["version"] = m.group(1)

    return info


def get_stripe_headers() -> dict:
    """Minimal Stripe-specific headers for use with curl_cffi impersonate.
    Browser headers (UA, sec-ch-ua, etc) are auto-set by curl_cffi."""
    return {
        "accept": "application/json",
        "content-type": "application/x-www-form-urlencoded",
        "origin": "https://checkout.stripe.com",
        "referer": "https://checkout.stripe.com/",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
    }


def get_headers(stripe_js: bool = False) -> dict:
    """Return headers mimicking Stripe.js browser requests."""
    ua = random.choice(USER_AGENTS)
    headers = {
        "accept": "application/json",
        "content-type": "application/x-www-form-urlencoded",
        "origin": "https://checkout.stripe.com",
        "referer": "https://checkout.stripe.com/",
        "user-agent": ua
    }
    if stripe_js:
        browser = _detect_browser_info(ua)
        v = browser["version"]
        platform = browser["platform"]

        headers["accept-language"] = random.choice([
            "en-US,en;q=0.9",
            "en-US,en;q=0.9,id;q=0.8",
            "en-GB,en;q=0.9,en-US;q=0.8",
            "en-US,en;q=0.9,nl;q=0.8",
            "en-US,en;q=0.9,de;q=0.8",
            "en-US,en;q=0.9,fr;q=0.8",
            "en-US,en;q=0.9,ja;q=0.8",
        ])
        headers["sec-fetch-dest"] = "empty"
        headers["sec-fetch-mode"] = "cors"
        headers["sec-fetch-site"] = "same-site"

        # Dynamic sec-ch-ua based on actual browser
        if browser["browser"] in ("Chrome", "Edge", "Opera"):
            not_a_brands = [
                '"Not(A:Brand";v="24"',
                '"Not_A Brand";v="8"',
                '"Not/A)Brand";v="8"',
                '"Not A(Brand";v="99"',
                '"Not)A;Brand";v="99"',
            ]
            not_a = random.choice(not_a_brands)
            if browser["browser"] == "Edge":
                headers["sec-ch-ua"] = f'"Chromium";v="{v}", {not_a}, "Microsoft Edge";v="{v}"'
            elif browser["browser"] == "Opera":
                headers["sec-ch-ua"] = f'"Chromium";v="{v}", {not_a}, "Opera";v="{v}"'
            else:
                headers["sec-ch-ua"] = f'"Chromium";v="{v}", {not_a}, "Google Chrome";v="{v}"'
            headers["sec-ch-ua-mobile"] = "?0"
            headers["sec-ch-ua-platform"] = f'"{platform}"'
        # Firefox/Safari don't send sec-ch-ua

    return headers

import hashlib
import aiohttp

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Real Stripe.js hash scraping from CDN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_cached_stripe_hashes = {
    "core": None,     # stripe.js main bundle hash
    "v3": None,       # stripe-js-v3 module hash
    "fetched": False, # whether we've attempted fetch
}


async def fetch_stripe_js_hashes():
    """Fetch real Stripe.js from CDN and extract build hashes.
    
    Should be called once at bot startup. Extracts fingerprint hashes
    from the webpack bundle's 'fingerprinted/js/' asset paths, which
    are the same hashes Stripe uses to identify legitimate JS clients.
    """
    global _cached_stripe_hashes
    
    if _cached_stripe_hashes["fetched"]:
        return
    
    _cached_stripe_hashes["fetched"] = True
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://js.stripe.com/v3/",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    "Accept": "*/*",
                },
                timeout=aiohttp.ClientTimeout(total=15),
                ssl=False,
            ) as resp:
                if resp.status != 200:
                    print(f"[DEBUG] Stripe.js fetch failed: HTTP {resp.status}")
                    return
                
                content = await resp.text()
                
                # Extract fingerprint hashes from the webpack bundle
                # Real Stripe.js contains paths like: fingerprinted/js/MODULE-HASH.js
                js_hashes = re.findall(
                    r'fingerprinted/js/[a-zA-Z0-9_-]+-([a-f0-9]{20,40})\.js',
                    content
                )
                
                if js_hashes:
                    # Use first two distinct hashes for core and v3
                    unique_hashes = list(dict.fromkeys(js_hashes))
                    _cached_stripe_hashes["core"] = unique_hashes[0][:10]
                    if len(unique_hashes) > 1:
                        _cached_stripe_hashes["v3"] = unique_hashes[1][:10]
                    else:
                        _cached_stripe_hashes["v3"] = unique_hashes[0][:10]
                    
                    print(f"[DEBUG] ✅ Stripe.js real hashes scraped: "
                          f"core={_cached_stripe_hashes['core']}, "
                          f"v3={_cached_stripe_hashes['v3']} "
                          f"(from {len(unique_hashes)} unique hashes)")
                else:
                    # Fallback: derive hash from content itself
                    content_hash = hashlib.sha256(content.encode()).hexdigest()
                    _cached_stripe_hashes["core"] = content_hash[:10]
                    _cached_stripe_hashes["v3"] = content_hash[10:20]
                    print(f"[DEBUG] ⚠️ No fingerprint paths found, using content hash: "
                          f"core={_cached_stripe_hashes['core']}, "
                          f"v3={_cached_stripe_hashes['v3']}")
                    
    except Exception as e:
        print(f"[DEBUG] ❌ Stripe.js hash fetch error: {str(e)[:80]}")


def get_random_stripe_js_agent() -> str:
    """Get Stripe.js payment_user_agent using real CDN hashes when available."""
    core = _cached_stripe_hashes.get("core")
    v3 = _cached_stripe_hashes.get("v3")
    
    if not core or not v3:
        # Last resort fallback — should rarely happen if fetch_stripe_js_hashes() was called
        core = hashlib.sha256(f"stripe-core-{random.randint(0,9999)}".encode()).hexdigest()[:10]
        v3 = hashlib.sha256(f"stripe-v3-{random.randint(0,9999)}".encode()).hexdigest()[:10]
        print(f"[DEBUG] ⚠️ Using generated hashes (CDN not fetched yet)")
    
    return f"stripe.js%2F{core}%3B+stripe-js-v3%2F{v3}%3B+checkout"


def _rand_hex(length: int) -> str:
    return ''.join(random.choices(string.hexdigits[:16], k=length))


def _uuid_format() -> str:
    return f"{_rand_hex(8)}-{_rand_hex(4)}-4{_rand_hex(3)}-{random.choice('89ab')}{_rand_hex(3)}-{_rand_hex(12)}"


def generate_stripe_fingerprints(user_id: int = None) -> dict:
    """Generate Stripe.js fingerprint identifiers.
    muid is persistent per user (like browser cookies).
    guid is per-page-load. sid is per-session."""

    # muid persistent per user (simulates __stripe_mid cookie)
    if user_id and user_id in _user_fingerprints:
        muid = _user_fingerprints[user_id]
    else:
        muid = _uuid_format()
        if user_id:
            _user_fingerprints[user_id] = muid

    # guid = per page load, sid = per session
    guid = _uuid_format()
    sid = _uuid_format()

    return {"muid": muid, "guid": guid, "sid": sid}


def generate_eid() -> str:
    """Generate a valid UUID v4 for the eid parameter."""
    return str(uuid.uuid4())


def get_stripe_cookies(fp: dict) -> str:
    """Generate Stripe cookie header mimicking real browser."""
    return f"__stripe_mid={fp['muid']}; __stripe_sid={fp['sid']}"


def generate_session_context(user_id: int = None) -> dict:
    """Generate a complete session context for one checkout session.
    
    This should be called ONCE per checkout session and reused for ALL
    card attempts. Mimics a real user opening checkout in one browser.
    
    Returns dict with:
        - tls_profile: browser TLS profile (same browser for all cards)
        - fingerprints: muid/guid/sid (same page load for all cards)
        - cookies: stripe cookie header
        - payment_user_agent: stripe.js agent string
        - pasted_fields: which fields were pasted
        - time_on_page_base: base time user spent on page (increases per card)
    """
    # Pick ONE browser for the entire session — TLS + UA always matched
    browser = get_random_browser_profile()
    tls_profile = browser["tls"]
    user_agent = browser["ua"]

    # Generate fingerprints ONCE (guid+sid stay same for all cards in session)
    fp = generate_stripe_fingerprints(user_id)

    # Cookies stay same for session
    cookies = get_stripe_cookies(fp)

    # Payment user agent stays same for session
    payment_user_agent = get_random_stripe_js_agent()

    # Randomize pasted_fields (some users type, some paste)
    pasted_fields = random.choice(["number", "number|cvc", "number|cvc|exp", ""])

    # Base time on page — starts at 20-60s, will increase per card
    time_on_page_base = random.randint(20000, 60000)

    return {
        "tls_profile": tls_profile,
        "user_agent": user_agent,
        "fingerprints": fp,
        "cookies": cookies,
        "payment_user_agent": payment_user_agent,
        "pasted_fields": pasted_fields,
        "time_on_page_base": time_on_page_base,
    }
