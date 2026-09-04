"""Application configuration module for AllInOneDiscordBot."""

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass(frozen=True)
class Colors:
    """Standardized embed color scheme."""
    PRIMARY: int = 0x5865F2    # Discord Blurple
    SUCCESS: int = 0x57F287    # Green
    WARNING: int = 0xFEE75C    # Yellow
    ERROR: int = 0xED4245      # Red
    INFO: int = 0x5865F2       # Blue
    NEUTRAL: int = 0x2B2D31    # Dark Slate
    GOLD: int = 0xF1C40F       # Gold for economy & levels


@dataclass(frozen=True)
class Config:
    """Bot runtime configuration."""
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "").strip()
    GUILD_ID: int | None = (
        int(os.getenv("GUILD_ID").strip())
        if os.getenv("GUILD_ID") and os.getenv("GUILD_ID").strip().isdigit()
        else None
    )
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/bot.db").strip()
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").strip().upper()

    # Brand / Visuals
    BOT_NAME: str = "All-In-One Bot"
    DEFAULT_FOOTER: str = "AllInOneDiscordBot • Powered by discord.py"
    COLORS: Colors = Colors()

    def validate(self) -> None:
        """Validate critical configuration fields."""
        if not self.DISCORD_TOKEN:
            raise ValueError(
                "CRITICAL: DISCORD_TOKEN is not set in your environment or .env file! "
                "Please configure DISCORD_TOKEN before starting the bot."
            )
        # Ensure database directory exists
        db_dir = Path(self.DATABASE_PATH).parent
        if db_dir and not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)


config = Config()
