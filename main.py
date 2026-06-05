import asyncio
import logging
from app.bot import bot, dp
from app.handlers import router

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    dp.include_router(router)

    print("=== AI Miro Assistant Bot successfully started ===")
    
    # Enabling Long Polling, skipping dead messages
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
