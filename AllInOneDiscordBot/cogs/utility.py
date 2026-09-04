"""Utility commands providing system diagnostic, user info, server info, avatar lookup, and calculations."""

import ast
import operator
import platform
import time
import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import create_base_embed, info_embed, error_embed
from utils.helpers import format_duration
from config import config

# Safe AST-based mathematical operator whitelist
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.Mod: operator.mod,
}


def safe_eval_math(node: ast.AST) -> float:
    """Safely evaluate mathematical AST nodes without code execution vulnerabilities."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError("Invalid constant type in expression.")
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type in SAFE_OPERATORS:
            left = safe_eval_math(node.left)
            right = safe_eval_math(node.right)
            if op_type is ast.Pow and right > 1000:
                raise ValueError("Exponent is too large to safely compute.")
            if op_type is ast.Div and right == 0:
                raise ZeroDivisionError("Division by zero.")
            return SAFE_OPERATORS[op_type](left, right)
        raise ValueError(f"Unsupported math operator: {op_type.__name__}")
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type in SAFE_OPERATORS:
            return SAFE_OPERATORS[op_type](safe_eval_math(node.operand))
        raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
    else:
        raise ValueError("Invalid mathematical syntax.")


class Utility(commands.Cog):
    """General utility and informational commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # -------------------------------------------------------------------------
    # PING
    # -------------------------------------------------------------------------
    @app_commands.command(name="ping", description="Check bot latency and database response speed.")
    async def ping(self, interaction: discord.Interaction) -> None:
        start_time = time.perf_counter()
        await interaction.response.defer()
        api_latency = (time.perf_counter() - start_time) * 1000

        # Database latency check
        db_start = time.perf_counter()
        await self.bot.db.connection.execute("SELECT 1;")
        db_latency = (time.perf_counter() - db_start) * 1000

        ws_latency = self.bot.latency * 1000

        embed = create_base_embed(
            title="🏓 Pong!",
            color=config.COLORS.SUCCESS,
        )
        embed.add_field(name="WebSocket Heartbeat", value=f"`{ws_latency:.1f} ms`", inline=True)
        embed.add_field(name="API Round-Trip", value=f"`{api_latency:.1f} ms`", inline=True)
        embed.add_field(name="Database Query", value=f"`{db_latency:.2f} ms`", inline=True)

        await interaction.followup.send(embed=embed)

    # -------------------------------------------------------------------------
    # SERVERINFO
    # -------------------------------------------------------------------------
    @app_commands.command(name="serverinfo", description="Display detailed server metadata and statistics.")
    async def serverinfo(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if not guild:
            return

        embed = create_base_embed(
            title=f"🏰 Server Information • {guild.name}",
            color=config.COLORS.PRIMARY,
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        owner = guild.owner or await guild.fetch_member(guild.owner_id)
        embed.add_field(name="👑 Owner", value=f"{owner.mention} (`{owner.id}`)", inline=True)
        embed.add_field(name="🆔 Server ID", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="📅 Created On", value=f"<t:{int(guild.created_at.timestamp())}:D>", inline=True)

        # Member counts
        bots = sum(1 for m in guild.members if m.bot)
        humans = guild.member_count - bots
        embed.add_field(
            name="👥 Members",
            value=f"**Total:** {guild.member_count}\nHumans: {humans} | Bots: {bots}",
            inline=True,
        )

        # Channel counts
        text_ch = len(guild.text_channels)
        voice_ch = len(guild.voice_channels)
        categories = len(guild.categories)
        embed.add_field(
            name="📁 Channels",
            value=f"**Total:** {len(guild.channels)}\nText: {text_ch} | Voice: {voice_ch} | Cat: {categories}",
            inline=True,
        )

        embed.add_field(name="🛡️ Roles", value=str(len(guild.roles)), inline=True)
        embed.add_field(name="🚀 Boost Level", value=f"Tier {guild.premium_tier} ({guild.premium_subscription_count} Boosts)", inline=True)
        embed.add_field(name="🔒 Verification", value=str(guild.verification_level).capitalize(), inline=True)

        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------------------------------
    # USERINFO
    # -------------------------------------------------------------------------
    @app_commands.command(name="userinfo", description="Display detailed user profile details.")
    @app_commands.describe(member="Member to inspect")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member | None = None) -> None:
        target = member or interaction.user
        if not isinstance(target, discord.Member):
            return

        embed = create_base_embed(
            title=f"👤 User Profile • {target.display_name}",
            color=target.color.value or config.COLORS.PRIMARY,
        )
        if target.display_avatar:
            embed.set_thumbnail(url=target.display_avatar.url)

        embed.add_field(name="Username", value=f"`{target.name}`", inline=True)
        embed.add_field(name="User ID", value=f"`{target.id}`", inline=True)
        embed.add_field(name="Bot?", value="Yes" if target.bot else "No", inline=True)

        embed.add_field(
            name="Registered",
            value=f"<t:{int(target.created_at.timestamp())}:D> (<t:{int(target.created_at.timestamp())}:R>)",
            inline=False,
        )
        if target.joined_at:
            embed.add_field(
                name="Joined Server",
                value=f"<t:{int(target.joined_at.timestamp())}:D> (<t:{int(target.joined_at.timestamp())}:R>)",
                inline=False,
            )

        roles = [r.mention for r in reversed(target.roles) if not r.is_default()]
        roles_str = " ".join(roles[:15]) if roles else "*None*"
        if len(roles) > 15:
            roles_str += f" and {len(roles) - 15} more..."
        embed.add_field(name=f"Roles ({len(roles)})", value=roles_str, inline=False)

        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------------------------------
    # AVATAR
    # -------------------------------------------------------------------------
    @app_commands.command(name="avatar", description="View user's full resolution avatar.")
    @app_commands.describe(member="Member whose avatar to view")
    async def avatar(self, interaction: discord.Interaction, member: discord.Member | None = None) -> None:
        target = member or interaction.user
        avatar_url = target.display_avatar.with_size(1024).url

        embed = create_base_embed(
            title=f"🖼️ Avatar • {target.display_name}",
            color=config.COLORS.PRIMARY,
        )
        embed.set_image(url=avatar_url)
        embed.description = f"[Direct Link to Image]({avatar_url})"
        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------------------------------
    # BOTINFO & UPTIME
    # -------------------------------------------------------------------------
    @app_commands.command(name="botinfo", description="View bot system specifications, libraries, and runtime status.")
    async def botinfo(self, interaction: discord.Interaction) -> None:
        uptime_seconds = int(time.time() - self.bot.start_time)

        embed = create_base_embed(
            title=f"🤖 {config.BOT_NAME} Status",
            color=config.COLORS.PRIMARY,
        )
        embed.add_field(name="Python Version", value=f"`{platform.python_version()}`", inline=True)
        embed.add_field(name="discord.py Version", value=f"`{discord.__version__}`", inline=True)
        embed.add_field(name="Uptime", value=format_duration(uptime_seconds), inline=True)

        embed.add_field(name="Guilds", value=f"`{len(self.bot.guilds)}`", inline=True)
        total_members = sum(g.member_count or 0 for g in self.bot.guilds)
        embed.add_field(name="Total Users", value=f"`{total_members}`", inline=True)
        embed.add_field(name="Loaded Cogs", value=f"`{len(self.bot.cogs)}`", inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="uptime", description="Check how long the bot has been running without restarts.")
    async def uptime(self, interaction: discord.Interaction) -> None:
        uptime_seconds = int(time.time() - self.bot.start_time)
        await interaction.response.send_message(
            embed=info_embed(
                "Bot Uptime",
                f"🕒 I have been online and running 24/7 for: **{format_duration(uptime_seconds)}**\n"
                f"Started: <t:{int(self.bot.start_time)}:R>",
            )
        )

    # -------------------------------------------------------------------------
    # CALCULATE
    # -------------------------------------------------------------------------
    @app_commands.command(name="calculate", description="Safely evaluate a mathematical equation.")
    @app_commands.describe(expression="Expression to evaluate (e.g. '25 * 4 + 10^2')")
    async def calculate(self, interaction: discord.Interaction, expression: str) -> None:
        cleaned = expression.replace("^", "**").strip()
        try:
            parsed = ast.parse(cleaned, mode="eval")
            result = safe_eval_math(parsed.body)
            # Format integer nicely if whole number
            if result.is_integer():
                result_str = f"{int(result):,}"
            else:
                result_str = f"{result:,.4f}".rstrip("0").rstrip(".")

            embed = info_embed(
                "🧮 Calculator",
                f"**Input:** `{expression}`\n**Result:** `{result_str}`",
            )
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed("Calculation Error", f"Could not evaluate expression: {e}"),
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Utility(bot))
