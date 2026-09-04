"""Leveling and XP progression system with ranks, leaderboards, and celebratory alerts."""

import logging
import random
import time
import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import info_embed, success_embed, create_base_embed
from utils.helpers import calculate_level, xp_for_level, render_progress_bar, format_number
from utils.checks import is_guild_admin
from config import config

logger = logging.getLogger("AllInOneBot.Levels")


class Levels(commands.Cog):
    """XP and leveling cog."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Award XP on message activity."""
        if message.author.bot or not message.guild or not isinstance(message.author, discord.Member):
            return

        guild = message.guild
        member = message.author
        now = int(time.time())

        user_data = await self.bot.db.repo.get_user_level(guild.id, member.id)

        # 60-second cooldown on XP awards
        if now - user_data["last_xp_time"] < 60:
            return

        guild_conf = await self.bot.db.repo.get_guild_config(guild.id)
        xp_rate = float(guild_conf.get("xp_rate") or 1.0)
        xp_gain = int(random.randint(15, 25) * xp_rate)

        new_total_xp = user_data["xp"] + xp_gain
        current_level = user_data["level"]
        new_calculated_level = calculate_level(new_total_xp)

        await self.bot.db.repo.add_xp(
            guild_id=guild.id,
            user_id=member.id,
            xp_amount=xp_gain,
            new_level=new_calculated_level,
            current_timestamp=now,
        )

        # Check for Level Up!
        if new_calculated_level > current_level:
            channel_id = guild_conf.get("level_up_channel_id")
            announce_channel = guild.get_channel(channel_id) if channel_id else message.channel

            if isinstance(announce_channel, discord.TextChannel):
                embed = create_base_embed(
                    title="🎉 Level Up!",
                    description=f"Congratulations {member.mention}! You just advanced to **Level {new_calculated_level}**!",
                    color=config.COLORS.GOLD,
                )
                if member.display_avatar:
                    embed.set_thumbnail(url=member.display_avatar.url)
                try:
                    await announce_channel.send(content=member.mention, embed=embed)
                except discord.HTTPException:
                    pass

    # -------------------------------------------------------------------------
    # RANK COMMAND
    # -------------------------------------------------------------------------
    @app_commands.command(name="rank", description="Display your or another member's level and rank card.")
    @app_commands.describe(member="Target member to inspect")
    async def rank(self, interaction: discord.Interaction, member: discord.Member | None = None) -> None:
        target = member or interaction.user
        if not isinstance(target, discord.Member):
            return

        user_data = await self.bot.db.repo.get_user_level(interaction.guild.id, target.id)
        rank_pos = await self.bot.db.repo.get_user_rank(interaction.guild.id, target.id)

        current_xp = user_data["xp"]
        current_level = user_data["level"]

        # Calculate XP into current level and required for next level
        base_xp = xp_for_level(current_level)
        next_xp = xp_for_level(current_level + 1)
        xp_in_level = max(0, current_xp - base_xp)
        xp_needed = max(1, next_xp - base_xp)

        progress_bar = render_progress_bar(xp_in_level, xp_needed, length=12)

        embed = create_base_embed(
            title=f"🏆 Rank Card • {target.display_name}",
            color=config.COLORS.GOLD,
        )
        if target.display_avatar:
            embed.set_thumbnail(url=target.display_avatar.url)

        embed.add_field(name="Server Rank", value=f"#{rank_pos}", inline=True)
        embed.add_field(name="Level", value=str(current_level), inline=True)
        embed.add_field(name="Total XP", value=format_number(current_xp), inline=True)

        embed.add_field(
            name=f"Progress to Level {current_level + 1}",
            value=f"`{progress_bar}` **{format_number(xp_in_level)} / {format_number(xp_needed)} XP**",
            inline=False,
        )

        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------------------------------
    # LEADERBOARD COMMAND
    # -------------------------------------------------------------------------
    @app_commands.command(name="leaderboard", description="View the server's top active members by XP.")
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        top_users = await self.bot.db.repo.get_level_leaderboard(interaction.guild.id, limit=10)
        if not top_users:
            await interaction.response.send_message(
                embed=info_embed("Leaderboard", "No member XP data has been recorded yet."),
                ephemeral=True,
            )
            return

        embed = create_base_embed(
            title=f"📊 XP Leaderboard • {interaction.guild.name}",
            color=config.COLORS.GOLD,
        )

        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        lines = []

        for idx, row in enumerate(top_users, start=1):
            member = interaction.guild.get_member(row["user_id"])
            tag = member.mention if member else f"`User {row['user_id']}`"
            prefix = medals.get(idx, f"`#{idx:02d}`")
            lines.append(
                f"{prefix} {tag} — **Level {row['level']}** ({format_number(row['xp'])} XP)"
            )

        embed.description = "\n\n".join(lines)
        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------------------------------
    # ADMIN SET LEVEL
    # -------------------------------------------------------------------------
    levels_group = app_commands.Group(name="levels", description="Manage leveling settings")

    @levels_group.command(name="set", description="Set a member's level directly.")
    @app_commands.describe(member="Member to modify", level="Target level")
    @app_commands.default_permissions(administrator=True)
    @is_guild_admin()
    async def set_level(
        self, interaction: discord.Interaction, member: discord.Member, level: app_commands.Range[int, 0, 1000]
    ) -> None:
        required_xp = xp_for_level(level)
        now = int(time.time())
        await self.bot.db.repo.add_xp(
            guild_id=interaction.guild.id,
            user_id=member.id,
            xp_amount=required_xp,
            new_level=level,
            current_timestamp=now,
        )
        await interaction.response.send_message(
            embed=success_embed(
                "Level Updated",
                f"{member.mention} has been set to **Level {level}** ({format_number(required_xp)} XP).",
            )
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Levels(bot))
