from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from cogs.music import Player
    from core.bot import Bot


class Context(commands.Context):
    if TYPE_CHECKING:
        bot: Bot
        voice_client: Player
        author: discord.Member
        guild: discord.Guild

    async def tick(self, *, value: bool = True) -> None:
        emoji = "\N{WHITE HEAVY CHECK MARK}" if value else "\N{CROSS MARK}"
        try:
            await self.message.add_reaction(emoji)
        except discord.Forbidden:
            pass

    async def is_dj(self) -> bool:
        if self.author.guild_permissions.manage_guild:
            return True

        query = r"""SELECT DJ_ROLE FROM GUILDS WHERE ID = ?"""

        dj_role = await self.bot.cache.get(query, (self.guild.id,))

        if dj_role is None:
            return False

        dj_role = self.guild.get_role(dj_role)
        if dj_role is None:
            return False

        return dj_role in self.author.roles

    async def prompt(self, *, content: str, delete_after: bool = False, timeout: float = 30.0) -> bool:
        message = await self.send(content)

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
