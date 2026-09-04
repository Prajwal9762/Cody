"""AutoMod cog protecting the server from spam, invites, excessive caps, mass mentions, and banned words."""

import json
import logging
import re
import time
from collections import defaultdict
from datetime import timedelta
import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import success_embed, error_embed, info_embed, warning_embed
from utils.checks import is_guild_admin

logger = logging.getLogger("AllInOneBot.AutoMod")

INVITE_REGEX = re.compile(
    r"(?:https?://)?(?:www\.)?(?:discord\.(?:gg|io|me|li)|discord(?:app)?\.com/invite)/[a-zA-Z0-9]+",
    re.IGNORECASE,
)


class AutoMod(commands.Cog):
    """Automated server moderation guards."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Track message timestamps per member for spam detection: guild_id -> user_id -> [timestamps]
        self._spam_tracker: dict[int, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Scan messages for automod rule violations."""
        # Ignore bot messages, DMs, and system messages
        if message.author.bot or not message.guild or not isinstance(message.author, discord.Member):
            return

        # Skip users with Manage Messages or Administrator
        if (
            message.author.guild_permissions.administrator
            or message.author.guild_permissions.manage_messages
        ):
            return

        guild = message.guild
        member = message.author
        content = message.content or ""

        # Fetch guild config and automod rules
        config = await self.bot.db.repo.get_guild_config(guild.id)
        if not config.get("automod_enabled", 1):
            return

        rules = await self.bot.db.repo.get_all_automod_rules(guild.id)

        # 1. ANTI-INVITE
        rule_invites = rules.get("invites", {"enabled": 1})
        if rule_invites["enabled"] and INVITE_REGEX.search(content):
            await self._trigger_violation(
                message, "Anti-Invite", "Advertising Discord invite links is strictly prohibited."
            )
            return

        # 2. ANTI-MASS-MENTIONS (> 5 mentions)
        rule_mentions = rules.get("mentions", {"enabled": 1})
        if rule_mentions["enabled"] and len(message.mentions) >= 5:
            await self._trigger_violation(
                message, "Mass Mentions", f"Mentioning {len(message.mentions)} users in a single message is not allowed."
            )
            return

        # 3. ANTI-CAPS (>70% uppercase on >10 char messages)
        rule_caps = rules.get("caps", {"enabled": 1})
        if rule_caps["enabled"] and len(content) > 10:
            letters = [c for c in content if c.isalpha()]
            if letters:
                caps_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
                if caps_ratio >= 0.75:
                    await self._trigger_violation(
                        message, "Excessive Caps", "Messages containing excessive capital letters are not allowed."
                    )
                    return

        # 4. ANTI-SPAM (More than 5 messages in 4 seconds)
        rule_spam = rules.get("spam", {"enabled": 1})
        if rule_spam["enabled"]:
            now = time.time()
            user_stamps = self._spam_tracker[guild.id][member.id]
            user_stamps.append(now)
            # Retain only last 4 seconds
            self._spam_tracker[guild.id][member.id] = [t for t in user_stamps if now - t <= 4.0]

            if len(self._spam_tracker[guild.id][member.id]) >= 5:
                # Clear tracker for user to avoid repeated rapid triggers
                self._spam_tracker[guild.id][member.id].clear()
                # Apply short 5m timeout
                try:
                    await member.timeout(
                        discord.utils.utcnow() + timedelta(minutes=5),
                        reason="AutoMod: Excessive rapid message spamming.",
                    )
                except discord.HTTPException:
                    pass

                await self._trigger_violation(
                    message,
                    "Spam Flood",
                    f"{member.mention} was timed out for 5 minutes for rapid message spam.",
                    delete_only=False,
                )
                return

        # 5. BANNED WORDS
        rule_words = rules.get("words", {"enabled": 1})
        if rule_words["enabled"]:
            words_data = rule_words.get("extra_data")
            if words_data:
                try:
                    banned_list = json.loads(words_data)
                    lower_content = content.lower()
                    for word in banned_list:
                        if word.lower() in lower_content:
                            await self._trigger_violation(
                                message,
                                "Banned Word Filter",
                                "Message contained a prohibited word or phrase.",
                            )
                            return
                except Exception as e:
                    logger.error("Error parsing banned words: %s", e)

    async def _trigger_violation(
        self,
        message: discord.Message,
        rule_name: str,
        reason: str,
        delete_only: bool = False,
    ) -> None:
        """Handle automod violation by deleting message and notifying."""
        try:
            await message.delete()
        except discord.HTTPException:
            pass

        # Send alert
        alert = warning_embed(
            f"AutoMod Action: {rule_name}",
            f"{message.author.mention}, your message was removed.\n**Reason:** {reason}",
        )
        try:
            warning_msg = await message.channel.send(embed=alert, delete_after=8)
        except discord.HTTPException:
            pass

        # Send to mod log if configured
        config = await self.bot.db.repo.get_guild_config(message.guild.id)
        channel_id = config.get("mod_log_channel_id")
        if channel_id:
            mod_channel = message.guild.get_channel(channel_id)
            if isinstance(mod_channel, discord.TextChannel):
                log_embed = warning_embed(
                    f"AutoMod Triggered: {rule_name}",
                    f"**User:** {message.author.mention} (`{message.author.id}`)\n"
                    f"**Channel:** {message.channel.mention}\n"
                    f"**Reason:** {reason}\n"
                    f"**Content:** ```\n{message.content[:500]}\n```",
                )
                await mod_channel.send(embed=log_embed)

    # =========================================================================
    # SLASH COMMANDS
    # =========================================================================
    automod_group = app_commands.Group(name="automod", description="Server automod settings")

    @automod_group.command(name="toggle", description="Enable or disable a specific automod rule.")
    @app_commands.describe(
        rule="Rule to toggle",
        enabled="Enable or disable this rule",
    )
    @app_commands.choices(
        rule=[
            app_commands.Choice(name="Anti-Invite Links", value="invites"),
            app_commands.Choice(name="Anti-Spam Flood", value="spam"),
            app_commands.Choice(name="Anti-Excessive Caps", value="caps"),
            app_commands.Choice(name="Anti-Mass Mentions", value="mentions"),
            app_commands.Choice(name="Banned Words Filter", value="words"),
        ]
    )
    @app_commands.default_permissions(administrator=True)
    @is_guild_admin()
    async def toggle(
        self,
        interaction: discord.Interaction,
        rule: app_commands.Choice[str],
        enabled: bool,
    ) -> None:
        await self.bot.db.repo.set_automod_rule(interaction.guild.id, rule.value, enabled)
        status = "enabled" if enabled else "disabled"
        await interaction.response.send_message(
            embed=success_embed("AutoMod Setting Updated", f"Rule **{rule.name}** is now **{status}**.")
        )

    @automod_group.command(name="status", description="Display active automod configuration.")
    @app_commands.default_permissions(administrator=True)
    @is_guild_admin()
    async def status(self, interaction: discord.Interaction) -> None:
        rules = await self.bot.db.repo.get_all_automod_rules(interaction.guild.id)
        embed = info_embed(f"AutoMod Settings for {interaction.guild.name}", "Current automated protection status:")

        rule_names = {
            "invites": "Anti-Invite Links",
            "spam": "Anti-Spam Flood",
            "caps": "Anti-Excessive Caps",
            "mentions": "Anti-Mass Mentions",
            "words": "Banned Words Filter",
        }

        for key, name in rule_names.items():
            r = rules.get(key, {"enabled": 1})
            status = "🟢 Enabled" if r.get("enabled", 1) else "🔴 Disabled"
            embed.add_field(name=name, value=status, inline=True)

        await interaction.response.send_message(embed=embed)

    @automod_group.command(name="bannedword", description="Add or remove words from the forbidden list.")
    @app_commands.describe(action="Add or remove word", word="The word/phrase to filter")
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Add", value="add"),
            app_commands.Choice(name="Remove", value="remove"),
            app_commands.Choice(name="List", value="list"),
        ]
    )
    @app_commands.default_permissions(administrator=True)
    @is_guild_admin()
    async def bannedword(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        word: str | None = None,
    ) -> None:
        rule = await self.bot.db.repo.get_automod_rule(interaction.guild.id, "words") or {}
        raw = rule.get("extra_data") or "[]"
        try:
            banned_words = json.loads(raw)
        except Exception:
            banned_words = []

        if action.value == "list":
            if not banned_words:
                await interaction.response.send_message(
                    embed=info_embed("Banned Words", "No words are currently added to the filter list."),
                    ephemeral=True,
                )
                return
            formatted = ", ".join(f"`{w}`" for w in banned_words)
            await interaction.response.send_message(
                embed=info_embed(f"Banned Words ({len(banned_words)})", formatted),
                ephemeral=True,
            )
            return

        if not word:
            await interaction.response.send_message(
                embed=error_embed("Missing Argument", "You must provide a word for add/remove."),
                ephemeral=True,
            )
            return

        word_clean = word.lower().strip()
        if action.value == "add":
            if word_clean in banned_words:
                await interaction.response.send_message(
                    embed=warning_embed("Already Exists", f"`{word_clean}` is already in the filter."),
                    ephemeral=True,
                )
                return
            banned_words.append(word_clean)
            await self.bot.db.repo.set_automod_rule(
                interaction.guild.id, "words", enabled=True, extra_data=json.dumps(banned_words)
            )
            await interaction.response.send_message(
                embed=success_embed("Word Added", f"Added `{word_clean}` to the banned words filter.")
            )
        elif action.value == "remove":
            if word_clean not in banned_words:
                await interaction.response.send_message(
                    embed=warning_embed("Not Found", f"`{word_clean}` is not in the filter list."),
                    ephemeral=True,
                )
                return
            banned_words.remove(word_clean)
            await self.bot.db.repo.set_automod_rule(
                interaction.guild.id, "words", enabled=True, extra_data=json.dumps(banned_words)
            )
            await interaction.response.send_message(
                embed=success_embed("Word Removed", f"Removed `{word_clean}` from the banned words filter.")
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutoMod(bot))
