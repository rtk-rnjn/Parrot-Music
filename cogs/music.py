from __future__ import annotations

import asyncio
import re
from time import time
from typing import cast

import discord
import wavelink
from discord.ext import commands
from jishaku.paginators import PaginatorEmbedInterface

from core import Bot, Cog, Context
from utils import CONFIG, in_voice_channel, try_connect


class Player(wavelink.Player):
    ctx: Context
    home: discord.TextChannel | discord.VoiceChannel
    main_message: discord.Message

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

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

        await wavelink.Pool.connect(nodes=[node], client=self.bot, cache_capacity=100)

    async def cog_unload(self) -> None:
        await wavelink.Pool.close()

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

        duration_graph = player.position / playable.length
        duration_bar = "\N{BLACK RECTANGLE}" * 20
        duration_bar = (
            duration_bar[: int(duration_graph * 20)] + "\N{RADIO BUTTON}" + duration_bar[int(duration_graph * 20) + 1 :]
        )

        timestamp = f"{player.position // 60000}:{(player.position // 1000) % 60:02d}"
        embed = (
            discord.Embed(
                description=description,
                timestamp=discord.utils.utcnow(),
            )
            .set_author(name=f"Author: {playable.author}")
            .add_field(
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
                value="Yes" if player.queue.mode.value in {1, 2} else "No",
            )
            .add_field(
                name=f"Queue [{player.queue.count or 'Empty'}]",
                value=f"Next: {player.queue._items[0] if player.queue else 'None'}",
            )
            .add_field(
                name="Requested by",
                value=f"{player.ctx.author.mention}",
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

        msg = await player.home.send(embed=embed)
        player.main_message = msg

    @Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload) -> None:
        print(f"[BOT] Node {payload.node.identifier} is ready!")

    @Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload) -> None:
        player: Player | None = cast(Player, payload.player)
        if player is None:
            return

        if player.channel.guild.id in self.skip_request:
            await self.skip_request[player.channel.guild.id].delete(delay=0)
            self.skip_request.pop(player.channel.guild.id)

        if hasattr(player, "main_message"):
            await player.main_message.delete(delay=0)

        if not player.queue:
            try:
                r = await asyncio.wait_for(player.queue.get_wait(), timeout=3 * 60)
            except asyncio.TimeoutError:
                await player.disconnect()
                return
            else:
                if not player.playing:
                    await player.play(r)

    @commands.command(aliases=["connect"])
    @commands.max_concurrency(1, per=commands.BucketType.guild)
    @in_voice_channel(user=True, bot=False)
    async def join(self, ctx: Context) -> None:
        """Join the voice channel of the author. You must be in a voice channel to use this command.

        If bot is already connected somewhere else and the author is in a different channel, also the author is a DJ, it will ask if you want to move the player to your channel.
        """
        assert ctx.author.voice

        if not ctx.author.voice.channel:
            return

        if ctx.voice_client and ctx.voice_client.channel == ctx.author.voice.channel:
            await ctx.reply("Bot is already in a voice channel.", delete_after=10)
            return

        if ctx.voice_client:
            warning = ""
            if ctx.voice_client.playing:
                warning = "The player is currently playing in another channel."
            msg = await ctx.reply(
                f"Bot is already connected to `{ctx.voice_client.channel.name}`. {warning}",
                delete_after=10,
            )
            if await ctx.is_dj():
                prompt = await ctx.prompt(
                    f"{msg.content.strip()} Do you want to move the player to your channel?",
                    delete_after=True,
                    message=msg,
                )
                if not prompt:
                    return

                await ctx.voice_client.move_to(ctx.author.voice.channel)
                await ctx.reply(f"Moved the player to {ctx.author.voice.channel.mention}.")
                await ctx.tick()
            return

        try:
            player = await ctx.author.voice.channel.connect(cls=Player)  # type: ignore
            player.home = ctx.channel  # type: ignore
            player.ctx = ctx
            await ctx.tick()
        except discord.ClientException:
            await ctx.reply("Failed connecting to channel", delete_after=10)

    @commands.command()
    @in_voice_channel(user=True, bot=True, same=False)
    @commands.max_concurrency(1, per=commands.BucketType.guild)
    @Context.dj_only()
    async def move(self, ctx: Context, *, channel: discord.VoiceChannel | None = None) -> None:
        """Move the bot to the voice channel of the author. You and the bot must be in a voice channel to use this command.

        If the bot is already in the author's channel, it will ask if you want to move the player to your channel.
        """
        assert ctx.author.voice and ctx.author.voice.channel

        if not (channel or ctx.author.voice.channel):
            return

        warning = ""
        if ctx.voice_client.playing:
            warning = "The player is currently playing in another channel. "

        if ctx.voice_client and ctx.voice_client.channel == (channel or ctx.author.voice.channel):
            await ctx.reply(
                f"Bot is already in {channel.mention if channel else ctx.author.voice.channel.mention}.",
                delete_after=10,
            )
            return

        if not ctx.voice_client:
            await ctx.reply("Bot is not in a voice channel.", delete_after=10)
            return

        prompt = await ctx.prompt(
            f"Bot is currently connected to {ctx.voice_client.channel.mention}. {warning}Do you want to move the player to your channel?",
            delete_after=True,
        )
        if not prompt:
            return

        await ctx.voice_client.move_to(channel or ctx.author.voice.channel)
        await ctx.reply(f"Moved the player to {ctx.author.voice.channel.mention}.")
        await ctx.tick()

    @commands.command()
    @commands.max_concurrency(1, per=commands.BucketType.guild)
    @in_voice_channel(user=True)
    @try_connect(cls=Player)
    async def play(self, ctx: Context, *, query: str) -> None:
        """Play a song with the given query. The best song which matches the query will be played. You must be in a voice channel to use this command.

        Consider using the `search` command to select a song from the search results.

        If the bot is not connected to a voice channel, it will try to connect to the author's channel.
        """

        if ctx.voice_client.home != ctx.channel:
            await ctx.reply(
                f"You can only play songs in {ctx.voice_client.home.mention}, as the player has already started there.",  # type: ignore
                delete_after=10,
            )
            return

        tracks: wavelink.Search = await wavelink.Playable.search(query)
        if not tracks:
            await ctx.reply(
                f"{ctx.author.mention} - Could not find any tracks with that query. Please try again.", delete_after=10
            )
            return

        added = 0

        for track in tracks:
            track.extras = {"requester_id": ctx.author.id}
            await ctx.voice_client.queue.put_wait(track)
            added += 1
            break

        await ctx.reply(f"Added the {added} song(s) to the queue.", delete_after=10)

        if not ctx.voice_client.playing:
            await ctx.voice_client.play(ctx.voice_client.queue.get())

    @commands.command()
    @commands.max_concurrency(1, per=commands.BucketType.guild)
    @in_voice_channel(user=True)
    @try_connect(cls=Player)
    async def playplaylist(self, ctx: Context, *, query: str) -> None:
        """Play a playlist with the given query. You must be in a voice channel to use this command.

        If the bot is not connected to a voice channel, it will try to connect to the author's channel.
        """

        if ctx.voice_client.home != ctx.channel:
            await ctx.reply(
                f"You can only play songs in {ctx.voice_client.home.mention}, as the player has already started there.",  # type: ignore
                delete_after=10,
            )
            return

        tracks: wavelink.Search = await wavelink.Playable.search(query)
        if not tracks:
            await ctx.reply("Could not find any tracks with that query. Please try again.", delete_after=10)
            return

        added = 0

        if not isinstance(tracks, wavelink.Playlist):
            await ctx.reply("The query is not a playlist.", delete_after=10)
            return

        for track in tracks:
            track.extras = {"requester_id": ctx.author.id}
            await ctx.voice_client.queue.put_wait(track)
            added += 1

        await ctx.reply(f"Added the {added} song(s) to the queue.", delete_after=10)

        if not ctx.voice_client.playing:
            await ctx.voice_client.play(ctx.voice_client.queue.get())

    @commands.command()
    @commands.max_concurrency(1, per=commands.BucketType.guild)
    @in_voice_channel(user=True, bot=True, same=True)
    @Context.with_typing
    async def search(self, ctx: Context, *, query: str) -> None:
        """Search for a song with the given query. You and the bot must be in same voice channel to use this command.

        The bot will show the top 10 results and ask you to select a song by typing the number of the song you want to play.
        """
        tracks: wavelink.Search = await wavelink.Playable.search(query)
        if not tracks:
            await ctx.reply(f"{ctx.author.mention} - Could not find any tracks with that query. Please try again.")
            return

        st = ""
        for index, track in enumerate(tracks, start=1):
            track.extras = {"requester_id": ctx.author.id}

            if track.uri:
                st += f"{index}. [{track.title}](<{track.uri}>) by {track.author}\n"
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

    skip_request: dict[int, discord.Message] = {}

    @commands.command()
    @commands.max_concurrency(1, per=commands.BucketType.guild)
    @in_voice_channel(bot=True, user=True, same=True)
    async def skip(self, ctx: Context) -> None:
        """Skip the current song. You and the bot must be in the same voice channel to use this command.

        If the author is a DJ, the bot will skip the current song without any votes.

        To skip a song without being a DJ, you must have more than 50% of the members in the voice channel to vote to skip the song.
        """
        if ctx.is_dj():
            await ctx.voice_client.skip(force=True)
            await ctx.tick()
            self.skip_request.pop(ctx.guild.id, None)
            return

        assert ctx.author.voice and ctx.author.voice.channel

        members = ctx.author.voice.channel.members

        assert len(members) > 3

        count = 1

        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            return user in members and reaction.emoji in {
                "\N{WHITE HEAVY CHECK MARK}",
                "\N{NEGATIVE SQUARED CROSS MARK}",
            }

        message = f"{ctx.author.mention} wants to skip the current song. React with \N{WHITE HEAVY CHECK MARK} to vote to skip the song."
        msg = await ctx.reply(
            f"{message} {count}/{len(members) // 2} votes are required to skip the song.",
        )

        self.skip_request[ctx.guild.id] = msg

        await msg.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        await msg.add_reaction("\N{NEGATIVE SQUARED CROSS MARK}")

        now = time() + (ctx.voice_client.position / 1000) - 1
        while count < len(members) // 2 and time() < now:
            try:
                reaction, _ = await ctx.bot.wait_for("reaction_add", check=check)
            except asyncio.TimeoutError:
                await msg.delete(delay=0)
                await ctx.add_reaction(["\N{ALARM CLOCK}"], message=msg, raise_exception=False)
                return

            count += 1
            await msg.edit(content=f"{message} {count}/{len(members) // 2} votes are required to skip the song.")

        if count >= len(members) // 2 and self.skip_request.get(ctx.guild.id):
            await ctx.voice_client.skip(force=True)
            await ctx.tick()
            self.skip_request.pop(ctx.guild.id, None)
            return

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
    async def volume(self, ctx: Context, *, percentage: str) -> None:
        """Set the volume of the Player. The volume must be between 0 and 100. Also supports + and - for relative volume changes.

        Examples:
        - `volume 50` - Sets the volume to 50%.
        - `volume +10` - Increases the volume by 10%.
        - `volume -10` - Decreases the volume by 10%.
        """
        if not re.match(r"(\+|-)?\d+(\.\d+)?", percentage):
            await ctx.reply("Invalid volume percentage. Please provide a valid percentage.", delete_after=10)
            return

        if percentage.startswith("+"):
            vol = ctx.voice_client.volume + int(float(percentage[1:]) * 10)
        elif percentage.startswith("-"):
            vol = ctx.voice_client.volume - int(float(percentage[1:]) * 10)
        else:
            vol = int(float(percentage) * 10)

        await ctx.voice_client.set_volume(vol)
        await ctx.tick()

    @commands.command()
    @in_voice_channel(bot=True, user=True, same=True)
    async def shuffle(self, ctx: Context) -> None:
        """Shuffle the queue."""
        ctx.voice_client.queue.shuffle()
        await ctx.tick()

    @commands.command(name="nowplaying", aliases=["np", "current", "currentsong"])
    @in_voice_channel(bot=True, user=True, same=True)
    async def now_playing(self, ctx: Context) -> None:
        """Show the currently playing song."""
        embed = self.playing_embed(ctx.voice_client)
        msg = await ctx.reply(embed=embed)
        if embed.description == "_There is currently no song playing._":
            await msg.delete(delay=10)
        else:
            if hasattr(ctx.voice_client, "main_message"):
                await ctx.voice_client.main_message.delete(delay=0)
            ctx.voice_client.main_message = msg

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
        prompt = await ctx.prompt("Are you sure you want to clear the queue?", delete_after=True)
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
            await ctx.reply("There are no lyrics available for this song.", delete_after=10)
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
        if not re.match(r"(\+|-)?\d+(\.\d+)?", seek):
            await ctx.reply("Invalid seek time. Please provide a valid time.", delete_after=10)
            return

        if ctx.voice_client.current is None:
            await ctx.reply("There is currently no song playing.", delete_after=10)
            return

        if seek.startswith("+"):
            seconds = ctx.voice_client.position + int(float(seek[1:]) * 1000)
        elif seek.startswith("-"):
            seconds = ctx.voice_client.position - int(float(seek[1:]) * 1000)
        else:
            seconds = int(float(seek) * 1000)

        seconds = max(0, min(seconds, ctx.voice_client.current.length))

        await ctx.voice_client.seek(int(seconds))
        timestamp = f"{ctx.voice_client.position // 60000}:{(ctx.voice_client.position // 1000) % 60:02d}"
        duration_graph = ctx.voice_client.position / ctx.voice_client.current.length
        duration_bar = "\N{BLACK RECTANGLE}" * 20
        duration_bar = (
            duration_bar[: int(duration_graph * 20)] + "\N{RADIO BUTTON}" + duration_bar[int(duration_graph * 20) + 1 :]
        )
        await ctx.reply(
            f"Seeked to {timestamp}/{ctx.voice_client.current.length // 60000}:{(ctx.voice_client.current.length // 1000) % 60:02d}\n`{duration_bar}`"
        )

    @commands.command()
    @in_voice_channel(bot=True, user=True, same=True)
    @Context.dj_only()
    async def loop(self, ctx: Context) -> None:
        """Loop the current song. This will toggle the loop state of the player."""
        if ctx.voice_client.queue.count:
            prompt = await ctx.prompt(
                "Do you want to loop the current song? Deny to loop entire Queue", delete_after=True
            )
            if not prompt:
                ctx.voice_client.queue.mode = wavelink.QueueMode.loop_all
            else:
                ctx.voice_client.queue.mode = wavelink.QueueMode.loop
        else:
            ctx.voice_client.queue.mode = wavelink.QueueMode.loop
        await ctx.tick()


async def setup(bot: Bot) -> None:
    await bot.add_cog(Music(bot))
