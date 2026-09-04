"""Self-assignable roles system utilizing interactive dropdown menus and buttons."""

import logging
import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import success_embed, error_embed, info_embed
from utils.checks import is_guild_admin

logger = logging.getLogger("AllInOneBot.Roles")


class SelfRoleSelect(discord.ui.Select):
    """Interactive select menu for toggling self roles."""

    def __init__(self, options: list[discord.SelectOption]):
        super().__init__(
            placeholder="Choose roles to add or remove...",
            min_values=1,
            max_values=min(len(options), 10),
            options=options,
            custom_id="allinone:self_roles_select",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        member = interaction.user
        guild = interaction.guild

        if not isinstance(member, discord.Member) or not guild:
            return

        added = []
        removed = []
        failed = []

        for role_id_str in self.values:
            role = guild.get_role(int(role_id_str))
            if not role:
                continue

            # Check bot hierarchy
            if role >= guild.me.top_role:
                failed.append(f"• {role.name} (Bot role hierarchy too low)")
                continue

            try:
                if role in member.roles:
                    await member.remove_roles(role, reason="Self-role toggled off")
                    removed.append(role.mention)
                else:
                    await member.add_roles(role, reason="Self-role toggled on")
                    added.append(role.mention)
            except discord.HTTPException:
                failed.append(f"• {role.name} (Discord API error)")

        response_lines = []
        if added:
            response_lines.append(f"✅ **Added:** {' '.join(added)}")
        if removed:
            response_lines.append(f"❌ **Removed:** {' '.join(removed)}")
        if failed:
            response_lines.append(f"⚠️ **Errors:**\n" + "\n".join(failed))

        description = "\n".join(response_lines) if response_lines else "No role changes made."
        await interaction.followup.send(
            embed=info_embed("Roles Updated", description),
            ephemeral=True,
        )


class SelfRolePanelView(discord.ui.View):
    """Persistent view housing the self role selection menu."""

    def __init__(self, options: list[discord.SelectOption] | None = None):
        super().__init__(timeout=None)
        if options:
            self.add_item(SelfRoleSelect(options))


class Roles(commands.Cog):
    """Self-assignable roles cog."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    selfrole_group = app_commands.Group(name="selfrole", description="Self-assignable roles commands")

    @selfrole_group.command(name="add", description="Add a role to the self-assignable catalogue.")
    @app_commands.describe(
        role="Target role to make self-assignable",
        label="Display name shown in the menu",
        emoji="Optional emoji symbol (e.g. 🎮)",
        description="Short description of the role",
    )
    @app_commands.default_permissions(manage_roles=True)
    @is_guild_admin()
    async def add(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        label: str,
        emoji: str | None = None,
        description: str | None = None,
    ) -> None:
        if role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                embed=error_embed(
                    "Hierarchy Error",
                    f"I cannot assign {role.mention} because it is positioned higher than or equal to my highest role ({interaction.guild.me.top_role.name}).",
                ),
                ephemeral=True,
            )
            return

        if role.is_default() or role.managed:
            await interaction.response.send_message(
                embed=error_embed("Invalid Role", "Managed bot roles or @everyone cannot be self-assigned."),
                ephemeral=True,
            )
            return

        await self.bot.db.repo.add_self_role(
            guild_id=interaction.guild.id,
            role_id=role.id,
            label=label[:50],
            emoji=emoji,
            description=description[:100] if description else None,
        )

        await interaction.response.send_message(
            embed=success_embed(
                "Role Added",
                f"{role.mention} has been added to the self-role catalog as **{label}**.",
            )
        )

    @selfrole_group.command(name="remove", description="Remove a role from the self-assignable catalogue.")
    @app_commands.describe(role="Role to remove from catalog")
    @app_commands.default_permissions(manage_roles=True)
    @is_guild_admin()
    async def remove(self, interaction: discord.Interaction, role: discord.Role) -> None:
        count = await self.bot.db.repo.remove_self_role(interaction.guild.id, role.id)
        if count > 0:
            await interaction.response.send_message(
                embed=success_embed("Role Removed", f"{role.mention} was removed from the self-role catalog.")
            )
        else:
            await interaction.response.send_message(
                embed=error_embed("Not Found", f"{role.mention} is not in the self-role catalog."),
                ephemeral=True,
            )

    @selfrole_group.command(name="list", description="List all self-assignable roles configured.")
    async def list_roles(self, interaction: discord.Interaction) -> None:
        roles_data = await self.bot.db.repo.get_self_roles(interaction.guild.id)
        if not roles_data:
            await interaction.response.send_message(
                embed=info_embed("Self Roles", "No self-assignable roles configured for this server."),
                ephemeral=True,
            )
            return

        lines = []
        for r in roles_data:
            role_obj = interaction.guild.get_role(r["role_id"])
            role_mention = role_obj.mention if role_obj else f"`[Deleted Role {r['role_id']}]`"
            emoji_str = f"{r['emoji']} " if r["emoji"] else ""
            lines.append(f"• {emoji_str}**{r['label']}** → {role_mention}")

        embed = info_embed(f"Self-Assignable Roles ({len(roles_data)})", "\n".join(lines))
        await interaction.response.send_message(embed=embed)

    @selfrole_group.command(name="panel", description="Post an interactive dropdown menu for self-assigning roles.")
    @app_commands.default_permissions(administrator=True)
    @is_guild_admin()
    async def panel(self, interaction: discord.Interaction) -> None:
        roles_data = await self.bot.db.repo.get_self_roles(interaction.guild.id)
        if not roles_data:
            await interaction.response.send_message(
                embed=error_embed("No Roles Configured", "Add roles using `/selfrole add` before posting a panel."),
                ephemeral=True,
            )
            return

        options = []
        for r in roles_data[:25]:  # Discord selects allow up to 25 items
            role_obj = interaction.guild.get_role(r["role_id"])
            if not role_obj:
                continue
            options.append(
                discord.SelectOption(
                    label=r["label"],
                    value=str(r["role_id"]),
                    description=r.get("description") or f"Toggle the @{role_obj.name} role",
                    emoji=r.get("emoji") or "🏷️",
                )
            )

        if not options:
            await interaction.response.send_message(
                embed=error_embed("No Valid Roles", "None of the configured roles exist in this server."),
                ephemeral=True,
            )
            return

        view = SelfRolePanelView(options)
        embed = info_embed(
            "🎭 Self-Assignable Roles",
            "Select one or more roles from the menu below to add or remove them from your profile.\n"
            "Selecting a role you already have will remove it.",
        )
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message(
            embed=success_embed("Panel Published", "Self-role panel successfully posted."),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    # Register persistent view template
    bot.add_view(SelfRolePanelView())
    await bot.add_cog(Roles(bot))
