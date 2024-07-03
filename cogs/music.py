from __future__ import annotations

import asyncio
from typing import cast

import discord
import wavelink
from discord.ext import commands
from jishaku.paginators import PaginatorEmbedInterface

from core import Bot, Cog, Context
from utils import CONFIG, in_voice_channel, try_connect


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

    _pool: dict = {}

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

        self._pool = await wavelink.Pool.connect(nodes=[node], client=self.bot, cache_capacity=100)

    def playing_embed(self, player: Player) -> discord.Embed:
        playable = player.current
        if not playable:
            embed = discord.Embed()
            embed.description = "_There is currently no song playing._"
            return embed

        if playable.uri:
            description = f"**[{playable.title}]({playable.uri})**"
        else:
            description = f"**{playable.title}**"

        embed = discord.Embed(
            description=description,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(name=f"Author: {playable.author}")

        duration_graph = player.position / playable.length
        duration_bar = "\N{BLACK RECTANGLE}" * 20
        duration_bar = (
            duration_bar[: int(duration_graph * 20)] + "\N{RADIO BUTTON}" + duration_bar[int(duration_graph * 20) + 1 :]
        )

        timestamp = f"{player.position // 60000}:{(player.position // 1000) % 60:02d}"

        (
            embed.add_field(
                name=f"Duration [{timestamp}/{playable.length // 60000}:{(playable.length // 1000) % 60:02d}]",
                value=f"`{duration_bar}`",
                inline=False,
            )
            .add_field(
                name="Volume",
                value=f"{player.volume}%",
            )
            .add_field(
                name="Looping",
                value="Yes" if player.loop else "No",
            )
            .add_field(
                name=f"Queue [{player.queue.count}]",
                value=f"Next: {player.queue._items[0] if player.queue else 'None'}",
            )
            .add_field(
                name="Requested by",
                value=f"{player.ctx.author.mention} in {player.ctx.channel.mention}",  # type: ignore
            )
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
            try:
                r = await asyncio.wait_for(player.queue.get_wait(), timeout=3 * 60)
            except asyncio.TimeoutError:
                await player.disconnect()
                return
            else:
                if not player.playing:
                    await player.play(r)

    @commands.command()
    @in_voice_channel(user=True)
    @try_connect(cls=Player)
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
            added = 0
            for track in tracks:
                track.extras = {"requester_id": ctx.author.id}
                await ctx.voice_client.queue.put_wait(track)
                added += 1

            await ctx.reply(f"Added the playlist **`{tracks.name}`** ({added} songs) to the queue.")
        else:
            track: wavelink.Playable = tracks[0]

            track.extras = {"requester_id": ctx.author.id}

            await ctx.voice_client.queue.put_wait(track)
            await ctx.reply(f"Added **`{track}`** to the queue.")

        if not ctx.voice_client.playing:
            await ctx.voice_client.play(ctx.voice_client.queue.get())

    @commands.command()
    @in_voice_channel(user=True)
    @try_connect(cls=Player)
    @Context.with_typing
    async def search(self, ctx: Context, *, query: str) -> None:
        """Search for a song with the given query."""
        tracks: wavelink.Search = await wavelink.Playable.search(query)
        if not tracks:
            await ctx.reply(f"{ctx.author.mention} - Could not find any tracks with that query. Please try again.")
            return

        st = ""
        for index, track in enumerate(tracks, start=1):
            track.extras = {"requester_id": ctx.author.id}

            if track.uri:
                st += f"{index}. [{track.title}](<{track.uri})>) by {track.author}\n"
            else:
                st += f"{index}. {track.title} by {track.author}\n"

            if index >= 10:
                break

        await ctx.reply(st)
        msg = await ctx.send("Please select a song by typing the number of the song you want to play.")

        while True:
            try:
                response = await ctx.bot.wait_for("message", check=lambda m: m.author == ctx.author, timeout=30.0)
            except asyncio.TimeoutError:
                await msg.delete(delay=0)
                await msg.add_reaction("\N{ALARM CLOCK}")
                return

            if not response.content.isdigit():
                continue

            index = int(response.content) - 1
            if index < 0 or index >= len(tracks):
                continue

            await msg.delete(delay=0)
            return await self.play(ctx, query=f"{tracks[index].title} {tracks[index].author}")

    @commands.command()
    @in_voice_channel(bot=True, user=True, same=True)
    async def skip(self, ctx: Context) -> None:
        """Skip the current song."""
        await ctx.voice_client.skip(force=True)
        await ctx.tick()

    @commands.command(name="toggle", aliases=["pause", "resume"])
    @in_voice_channel(bot=True, user=True, same=True)
    async def pause_resume(self, ctx: Context) -> None:
        """Pause or Resume the Player depending on its current state."""

        await ctx.voice_client.pause(not ctx.voice_client.paused)
        await ctx.tick()

    @commands.command(aliases=["dc"])
    @in_voice_channel(bot=True, user=True, same=True)
    async def disconnect(self, ctx: Context) -> None:
        """Disconnect the Player."""
        await ctx.voice_client.disconnect()
        await ctx.tick()

    @commands.command()
    @in_voice_channel(bot=True, user=True, same=True)
    async def volume(self, ctx: Context, *, percentage: float) -> None:
        """Set the volume of the Player."""
        await ctx.voice_client.set_volume(int(percentage * 10))
        await ctx.tick()

    @commands.command(name="nowplaying", aliases=["np", "current", "currentsong"])
    @in_voice_channel(bot=True, user=True, same=True)
    async def now_playing(self, ctx: Context) -> None:
        """Show the currently playing song."""
        await ctx.reply(embed=self.playing_embed(ctx.voice_client))

    @commands.command(name="stop")
    @in_voice_channel(bot=True, user=True, same=True)
    async def stop(self, ctx: Context) -> None:
        """Stop the Player and clear the queue."""
        ctx.voice_client.queue.clear()
        await ctx.voice_client.stop(force=True)
        await ctx.tick()

    @commands.command()
    @in_voice_channel(bot=True, user=True, same=True)
    async def queue(self, ctx: Context) -> None:
        """Show the current queue."""
        queue = ctx.voice_client.queue
        if not queue:
            await ctx.reply("The queue is currently empty.")
            return

        st = f"**Queue [{queue.count}]**\n\n"
        for index, track in enumerate(queue):
            member = ctx.guild.get_member(track.extras.requester_id)

            if track.uri:
                st += f"{index + 1}. [{track.title}](<{track.uri}>)\n by {track.author} - Requested by {member or 'N/A'}\n"
            else:
                st += f"{index + 1}. {track.title} by {track.author} - Requested by {member or 'N/A'}\n"

            if len(st) > 1900:
                break

        await ctx.reply(st)

    @commands.command()
    @in_voice_channel(bot=True, user=True, same=True)
    @Context.dj_only()
    async def clear(self, ctx: Context) -> None:
        """Clear the current queue."""
        prompt = await ctx.prompt("Are you sure you want to clear the queue?")
        if not prompt:
            return
        ctx.voice_client.queue.clear()

    @commands.command()
    @in_voice_channel(bot=True, user=True, same=True)
    @Context.with_typing
    async def lyrics(self, ctx: Context) -> None:
        """Show the lyrics of the currently playing song."""
        node = ctx.voice_client.node
        if ctx.voice_client.current is None:
            await ctx.reply("There is currently no song playing.")
            return

        path = f"v4/sessions/{node.session_id}/players/{ctx.guild.id}/lyrics"
        try:
            data: dict = await node.send("GET", path=path)
        except (wavelink.LavalinkException, wavelink.NodeException):
            await ctx.reply("There are no lyrics available for this song.")
            return

        paginator = commands.Paginator(prefix="", suffix="", max_size=1900)
        for line in data["lines"]:
            paginator.add_line(line["line"])

        embed = discord.Embed(
            title=f"Lyrics for {ctx.voice_client.current.title}",
        )
        interface = PaginatorEmbedInterface(ctx.bot, paginator, owner=ctx.author, embed=embed)
        await interface.send_to(ctx)

    @commands.command()
    @in_voice_channel(bot=True, user=True, same=True)
    async def seek(self, ctx: Context, *, seek: str) -> None:
        """Seek to a specific time in the current song. Supports + and - for relative seeking.

        Examples:
        - `seek 30` - Seeks to 30 seconds.
        - `seek +10` - Seeks 10 seconds forward.
        - `seek -10` - Seeks 10 seconds backward.
        """
        if ctx.voice_client.current is None:
            await ctx.reply("There is currently no song playing.")
            return

        if seek.startswith("+"):
            seconds = ctx.voice_client.position + int(seek[1:])
        elif seek.startswith("-"):
            seconds = ctx.voice_client.position - int(seek[1:])
        else:
            seconds = int(seek)

        if seconds < 0:
            seconds = 0
        elif seconds > ctx.voice_client.current.length:
            seconds = ctx.voice_client.current.length

        await ctx.voice_client.seek(seconds * 1000)
        timestamp = f"{ctx.voice_client.position // 60000}:{(ctx.voice_client.position // 1000) % 60:02d}"
        duration_graph = ctx.voice_client.position / ctx.voice_client.current.length
        duration_bar = "\N{BLACK RECTANGLE}" * 20
        duration_bar = (
            duration_bar[: int(duration_graph * 20)] + "\N{RADIO BUTTON}" + duration_bar[int(duration_graph * 20) + 1 :]
        )
        await ctx.reply(
            f"Seeked to {timestamp}/{ctx.voice_client.current.length // 60000}:{(ctx.voice_client.current.length // 1000) % 60:02d}\n`{duration_bar}`"
        )


async def setup(bot: Bot) -> None:
    await bot.add_cog(Music(bot))
