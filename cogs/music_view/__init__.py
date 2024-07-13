from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from cogs.music import Music, Player
    from core import Context


class MusicView(discord.ui.View):
    message: discord.Message | None

    def __init__(self, timeout: float, ctx: Context):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.music_cog: Music = ctx.bot.get_cog("Music")  # type: ignore

    def disable_all(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button) and not child.disabled:
                child.disabled = True

    async def on_timeout(self) -> None:
        if self.message:
            await self.message.edit(view=self)

    async def interaction_check(self, interaction: discord.Interaction[discord.Client]) -> bool:
        if interaction.user.id == self.ctx.author.id:
            return True
        await interaction.response.send_message(
            "You are not allowed to interact with this view", ephemeral=True
        )
        return False

    @discord.ui.button(
        style=discord.ButtonStyle.primary,
        emoji="\N{BLACK RIGHT-POINTING TRIANGLE WITH DOUBLE VERTICAL BAR}",
    )
    async def play(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)
        player: Player = self.ctx.voice_client
        await player.pause(not player.paused)

        await interaction.followup.send(
            f"Music {'paused' if player.paused else 'resumed'}", ephemeral=True
        )

    @discord.ui.button(style=discord.ButtonStyle.danger, emoji="\N{BLACK SQUARE FOR STOP}")
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)
        player: Player = self.ctx.voice_client
        if await self.ctx.is_dj():
            player.queue.clear()
            await player.stop()
        else:
            await interaction.followup.send("You are not a DJ", ephemeral=True)

        await interaction.followup.send("Music stopped", ephemeral=True)

    @discord.ui.button(
        style=discord.ButtonStyle.secondary,
        emoji="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}",
    )
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer(ephemeral=True)
        await self.music_cog.skip(self.ctx)

    @discord.ui.button(style=discord.ButtonStyle.danger, emoji="\N{WAVING HAND SIGN}")
    async def disconnect(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        # TODO
        await interaction.response.edit_message(view=self)

    @discord.ui.button(
        label="Volume",
        style=discord.ButtonStyle.secondary,
        emoji="\N{UPWARDS BLACK ARROW}",
        row=1,
    )
    async def volume_up(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        # TODO
        await interaction.response.edit_message(view=self)

    @discord.ui.button(
        label="Volume",
        style=discord.ButtonStyle.secondary,
        emoji="\N{DOWNWARDS BLACK ARROW}",
        row=1,
    )
    async def volume_down(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        # TODO
        await interaction.response.edit_message(view=self)
