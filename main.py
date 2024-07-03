import asyncio
import contextlib
import os

from dotenv import load_dotenv

from core import Bot
from utils import JAVA_INSTALLED

load_dotenv()

if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    with contextlib.suppress(ImportError):
        import uvloop

        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

VERSION = (1, 0, 0)

if not JAVA_INSTALLED:
    raise EnvironmentError("Java 17 or higher is required to run this bot.")

LAVALINK = r"java -jar lavalink/Lavalink.jar"


async def run_terminal_command(command: str) -> None:
    process = await asyncio.create_subprocess_shell(command)
    await process.communicate()


async def main() -> None:
    bot = Bot(version=VERSION)
    await asyncio.gather(*(run_terminal_command(LAVALINK), bot.start(os.environ["TOKEN"])))


if __name__ == "__main__":
    asyncio.run(main())
