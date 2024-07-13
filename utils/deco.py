from __future__ import annotations

from typing import TYPE_CHECKING, Type

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from discord.ext.commands._types import Check

    from cogs.music import Player
    from core import Context


def in_voice_channel(*, bot: bool = False, user: bool = True, same: bool = True) -> Check[Context]:
    async def predicate(ctx: Context) -> bool:
        assert isinstance(ctx.author, discord.Member)
        if user and ctx.author.voice is None:
            raise commands.CheckFailure("You must be in a voice channel to use this command.")
        if bot and ctx.guild.voice_client is None:
            raise commands.CheckFailure("Bot is not in a voice channel.")

        if (
            bot
            and user
            and same
            and ctx.voice_client
            and ctx.author.voice
            and ctx.voice_client.channel != ctx.author.voice.channel
        ):
            raise commands.CheckFailure("You must be in same voice channel of Bot's")

        return True

    return commands.check(predicate)


def try_connect(*, cls: Type[Player]) -> Check[Context]:
    async def predicate(ctx: Context) -> bool:
        if ctx.author.voice is None:
            raise commands.CheckFailure("You must be in a voice channel to use this command.")

        if ctx.voice_client and ctx.voice_client.channel == ctx.author.voice.channel:
            return True

        if ctx.voice_client and ctx.voice_client.channel != ctx.author.voice.channel:
            raise commands.CheckFailure(
                f"Bot is already in a voice channel ({ctx.voice_client.channel.mention})."
            )

        if ctx.author.voice.channel:
            try:
                player = await ctx.author.voice.channel.connect(cls=cls)
                player.home = ctx.channel
                player.ctx = ctx
            except discord.ClientException as e:
                raise commands.CheckFailure("Failed connecting to channel") from e
        return True

    return commands.check(predicate)
