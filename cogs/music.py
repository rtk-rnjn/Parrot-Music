from __future__ import annotations

from typing import cast

import discord
import wavelink
from discord.ext import commands

from core import Bot, Cog, Context
from utils import CONFIG, bot_in_voice_channel, both_in_voice_channel


class Player(wavelink.Player):
    ctx: Context
    home: discord.abc.MessageableChannel

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.loop = False

    async def is_dj(self) -> bool:
        """Shortcut from ctx.is_dj."""
        return await self.ctx.is_dj()


class Music(Cog):
    """A simple Music Cog that uses wavelink to play music in a voice channel."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        host = CONFIG.lavalink.host
        port = CONFIG.lavalink.port

        uri = f"ws://{host}:{port}"
        node = wavelink.Node(
            identifier="MAIN",
            uri=uri,
            password=CONFIG.lavalink.password,
        )

        await wavelink.Pool.connect(nodes=[node], client=self.bot, cache_capacity=100)

    def playing_embed(self, player: Player) -> discord.Embed:
        playable = player.current
        if not playable:
            embed = discord.Embed()
            embed.description = "_There is currently no song playing._"
            return embed

        embed = discord.Embed(
            description=f"**[{playable.title}]({playable.uri})**",
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(name=f"Author: {playable.author}")

        duration_graph = player.position / playable.length
        duration_bar = "\N{BLACK RECTANGLE}" * 20
        duration_bar = (
            duration_bar[: int(duration_graph * 20)] + "\N{RADIO BUTTON}" + duration_bar[int(duration_graph * 20) + 1 :]
        )

        timestamp = f"{player.position // 60000}:{(player.position // 1000) % 60:02d}"

        embed.add_field(
            name=f"Duration [{timestamp}/{playable.length // 60000}:{(playable.length // 1000) % 60:02d}]",
            value=f"`{duration_bar}`",
            inline=False,
        )

        if player.paused:
            embed.set_footer(text="The player is currently paused.")

        if playable.artwork:
            embed.set_thumbnail(url=playable.artwork)

        return embed

    @Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload) -> None:
        player: Player | None = cast(Player, payload.player)
        if player is None:
            return

        embed = self.playing_embed(player)

        await player.home.send(embed=embed)  # type: ignore

    @Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload) -> None:
        print(f"[BOT] Node {payload.node.identifier} is ready!")

    @Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload) -> None:
        player: Player | None = cast(Player, payload.player)
        if player is None:
            return

        if not player.queue:
            await player.disconnect()
            return

        await player.play(player.queue.get())

    @commands.command()
    @bot_in_voice_channel(cls=Player)  # type: ignore
    async def play(self, ctx: Context, *, query: str) -> None:
        """Play a song with the given query."""

        if ctx.voice_client.home != ctx.channel:
            await ctx.reply(
                f"You can only play songs in {ctx.voice_client.home.mention}, as the player has already started there."  # type: ignore
            )
            return

        tracks: wavelink.Search = await wavelink.Playable.search(query)
        if not tracks:
            await ctx.reply(f"{ctx.author.mention} - Could not find any tracks with that query. Please try again.")
            return

        if isinstance(tracks, wavelink.Playlist):
            added: int = await ctx.voice_client.queue.put_wait(tracks)
            await ctx.reply(f"Added the playlist **`{tracks.name}`** ({added} songs) to the queue.")
        else:
            track: wavelink.Playable = tracks[0]
            await ctx.voice_client.queue.put_wait(track)
            await ctx.reply(f"Added **`{track}`** to the queue.")

        if not ctx.voice_client.playing:
            await ctx.voice_client.play(ctx.voice_client.queue.get())

    @commands.command()
    @both_in_voice_channel()
    async def skip(self, ctx: Context) -> None:
        """Skip the current song."""
        await ctx.voice_client.skip(force=True)
        await ctx.tick()

    @commands.command(name="toggle", aliases=["pause", "resume"])
    @both_in_voice_channel()
    async def pause_resume(self, ctx: Context) -> None:
        """Pause or Resume the Player depending on its current state."""

        await ctx.voice_client.pause(not ctx.voice_client.paused)
        await ctx.tick()

    @commands.command(aliases=["dc"])
    @both_in_voice_channel()
    async def disconnect(self, ctx: Context) -> None:
        """Disconnect the Player."""
        await ctx.voice_client.disconnect()
        await ctx.tick()

    @commands.command()
    @both_in_voice_channel()
    async def volume(self, ctx: Context, *, percentage: float) -> None:
        """Set the volume of the Player."""
        await ctx.voice_client.set_volume(int(percentage * 10))
        await ctx.tick()

    @commands.command()
    @both_in_voice_channel()
    async def now_playing(self, ctx: Context) -> None:
        """Show the currently playing song."""
        await ctx.reply(embed=self.playing_embed(ctx.voice_client))


async def setup(bot: Bot) -> None:
    await bot.add_cog(Music(bot))
