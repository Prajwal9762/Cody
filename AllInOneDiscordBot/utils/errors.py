"""Custom exception classes and global slash command error handling."""

import logging
import discord
from discord import app_commands
from utils.embeds import error_embed

logger = logging.getLogger("AllInOneBot.Errors")


class BotError(app_commands.AppCommandError):
    """Base application exception for intentional user-facing errors."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ModerationError(BotError):
    """Raised when a moderation action violates business logic."""
    pass


class HierarchyError(ModerationError):
    """Raised when role hierarchy forbids an action."""
    pass


async def handle_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
) -> None:
    """Unified slash command error responder."""
    # Unwrap original if present
    if isinstance(error, app_commands.CommandInvokeError):
        error = error.original  # type: ignore

    if isinstance(error, app_commands.CommandOnCooldown):
        seconds = int(error.retry_after)
        embed = error_embed(
            "Command On Cooldown",
            f"Please wait `{seconds}` second(s) before trying again."
        )
    elif isinstance(error, app_commands.MissingPermissions):
        missing = ", ".join(f"`{p.replace('_', ' ').title()}`" for p in error.missing_permissions)
        embed = error_embed(
            "Missing Permissions",
            f"You do not possess the required permission(s) to execute this command:\n{missing}"
        )
    elif isinstance(error, app_commands.BotMissingPermissions):
        missing = ", ".join(f"`{p.replace('_', ' ').title()}`" for p in error.missing_permissions)
        embed = error_embed(
            "Bot Missing Permissions",
            f"I cannot execute this action because I am missing required permission(s):\n{missing}\n"
            f"Please ensure my bot role has the required permissions and is moved high in server settings."
        )
    elif isinstance(error, (BotError, ModerationError, HierarchyError)):
        embed = error_embed("Action Denied", str(error))
    elif isinstance(error, app_commands.CheckFailure):
        embed = error_embed("Access Denied", "You do not meet the criteria to run this command.")
    else:
        logger.error(
            "Unhandled command exception in command '%s': %s",
            interaction.command.name if interaction.command else "Unknown",
            error,
            exc_info=error,
        )
        embed = error_embed(
            "Unexpected Error",
            "An unexpected error occurred while executing this command. The issue has been logged."
        )

    try:
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as send_err:
        logger.error("Failed to transmit error message to user: %s", send_err)
