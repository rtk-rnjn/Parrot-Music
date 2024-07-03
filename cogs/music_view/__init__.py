from __future__ import annotations

import discord


class MusicView(discord.ui.View):
    message: discord.Message | None

    def __init__(self, timeout: float):
        super().__init__(timeout=timeout)

    def disable_all(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button) and not child.disabled:
                child.disabled = True

    async def on_timeout(self) -> None:
        if self.message:
            await self.message.edit(view=self)

    @discord.ui.button(
        label="Play",
        style=discord.ButtonStyle.primary,
        emoji="\N{BLACK RIGHT-POINTING TRIANGLE WITH DOUBLE VERTICAL BAR}",
    )
    async def play(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        button.label = "Pause"
        # TODO
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger, emoji="\N{BLACK SQUARE FOR STOP}")
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        # TODO
        await interaction.response.edit_message(view=self)

    @discord.ui.button(
        label="Skip", style=discord.ButtonStyle.secondary, emoji="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}"
    )
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        # TODO
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Disconnect", style=discord.ButtonStyle.danger, emoji="\N{WAVING HAND SIGN}")
    async def disconnect(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        # TODO
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Volume", style=discord.ButtonStyle.secondary, emoji="\N{UPWARDS BLACK ARROW}", row=1)
    async def volume_up(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        # TODO
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Volume", style=discord.ButtonStyle.secondary, emoji="\N{DOWNWARDS BLACK ARROW}", row=1)
    async def volume_down(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        # TODO
        await interaction.response.edit_message(view=self)
