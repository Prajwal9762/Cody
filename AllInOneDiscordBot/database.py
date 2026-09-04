"""Database connection manager and schema lifecycle for AllInOneDiscordBot."""

import logging
from pathlib import Path
import aiosqlite

from database.schema import SCHEMA_STATEMENTS
from database.repositories import DatabaseRepository

logger = logging.getLogger("AllInOneBot.Database")


class Database:
    """Manages SQLite async connection and lifecycle."""

    def __init__(self, db_path: str = "data/bot.db"):
        self.db_path = db_path
        self._connection: aiosqlite.Connection | None = None
        self.repo: DatabaseRepository | None = None

    @property
    def connection(self) -> aiosqlite.Connection:
        """Access active connection instance."""
        if self._connection is None:
            raise RuntimeError("Database connection has not been initialized. Call connect() first.")
        return self._connection

    async def connect(self) -> None:
        """Establish asynchronous connection and ensure schema tables exist."""
        # Ensure parent directory exists
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info("Connecting to SQLite database at: %s", self.db_path)
        self._connection = await aiosqlite.connect(self.db_path)
        # Enable WAL mode for high concurrent throughput & foreign keys
        await self._connection.execute("PRAGMA journal_mode=WAL;")
        await self._connection.execute("PRAGMA foreign_keys=ON;")

        # Run schema migration
        await self._connection.executescript(SCHEMA_STATEMENTS)
        await self._connection.commit()

        # Initialize repository
        self.repo = DatabaseRepository(self._connection)
        logger.info("Database schema validated and repository ready.")

    async def close(self) -> None:
        """Safely flush commits and close database connection."""
        if self._connection:
            logger.info("Closing database connection...")
            await self._connection.commit()
            await self._connection.close()
            self._connection = None
            self.repo = None
            logger.info("Database connection cleanly closed.")
