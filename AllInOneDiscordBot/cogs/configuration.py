"""Guild configuration commands for customizing channels, roles, messages, and multipliers."""

import logging
import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import create_base_embed, success_embed, info_embed
from utils.checks import is_guild_admin
from config import config

logger = logging.getLogger("AllInOneBot.Configuration")


class Configuration(commands.Cog):
    """Server setup and administrative configuration cog."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    config_group = app_commands.Group(name="config", description="Configure server settings and channels")

    # -------------------------------------------------------------------------
    # VIEW CONFIG
    # -------------------------------------------------------------------------
    @config_group.command(name="view", description="View current server configuration and channel bindings.")
    @app_commands.default_permissions(administrator=True)
    @is_guild_admin()
    async def view(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        cfg = await self.bot.db.repo.get_guild_config(guild.id)

        embed = create_base_embed(
            title=f"⚙️ Configuration • {guild.name}",
            color=config.COLORS.PRIMARY,
        )

        def ch_fmt(cid: int | None) -> str:
            if not cid:
                return "*Not Set*"
            ch = guild.get_channel(cid)
            return ch.mention if ch else f"`Deleted ({cid})`"

        def role_fmt(rid: int | None) -> str:
            if not rid:
                return "*Not Set*"
            r = guild.get_role(rid)
            return r.mention if r else f"`Deleted ({rid})`"

        embed.add_field(name="🛡️ Mod Log Channel", value=ch_fmt(cfg.get("mod_log_channel_id")), inline=True)
        embed.add_field(name="📜 Server Audit Logs", value=ch_fmt(cfg.get("server_log_channel_id")), inline=True)
        embed.add_field(name="🎫 Ticket Category", value=ch_fmt(cfg.get("ticket_category_id")), inline=True)

        embed.add_field(name="👋 Welcome Channel", value=ch_fmt(cfg.get("welcome_channel_id")), inline=True)
        embed.add_field(name="🚪 Farewell Channel", value=ch_fmt(cfg.get("leave_channel_id")), inline=True)
        embed.add_field(name="🎭 Join Auto-Role", value=role_fmt(cfg.get("autorole_id")), inline=True)

        embed.add_field(name="🎉 Level-Up Channel", value=ch_fmt(cfg.get("level_up_channel_id")), inline=True)
        embed.add_field(name="📈 XP Multiplier", value=f"`{cfg.get('xp_rate', 1.0)}x`", inline=True)
        automod_status = "Enabled" if cfg.get("automod_enabled", 1) else "Disabled"
        embed.add_field(name="🤖 AutoMod Global", value=f"`{automod_status}`", inline=True)

        embed.add_field(
            name="Welcome Message Template",
            value=f"```\n{cfg.get('welcome_message') or 'Default'}\n```",
            inline=False,
        )

        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------------------------------
    # WELCOME & LEAVE
    # -------------------------------------------------------------------------
    @config_group.command(name="welcome", description="Configure welcome channel and optional greeting text.")
    @app_commands.describe(
        channel="Channel to broadcast welcome cards in",
        message="Template: use {user}, {server}, {count}",
    )
    @app_commands.default_permissions(administrator=True)
    @is_guild_admin()
    async def set_welcome(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: str | None = None,
    ) -> None:
        updates = {"welcome_channel_id": channel.id}
        if message:
            updates["welcome_message"] = message

        await self.bot.db.repo.update_guild_config(interaction.guild.id, **updates)
        await interaction.response.send_message(
            embed=success_embed(
                "Welcome Channel Set",
                f"New members will be greeted in {channel.mention}."
                + (f"\n**Message:**\n`{message}`" if message else ""),
            )
        )

    @config_group.command(name="leave", description="Configure leave/farewell channel.")
    @app_commands.describe(channel="Channel for leave notices", message="Template message")
    @app_commands.default_permissions(administrator=True)
    @is_guild_admin()
    async def set_leave(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: str | None = None,
    ) -> None:
        updates = {"leave_channel_id": channel.id}
        if message:
            updates["leave_message"] = message

        await self.bot.db.repo.update_guild_config(interaction.guild.id, **updates)
        await interaction.response.send_message(
            embed=success_embed("Farewell Channel Set", f"Departure alerts will be sent in {channel.mention}.")
        )

    # -------------------------------------------------------------------------
    # LOGGING CHANNELS
    # -------------------------------------------------------------------------
    @config_group.command(name="modlog", description="Set channel for moderation logs (kicks, bans, warns).")
    @app_commands.describe(channel="Moderation logs channel")
    @app_commands.default_permissions(administrator=True)
    @is_guild_admin()
    async def set_modlog(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        await self.bot.db.repo.update_guild_config(interaction.guild.id, mod_log_channel_id=channel.id)
        await interaction.response.send_message(
            embed=success_embed("Mod Log Channel Set", f"Moderation cases will be dispatched to {channel.mention}.")
        )

    @config_group.command(name="serverlog", description="Set channel for server audit logs (edits, deletes).")
    @app_commands.describe(channel="Server audit log channel")
    @app_commands.default_permissions(administrator=True)
    @is_guild_admin()
    async def set_serverlog(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        await self.bot.db.repo.update_guild_config(interaction.guild.id, server_log_channel_id=channel.id)
        await interaction.response.send_message(
            embed=success_embed("Server Log Channel Set", f"Server events will be dispatched to {channel.mention}.")
        )

    # -------------------------------------------------------------------------
    # TICKETS & AUTOROLE
    # -------------------------------------------------------------------------
    @config_group.command(name="tickets", description="Set category under which support ticket channels are created.")
    @app_commands.describe(category="Target category")
    @app_commands.default_permissions(administrator=True)
    @is_guild_admin()
    async def set_ticket_category(
        self, interaction: discord.Interaction, category: discord.CategoryChannel
    ) -> None:
        await self.bot.db.repo.update_guild_config(interaction.guild.id, ticket_category_id=category.id)
        await interaction.response.send_message(
            embed=success_embed("Ticket Category Set", f"New tickets will be generated under **{category.name}**.")
        )

    @config_group.command(name="autorole", description="Set a role assigned to new members upon joining.")
    @app_commands.describe(role="Role to grant automatically")
    @app_commands.default_permissions(administrator=True)
    @is_guild_admin()
    async def set_autorole(self, interaction: discord.Interaction, role: discord.Role) -> None:
        if role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                embed=info_embed("Hierarchy Notice", "Ensure my bot role is higher than this role so I can assign it."),
                ephemeral=True,
            )
        await self.bot.db.repo.update_guild_config(interaction.guild.id, autorole_id=role.id)
        await interaction.response.send_message(
            embed=success_embed("Auto-Role Configured", f"New members will automatically receive {role.mention}.")
        )

    @config_group.command(name="xprate", description="Adjust server-wide experience multiplier.")
    @app_commands.describe(rate="XP multiplier (e.g., 1.0, 1.5, 2.0)")
    @app_commands.default_permissions(administrator=True)
    @is_guild_admin()
    async def set_xprate(
        self, interaction: discord.Interaction, rate: app_commands.Range[float, 0.1, 5.0]
    ) -> None:
        await self.bot.db.repo.update_guild_config(interaction.guild.id, xp_rate=rate)
        await interaction.response.send_message(
            embed=success_embed("XP Rate Updated", f"Server XP rate is now set to **{rate}x**.")
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Configuration(bot))
