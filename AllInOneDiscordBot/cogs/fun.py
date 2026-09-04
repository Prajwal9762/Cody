"""Fun and entertainment commands including interactive games, dice, 8ball, memes, and jokes."""

import logging
import random
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import create_base_embed, info_embed, success_embed
from config import config

logger = logging.getLogger("AllInOneBot.Fun")

EIGHT_BALL_RESPONSES = [
    "It is certain.",
    "Without a doubt.",
    "You may rely on it.",
    "Yes, definitely.",
    "As I see it, yes.",
    "Most likely.",
    "Outlook good.",
    "Yes.",
    "Signs point to yes.",
    "Reply hazy, try again.",
    "Ask again later.",
    "Better not tell you now.",
    "Cannot predict now.",
    "Concentrate and ask again.",
    "Don't count on it.",
    "My reply is no.",
    "My sources say no.",
    "Outlook not so good.",
    "Very doubtful.",
]


class RPSView(discord.ui.View):
    """Interactive Rock Paper Scissors game view."""

    def __init__(self, author: discord.Member):
        super().__init__(timeout=60)
        self.author = author

    async def _handle_choice(self, interaction: discord.Interaction, player_choice: str) -> None:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("This is not your game!", ephemeral=True)
            return

        bot_choice = random.choice(["Rock", "Paper", "Scissors"])
        emojis = {"Rock": "🪨", "Paper": "📄", "Scissors": "✂️"}

        if player_choice == bot_choice:
            result = "It's a tie!"
            color = config.COLORS.WARNING
        elif (
            (player_choice == "Rock" and bot_choice == "Scissors")
            or (player_choice == "Paper" and bot_choice == "Rock")
            or (player_choice == "Scissors" and bot_choice == "Paper")
        ):
            result = "You won! 🎉"
            color = config.COLORS.SUCCESS
        else:
            result = "The bot won! 🤖"
            color = config.COLORS.ERROR

        embed = create_base_embed(
            title="🎮 Rock Paper Scissors",
            description=(
                f"**You picked:** {emojis[player_choice]} {player_choice}\n"
                f"**Bot picked:** {emojis[bot_choice]} {bot_choice}\n\n"
                f"### {result}"
            ),
            color=color,
        )

        for item in self.children:
            item.disabled = True  # type: ignore

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Rock", style=discord.ButtonStyle.primary, emoji="🪨")
    async def rock_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._handle_choice(interaction, "Rock")

    @discord.ui.button(label="Paper", style=discord.ButtonStyle.primary, emoji="📄")
    async def paper_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._handle_choice(interaction, "Paper")

    @discord.ui.button(label="Scissors", style=discord.ButtonStyle.primary, emoji="✂️")
    async def scissors_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._handle_choice(interaction, "Scissors")


class Fun(commands.Cog):
    """Fun and games cog."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # -------------------------------------------------------------------------
    # 8BALL
    # -------------------------------------------------------------------------
    @app_commands.command(name="8ball", description="Ask the magic 8-ball any question.")
    @app_commands.describe(question="The question to ask")
    async def eight_ball(self, interaction: discord.Interaction, question: str) -> None:
        answer = random.choice(EIGHT_BALL_RESPONSES)
        embed = info_embed(
            "🎱 Magic 8-Ball",
            f"**Question:** {question}\n**Answer:** {answer}",
        )
        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------------------------------
    # COINFLIP
    # -------------------------------------------------------------------------
    @app_commands.command(name="coinflip", description="Flip a coin.")
    async def coinflip(self, interaction: discord.Interaction) -> None:
        outcome = random.choice(["Heads", "Tails"])
        emoji = "🪙" if outcome == "Heads" else "🪙"
        embed = success_embed(
            "Coin Flip",
            f"{emoji} The coin flipped and landed on **{outcome}**!",
        )
        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------------------------------
    # ROLL
    # -------------------------------------------------------------------------
    @app_commands.command(name="roll", description="Roll one or multiple dice.")
    @app_commands.describe(sides="Number of sides per die (default 6)", count="Number of dice (1-10)")
    async def roll(
        self,
        interaction: discord.Interaction,
        sides: app_commands.Range[int, 2, 100] = 6,
        count: app_commands.Range[int, 1, 10] = 1,
    ) -> None:
        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls)
        rolls_str = ", ".join(str(r) for r in rolls)

        embed = info_embed(
            "🎲 Dice Roll",
            f"**Rolled:** {count}d{sides}\n"
            f"**Results:** `[{rolls_str}]`\n"
            f"**Total Sum:** **{total}**",
        )
        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------------------------------
    # CHOOSE
    # -------------------------------------------------------------------------
    @app_commands.command(name="choose", description="Randomly pick between multiple comma-separated options.")
    @app_commands.describe(options="Options separated by commas (e.g. Pizza, Burger, Tacos)")
    async def choose(self, interaction: discord.Interaction, options: str) -> None:
        choices = [c.strip() for c in options.split(",") if c.strip()]
        if len(choices) < 2:
            await interaction.response.send_message(
                embed=info_embed("Not Enough Options", "Please provide at least 2 comma-separated options."),
                ephemeral=True,
            )
            return

        picked = random.choice(choices)
        embed = success_embed("Decision Made", f"I pick: **{picked}**!")
        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------------------------------
    # ROCK PAPER SCISSORS
    # -------------------------------------------------------------------------
    @app_commands.command(name="rps", description="Play Rock, Paper, Scissors with buttons against the bot.")
    async def rps(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        view = RPSView(author=interaction.user)
        embed = info_embed(
            "🎮 Rock Paper Scissors",
            "Choose your move below by clicking one of the buttons:",
        )
        await interaction.response.send_message(embed=embed, view=view)

    # -------------------------------------------------------------------------
    # MEME
    # -------------------------------------------------------------------------
    @app_commands.command(name="meme", description="Fetch a fresh meme from Reddit.")
    async def meme(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://meme-api.com/gimme") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        embed = create_base_embed(
                            title=data.get("title", "Random Meme"),
                            color=config.COLORS.PRIMARY,
                        )
                        embed.set_image(url=data.get("url"))
                        embed.set_footer(text=f"r/{data.get('subreddit', 'memes')} • 👍 {data.get('ups', 0)}")
                        await interaction.followup.send(embed=embed)
                        return
        except Exception as e:
            logger.error("Error fetching meme: %s", e)

        # Fallback
        await interaction.followup.send(
            embed=info_embed("Meme Service Busy", "Could not fetch a meme right now. Please try again later!")
        )

    # -------------------------------------------------------------------------
    # JOKE
    # -------------------------------------------------------------------------
    @app_commands.command(name="joke", description="Hear a funny joke.")
    async def joke(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://official-joke-api.appspot.com/random_joke") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        embed = info_embed(
                            "😄 Joke of the Moment",
                            f"**{data.get('setup')}**\n\n*||{data.get('punchline')}||*",
                        )
                        await interaction.followup.send(embed=embed)
                        return
        except Exception:
            pass

        # Built-in fallback jokes
        fallback = [
            ("Why do programmers prefer dark mode?", "Because light attracts bugs!"),
            ("How many programmers does it take to change a light bulb?", "None. It's a hardware problem."),
            ("There are 10 types of people in the world:", "Those who understand binary, and those who don't."),
        ]
        q, a = random.choice(fallback)
        await interaction.followup.send(
            embed=info_embed("😄 Joke of the Moment", f"**{q}**\n\n*||{a}||*")
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Fun(bot))
