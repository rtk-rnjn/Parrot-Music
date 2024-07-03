from __future__ import annotations

import logging
import logging.handlers
import os
import re

import aiosqlite
import discord
import jishaku  # noqa: F401
import jishaku.help_command
from discord.ext import commands, tasks

from utils import CONFIG, Cache

from .context import Context

os.environ["JISHAKU_HIDE"] = "True"
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
os.environ["JISHAKU_FORCE_PAGINATOR"] = "True"

file_handler = logging.handlers.RotatingFileHandler(filename=r"logs/bot.log", mode="w")
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
discord.utils.setup_logging(handler=file_handler, level=logging.INFO, root=True)


class Bot(commands.Bot):
    color = 0x2F3136
    sql: aiosqlite.Connection
    need_commit: bool = False

    def __init__(self, *, version: tuple[int, int, int], **kwargs):
        super().__init__(
            command_prefix=self.get_prefix,  # type: ignore
            case_insensitive=True,
            intents=discord.Intents.all(),
            help_command=jishaku.help_command.MinimalEmbedPaginatorHelp(),
            **kwargs,
        )
        self.version: tuple[int, int, int] = version

        self._BotBase__cogs = commands.core._CaseInsensitiveDict()

    async def setup_hook(self) -> None:
        self.sql = await aiosqlite.connect(CONFIG.database_file)
        self.cache = Cache(self)
        await self.sql.executescript(CONFIG.datbase_schema)

        await self.load_extension("jishaku")
        print("[COG] `jishaku` loaded")

        for cog in CONFIG.cogs:
            try:
                await self.load_extension(cog)
                print(f"[COG] `{cog}` loaded")
            except Exception as e:
                print(f"[COG] `{cog}` failed to load: {e}")

        self.global_commit.start()

    async def on_ready(self) -> None:
        print(f"[BOT] {self.user} is ready")

    @staticmethod
    def _check_permissions(channel: discord.abc.MessageableChannel, **kwargs) -> bool:
        permssions = discord.Permissions(**kwargs)
        return channel.permissions_for(channel.guild.me).is_superset(permssions)  # type: ignore

    async def process_commands(self, message: discord.Message) -> None:
        ctx = await self.get_context(message, cls=Context)

        if ctx.command is None:
            return

        if ctx.guild is None:
            return

        if not self._check_permissions(ctx.channel, send_messages=True, embed_links=True):
            return

        await self.invoke(ctx)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        if re.fullmatch(rf"<@!?{self.user.id}>", message.content):  # type: ignore
            await message.channel.send(f"Prefixes: `{'`, `'.join(await self.get_prefix(message))}`")
            return

        await self.process_commands(message)

    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if before.content == after.content:
            return

        if self.application and after.author == self.application.owner:
            await self.process_commands(after)

    async def get_prefix(self, message: discord.Message) -> list[str] | str:
        if message.guild is None:
            return commands.when_mentioned_or(*CONFIG.default_prefixes)(self, message)

        query = r"""SELECT BOT_PREFIX FROM GUILDS WHERE ID = ?"""

        prefix: str | None = await self.cache.get(query, (message.guild.id,))

        if prefix is None:
            await self.on_guild_join(message.guild)
            return commands.when_mentioned_or(*CONFIG.default_prefixes)(self, message)

        return commands.when_mentioned_or(prefix)(self, message)

    async def on_guild_join(self, guild: discord.Guild) -> None:
        query = r"""INSERT INTO GUILDS (ID) VALUES (?)"""

        await self.cache.put(query, (guild.id,))

    @tasks.loop(seconds=1)
    async def global_commit(self) -> None:
        if self.need_commit:
            await self.sql.commit()
            self.need_commit = False

    async def on_command_error(self, context: Context, exception: commands.CommandError) -> None:
        exception = getattr(exception, "original", exception)

        if isinstance(exception, commands.CommandNotFound):
            return

        await context.reply(f"An error occurred: {exception}")
        raise exception
