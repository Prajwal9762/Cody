"""Custom slash command check decorators."""

import discord
from discord import app_commands


def guild_only():
    """Ensure command is only run within a guild."""
    async def predicate(interaction: discord.Interaction) -> bool:
        return interaction.guild is not None
    return app_commands.check(predicate)


def is_guild_moderator():
    """Check if user has kick/ban/manage_messages or Administrator permissions."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return False
        perms = interaction.user.guild_permissions
        return perms.administrator or perms.manage_guild or perms.kick_members or perms.ban_members or perms.manage_messages
    return app_commands.check(predicate)


def is_guild_admin():
    """Check if user has Administrator or Manage Server permissions."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return False
        perms = interaction.user.guild_permissions
        return perms.administrator or perms.manage_guild
    return app_commands.check(predicate)
