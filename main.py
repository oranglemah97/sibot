import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from commands import router

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.include_router(router)

from utils.stripe import fetch_stripe_js_hashes

async def main():
    # Fetch real Stripe.js hashes from CDN before starting
    await fetch_stripe_js_hashes()
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
