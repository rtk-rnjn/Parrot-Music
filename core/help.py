from __future__ import annotations
from typing import Any, Mapping, TYPE_CHECKING

import discord
from discord.ext import commands
import inspect

if TYPE_CHECKING:
    from cog import Cog


class HelpCommand(commands.HelpCommand):

    def __init__(self):
        super().__init__()
        self.command_attrs["hidden"] = True

    async def send_bot_help(self, mapping: Mapping[Cog | None, list[commands.Command[Any, ..., Any]]]) -> None:
        embed = discord.Embed(title="Help", color=discord.Color.blurple())
        desc = inspect.cleandoc(
            """
            Welcome to the help command! This is a simple Music bot that can play music from any platform.

            How to help yourself?
            - `!help` - Shows this message.
            - `!help <command>` - Shows help for a specific command.
            - `!help <category>` - Shows help for a specific category.

            Some commands are grouped as well.
            - `!help <command> <subcommand>` - Shows help for a specific subcommand.

            If you need more help, feel free to join the support server or contact the developer.
            """
        )
        embed.description = desc

        for cog, cmds in mapping.items():
            if not cog:
                continue

            if sum(not cmd.hidden for cmd in cmds) == 0:
                continue

            assert len(cmds) > 0

            name = f"{cog.qualified_name.upper()} [{len(cmds)}]"
            desc = cog.description or "No description available."
            embed.add_field(name=name, value=desc)

        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog: Cog) -> None:
        embed = discord.Embed(title=f"{cog.qualified_name.upper()} Help", color=discord.Color.blurple())
        desc = cog.description or "No description available."
        embed.description = desc

        for cmd in cog.get_commands():
            if cmd.hidden:
                continue

            embed.add_field(
                name=cmd.qualified_name,
                value=cmd.short_doc or "No description available.",
            )

        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command: commands.Command[Any, ..., Any]) -> None:
        embed = discord.Embed(title=f"{command.qualified_name} Help", color=discord.Color.blurple())
        desc = command.help or "No description available."
        embed.description = desc

        if command.aliases:
            embed.add_field(name="Aliases", value=", ".join(command.aliases))
        
        if command.signature:
            embed.add_field(name="Syntax", value=f"`{self.context.prefix}{command.qualified_name} {command.signature}`")

        await self.get_destination().send(embed=embed)
    
    async def send_group_help(self, group: commands.Group[Any, ..., Any]) -> None:
        embed = discord.Embed(title=f"{group.qualified_name} Help", color=discord.Color.blurple())
        desc = group.help or "No description available."
        embed.description = desc

        for cmd in group.commands:
            if cmd.hidden:
                continue

            embed.add_field(
                name=cmd.qualified_name,
                value=cmd.short_doc or "No description available.",
            )

        await self.get_destination().send(embed=embed)
