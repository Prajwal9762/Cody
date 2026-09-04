"""Welcome and farewell cog managing greet messages, leave alerts, and autoroles."""

import logging
import discord
from discord.ext import commands

from utils.embeds import create_base_embed
from config import config

logger = logging.getLogger("AllInOneBot.Welcome")


class Welcome(commands.Cog):
    """Handles member entry and exit events."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _format_message(self, template: str, member: discord.Member) -> str:
        """Format dynamic variables in message templates."""
        return (
            template.replace("{user}", member.mention)
            .replace("{username}", member.name)
            .replace("{server}", member.guild.name)
            .replace("{count}", str(member.guild.member_count))
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Process incoming member joins."""
        guild = member.guild
        guild_conf = await self.bot.db.repo.get_guild_config(guild.id)

        # 1. Assign Auto-Role if configured
        autorole_id = guild_conf.get("autorole_id")
        if autorole_id:
            role = guild.get_role(autorole_id)
            if role:
                try:
                    await member.add_roles(role, reason="Auto-Role on member join")
                except discord.HTTPException as e:
                    logger.error("Failed to assign auto-role in %s: %s", guild.id, e)

        # 2. Send Welcome Message
        channel_id = guild_conf.get("welcome_channel_id")
        if not channel_id:
            return

        channel = guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return

        raw_template = guild_conf.get("welcome_message") or "Welcome to {server}, {user}!"
        formatted_text = self._format_message(raw_template, member)

        embed = create_base_embed(
            title=f"👋 Welcome to {guild.name}!",
            description=formatted_text,
            color=config.COLORS.SUCCESS,
        )
        if member.display_avatar:
            embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="Member Count", value=f"#{guild.member_count}", inline=True)

        try:
            await channel.send(content=member.mention, embed=embed)
        except discord.HTTPException as e:
            logger.error("Could not send welcome message: %s", e)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        """Process member departures."""
        guild = member.guild
        guild_conf = await self.bot.db.repo.get_guild_config(guild.id)

        channel_id = guild_conf.get("leave_channel_id")
        if not channel_id:
            return

        channel = guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return

        raw_template = guild_conf.get("leave_message") or "{user} has left {server}."
        formatted_text = self._format_message(raw_template, member)

        embed = create_base_embed(
            title="👋 Member Left",
            description=formatted_text,
            color=config.COLORS.NEUTRAL,
        )
        if member.display_avatar:
            embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "Unknown", inline=True)
        embed.add_field(name="Current Members", value=str(guild.member_count), inline=True)

        try:
            await channel.send(embed=embed)
        except discord.HTTPException as e:
            logger.error("Could not send farewell message: %s", e)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Welcome(bot))
