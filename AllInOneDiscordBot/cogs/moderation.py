"""Moderation commands cog supporting kick, ban, unban, timeout, warns, purge, and locks."""

from datetime import timedelta
import logging
import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import success_embed, error_embed, info_embed, mod_embed
from utils.permissions import can_moderate
from utils.helpers import parse_duration, format_duration
from utils.checks import is_guild_moderator, is_guild_admin

logger = logging.getLogger("AllInOneBot.Moderation")


class Moderation(commands.Cog):
    """Server moderation commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _log_case(
        self,
        guild: discord.Guild,
        action: str,
        target: discord.User | discord.Member,
        moderator: discord.Member,
        reason: str | None = None,
        duration: str | None = None,
    ) -> None:
        """Helper to save moderation case to database and send embed to configured log channel."""
        try:
            # 1. Save to DB
            case_id = await self.bot.db.repo.add_case(
                guild_id=guild.id,
                case_type=action.lower(),
                user_id=target.id,
                moderator_id=moderator.id,
                reason=reason,
                duration=None,
            )

            # 2. Check if mod log channel is configured
            config = await self.bot.db.repo.get_guild_config(guild.id)
            channel_id = config.get("mod_log_channel_id")
            if channel_id:
                channel = guild.get_channel(channel_id)
                if isinstance(channel, discord.TextChannel):
                    embed = mod_embed(
                        action=action,
                        target=target,
                        moderator=moderator,
                        reason=reason,
                        duration=duration,
                        case_id=case_id,
                    )
                    await channel.send(embed=embed)
        except Exception as e:
            logger.error("Failed to log moderation case: %s", e)

    # -------------------------------------------------------------------------
    # KICK
    # -------------------------------------------------------------------------
    @app_commands.command(name="kick", description="Kick a member from the server.")
    @app_commands.describe(member="Member to kick", reason="Reason for kicking")
    @app_commands.default_permissions(kick_members=True)
    @is_guild_moderator()
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided.",
    ) -> None:
        allowed, msg = can_moderate(interaction.user, member)
        if not allowed:
            await interaction.response.send_message(embed=error_embed("Action Denied", msg), ephemeral=True)
            return

        # Attempt DM
        try:
            await member.send(
                embed=error_embed(
                    f"Kicked from {interaction.guild.name}",
                    f"**Reason:** {reason}\n**Moderator:** {interaction.user.mention}",
                )
            )
        except discord.HTTPException:
            pass

        await member.kick(reason=f"{reason} | Moderated by {interaction.user}")
        await self._log_case(interaction.guild, "Kick", member, interaction.user, reason)

        await interaction.response.send_message(
            embed=success_embed(
                "Member Kicked",
                f"{member.mention} (`{member.id}`) was kicked.\n**Reason:** {reason}",
            )
        )

    # -------------------------------------------------------------------------
    # BAN
    # -------------------------------------------------------------------------
    @app_commands.command(name="ban", description="Ban a member or user from the server.")
    @app_commands.describe(
        member="Member or user to ban",
        reason="Reason for banning",
        delete_days="Number of days of messages to delete (0-7)",
    )
    @app_commands.default_permissions(ban_members=True)
    @is_guild_moderator()
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided.",
        delete_days: app_commands.Range[int, 0, 7] = 0,
    ) -> None:
        allowed, msg = can_moderate(interaction.user, member)
        if not allowed:
            await interaction.response.send_message(embed=error_embed("Action Denied", msg), ephemeral=True)
            return

        try:
            await member.send(
                embed=error_embed(
                    f"Banned from {interaction.guild.name}",
                    f"**Reason:** {reason}\n**Moderator:** {interaction.user.mention}",
                )
            )
        except discord.HTTPException:
            pass

        await interaction.guild.ban(
            member,
            reason=f"{reason} | Moderated by {interaction.user}",
            delete_message_seconds=delete_days * 86400,
        )
        await self._log_case(interaction.guild, "Ban", member, interaction.user, reason)

        await interaction.response.send_message(
            embed=success_embed(
                "Member Banned",
                f"{member.mention} (`{member.id}`) was banned.\n**Reason:** {reason}",
            )
        )

    # -------------------------------------------------------------------------
    # UNBAN
    # -------------------------------------------------------------------------
    @app_commands.command(name="unban", description="Unban a user by their user ID.")
    @app_commands.describe(user_id="Discord User ID of the banned user", reason="Reason for unban")
    @app_commands.default_permissions(ban_members=True)
    @is_guild_moderator()
    async def unban(
        self,
        interaction: discord.Interaction,
        user_id: str,
        reason: str = "No reason provided.",
    ) -> None:
        if not user_id.isdigit():
            await interaction.response.send_message(
                embed=error_embed("Invalid ID", "Please provide a numeric user ID."),
                ephemeral=True,
            )
            return

        uid = int(user_id)
        try:
            user = await self.bot.fetch_user(uid)
            await interaction.guild.unban(user, reason=f"{reason} | Moderated by {interaction.user}")
            await self._log_case(interaction.guild, "Unban", user, interaction.user, reason)

            await interaction.response.send_message(
                embed=success_embed("User Unbanned", f"Successfully unbanned {user.mention} (`{user.id}`).")
            )
        except discord.NotFound:
            await interaction.response.send_message(
                embed=error_embed("Not Found", "This user is not currently banned."),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed("Unban Failed", str(e)),
                ephemeral=True,
            )

    # -------------------------------------------------------------------------
    # TIMEOUT (MUTE)
    # -------------------------------------------------------------------------
    @app_commands.command(name="timeout", description="Timeout (mute) a member temporarily.")
    @app_commands.describe(
        member="Member to timeout",
        duration="Duration format (e.g. 10m, 2h, 1d)",
        reason="Reason for timeout",
    )
    @app_commands.default_permissions(moderate_members=True)
    @is_guild_moderator()
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: str,
        reason: str = "No reason provided.",
    ) -> None:
        allowed, msg = can_moderate(interaction.user, member)
        if not allowed:
            await interaction.response.send_message(embed=error_embed("Action Denied", msg), ephemeral=True)
            return

        try:
            seconds = parse_duration(duration)
            if seconds > 2419200:  # Discord 28-day timeout max
                await interaction.response.send_message(
                    embed=error_embed("Invalid Duration", "Discord timeouts cannot exceed 28 days."),
                    ephemeral=True,
                )
                return
        except ValueError as err:
            await interaction.response.send_message(embed=error_embed("Format Error", str(err)), ephemeral=True)
            return

        until = discord.utils.utcnow() + timedelta(seconds=seconds)
        await member.timeout(until, reason=f"{reason} | Moderated by {interaction.user}")
        dur_str = format_duration(seconds)

        await self._log_case(interaction.guild, "Timeout", member, interaction.user, reason, dur_str)
        await interaction.response.send_message(
            embed=success_embed(
                "Member Timed Out",
                f"{member.mention} has been timed out for **{dur_str}**.\n**Reason:** {reason}",
            )
        )

    # -------------------------------------------------------------------------
    # UNTIMEOUT
    # -------------------------------------------------------------------------
    @app_commands.command(name="untimeout", description="Remove timeout from a member.")
    @app_commands.describe(member="Member to remove timeout from", reason="Reason for removal")
    @app_commands.default_permissions(moderate_members=True)
    @is_guild_moderator()
    async def untimeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Timeout lifted early.",
    ) -> None:
        if not member.is_timed_out():
            await interaction.response.send_message(
                embed=warning_embed("Not Timed Out", f"{member.mention} is not currently timed out."),
                ephemeral=True,
            )
            return

        await member.timeout(None, reason=f"{reason} | Moderated by {interaction.user}")
        await self._log_case(interaction.guild, "Untimeout", member, interaction.user, reason)

        await interaction.response.send_message(
            embed=success_embed("Timeout Removed", f"{member.mention} is no longer timed out.")
        )

    # -------------------------------------------------------------------------
    # WARN
    # -------------------------------------------------------------------------
    @app_commands.command(name="warn", description="Issue a formal warning to a member.")
    @app_commands.describe(member="Member to warn", reason="Reason for warning")
    @app_commands.default_permissions(moderate_members=True)
    @is_guild_moderator()
    async def warn(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str,
    ) -> None:
        allowed, msg = can_moderate(interaction.user, member)
        if not allowed:
            await interaction.response.send_message(embed=error_embed("Action Denied", msg), ephemeral=True)
            return

        warn_id = await self.bot.db.repo.add_warn(
            guild_id=interaction.guild.id,
            user_id=member.id,
            moderator_id=interaction.user.id,
            reason=reason,
        )

        # Notify member
        try:
            await member.send(
                embed=warning_embed(
                    f"Warning in {interaction.guild.name}",
                    f"**Warning ID:** #{warn_id}\n**Reason:** {reason}\n**Moderator:** {interaction.user.mention}",
                )
            )
        except discord.HTTPException:
            pass

        await self._log_case(interaction.guild, f"Warning #{warn_id}", member, interaction.user, reason)

        total_warns = len(await self.bot.db.repo.get_warns(interaction.guild.id, member.id))
        await interaction.response.send_message(
            embed=success_embed(
                "Member Warned",
                f"{member.mention} received warning `#{warn_id}`.\n"
                f"**Reason:** {reason}\n"
                f"**Total Warnings:** {total_warns}",
            )
        )

    # -------------------------------------------------------------------------
    # WARNINGS
    # -------------------------------------------------------------------------
    @app_commands.command(name="warnings", description="View warnings logged against a member.")
    @app_commands.describe(member="Member to look up")
    @app_commands.default_permissions(moderate_members=True)
    @is_guild_moderator()
    async def warnings(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
    ) -> None:
        warns = await self.bot.db.repo.get_warns(interaction.guild.id, member.id)
        if not warns:
            await interaction.response.send_message(
                embed=info_embed("No Warnings", f"{member.mention} has a clean record with no warnings."),
                ephemeral=True,
            )
            return

        embed = info_embed(f"Warnings for {member.display_name}", f"Total warnings: **{len(warns)}**\n")
        for w in warns[:15]:  # show up to 15
            mod = interaction.guild.get_member(w["moderator_id"])
            mod_str = mod.mention if mod else f"ID: `{w['moderator_id']}`"
            timestamp = f"<t:{w['timestamp']}:R>"
            embed.add_field(
                name=f"Warning #{w['id']} • {timestamp}",
                value=f"**Mod:** {mod_str}\n**Reason:** {w['reason']}",
                inline=False,
            )

        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------------------------------
    # CLEARWARNS
    # -------------------------------------------------------------------------
    @app_commands.command(name="clearwarns", description="Clear all warnings for a member.")
    @app_commands.describe(member="Member whose warnings should be cleared")
    @app_commands.default_permissions(administrator=True)
    @is_guild_admin()
    async def clearwarns(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
    ) -> None:
        count = await self.bot.db.repo.clear_warns(interaction.guild.id, member.id)
        await interaction.response.send_message(
            embed=success_embed("Warnings Cleared", f"Cleared **{count}** warning(s) for {member.mention}.")
        )

    # -------------------------------------------------------------------------
    # PURGE
    # -------------------------------------------------------------------------
    @app_commands.command(name="purge", description="Bulk delete messages in the current channel.")
    @app_commands.describe(amount="Number of messages to delete (1-100)")
    @app_commands.default_permissions(manage_messages=True)
    @is_guild_moderator()
    async def purge(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 100],
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(
            embed=success_embed("Purge Complete", f"Successfully deleted **{len(deleted)}** message(s)."),
            ephemeral=True,
        )

    # -------------------------------------------------------------------------
    # SLOWMODE
    # -------------------------------------------------------------------------
    @app_commands.command(name="slowmode", description="Set channel message cooldown rate.")
    @app_commands.describe(seconds="Slowmode cooldown in seconds (0 to disable)")
    @app_commands.default_permissions(manage_channels=True)
    @is_guild_moderator()
    async def slowmode(
        self,
        interaction: discord.Interaction,
        seconds: app_commands.Range[int, 0, 21600],
    ) -> None:
        await interaction.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            msg = "Slowmode disabled for this channel."
        else:
            msg = f"Slowmode configured to **{seconds}** seconds."
        await interaction.response.send_message(embed=success_embed("Slowmode Updated", msg))

    # -------------------------------------------------------------------------
    # LOCK / UNLOCK
    # -------------------------------------------------------------------------
    @app_commands.command(name="lock", description="Lock channel preventing standard members from speaking.")
    @app_commands.describe(reason="Reason for locking channel")
    @app_commands.default_permissions(manage_channels=True)
    @is_guild_moderator()
    async def lock(
        self,
        interaction: discord.Interaction,
        reason: str = "Channel locked by moderation.",
    ) -> None:
        default_role = interaction.guild.default_role
        overwrite = interaction.channel.overwrites_for(default_role)
        overwrite.send_messages = False
        await interaction.channel.set_permissions(default_role, overwrite=overwrite, reason=reason)

        await interaction.response.send_message(
            embed=warning_embed(
                "Channel Locked",
                f"🔒 This channel was locked by {interaction.user.mention}.\n**Reason:** {reason}",
            )
        )

    @app_commands.command(name="unlock", description="Unlock channel allowing standard members to speak.")
    @app_commands.default_permissions(manage_channels=True)
    @is_guild_moderator()
    async def unlock(self, interaction: discord.Interaction) -> None:
        default_role = interaction.guild.default_role
        overwrite = interaction.channel.overwrites_for(default_role)
        overwrite.send_messages = None  # Reset to default
        await interaction.channel.set_permissions(default_role, overwrite=overwrite, reason="Channel unlocked.")

        await interaction.response.send_message(
            embed=success_embed(
                "Channel Unlocked",
                f"🔓 This channel was unlocked by {interaction.user.mention}.",
            )
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
