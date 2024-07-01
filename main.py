import asyncio
import contextlib
import os

from dotenv import load_dotenv

from core import Bot

load_dotenv()

if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    with contextlib.suppress(ImportError):
        import uvloop

        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

TOKEN = os.getenv("TOKEN")

if TOKEN is None:
    raise ValueError("token is missing")

VERSION = (1, 0, 0)


async def main() -> None:
    bot = Bot(version=VERSION)
    await bot.start(TOKEN)  # type: ignore # TOKEN check is done above


if __name__ == "__main__":
    asyncio.run(main())
