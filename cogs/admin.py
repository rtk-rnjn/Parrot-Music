from __future__ import annotations

import discord
from discord.ext import commands

from core import Bot, Cog, Context


class Admin(Cog):
    """A Admin Cog that provides administrative commands."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.command(name="block", hidden=True)
    @commands.is_owner()
    async def block(self, ctx: Context, *, obj: discord.User | discord.Member) -> None:
        """Block a user, member, guild or user ID."""

        confirm = ctx.prompt(
            content=f"Are you sure you want to block {obj}?",
            timeout=30.0,
        )
        if not confirm:
            return

        query = r"""INSERT INTO USERS (ID, BLACKLISTED) VALUES (?, 1)"""
        await self.bot.cache.insert(query, (obj.id,))
        await ctx.tick()

    @commands.command(name="unblock", hidden=True)
    @commands.is_owner()
    async def unblock(self, ctx: Context, *, obj: discord.User | discord.Member) -> None:
        """Unblock a user, member, guild or user ID."""

        confirm = ctx.prompt(
            content=f"Are you sure you want to unblock {obj}?",
            timeout=30.0,
        )
        if not confirm:
            return

        query = r"""UPDATE USERS SET BLACKLISTED = 0 WHERE ID = ?"""
        await self.bot.cache.update(query, (obj.id,))
        await ctx.tick()