from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from discord.ext.commands._types import Check

    from core import Context


def in_voice_channel() -> Check[Context]:
    async def predicate(ctx: Context) -> bool:
        assert isinstance(ctx.author, discord.Member)
        if ctx.author.voice is None:
            raise commands.CheckFailure("You must be in a voice channel to use this command.")
        return True

    return commands.check(predicate)


def bot_in_voice_channel(cls: discord.VoiceProtocol) -> Check[Context]:
    async def predicate(ctx: Context) -> bool:
        assert isinstance(ctx.author, discord.Member)
        if ctx.author.voice is None:
            raise commands.CheckFailure("You must be in a voice channel to use this command.")

        if ctx.voice_client is None:
            try:
                if ctx.author.voice.channel is None:
                    raise commands.CheckFailure("Please join a voice channel first before using this command.")

                player = await ctx.author.voice.channel.connect(cls=cls)  # type: ignore

                player.home = ctx.channel  # type: ignore
                player.ctx = ctx
            except discord.ClientException:
                raise commands.CheckFailure("Bot was unable to join this voice channel. Please try again.")

        return True

    return commands.check(predicate)


def both_in_voice_channel() -> Check[Context]:
    async def predicate(ctx: Context) -> bool:
        assert isinstance(ctx.author, discord.Member)
        if ctx.author.voice is None:
            raise commands.CheckFailure("You must be in a voice channel to use this command.")
        if ctx.voice_client is None:
            raise commands.CheckFailure("Bot must be in a voice channel to use this command.")

        if ctx.author.voice.channel != ctx.voice_client.channel:
            raise commands.CheckFailure("You must be in the same voice channel as the bot to use this command.")

        return True

    return commands.check(predicate)
