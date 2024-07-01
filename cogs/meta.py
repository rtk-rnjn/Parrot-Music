from __future__ import annotations

import time

from discord.ext import commands

from core import Bot, Cog, Context


class Meta(Cog):
    """Commands related to the bot itself."""

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name="ping")
    async def ping_command(self, ctx: Context) -> None:
        """Check the bot's latency."""
        ini = time.perf_counter()
        message = await ctx.reply("Pong!")
        delta = time.perf_counter() - ini

        await message.edit(content=f"Pong! ({delta * 1000:.2f}ms)")

    @commands.command(name="version", aliases=["v"])
    async def version_command(self, ctx: Context) -> None:
        """Display the bot's version."""

        await ctx.reply(f"Version {self.bot.version}")

    @commands.command(name="owner", aliases=["creator"])
    async def owner_command(self, ctx: Context) -> None:
        """Display the bot's owner."""

        appinfo = self.bot.application
        if appinfo is None:
            await ctx.reply("Failed to fetch application info.")
            return

        await ctx.reply(f"Bot owner: {appinfo.owner} ({appinfo.owner.id})")


async def setup(bot: Bot) -> None:
    await bot.add_cog(Meta(bot))
