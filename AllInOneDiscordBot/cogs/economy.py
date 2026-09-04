"""Virtual economy cog featuring wallet, bank, daily rewards, jobs, gambling, and robbery."""

import logging
import random
import time
import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import success_embed, error_embed, info_embed, warning_embed, create_base_embed
from utils.helpers import format_number, format_duration
from config import config

logger = logging.getLogger("AllInOneBot.Economy")

JOBS = [
    ("Software Engineer", 120, "fixed a memory leak in the production container"),
    ("Discord Moderator", 80, "banned 50 spammers and cleaned the chat"),
    ("Barista", 65, "crafted 45 oat milk lattes with perfect foam art"),
    ("Dog Walker", 70, "walked six golden retrievers through the park"),
    ("Pizza Delivery Driver", 90, "delivered 15 hot pizzas before the timer ran out"),
    ("Cybersecurity Analyst", 140, "thwarted a DDoS attack on the main server"),
]


class Economy(commands.Cog):
    """Virtual currency and banking system."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # -------------------------------------------------------------------------
    # BALANCE
    # -------------------------------------------------------------------------
    @app_commands.command(name="balance", description="Check your or another member's bank and wallet balance.")
    @app_commands.describe(member="Member whose balance to view")
    async def balance(self, interaction: discord.Interaction, member: discord.Member | None = None) -> None:
        target = member or interaction.user
        if not isinstance(target, discord.Member):
            return

        acc = await self.bot.db.repo.get_economy(interaction.guild.id, target.id)
        wallet = acc["wallet"]
        bank = acc["bank"]
        net_worth = wallet + bank

        embed = create_base_embed(
            title=f"💰 Financial Overview • {target.display_name}",
            color=config.COLORS.GOLD,
        )
        if target.display_avatar:
            embed.set_thumbnail(url=target.display_avatar.url)

        embed.add_field(name="💵 Wallet", value=f"🪙 {format_number(wallet)}", inline=True)
        embed.add_field(name="🏦 Bank", value=f"🪙 {format_number(bank)}", inline=True)
        embed.add_field(name="💎 Net Worth", value=f"🪙 {format_number(net_worth)}", inline=True)

        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------------------------------
    # DAILY
    # -------------------------------------------------------------------------
    @app_commands.command(name="daily", description="Claim your daily coin stipend (every 24 hours).")
    async def daily(self, interaction: discord.Interaction) -> None:
        now = int(time.time())
        acc = await self.bot.db.repo.get_economy(interaction.guild.id, interaction.user.id)
        last = acc.get("last_daily", 0)

        cooldown = 86400  # 24h
        if now - last < cooldown:
            remaining = cooldown - (now - last)
            await interaction.response.send_message(
                embed=warning_embed(
                    "Daily Already Claimed",
                    f"You have already claimed your daily reward!\nCome back in **{format_duration(remaining)}**.",
                ),
                ephemeral=True,
            )
            return

        reward = 350
        await self.bot.db.repo.update_economy(
            interaction.guild.id,
            interaction.user.id,
            wallet=acc["wallet"] + reward,
            last_daily=now,
        )

        await interaction.response.send_message(
            embed=success_embed(
                "Daily Reward Claimed",
                f"You received your daily reward of **🪙 {format_number(reward)} coins**!\n"
                f"New Wallet Balance: **🪙 {format_number(acc['wallet'] + reward)}**",
            )
        )

    # -------------------------------------------------------------------------
    # WORK
    # -------------------------------------------------------------------------
    @app_commands.command(name="work", description="Work a job shift to earn coins (1-hour cooldown).")
    async def work(self, interaction: discord.Interaction) -> None:
        now = int(time.time())
        acc = await self.bot.db.repo.get_economy(interaction.guild.id, interaction.user.id)
        last = acc.get("last_work", 0)

        cooldown = 3600  # 1h
        if now - last < cooldown:
            remaining = cooldown - (now - last)
            await interaction.response.send_message(
                embed=warning_embed(
                    "Resting",
                    f"You are exhausted from your last shift. Rest for **{format_duration(remaining)}**.",
                ),
                ephemeral=True,
            )
            return

        job_title, base_wage, description = random.choice(JOBS)
        earned = base_wage + random.randint(-15, 25)

        await self.bot.db.repo.update_economy(
            interaction.guild.id,
            interaction.user.id,
            wallet=acc["wallet"] + earned,
            last_work=now,
        )

        await interaction.response.send_message(
            embed=success_embed(
                f"Shift Completed: {job_title}",
                f"You {description} and earned **🪙 {format_number(earned)} coins**!",
            )
        )

    # -------------------------------------------------------------------------
    # BEG
    # -------------------------------------------------------------------------
    @app_commands.command(name="beg", description="Beg for some spare change (5-minute cooldown).")
    async def beg(self, interaction: discord.Interaction) -> None:
        now = int(time.time())
        acc = await self.bot.db.repo.get_economy(interaction.guild.id, interaction.user.id)
        last = acc.get("last_beg", 0)

        cooldown = 300  # 5 min
        if now - last < cooldown:
            remaining = cooldown - (now - last)
            await interaction.response.send_message(
                embed=warning_embed(
                    "Have Dignity",
                    f"People are ignoring you. Try again in **{format_duration(remaining)}**.",
                ),
                ephemeral=True,
            )
            return

        success = random.choice([True, True, False])
        if not success:
            await self.bot.db.repo.update_economy(interaction.guild.id, interaction.user.id, last_beg=now)
            await interaction.response.send_message(
                embed=info_embed("Nobody Helped", "A passerby looked at you with pity and walked away.")
            )
            return

        coins = random.randint(15, 50)
        donors = ["MrBeast", "A generous grandma", "A passing billionaire", "A friendly stranger"]
        donor = random.choice(donors)

        await self.bot.db.repo.update_economy(
            interaction.guild.id,
            interaction.user.id,
            wallet=acc["wallet"] + coins,
            last_beg=now,
        )

        await interaction.response.send_message(
            embed=success_embed("Generous Donation", f"**{donor}** handed you **🪙 {coins} coins**!")
        )

    # -------------------------------------------------------------------------
    # DEPOSIT & WITHDRAW
    # -------------------------------------------------------------------------
    @app_commands.command(name="deposit", description="Deposit coins from your wallet into your safe bank account.")
    @app_commands.describe(amount="Amount of coins to deposit (or 'all')")
    async def deposit(self, interaction: discord.Interaction, amount: str) -> None:
        acc = await self.bot.db.repo.get_economy(interaction.guild.id, interaction.user.id)
        wallet = acc["wallet"]

        if amount.lower() == "all":
            deposit_amount = wallet
        else:
            if not amount.isdigit() or int(amount) <= 0:
                await interaction.response.send_message(
                    embed=error_embed("Invalid Amount", "Please enter a positive numeric value or 'all'."),
                    ephemeral=True,
                )
                return
            deposit_amount = int(amount)

        if deposit_amount <= 0:
            await interaction.response.send_message(
                embed=error_embed("Insufficient Funds", "You don't have any coins to deposit."),
                ephemeral=True,
            )
            return

        if deposit_amount > wallet:
            await interaction.response.send_message(
                embed=error_embed(
                    "Insufficient Funds",
                    f"You only have **🪙 {format_number(wallet)}** in your wallet.",
                ),
                ephemeral=True,
            )
            return

        await self.bot.db.repo.update_economy(
            interaction.guild.id,
            interaction.user.id,
            wallet=wallet - deposit_amount,
            bank=acc["bank"] + deposit_amount,
        )

        await interaction.response.send_message(
            embed=success_embed(
                "Deposit Successful",
                f"Deposited **🪙 {format_number(deposit_amount)}** into your bank account.",
            )
        )

    @app_commands.command(name="withdraw", description="Withdraw coins from your bank account into your wallet.")
    @app_commands.describe(amount="Amount of coins to withdraw (or 'all')")
    async def withdraw(self, interaction: discord.Interaction, amount: str) -> None:
        acc = await self.bot.db.repo.get_economy(interaction.guild.id, interaction.user.id)
        bank = acc["bank"]

        if amount.lower() == "all":
            withdraw_amount = bank
        else:
            if not amount.isdigit() or int(amount) <= 0:
                await interaction.response.send_message(
                    embed=error_embed("Invalid Amount", "Please enter a positive numeric value or 'all'."),
                    ephemeral=True,
                )
                return
            withdraw_amount = int(amount)

        if withdraw_amount <= 0:
            await interaction.response.send_message(
                embed=error_embed("Empty Bank", "Your bank account is currently empty."),
                ephemeral=True,
            )
            return

        if withdraw_amount > bank:
            await interaction.response.send_message(
                embed=error_embed(
                    "Insufficient Funds",
                    f"You only have **🪙 {format_number(bank)}** in your bank account.",
                ),
                ephemeral=True,
            )
            return

        await self.bot.db.repo.update_economy(
            interaction.guild.id,
            interaction.user.id,
            wallet=acc["wallet"] + withdraw_amount,
            bank=bank - withdraw_amount,
        )

        await interaction.response.send_message(
            embed=success_embed(
                "Withdrawal Successful",
                f"Withdrew **🪙 {format_number(withdraw_amount)}** to your wallet.",
            )
        )

    # -------------------------------------------------------------------------
    # PAY
    # -------------------------------------------------------------------------
    @app_commands.command(name="pay", description="Transfer coins from your wallet to another member.")
    @app_commands.describe(member="Recipient member", amount="Amount of coins to transfer")
    async def pay(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        amount: app_commands.Range[int, 1, 1000000],
    ) -> None:
        if member.id == interaction.user.id:
            await interaction.response.send_message(
                embed=error_embed("Invalid Transfer", "You cannot transfer coins to yourself."),
                ephemeral=True,
            )
            return

        if member.bot:
            await interaction.response.send_message(
                embed=error_embed("Invalid Transfer", "You cannot send coins to bots."),
                ephemeral=True,
            )
            return

        sender_acc = await self.bot.db.repo.get_economy(interaction.guild.id, interaction.user.id)
        if sender_acc["wallet"] < amount:
            await interaction.response.send_message(
                embed=error_embed(
                    "Insufficient Funds",
                    f"You only have **🪙 {format_number(sender_acc['wallet'])}** in your wallet.",
                ),
                ephemeral=True,
            )
            return

        target_acc = await self.bot.db.repo.get_economy(interaction.guild.id, member.id)

        # Execute transfer
        await self.bot.db.repo.update_economy(
            interaction.guild.id,
            interaction.user.id,
            wallet=sender_acc["wallet"] - amount,
        )
        await self.bot.db.repo.update_economy(
            interaction.guild.id,
            member.id,
            wallet=target_acc["wallet"] + amount,
        )

        await interaction.response.send_message(
            embed=success_embed(
                "Payment Sent",
                f"Sent **🪙 {format_number(amount)} coins** to {member.mention}!",
            )
        )

    # -------------------------------------------------------------------------
    # GAMBLE
    # -------------------------------------------------------------------------
    @app_commands.command(name="gamble", description="Gamble coins on a double-or-nothing coin toss.")
    @app_commands.describe(amount="Amount of coins from wallet to bet")
    async def gamble(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 10, 50000],
    ) -> None:
        acc = await self.bot.db.repo.get_economy(interaction.guild.id, interaction.user.id)
        if acc["wallet"] < amount:
            await interaction.response.send_message(
                embed=error_embed(
                    "Insufficient Balance",
                    f"You need **🪙 {format_number(amount)}** in your wallet to place this bet.",
                ),
                ephemeral=True,
            )
            return

        won = random.random() < 0.48  # 48% house edge
        if won:
            new_wallet = acc["wallet"] + amount
            await self.bot.db.repo.update_economy(interaction.guild.id, interaction.user.id, wallet=new_wallet)
            await interaction.response.send_message(
                embed=success_embed(
                    "🎰 Winner!",
                    f"The coin landed in your favor! You won **🪙 {format_number(amount)} coins**!\n"
                    f"Wallet balance: **🪙 {format_number(new_wallet)}**",
                )
            )
        else:
            new_wallet = acc["wallet"] - amount
            await self.bot.db.repo.update_economy(interaction.guild.id, interaction.user.id, wallet=new_wallet)
            await interaction.response.send_message(
                embed=error_embed(
                    "🎰 Busted!",
                    f"Tough luck! You lost **🪙 {format_number(amount)} coins**.\n"
                    f"Wallet balance: **🪙 {format_number(new_wallet)}**",
                )
            )

    # -------------------------------------------------------------------------
    # ROB
    # -------------------------------------------------------------------------
    @app_commands.command(name="rob", description="Attempt to pickpocket another member's wallet.")
    @app_commands.describe(member="Member to rob")
    async def rob(self, interaction: discord.Interaction, member: discord.Member) -> None:
        if member.id == interaction.user.id or member.bot:
            await interaction.response.send_message(embed=error_embed("Invalid Target", "Invalid target."), ephemeral=True)
            return

        now = int(time.time())
        robber_acc = await self.bot.db.repo.get_economy(interaction.guild.id, interaction.user.id)
        last = robber_acc.get("last_rob", 0)

        cooldown = 1800  # 30 min
        if now - last < cooldown:
            remaining = cooldown - (now - last)
            await interaction.response.send_message(
                embed=warning_embed(
                    "Laying Low",
                    f"The police are watching you! Lay low for **{format_duration(remaining)}**.",
                ),
                ephemeral=True,
            )
            return

        target_acc = await self.bot.db.repo.get_economy(interaction.guild.id, member.id)
        if target_acc["wallet"] < 50:
            await interaction.response.send_message(
                embed=warning_embed("Not Worth It", f"{member.mention} has less than 50 coins in their wallet."),
                ephemeral=True,
            )
            return

        if robber_acc["wallet"] < 100:
            await interaction.response.send_message(
                embed=error_embed("Too Poor to Rob", "You need at least 100 coins in your wallet to cover bail fines if caught!"),
                ephemeral=True,
            )
            return

        success = random.random() < 0.40  # 40% success rate
        if success:
            steal_percent = random.uniform(0.15, 0.45)
            stolen = int(target_acc["wallet"] * steal_percent)

            await self.bot.db.repo.update_economy(
                interaction.guild.id, interaction.user.id, wallet=robber_acc["wallet"] + stolen, last_rob=now
            )
            await self.bot.db.repo.update_economy(
                interaction.guild.id, member.id, wallet=target_acc["wallet"] - stolen
            )

            await interaction.response.send_message(
                embed=success_embed(
                    "Heist Succeeded! 🥷",
                    f"You managed to sneak away with **🪙 {format_number(stolen)} coins** from {member.mention}'s wallet!",
                )
            )
        else:
            fine = min(robber_acc["wallet"], random.randint(50, 150))
            await self.bot.db.repo.update_economy(
                interaction.guild.id, interaction.user.id, wallet=robber_acc["wallet"] - fine, last_rob=now
            )
            await interaction.response.send_message(
                embed=error_embed(
                    "Busted by the Police! 🚨",
                    f"You were caught trying to rob {member.mention} and had to pay a fine of **🪙 {fine} coins**!",
                )
            )

    # -------------------------------------------------------------------------
    # ECONOMY LEADERBOARD
    # -------------------------------------------------------------------------
    @app_commands.command(name="economy_leaderboard", description="View the richest users in this server.")
    async def economy_leaderboard(self, interaction: discord.Interaction) -> None:
        top_users = await self.bot.db.repo.get_economy_leaderboard(interaction.guild.id, limit=10)
        if not top_users:
            await interaction.response.send_message(
                embed=info_embed("Economy Leaderboard", "No economy records found yet."),
                ephemeral=True,
            )
            return

        embed = create_base_embed(
            title=f"🏦 Wealth Leaderboard • {interaction.guild.name}",
            color=config.COLORS.GOLD,
        )

        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        lines = []
        for idx, row in enumerate(top_users, start=1):
            member = interaction.guild.get_member(row["user_id"])
            tag = member.mention if member else f"`User {row['user_id']}`"
            prefix = medals.get(idx, f"`#{idx:02d}`")
            net_worth = row["wallet"] + row["bank"]
            lines.append(
                f"{prefix} {tag} — **🪙 {format_number(net_worth)}** (W: {format_number(row['wallet'])}, B: {format_number(row['bank'])})"
            )

        embed.description = "\n\n".join(lines)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Economy(bot))
