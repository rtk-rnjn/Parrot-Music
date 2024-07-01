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
