from __future__ import annotations

import discord
from discord.ext import commands

from core import Bot, Cog, Context


class Config(Cog):
    """A simple Config Cog that allows users to configure the bot."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.group(name="cfg", aliases=["config"])
    @commands.has_permissions(manage_guild=True)
    async def config(self, ctx: Context) -> None:
        """Configure the bot."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @config.command(name="prefix")
    @commands.has_permissions(manage_guild=True)
    async def prefix(self, ctx: Context, prefix: str) -> None:
        """Set the bot's prefix.

        The prefix can't be longer than 32 characters.

        Example:
        `p!config prefix !`
        """
        query = r"""UPDATE GUILDS SET BOT_PREFIX = ? WHERE ID = ?"""
        if len(prefix) > 32:
            await ctx.tick(value=False)
            await ctx.send("The prefix can't be longer than 32 characters.", delete_after=5)
            return

        await self.bot.cache.update(query, (prefix, ctx.guild.id))
        await ctx.tick()

    @config.command(name="djrole")
    @commands.has_permissions(manage_guild=True)
    async def djrole(self, ctx: Context, *, role: discord.Role | None = None) -> None:
        """Set the DJ role.

        The DJ role allows users to control the music bot. If not role is given, the DJ role will be removed.

        Example:
        `p!config djrole @DJ`
        """
        query = r"""UPDATE GUILDS SET DJ_ROLE = ? WHERE ID = ?"""

        await self.bot.cache.update(query, (role.id if role else 0, ctx.guild.id))
        await ctx.tick()


async def setup(bot: Bot) -> None:
    await bot.add_cog(Config(bot))
