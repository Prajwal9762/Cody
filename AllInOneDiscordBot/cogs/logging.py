"""Server activity logging cog for message edits, deletions, role updates, and channel events."""

import logging
import discord
from discord.ext import commands

from utils.embeds import create_base_embed
from utils.helpers import truncate_string
from config import config

logger = logging.getLogger("AllInOneBot.Logging")


class Logging(commands.Cog):
    """Monitors server events and broadcasts audit logs."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _get_log_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        """Fetch configured server log channel."""
        conf = await self.bot.db.repo.get_guild_config(guild.id)
        cid = conf.get("server_log_channel_id")
        if not cid:
            return None
        channel = guild.get_channel(cid)
        return channel if isinstance(channel, discord.TextChannel) else None

    # -------------------------------------------------------------------------
    # MESSAGE DELETED
    # -------------------------------------------------------------------------
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if not message.guild or message.author.bot:
            return

        channel = await self._get_log_channel(message.guild)
        if not channel:
            return

        embed = create_base_embed(
            title="🗑️ Message Deleted",
            color=config.COLORS.ERROR,
        )
        embed.add_field(name="Author", value=f"{message.author.mention} (`{message.author.id}`)", inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        content = message.content or "*No text content (embed or attachment only)*"
        embed.add_field(name="Content", value=truncate_string(content, 1000), inline=False)

        if message.attachments:
            att_names = ", ".join(f"`{a.filename}`" for a in message.attachments)
            embed.add_field(name="Attachments", value=truncate_string(att_names, 500), inline=False)

        try:
            await channel.send(embed=embed)
        except discord.HTTPException as e:
            logger.error("Failed to send message delete log: %s", e)

    # -------------------------------------------------------------------------
    # MESSAGE EDITED
    # -------------------------------------------------------------------------
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if not before.guild or before.author.bot or before.content == after.content:
            return

        channel = await self._get_log_channel(before.guild)
        if not channel:
            return

        embed = create_base_embed(
            title="✏️ Message Edited",
            color=config.COLORS.INFO,
        )
        embed.add_field(name="Author", value=f"{before.author.mention} (`{before.author.id}`)", inline=True)
        embed.add_field(name="Channel", value=before.channel.mention, inline=True)
        embed.add_field(name="Jump to Message", value=f"[Click Here]({after.jump_url})", inline=True)
        embed.add_field(name="Before", value=truncate_string(before.content or "*None*", 500), inline=False)
        embed.add_field(name="After", value=truncate_string(after.content or "*None*", 500), inline=False)

        try:
            await channel.send(embed=embed)
        except discord.HTTPException as e:
            logger.error("Failed to send message edit log: %s", e)

    # -------------------------------------------------------------------------
    # MEMBER UPDATED (Roles, Nicknames)
    # -------------------------------------------------------------------------
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        channel = await self._get_log_channel(before.guild)
        if not channel:
            return

        # Nickname Change
        if before.nick != after.nick:
            embed = create_base_embed(
                title="👤 Nickname Changed",
                color=config.COLORS.INFO,
            )
            embed.add_field(name="User", value=after.mention, inline=True)
            embed.add_field(name="Before", value=f"`{before.nick or before.name}`", inline=True)
            embed.add_field(name="After", value=f"`{after.nick or after.name}`", inline=True)
            try:
                await channel.send(embed=embed)
            except discord.HTTPException:
                pass

        # Role Changes
        if before.roles != after.roles:
            added = [r.mention for r in after.roles if r not in before.roles]
            removed = [r.mention for r in before.roles if r not in after.roles]
            if added or removed:
                embed = create_base_embed(
                    title="🛡️ Member Roles Updated",
                    color=config.COLORS.PRIMARY,
                )
                embed.add_field(name="User", value=after.mention, inline=True)
                if added:
                    embed.add_field(name="Roles Added", value=" ".join(added), inline=False)
                if removed:
                    embed.add_field(name="Roles Removed", value=" ".join(removed), inline=False)
                try:
                    await channel.send(embed=embed)
                except discord.HTTPException:
                    pass

    # -------------------------------------------------------------------------
    # CHANNEL CREATED / DELETED
    # -------------------------------------------------------------------------
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        log_ch = await self._get_log_channel(channel.guild)
        if not log_ch or log_ch.id == channel.id:
            return

        embed = create_base_embed(
            title="📁 Channel Created",
            color=config.COLORS.SUCCESS,
        )
        embed.add_field(name="Name", value=f"#{channel.name} (`{channel.id}`)", inline=True)
        embed.add_field(name="Type", value=str(channel.type).capitalize(), inline=True)

        try:
            await log_ch.send(embed=embed)
        except discord.HTTPException:
            pass

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        log_ch = await self._get_log_channel(channel.guild)
        if not log_ch or log_ch.id == channel.id:
            return

        embed = create_base_embed(
            title="🗑️ Channel Deleted",
            color=config.COLORS.ERROR,
        )
        embed.add_field(name="Name", value=f"#{channel.name} (`{channel.id}`)", inline=True)
        embed.add_field(name="Type", value=str(channel.type).capitalize(), inline=True)

        try:
            await log_ch.send(embed=embed)
        except discord.HTTPException:
            pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Logging(bot))
