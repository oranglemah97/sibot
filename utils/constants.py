import os
import random

from config import SERVER_ID

# Server flag emojis
SERVER_FLAGS = {
    'us1': '🇺🇸 US1', 'us2': '🇺🇸 US2', 'us3': '🇺🇸 US3',
    'nl': '🇳🇱 NL', 'neth': '🇳🇱 NETH',
    'sg': '🇸🇬 SG', 'jp': '🇯🇵 JP',
    'de': '🇩🇪 DE', 'uk': '🇬🇧 UK', 'fr': '🇫🇷 FR',
    'id': '🇮🇩 ID', 'in': '🇮🇳 IN', 'au': '🇦🇺 AU',
    'co': '🌐 BOT',
}
SERVER_DISPLAY = SERVER_FLAGS.get(SERVER_ID, f'🌐 {SERVER_ID.upper()}')
CMD_NAME = SERVER_ID

PROXY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "proxies.json")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Browser Profiles — TLS + UA always matched
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Each entry maps a curl_cffi TLS profile to its compatible User-Agent strings.
# This ensures the TLS fingerprint (JA3/JA4) matches the UA being sent.
BROWSER_PROFILES = [
    # ── Chrome Windows ──
    {"tls": "chrome131", "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"},
    {"tls": "chrome131", "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"},
    {"tls": "chrome131", "ua": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"},
    {"tls": "chrome136", "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"},
    {"tls": "chrome133a", "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"},
    {"tls": "chrome133a", "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"},
    {"tls": "chrome124", "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"},
    {"tls": "chrome124", "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"},
    {"tls": "chrome123", "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"},
    {"tls": "chrome123", "ua": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"},
    {"tls": "chrome120", "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"},
    {"tls": "chrome120", "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"},
    # ── Edge (uses Chrome TLS internally) ──
    {"tls": "edge101", "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"},
    {"tls": "edge101", "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"},
    {"tls": "edge101", "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0"},
    {"tls": "edge99", "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0"},
    {"tls": "edge99", "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0"},
    {"tls": "edge99", "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0"},
    # ── Firefox ──
    {"tls": "firefox135", "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0"},
    {"tls": "firefox135", "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0"},
    {"tls": "firefox135", "ua": "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0"},
    {"tls": "firefox133", "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0"},
    {"tls": "firefox133", "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:132.0) Gecko/20100101 Firefox/132.0"},
    {"tls": "firefox133", "ua": "Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0"},
    {"tls": "firefox133", "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0"},
    {"tls": "firefox133", "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0"},
    {"tls": "firefox133", "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0"},
    # ── Safari (Mac only) ──
    {"tls": "safari18_0", "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15"},
    {"tls": "safari18_0", "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15"},
    {"tls": "safari17_0", "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15"},
    {"tls": "safari17_0", "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15"},
    # ── Opera (uses Chrome TLS internally) ──
    {"tls": "chrome131", "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 OPR/116.0.0.0"},
    {"tls": "chrome124", "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 OPR/115.0.0.0"},
    {"tls": "chrome123", "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 OPR/114.0.0.0"},
]

# Derived lists for backward compatibility
USER_AGENTS = [p["ua"] for p in BROWSER_PROFILES]
TLS_PROFILES = list(set(p["tls"] for p in BROWSER_PROFILES))

# Stripe.js version patterns
STRIPE_JS_VERSIONS = [
    "v3", "v3.1", "v3.2", "v3.3", "v3.4", "v3.5",
]


def get_random_browser_profile() -> dict:
    """Pick a random browser profile with matched TLS + UA.
    Returns dict with 'tls' and 'ua' keys."""
    return random.choice(BROWSER_PROFILES)

# Pool of realistic billing addresses for randomization
BILLING_ADDRESSES = [
    # US addresses (various states)
    {"name": "James Wilson", "line1": "742 Evergreen Terrace", "city": "Springfield", "state": "IL", "zip": "62704", "country": "US"},
    {"name": "Sarah Johnson", "line1": "1520 Oak Street", "city": "San Francisco", "state": "CA", "zip": "94117", "country": "US"},
    {"name": "Michael Brown", "line1": "308 Meadow Lane", "city": "Austin", "state": "TX", "zip": "78701", "country": "US"},
    {"name": "Emily Davis", "line1": "2145 Birch Drive", "city": "Denver", "state": "CO", "zip": "80202", "country": "US"},
    {"name": "Robert Martinez", "line1": "987 Pine Avenue", "city": "Miami", "state": "FL", "zip": "33101", "country": "US"},
    {"name": "Jessica Taylor", "line1": "1100 Maple Road", "city": "Seattle", "state": "WA", "zip": "98101", "country": "US"},
    {"name": "David Anderson", "line1": "456 Cedar Boulevard", "city": "Portland", "state": "OR", "zip": "97201", "country": "US"},
    {"name": "Ashley Thomas", "line1": "2301 Elm Street", "city": "Chicago", "state": "IL", "zip": "60601", "country": "US"},
    {"name": "Christopher Lee", "line1": "789 Walnut Court", "city": "Boston", "state": "MA", "zip": "02101", "country": "US"},
    {"name": "Amanda White", "line1": "1435 Spruce Way", "city": "Nashville", "state": "TN", "zip": "37201", "country": "US"},
    {"name": "Daniel Harris", "line1": "562 Willow Lane", "city": "Phoenix", "state": "AZ", "zip": "85001", "country": "US"},
    {"name": "Stephanie Clark", "line1": "3200 Ash Drive", "city": "Las Vegas", "state": "NV", "zip": "89101", "country": "US"},
    {"name": "Matthew Lewis", "line1": "871 Poplar Street", "city": "Atlanta", "state": "GA", "zip": "30301", "country": "US"},
    {"name": "Jennifer Robinson", "line1": "1028 Magnolia Ave", "city": "Charlotte", "state": "NC", "zip": "28201", "country": "US"},
    {"name": "Andrew Walker", "line1": "445 Hickory Road", "city": "Minneapolis", "state": "MN", "zip": "55401", "country": "US"},
    {"name": "Lauren Hall", "line1": "1567 Chestnut Blvd", "city": "San Diego", "state": "CA", "zip": "92101", "country": "US"},
    {"name": "Joshua Allen", "line1": "2890 Sycamore Dr", "city": "Dallas", "state": "TX", "zip": "75201", "country": "US"},
    {"name": "Megan Young", "line1": "634 Dogwood Lane", "city": "Philadelphia", "state": "PA", "zip": "19101", "country": "US"},
    {"name": "Ryan King", "line1": "1750 Juniper Street", "city": "Columbus", "state": "OH", "zip": "43201", "country": "US"},
    {"name": "Brittany Wright", "line1": "903 Redwood Ave", "city": "San Antonio", "state": "TX", "zip": "78201", "country": "US"},
    {"name": "Kevin Scott", "line1": "2100 Cypress Road", "city": "Indianapolis", "state": "IN", "zip": "46201", "country": "US"},
    {"name": "Rachel Green", "line1": "1388 Laurel Way", "city": "Jacksonville", "state": "FL", "zip": "32099", "country": "US"},
    {"name": "Brandon Adams", "line1": "476 Hazel Court", "city": "Fort Worth", "state": "TX", "zip": "76101", "country": "US"},
    {"name": "Samantha Nelson", "line1": "2567 Palm Drive", "city": "Tucson", "state": "AZ", "zip": "85701", "country": "US"},
    {"name": "Tyler Carter", "line1": "831 Aspen Lane", "city": "Raleigh", "state": "NC", "zip": "27601", "country": "US"},
    {"name": "Kayla Mitchell", "line1": "1245 Linden Blvd", "city": "Kansas City", "state": "MO", "zip": "64101", "country": "US"},
    {"name": "Jason Perez", "line1": "390 Beech Street", "city": "Sacramento", "state": "CA", "zip": "95801", "country": "US"},
    {"name": "Nicole Roberts", "line1": "1680 Hemlock Road", "city": "Salt Lake City", "state": "UT", "zip": "84101", "country": "US"},
    {"name": "Justin Turner", "line1": "2034 Alder Ave", "city": "Milwaukee", "state": "WI", "zip": "53201", "country": "US"},
    {"name": "Heather Phillips", "line1": "517 Cottonwood Dr", "city": "Tampa", "state": "FL", "zip": "33601", "country": "US"},
    {"name": "Aaron Campbell", "line1": "1890 Fir Street", "city": "Pittsburgh", "state": "PA", "zip": "15201", "country": "US"},
    {"name": "Tiffany Parker", "line1": "643 Sequoia Way", "city": "Cincinnati", "state": "OH", "zip": "45201", "country": "US"},
    {"name": "Nathan Evans", "line1": "2456 Ivy Lane", "city": "Orlando", "state": "FL", "zip": "32801", "country": "US"},
    {"name": "Christina Edwards", "line1": "1102 Holly Road", "city": "St. Louis", "state": "MO", "zip": "63101", "country": "US"},
    {"name": "Patrick Collins", "line1": "785 Oakwood Blvd", "city": "Honolulu", "state": "HI", "zip": "96801", "country": "US"},
    {"name": "Amber Stewart", "line1": "1934 Pinewood Ave", "city": "Anchorage", "state": "AK", "zip": "99501", "country": "US"},
    {"name": "Sean Morris", "line1": "328 Birchwood Ct", "city": "Newark", "state": "NJ", "zip": "07101", "country": "US"},
    {"name": "Vanessa Rogers", "line1": "2710 Cedarwood Dr", "city": "Louisville", "state": "KY", "zip": "40201", "country": "US"},
    {"name": "Derek Reed", "line1": "1456 Maplewood St", "city": "Richmond", "state": "VA", "zip": "23218", "country": "US"},
    {"name": "Melissa Cook", "line1": "892 Timberline Rd", "city": "Boise", "state": "ID", "zip": "83701", "country": "US"},
    # Macau addresses
    {"name": "Wong Ka Ming", "line1": "Rua de S. Paulo No. 45", "city": "Macau", "state": "Macau", "zip": "999078", "country": "MO"},
    {"name": "Chan Mei Ling", "line1": "Av. de Almeida Ribeiro 128", "city": "Macau", "state": "Macau", "zip": "999078", "country": "MO"},
    {"name": "Ho Siu Wai", "line1": "Rua do Campo No. 78", "city": "Macau", "state": "Macau", "zip": "999078", "country": "MO"},
    {"name": "Leong Chi Keong", "line1": "Estrada do Repouso 32", "city": "Taipa", "state": "Macau", "zip": "999078", "country": "MO"},
    {"name": "Lam Pui San", "line1": "Rua de Pedro Coutinho 56", "city": "Macau", "state": "Macau", "zip": "999078", "country": "MO"},
    {"name": "Fong Weng Chon", "line1": "Av. do Conselheiro Ferreira de Almeida 90", "city": "Macau", "state": "Macau", "zip": "999078", "country": "MO"},
    {"name": "Cheang Sok Ian", "line1": "Rua dos Mercadores 112", "city": "Macau", "state": "Macau", "zip": "999078", "country": "MO"},
    {"name": "Ng Kuok Cheong", "line1": "Travessa do Mastro 18", "city": "Macau", "state": "Macau", "zip": "999078", "country": "MO"},
    {"name": "Tam Wai Man", "line1": "Rua da Tercena 24", "city": "Coloane", "state": "Macau", "zip": "999078", "country": "MO"},
    {"name": "Lei Kin Yun", "line1": "Av. de Kwong Tung 67", "city": "Taipa", "state": "Macau", "zip": "999078", "country": "MO"},
]

CARD_SEPARATOR = "━ ━ ━ ━ ━ ━━━ ━ ━ ━ ━ ━"
STATUS_EMOJIS = {
    'CHARGED': '😎', 'LIVE': '✅', 'DECLINED': '🥲', '3DS': '😡',
    'ERROR': '💀', 'FAILED': '💀', 'UNKNOWN': '❓'
}

# Decline codes that mean the card is LIVE (valid number, wrong details)
LIVE_DECLINE_CODES = {
    'incorrect_cvc', 'incorrect_zip', 'insufficient_funds',
    'invalid_cvc', 'card_velocity_exceeded', 'do_not_honor',
    'try_again_later', 'not_permitted', 'withdrawal_count_limit_exceeded',
}


def get_random_billing() -> dict:
    """Get a random billing address from the pool."""
    return random.choice(BILLING_ADDRESSES)


def get_currency_symbol(currency: str) -> str:
    symbols = {
        "USD": "$", "EUR": "€", "GBP": "£", "INR": "₹", "JPY": "¥",
        "CNY": "¥", "KRW": "₩", "RUB": "₽", "BRL": "R$", "CAD": "C$",
        "AUD": "A$", "MXN": "MX$", "SGD": "S$", "HKD": "HK$", "THB": "฿",
        "VND": "₫", "PHP": "₱", "IDR": "Rp", "MYR": "RM", "ZAR": "R",
        "CHF": "CHF", "SEK": "kr", "NOK": "kr", "DKK": "kr", "PLN": "zł",
        "TRY": "₺", "AED": "د.إ", "SAR": "﷼", "ILS": "₪", "TWD": "NT$"
    }
    return symbols.get(currency, "")


def format_time(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.2f}s"
    mins = int(seconds // 60)
    secs = seconds % 60
    return f"{mins}m {secs:.2f}s"
