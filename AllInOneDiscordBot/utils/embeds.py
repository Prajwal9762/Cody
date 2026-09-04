"""Discord embed factories providing consistent, elegant visuals."""

from datetime import datetime, timezone
import discord
from config import config


def create_base_embed(
    title: str | None = None,
    description: str | None = None,
    color: int = config.COLORS.PRIMARY,
    timestamp: bool = True,
) -> discord.Embed:
    """Create a standardized base embed with unified styling."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
    )
    if timestamp:
        embed.timestamp = datetime.now(timezone.utc)
    embed.set_footer(text=config.DEFAULT_FOOTER)
    return embed


def success_embed(title: str = "Success", description: str = "") -> discord.Embed:
    """Generate a green success embed."""
    return create_base_embed(
        title=f"✅ {title}",
        description=description,
        color=config.COLORS.SUCCESS,
    )


def error_embed(title: str = "Error", description: str = "") -> discord.Embed:
    """Generate a red error embed."""
    return create_base_embed(
        title=f"❌ {title}",
        description=description,
        color=config.COLORS.ERROR,
    )


def warning_embed(title: str = "Warning", description: str = "") -> discord.Embed:
    """Generate a yellow warning embed."""
    return create_base_embed(
        title=f"⚠️ {title}",
        description=description,
        color=config.COLORS.WARNING,
    )


def info_embed(title: str = "Information", description: str = "") -> discord.Embed:
    """Generate a blue informational embed."""
    return create_base_embed(
        title=f"ℹ️ {title}",
        description=description,
        color=config.COLORS.INFO,
    )


def mod_embed(
    action: str,
    target: discord.User | discord.Member,
    moderator: discord.User | discord.Member,
    reason: str | None = None,
    duration: str | None = None,
    case_id: int | None = None,
) -> discord.Embed:
    """Standardized embed for moderation actions and audit logs."""
    title = f"🔨 Moderation: {action}"
    if case_id:
        title += f" [Case #{case_id}] "

    embed = create_base_embed(
        title=title,
        color=config.COLORS.ERROR if action in ["Ban", "Kick", "Mute"] else config.COLORS.WARNING,
    )
    embed.add_field(name="Target", value=f"{target.mention} (`{target.id}`)", inline=True)
    embed.add_field(name="Moderator", value=f"{moderator.mention} (`{moderator.id}`)", inline=True)
    if duration:
        embed.add_field(name="Duration", value=duration, inline=True)
    embed.add_field(name="Reason", value=reason or "No reason provided.", inline=False)
    if target.display_avatar:
        embed.set_thumbnail(url=target.display_avatar.url)
    return embed
