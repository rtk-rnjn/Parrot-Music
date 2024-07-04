from __future__ import annotations

import discord
from typing import cast
import wavelink
from time import time
from core import Context, Bot
import asyncio

class MusicView(discord.ui.View):
    message: discord.Message | None
    ctx: Context
    bot: Bot
    def __init__(self, timeout: float):
        super().__init__(timeout=timeout)

    def disable_all(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button) and not child.disabled:
                child.disabled = True

    async def on_timeout(self) -> None:
        if self.message:
            await self.message.edit(view=self)

    async def update_button_and_notify(self, button: discord.ui.Button, label: str, state: str, emoji: str, interaction: discord.Interaction) -> None:
        button.label = label
        button.emoji = emoji
        await self.message.edit(view=self)
        await interaction.response.send_message(f"{state}", ephemeral=True)

    @discord.ui.button(label="Pause", style=discord.ButtonStyle.primary, emoji="\N{DOUBLE VERTICAL BAR}")
    async def toggle_pause(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        player = cast(wavelink.Player, self.ctx.voice_client)
        if not player.paused:
            await self.update_button_and_notify_(button, "Play", "paused", "\N{BLACK RIGHT-POINTING TRIANGLE}", interaction,)
            await player.pause(True)
        else:
            await self.update_button_and_notify(button, "Pause", "resumed", "\N{DOUBLE VERTICAL BAR}", interaction)
            await player.pause(False)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger, emoji="\N{BLACK SQUARE FOR STOP}")
    async def stop_player(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        player = cast(wavelink.Player, self.ctx.voice_client)
        if player.paused:
            await interaction.response.send_message("Player is not playing any song right now", ephemeral=True)
        else:
            player.cleanup()
            await player.disconnect()
            await interaction.response.send_message("Stopped and cleared the queue", ephemeral=True)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, emoji="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}")
    async def skip_song(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.ctx.voice_client.queue.count == 0:
            await interaction.response.send_message("There are no songs in the queue.", ephemeral=True)
            return
        if self.ctx.is_dj():
            await self.ctx.voice_client.skip(force=True)
            await self.ctx.tick()
            self.bot.music_cog.skip_request.pop(self.ctx.guild.id, None)
            return

        assert self.ctx.author.voice and self.ctx.author.voice.channel
        members = self.ctx.author.voice.channel.members
        assert len(members) > 3
        count = 1

        await self.ctx.defer()
        
        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            return user in members and reaction.emoji in {"\N{WHITE HEAVY CHECK MARK}", "\N{NEGATIVE SQUARED CROSS MARK}"}

        message = f"{self.ctx.author.mention} wants to skip the current song. React with \N{WHITE HEAVY CHECK MARK} to vote to skip the song."
        msg = await self.ctx.reply(f"{message} {count}/{len(members) // 2} votes are required to skip the song.")
        self.bot.music_cog.skip_request[self.ctx.guild.id] = msg
        await msg.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        await msg.add_reaction("\N{NEGATIVE SQUARED CROSS MARK}")

        

        now = time() + (self.ctx.voice_client.position / 1000) - 1
        while count < len(members) // 2 and time() < now:
            try:
                reaction, _ = await self.ctx.bot.wait_for("reaction_add", check=check)
            except asyncio.TimeoutError:
                await msg.delete(delay=0)
                await self.ctx.add_reaction(["\N{ALARM CLOCK}"], message=msg, raise_exception=False)
                return

            count += 1
            await msg.edit(content=f"{message} {count}/{len(members) // 2} votes are required to skip the song.")

        if count >= len(members) // 2 and self.bot.music_cog.skip_request.get(self.ctx.guild.id):
            await self.ctx.voice_client.skip(force=True)
            await self.ctx.tick()
            self.bot.music_cog.skip_request.pop(self.ctx.guild.id, None)

    async def change_volume(self, interaction: discord.Interaction, change: int) -> None:
        player = cast(wavelink.Player, self.ctx.voice_client)
        new_volume = max(10, min(100, player.volume + change))
        if player.volume == new_volume:
            message = "Volume is already at the limit"
            await interaction.response.send_message(message, ephemeral=True)
        else:
            await player.set_volume(new_volume)
            embed = self.message.embeds[0].set_field_at(1, name="Volume", value=f"{new_volume}%")
            await self.message.edit(embed=embed)
            await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Volume Up", style=discord.ButtonStyle.secondary, emoji="\N{UPWARDS BLACK ARROW}", row=1)
    async def volume_up(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.change_volume(interaction, 10)

    @discord.ui.button(label="Volume Down", style=discord.ButtonStyle.secondary, emoji="\N{DOWNWARDS BLACK ARROW}", row=1)
    async def volume_down(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.change_volume(interaction, -10)

    async def change_loop_mode(self, interaction: discord.Interaction, mode: wavelink.QueueMode) -> None:
        player = cast(wavelink.Player, self.ctx.voice_client)
        player.queue.mode = mode
        em = self.message.embeds[0].set_field_at(2, name="Loop mode", value="Yes" if player.queue.mode.value in {1, 2} else "No",)
        await self.message.edit(embed=em)
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Loop", style=discord.ButtonStyle.secondary, emoji="\N{CLOCKWISE DOWNWARDS AND UPWARDS OPEN CIRCLE ARROWS}", row=2)
    async def toggle_loop(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        player = cast(wavelink.Player, self.ctx.voice_client)
        if player.queue.mode == wavelink.QueueMode.normal:
            await self.change_loop_mode(interaction, wavelink.QueueMode.loop_all)
        else:
            await self.change_loop_mode(interaction, wavelink.QueueMode.normal)