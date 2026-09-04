"""Support tickets system with interactive buttons, modals, role permissions, and transcripts."""

import io
import logging
import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import success_embed, error_embed, info_embed, warning_embed
from utils.checks import is_guild_admin

logger = logging.getLogger("AllInOneBot.Tickets")


class TicketModal(discord.ui.Modal, title="Open Support Ticket"):
    """Modal prompting the member for ticket details."""

    reason_input = discord.ui.TextInput(
        label="Ticket Reason / Problem Description",
        style=discord.TextStyle.paragraph,
        placeholder="Please describe how we can assist you today...",
        required=True,
        max_length=500,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        bot = interaction.client

        # Check if user already has an open ticket
        existing = await bot.db.repo.get_open_ticket_by_user(interaction.guild.id, interaction.user.id)
        if existing:
            ch = interaction.guild.get_channel(existing["channel_id"])
            ch_mention = ch.mention if ch else f"channel ID `{existing['channel_id']}`"
            await interaction.followup.send(
                embed=error_embed(
                    "Ticket Already Open",
                    f"You already have an active ticket open in {ch_mention}. Please use your existing ticket."
                ),
                ephemeral=True,
            )
            return

        # Fetch category from config
        config = await bot.db.repo.get_guild_config(interaction.guild.id)
        category_id = config.get("ticket_category_id")
        category = interaction.guild.get_channel(category_id) if category_id else None

        # Setup permission overwrites: hide from @everyone, allow bot and creator
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True, attach_files=True
            ),
            interaction.guild.me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, manage_channels=True, read_message_history=True
            ),
        }

        channel_name = f"ticket-{interaction.user.name[:15]}-{interaction.user.discriminator}"
        if channel_name.endswith("#0"):
            channel_name = f"ticket-{interaction.user.name[:18]}"

        try:
            channel = await interaction.guild.create_text_channel(
                name=channel_name,
                category=category if isinstance(category, discord.CategoryChannel) else None,
                overwrites=overwrites,
                reason=f"Support ticket created by {interaction.user}",
            )
        except Exception as e:
            logger.error("Failed to create ticket channel: %s", e)
            await interaction.followup.send(
                embed=error_embed("Creation Failed", f"Could not create ticket channel: {e}"),
                ephemeral=True,
            )
            return

        # Record ticket in database
        ticket_id = await bot.db.repo.create_ticket(
            guild_id=interaction.guild.id,
            channel_id=channel.id,
            user_id=interaction.user.id,
            reason=self.reason_input.value,
        )

        # Send welcome message in ticket channel
        embed = info_embed(
            f"Ticket #{ticket_id} • Support Desk",
            f"Welcome {interaction.user.mention}! Support staff have been alerted and will assist you shortly.\n\n"
            f"**Reason for Ticket:**\n{self.reason_input.value}\n\n"
            f"Use the buttons below to manage this ticket.",
        )
        view = TicketControlView()
        await channel.send(content=f"{interaction.user.mention}", embed=embed, view=view)

        await interaction.followup.send(
            embed=success_embed("Ticket Created", f"Your ticket was created in {channel.mention}."),
            ephemeral=True,
        )


class TicketLaunchView(discord.ui.View):
    """Persistent button panel for initiating support tickets."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.primary,
        emoji="📩",
        custom_id="allinone:ticket_create_btn",
    )
    async def create_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(TicketModal())


class TicketControlView(discord.ui.View):
    """Controls inside an active ticket channel."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Claim Ticket",
        style=discord.ButtonStyle.secondary,
        emoji="🙋‍♂️",
        custom_id="allinone:ticket_claim_btn",
    )
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not (
            interaction.user.guild_permissions.manage_messages
            or interaction.user.guild_permissions.administrator
        ):
            await interaction.response.send_message(
                embed=error_embed("Staff Only", "Only support staff or moderators can claim tickets."),
                ephemeral=True,
            )
            return

        button.disabled = True
        button.label = f"Claimed by {interaction.user.display_name}"
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(
            embed=info_embed("Ticket Claimed", f"This ticket has been claimed by {interaction.user.mention}.")
        )

    @discord.ui.button(
        label="Transcript",
        style=discord.ButtonStyle.secondary,
        emoji="📜",
        custom_id="allinone:ticket_transcript_btn",
    )
    async def transcript_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        messages = []
        async for m in interaction.channel.history(limit=500, oldest_first=True):
            ts = m.created_at.strftime("%Y-%m-%d %H:%M:%S")
            messages.append(f"[{ts}] {m.author} ({m.author.id}): {m.clean_content}")

        text_file = io.BytesIO("\n".join(messages).encode("utf-8"))
        discord_file = discord.File(text_file, filename=f"transcript-{interaction.channel.name}.txt")
        await interaction.followup.send(
            content="Here is the complete message transcript for this ticket:",
            file=discord_file,
        )

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="allinone:ticket_close_btn",
    )
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        bot = interaction.client
        ticket = await bot.db.repo.get_ticket_by_channel(interaction.channel.id)

        # Allow ticket author or staff
        is_author = ticket and ticket["user_id"] == interaction.user.id
        is_staff = (
            interaction.user.guild_permissions.manage_messages
            or interaction.user.guild_permissions.administrator
        )

        if not (is_author or is_staff):
            await interaction.response.send_message(
                embed=error_embed("Permission Denied", "You do not have permission to close this ticket."),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=warning_embed("Closing Ticket", "This ticket is being archived and deleted in 5 seconds...")
        )

        # Close in database
        await bot.db.repo.close_ticket(interaction.channel.id, interaction.user.id)

        # Wait 5 seconds and delete channel
        import asyncio
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
        except discord.HTTPException as e:
            logger.error("Could not delete ticket channel: %s", e)


class Tickets(commands.Cog):
    """Support tickets management cog."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    ticket_group = app_commands.Group(name="ticket", description="Ticket commands")

    @ticket_group.command(name="panel", description="Send a persistent ticket creation panel to this channel.")
    @app_commands.default_permissions(administrator=True)
    @is_guild_admin()
    async def panel(self, interaction: discord.Interaction) -> None:
        embed = info_embed(
            "🎫 Support Tickets",
            "Need help or have questions for server staff?\n\n"
            "Click the button below to open a private support ticket. "
            "Our team will assist you as soon as possible!",
        )
        await interaction.channel.send(embed=embed, view=TicketLaunchView())
        await interaction.response.send_message(
            embed=success_embed("Panel Created", "Ticket panel successfully deployed."),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    # Register persistent views so buttons work across restarts
    bot.add_view(TicketLaunchView())
    bot.add_view(TicketControlView())
    await bot.add_cog(Tickets(bot))
