"""Main entry point for AllInOneDiscordBot."""

import asyncio
import logging
import sys
import time
import discord
from discord.ext import commands

from config import config
from database import Database
from cogs import COGS_LIST
from utils.errors import handle_app_command_error

# Configure structured logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("AllInOneBot")


class AllInOneBot(commands.Bot):
    """Production-grade asynchronous Discord bot."""

    def __init__(self):
        # Configure Discord gateway intents
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True

        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            help_command=None,
        )

        self.db = Database(db_path=config.DATABASE_PATH)
        self.start_time = time.time()

    async def setup_hook(self) -> None:
        """Executed automatically before the websocket connection starts."""
        logger.info("Initializing database connection and tables...")
        await self.db.connect()

        # Connect global slash command error handling
        self.tree.on_error = handle_app_command_error

        # Dynamically load all registered cog modules
        logger.info("Loading cog extensions...")
        for cog in COGS_LIST:
            try:
                await self.load_extension(cog)
                logger.info("Loaded cog: %s", cog)
            except Exception as e:
                logger.error("Failed to load cog %s: %s", cog, e, exc_info=e)

        # Synchronize slash commands
        if config.GUILD_ID:
            logger.info("Dev Mode: Synchronizing commands to test guild ID: %s", config.GUILD_ID)
            test_guild = discord.Object(id=config.GUILD_ID)
            self.tree.copy_global_to(guild=test_guild)
            synced = await self.tree.sync(guild=test_guild)
            logger.info("Synced %d slash commands to test guild %s", len(synced), config.GUILD_ID)
        else:
            logger.info("Production Mode: Synchronizing slash commands globally...")
            synced = await self.tree.sync()
            logger.info("Synced %d slash commands globally.", len(synced))

    async def on_ready(self) -> None:
        """Fired when bot has successfully authenticated and connected."""
        logger.info("=" * 60)
        logger.info("Logged in as: %s (ID: %s)", self.user.name, self.user.id)
        logger.info("discord.py Version: %s", discord.__version__)
        logger.info("Connected to %d guild(s)", len(self.guilds))
        logger.info("Gateway Latency: %.2f ms", self.latency * 1000)
        logger.info("=" * 60)

        # Set rich presence activity
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"/help • {len(self.guilds)} servers",
        )
        await self.change_presence(status=discord.Status.online, activity=activity)

    async def close(self) -> None:
        """Graceful shutdown hook to cleanly close database connections."""
        logger.info("Shutting down bot. Releasing resources...")
        await self.db.close()
        await super().close()
        logger.info("Bot shutdown complete.")


async def main() -> None:
    """Validate environment and run bot."""
    config.validate()
    bot = AllInOneBot()
    async with bot:
        await bot.start(config.DISCORD_TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Process interrupted by user. Exiting.")
    except Exception as e:
        logger.critical("Fatal error encountered during execution: %s", e, exc_info=e)
        sys.exit(1)
