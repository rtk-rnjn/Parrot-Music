from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Callable

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from bot import Bot
    from cog import Cog

    from cogs.music import Player


class Context(commands.Context):
    if TYPE_CHECKING:
        bot: Bot
        voice_client: Player
        author: discord.Member
        guild: discord.Guild

    async def tick(self, *, value: bool = True) -> None:
        # sourcery skip: use-contextlib-suppress
        emoji = "\N{WHITE HEAVY CHECK MARK}" if value else "\N{CROSS MARK}"
        try:
            await self.message.add_reaction(emoji)
        except discord.Forbidden:
            pass

    async def is_dj(self) -> bool:
        if self.author.guild_permissions.manage_channels:
            return True

        if (
            self.author.voice
            and self.author.voice.channel
            and len(self.author.voice.channel.members) < 3
            and self.voice_client
            and self.voice_client.channel == self.author.voice.channel
        ):
            return True

        query = r"""SELECT DJ_ROLE FROM GUILDS WHERE ID = ?"""

        dj_role = await self.bot.cache.get(query, (self.guild.id,))

        if dj_role is None:
            return True

        dj_role = self.guild.get_role(dj_role)
        return True if dj_role is None else dj_role in self.author.roles

    @staticmethod
    def dj_only():
        async def predicate(ctx: Context) -> bool:
            dj = await ctx.is_dj()
            if not dj:
                raise commands.CheckFailure("You must be a DJ to use this command.")
            return True

        return commands.check(predicate)

    @staticmethod
    def with_typing(func: Callable):
        @wraps(func)
        async def wrapped(*args, **kwargs) -> discord.Message | None:
            context: Context | Cog = args[0] if isinstance(args[0], Context) else args[1]
            async with context.typing():
                return await func(*args, **kwargs)

        return wrapped

    async def prompt(
        self, content: str, *, delete_after: bool = False, timeout: float = 30.0, message: discord.Message | None = None
    ) -> bool:
        if message is None:
            message = await self.send(content)
        else:
            message = await message.edit(content=content)

        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            return user == self.author and reaction.message.id == message.id

        await message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        await message.add_reaction("\N{CROSS MARK}")

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", check=check, timeout=timeout)
        except TimeoutError:
            await message.add_reaction("\N{ALARM CLOCK}")
            return False

        assert isinstance(reaction, discord.Reaction)

        if delete_after:
            await message.delete(delay=0)

        return str(reaction.emoji) == "\N{WHITE HEAVY CHECK MARK}"
