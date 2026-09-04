"""Interactive polls cog featuring real-time button voting, live progress bars, and vote tracking."""

import json
import logging
import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import create_base_embed, error_embed, success_embed
from utils.helpers import render_progress_bar
from config import config

logger = logging.getLogger("AllInOneBot.Polls")

OPTION_LETTERS = ["🇦", "🇧", "🇨", "🇩", "🇪"]


class PollVoteView(discord.ui.View):
    """Dynamic buttons for voting on poll options."""

    def __init__(self, options: list[str]):
        super().__init__(timeout=None)
        self.options = options

        for idx, opt in enumerate(options):
            letter = chr(65 + idx)  # A, B, C...
            button = discord.ui.Button(
                label=f"{letter}: {opt[:20]}",
                style=discord.ButtonStyle.primary,
                emoji=OPTION_LETTERS[idx],
                custom_id=f"allinone:poll_opt_{idx}",
            )
            button.callback = self.make_callback(idx)
            self.add_item(button)

    def make_callback(self, option_index: int):
        async def callback(interaction: discord.Interaction) -> None:
            await interaction.response.defer(ephemeral=True)
            bot = interaction.client

            poll_record = await bot.db.repo.get_poll_by_message(interaction.message.id)
            if not poll_record:
                await interaction.followup.send(
                    embed=error_embed("Poll Not Found", "Could not locate this poll in the database."),
                    ephemeral=True,
                )
                return

            if poll_record["closed"]:
                await interaction.followup.send(
                    embed=error_embed("Poll Closed", "This poll has concluded and is no longer accepting votes."),
                    ephemeral=True,
                )
                return

            votes = json.loads(poll_record["votes_json"])
            user_id_str = str(interaction.user.id)
            previous_vote = votes.get(user_id_str)

            # Cast or change vote
            votes[user_id_str] = option_index
            await bot.db.repo.update_poll_votes(interaction.message.id, votes)

            # Re-render message embed
            options_list = json.loads(poll_record["options_json"])
            new_embed = Polls.render_poll_embed(poll_record["question"], options_list, votes, interaction.user)
            await interaction.message.edit(embed=new_embed)

            action_msg = "changed to" if previous_vote is not None else "cast for"
            opt_label = options_list[option_index]
            await interaction.followup.send(
                embed=success_embed("Vote Recorded", f"Your vote has been {action_msg} **Option {chr(65 + option_index)}: {opt_label}**!"),
                ephemeral=True,
            )

        return callback


class Polls(commands.Cog):
    """Interactive polling system."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def render_poll_embed(
        question: str,
        options: list[str],
        votes: dict[str, int],
        author: discord.User | discord.Member | None = None,
        closed: bool = False,
    ) -> discord.Embed:
        """Render poll embed with live vote tallies and Unicode progress bars."""
        total_votes = len(votes)
        status_suffix = " [CLOSED]" if closed else ""

        embed = create_base_embed(
            title=f"📊 Poll: {question}{status_suffix}",
            color=config.COLORS.NEUTRAL if closed else config.COLORS.PRIMARY,
        )

        counts = [0] * len(options)
        for voter, opt_idx in votes.items():
            if 0 <= opt_idx < len(counts):
                counts[opt_idx] += 1

        for idx, (opt, count) in enumerate(zip(options, counts)):
            percentage = (count / total_votes * 100) if total_votes > 0 else 0.0
            bar = render_progress_bar(count, total_votes if total_votes > 0 else 1, length=10)
            letter = chr(65 + idx)
            embed.add_field(
                name=f"{OPTION_LETTERS[idx]} Option {letter}: {opt}",
                value=f"`{bar}` **{count} votes** ({percentage:.1f}%)",
                inline=False,
            )

        embed.set_footer(text=f"Total Votes: {total_votes} • {config.DEFAULT_FOOTER}")
        return embed

    poll_group = app_commands.Group(name="poll", description="Create and manage interactive polls")

    @poll_group.command(name="create", description="Create an interactive poll with up to 5 options.")
    @app_commands.describe(
        question="Poll question",
        option1="First option",
        option2="Second option",
        option3="Third option (optional)",
        option4="Fourth option (optional)",
        option5="Fifth option (optional)",
    )
    async def create(
        self,
        interaction: discord.Interaction,
        question: str,
        option1: str,
        option2: str,
        option3: str | None = None,
        option4: str | None = None,
        option5: str | None = None,
    ) -> None:
        opts = [o.strip() for o in [option1, option2, option3, option4, option5] if o and o.strip()]
        if len(opts) < 2:
            await interaction.response.send_message(
                embed=error_embed("Invalid Options", "A poll must contain at least 2 distinct choices."),
                ephemeral=True,
            )
            return

        embed = self.render_poll_embed(question, opts, {}, interaction.user)
        view = PollVoteView(opts)

        await interaction.response.send_message(
            embed=success_embed("Poll Created", "Your poll is now live in this channel!"),
            ephemeral=True,
        )
        msg = await interaction.channel.send(embed=embed, view=view)

        await self.bot.db.repo.create_poll(
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            message_id=msg.id,
            question=question,
            options=opts,
            author_id=interaction.user.id,
        )

    @poll_group.command(name="end", description="End and close an existing poll.")
    @app_commands.describe(message_id="Message ID of the poll")
    async def end(self, interaction: discord.Interaction, message_id: str) -> None:
        if not message_id.isdigit():
            await interaction.response.send_message(
                embed=error_embed("Invalid ID", "Please provide a valid numeric message ID."),
                ephemeral=True,
            )
            return

        mid = int(message_id)
        poll = await self.bot.db.repo.get_poll_by_message(mid)
        if not poll:
            await interaction.response.send_message(
                embed=error_embed("Not Found", "No poll matching that message ID was found."),
                ephemeral=True,
            )
            return

        is_author = poll["author_id"] == interaction.user.id
        is_mod = (
            interaction.user.guild_permissions.manage_messages
            or interaction.user.guild_permissions.administrator
        )
        if not (is_author or is_mod):
            await interaction.response.send_message(
                embed=error_embed("Permission Denied", "Only the poll creator or moderators can end this poll."),
                ephemeral=True,
            )
            return

        await self.bot.db.repo.close_poll(mid)

        # Try updating message
        try:
            channel = interaction.guild.get_channel(poll["channel_id"])
            if channel:
                msg = await channel.fetch_message(mid)
                options = json.loads(poll["options_json"])
                votes = json.loads(poll["votes_json"])
                closed_embed = self.render_poll_embed(poll["question"], options, votes, closed=True)
                await msg.edit(embed=closed_embed, view=None)
        except Exception as e:
            logger.error("Could not edit poll message on close: %s", e)

        await interaction.response.send_message(
            embed=success_embed("Poll Closed", "The poll has ended and buttons have been removed.")
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Polls(bot))
