import os
import json
import time
import random
import asyncio
import aiohttp

from utils.constants import PROXY_FILE


def load_proxies() -> dict:
    """Load proxies from JSON file."""
    if os.path.exists(PROXY_FILE):
        try:
            with open(PROXY_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"[WARN] Failed to load proxies: {e}")
            return {}
    return {}


def save_proxies(data: dict):
    """Save proxies to JSON file."""
    try:
        with open(PROXY_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        print(f"[ERROR] Failed to save proxies: {e}")


def parse_proxy_format(proxy_str: str) -> dict:
    """Parse various proxy string formats into components."""
    proxy_str = proxy_str.strip()
    result = {"user": None, "password": None, "host": None, "port": None, "raw": proxy_str}

    try:
        if '@' in proxy_str:
            if proxy_str.count('@') == 1:
                auth_part, host_part = proxy_str.rsplit('@', 1)
                if ':' in auth_part:
                    result["user"], result["password"] = auth_part.split(':', 1)
                if ':' in host_part:
                    result["host"], port_str = host_part.rsplit(':', 1)
                    result["port"] = int(port_str)
        else:
            parts = proxy_str.split(':')
            if len(parts) == 4:
                result["host"] = parts[0]
                result["port"] = int(parts[1])
                result["user"] = parts[2]
                result["password"] = parts[3]
            elif len(parts) == 2:
                result["host"] = parts[0]
                result["port"] = int(parts[1])
    except (ValueError, IndexError) as e:
        print(f"[WARN] Failed to parse proxy '{proxy_str[:20]}...': {e}")

    return result


def get_proxy_url(proxy_str: str) -> str:
    """Convert proxy string to HTTP URL format."""
    parsed = parse_proxy_format(proxy_str)
    if parsed["host"] and parsed["port"]:
        if parsed["user"] and parsed["password"]:
            return f"http://{parsed['user']}:{parsed['password']}@{parsed['host']}:{parsed['port']}"
        else:
            return f"http://{parsed['host']}:{parsed['port']}"
    return None


def get_user_proxies(user_id: int) -> list:
    """Get list of proxies for a user."""
    proxies = load_proxies()
    user_data = proxies.get(str(user_id), [])
    if isinstance(user_data, str):
        return [user_data] if user_data else []
    return user_data if isinstance(user_data, list) else []


def add_user_proxy(user_id: int, proxy: str):
    """Add a proxy to a user's list."""
    proxies = load_proxies()
    user_key = str(user_id)
    if user_key not in proxies:
        proxies[user_key] = []
    elif isinstance(proxies[user_key], str):
        proxies[user_key] = [proxies[user_key]] if proxies[user_key] else []

    if proxy not in proxies[user_key]:
        proxies[user_key].append(proxy)
    save_proxies(proxies)


def remove_user_proxy(user_id: int, proxy: str = None):
    """Remove a proxy (or all) from a user's list."""
    proxies = load_proxies()
    user_key = str(user_id)
    if user_key in proxies:
        if proxy is None or proxy.lower() == "all":
            del proxies[user_key]
        else:
            if isinstance(proxies[user_key], list):
                proxies[user_key] = [p for p in proxies[user_key] if p != proxy]
                if not proxies[user_key]:
                    del proxies[user_key]
            elif isinstance(proxies[user_key], str) and proxies[user_key] == proxy:
                del proxies[user_key]
        save_proxies(proxies)
        return True
    return False


def get_global_proxies() -> list:
    """Get global proxy list."""
    proxies = load_proxies()
    data = proxies.get("global", [])
    return data if isinstance(data, list) else []


def add_global_proxy(proxy: str):
    """Add a global proxy."""
    proxies = load_proxies()
    if "global" not in proxies:
        proxies["global"] = []
    if proxy not in proxies["global"]:
        proxies["global"].append(proxy)
    save_proxies(proxies)


def remove_global_proxy(proxy: str = None):
    """Remove a global proxy (or all)."""
    proxies = load_proxies()
    if "global" in proxies:
        if proxy is None or proxy.lower() == "all":
            del proxies["global"]
        else:
            proxies["global"] = [p for p in proxies["global"] if p != proxy]
            if not proxies["global"]:
                del proxies["global"]
        save_proxies(proxies)
        return True
    return False


def get_user_proxy(user_id: int) -> str:
    """Get a random proxy for a user (random per attempt)."""
    user_proxies = get_user_proxies(user_id)
    global_proxies = get_global_proxies()
    all_proxies = user_proxies + global_proxies
    if not all_proxies:
        return None

    return random.choice(all_proxies)



def obfuscate_ip(ip: str) -> str:
    """Obfuscate an IP address for display."""
    if not ip:
        return "N/A"
    parts = ip.split('.')
    if len(parts) == 4:
        return f"{parts[0][0]}XX.{parts[1][0]}XX.{parts[2][0]}XX.{parts[3][0]}XX"
    return "N/A"


async def get_proxy_info(proxy_str: str = None, timeout: int = 10) -> dict:
    """Get info about a proxy (IP, location, ISP)."""
    result = {
        "status": "dead",
        "ip": None,
        "ip_obfuscated": None,
        "country": None,
        "city": None,
        "org": None,
        "using_proxy": False
    }

    proxy_url = None
    if proxy_str:
        proxy_url = get_proxy_url(proxy_str)
        result["using_proxy"] = True

    try:
        async with aiohttp.ClientSession() as session:
            kwargs = {"timeout": aiohttp.ClientTimeout(total=timeout)}
            if proxy_url:
                kwargs["proxy"] = proxy_url

            async with session.get("http://ip-api.com/json", **kwargs) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result["status"] = "alive"
                    result["ip"] = data.get("query")
                    result["ip_obfuscated"] = obfuscate_ip(data.get("query"))
                    result["country"] = data.get("country")
                    result["city"] = data.get("city")
                    result["org"] = data.get("isp")
    except Exception as e:
        result["status"] = "dead"
        print(f"[DEBUG] Proxy info error: {str(e)[:50]}")

    return result


async def check_proxy_alive(proxy_str: str, timeout: int = 10) -> dict:
    """Check if a proxy is alive and measure response time."""
    result = {
        "proxy": proxy_str,
        "status": "dead",
        "response_time": None,
        "external_ip": None,
        "error": None
    }

    proxy_url = get_proxy_url(proxy_str)
    if not proxy_url:
        result["error"] = "Invalid format"
        return result

    try:
        start = time.perf_counter()
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://ip-api.com/json",
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                elapsed = round((time.perf_counter() - start) * 1000, 2)
                if resp.status == 200:
                    data = await resp.json()
                    result["status"] = "alive"
                    result["response_time"] = f"{elapsed}ms"
                    result["external_ip"] = data.get("query")
    except asyncio.TimeoutError:
        result["error"] = "Timeout"
    except Exception as e:
        result["error"] = str(e)[:30]

    return result


async def check_proxies_batch(proxies: list, max_threads: int = 10) -> list:
    """Check multiple proxies concurrently."""
    semaphore = asyncio.Semaphore(max_threads)

    async def check_with_semaphore(proxy):
        async with semaphore:
            return await check_proxy_alive(proxy)

    tasks = [check_with_semaphore(p) for p in proxies]
    return await asyncio.gather(*tasks)
