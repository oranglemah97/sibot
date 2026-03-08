import asyncio
import aiohttp

from config import NOPECHA_KEY


NOPECHA_TOKEN_URL = "https://api.nopecha.com/token/"
NOPECHA_TIMEOUT = 120  # Max waktu tunggu solve (detik)
NOPECHA_POLL_INTERVAL = 3  # Interval poll status (detik)


# NopeCHA error codes
_NOPECHA_ERRORS = {
    1: "Invalid request — bad parameters",
    2: "Not enough credit balance",
    3: "Invalid API key size",
    4: "Unrecognized CAPTCHA type",
    5: "Server too busy, try again",
    6: "Internal server error",
    7: "Invalid sitekey",
    9: "Rate limited — too many requests",
    10: "Invalid request — check proxy format or API key",
    11: "Unsupported captcha type",
    12: "Proxy error",
    14: "Banned — contact NopeCHA support",
}


async def solve_hcaptcha(site_key: str, url: str, rqdata: str = None, proxy: str = None, user_agent: str = None) -> str | None:
    """Solve hCaptcha menggunakan NopeCHA Token API.
    
    Args:
        site_key: hCaptcha sitekey dari Stripe response
        url: URL halaman checkout (dimana hCaptcha muncul)
        rqdata: Optional rqdata dari Stripe hCaptcha Enterprise
        proxy: Optional proxy string (format: host:port:user:pass)
        user_agent: Optional user agent string
        
    Returns:
        Token string jika berhasil, None jika gagal/timeout.
    """
    if not NOPECHA_KEY:
        print("[DEBUG] ❌ NOPECHA_KEY not configured — skipping captcha solve")
        print("[DEBUG]    Get your key at: https://nopecha.com/manage")
        return None
    
    if not site_key:
        print("[DEBUG] ❌ No site_key provided — cannot solve captcha")
        return None
    
    print(f"[DEBUG] 🔄 Solving hCaptcha via NopeCHA...")
    print(f"[DEBUG]    site_key: {site_key[:20]}...")
    print(f"[DEBUG]    url: {url[:60]}...")
    if rqdata:
        print(f"[DEBUG]    rqdata: {rqdata[:30]}... (Enterprise)")
    
    # Build request body
    body = {
        "key": NOPECHA_KEY,
        "type": "hcaptcha",
        "sitekey": site_key,
        "url": url,
    }
    
    # Add rqdata for hCaptcha Enterprise (Stripe uses this)
    if rqdata:
        body["data"] = {"rqdata": rqdata}
    
    # Add optional proxy (NopeCHA format)
    if proxy:
        proxy_parts = _parse_proxy_for_nopecha(proxy)
        if proxy_parts:
            body["proxy"] = proxy_parts
            print(f"[DEBUG]    proxy: {proxy_parts}")
        else:
            print(f"[DEBUG]    ⚠️ Could not parse proxy: {proxy[:40]}...")
    
    # Add optional user agent
    if user_agent:
        body["useragent"] = user_agent
    
    # Debug: show full request body (sans key)
    debug_body = {k: (v if k != 'key' else v[:8] + '...') for k, v in body.items()}
    print(f"[DEBUG]    NopeCHA body: {debug_body}")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Step 1: Submit captcha task
            async with session.post(
                NOPECHA_TOKEN_URL,
                json=body,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                data = await resp.json()
                
                if resp.status != 200:
                    err_code = data.get("error", "unknown")
                    err_msg = data.get("message", "")
                    err_type = data.get("type", "")
                    known = _NOPECHA_ERRORS.get(err_code, "") if isinstance(err_code, int) else ""
                    print(f"[DEBUG] ❌ NopeCHA HTTP {resp.status} — error={err_code}, message={err_msg}, type={err_type}")
                    if known:
                        print(f"[DEBUG]    Known: {known}")
                    print(f"[DEBUG]    Full response: {data}")
                    return None
                
                # Check if token returned immediately
                if isinstance(data, str) and len(data) > 50:
                    print(f"[DEBUG] ✅ hCaptcha solved instantly! Token: {data[:30]}...")
                    return data
                
                if isinstance(data, dict) and data.get("data"):
                    token = data["data"]
                    print(f"[DEBUG] ✅ hCaptcha solved instantly! Token: {token[:30]}...")
                    return token
                
                # Check if we need to poll
                if isinstance(data, dict) and data.get("error") == "Incomplete":
                    print(f"[DEBUG] ⏳ NopeCHA processing... polling for result")
                
            # Step 2: Poll for result
            elapsed = 0
            while elapsed < NOPECHA_TIMEOUT:
                await asyncio.sleep(NOPECHA_POLL_INTERVAL)
                elapsed += NOPECHA_POLL_INTERVAL
                
                async with session.post(
                    NOPECHA_TOKEN_URL,
                    json=body,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as poll_resp:
                    poll_data = await poll_resp.json()
                    
                    # Token returned as string
                    if isinstance(poll_data, str) and len(poll_data) > 50:
                        print(f"[DEBUG] ✅ hCaptcha solved! ({elapsed}s) Token: {poll_data[:30]}...")
                        return poll_data
                    
                    if isinstance(poll_data, dict):
                        # Token in data field
                        if poll_data.get("data"):
                            token = poll_data["data"]
                            print(f"[DEBUG] ✅ hCaptcha solved! ({elapsed}s) Token: {token[:30]}...")
                            return token
                        
                        # Still processing
                        error = poll_data.get("error", "")
                        if error == "Incomplete":
                            print(f"[DEBUG] ⏳ Still solving... ({elapsed}s/{NOPECHA_TIMEOUT}s)")
                            continue
                        
                        # Real error
                        if error and error != "Incomplete":
                            print(f"[DEBUG] ❌ NopeCHA error: {error}")
                            return None
                
                print(f"[DEBUG] ⏳ Polling... ({elapsed}s/{NOPECHA_TIMEOUT}s)")
            
            print(f"[DEBUG] ❌ NopeCHA timeout after {NOPECHA_TIMEOUT}s")
            return None
            
    except asyncio.TimeoutError:
        print(f"[DEBUG] ❌ NopeCHA request timeout")
        return None
    except Exception as e:
        print(f"[DEBUG] ❌ NopeCHA error: {str(e)[:80]}")
        return None


def _parse_proxy_for_nopecha(proxy_str: str) -> dict | None:
    """Convert proxy string ke format NopeCHA API.
    
    Supports formats:
        http://user:pass@host:port  (from get_proxy_url())
        http://host:port
        host:port:user:pass
        user:pass@host:port
        host:port
    
    Returns dict: {"scheme": "http", "host": ..., "port": ..., "username": ..., "password": ...}
    """
    try:
        scheme = "http"
        username = None
        password = None
        
        # Strip scheme prefix (http://, https://, socks5://)
        clean = proxy_str
        if "://" in clean:
            scheme_part, clean = clean.split("://", 1)
            if scheme_part in ("http", "https", "socks5", "socks4"):
                scheme = scheme_part
        
        if "@" in clean:
            # user:pass@host:port
            auth, hostport = clean.rsplit("@", 1)
            parts = auth.split(":", 1)
            username = parts[0]
            password = parts[1] if len(parts) > 1 else None
            hp = hostport.split(":")
            host = hp[0]
            port = int(hp[1]) if len(hp) > 1 else 8080
        else:
            parts = clean.split(":")
            if len(parts) == 4:
                # host:port:user:pass
                host, port, username, password = parts[0], int(parts[1]), parts[2], parts[3]
            elif len(parts) == 2:
                # host:port
                host, port = parts[0], int(parts[1])
            else:
                return None
        
        result = {
            "scheme": scheme,
            "host": host,
            "port": port,
        }
        if username:
            result["username"] = username
        if password:
            result["password"] = password
        
        return result
        
    except Exception:
        return None
