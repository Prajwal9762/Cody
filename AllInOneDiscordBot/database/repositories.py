"""Database repository classes providing asynchronous data access layer."""

import json
import time
from typing import Any
import aiosqlite


class DatabaseRepository:
    """Consolidated repository providing asynchronous database operations."""

    def __init__(self, db: aiosqlite.Connection):
        self.db = db
        self.db.row_factory = aiosqlite.Row

    # =========================================================================
    # GUILD CONFIGURATION
    # =========================================================================

    async def get_guild_config(self, guild_id: int) -> dict[str, Any]:
        """Fetch guild configuration or create default row if not present."""
        async with self.db.execute(
            "SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)

        # Insert defaults if non-existent
        await self.db.execute(
            "INSERT OR IGNORE INTO guild_config (guild_id) VALUES (?)", (guild_id,)
        )
        await self.db.commit()

        async with self.db.execute(
            "SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else {}

    async def update_guild_config(self, guild_id: int, **fields: Any) -> None:
        """Dynamically update specified fields on guild_config."""
        if not fields:
            return
        await self.get_guild_config(guild_id)  # Ensure row exists
        set_clause = ", ".join(f"{k} = ?" for k in fields.keys())
        values = list(fields.values()) + [guild_id]
        await self.db.execute(
            f"UPDATE guild_config SET {set_clause} WHERE guild_id = ?", values
        )
        await self.db.commit()

    # =========================================================================
    # MODERATION & WARNS
    # =========================================================================

    async def add_warn(self, guild_id: int, user_id: int, moderator_id: int, reason: str) -> int:
        """Record a member warning."""
        now = int(time.time())
        cursor = await self.db.execute(
            """
            INSERT INTO warns (guild_id, user_id, moderator_id, reason, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (guild_id, user_id, moderator_id, reason, now),
        )
        await self.db.commit()
        return cursor.lastrowid or 0

    async def get_warns(self, guild_id: int, user_id: int) -> list[dict[str, Any]]:
        """Retrieve warnings for a member in a guild."""
        async with self.db.execute(
            "SELECT * FROM warns WHERE guild_id = ? AND user_id = ? ORDER BY timestamp DESC",
            (guild_id, user_id),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def clear_warns(self, guild_id: int, user_id: int) -> int:
        """Clear all warnings for a member."""
        cursor = await self.db.execute(
            "DELETE FROM warns WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        await self.db.commit()
        return cursor.rowcount

    async def add_case(
        self,
        guild_id: int,
        case_type: str,
        user_id: int,
        moderator_id: int,
        reason: str | None = None,
        duration: int | None = None,
    ) -> int:
        """Record a moderation case (ban, kick, mute, etc.)."""
        now = int(time.time())
        cursor = await self.db.execute(
            """
            INSERT INTO moderation_cases (guild_id, case_type, user_id, moderator_id, reason, duration, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (guild_id, case_type, user_id, moderator_id, reason, duration, now),
        )
        await self.db.commit()
        return cursor.lastrowid or 0

    async def get_user_cases(self, guild_id: int, user_id: int) -> list[dict[str, Any]]:
        """Fetch all moderation cases logged against a user."""
        async with self.db.execute(
            "SELECT * FROM moderation_cases WHERE guild_id = ? AND user_id = ? ORDER BY timestamp DESC",
            (guild_id, user_id),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # =========================================================================
    # AUTOMOD RULES
    # =========================================================================

    async def get_automod_rule(self, guild_id: int, rule_type: str) -> dict[str, Any] | None:
        """Get rule config (e.g., 'invites', 'spam', 'words', 'mentions')."""
        async with self.db.execute(
            "SELECT * FROM automod_rules WHERE guild_id = ? AND rule_type = ?",
            (guild_id, rule_type),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def set_automod_rule(
        self, guild_id: int, rule_type: str, enabled: bool, extra_data: str | None = None
    ) -> None:
        """Upsert an automod rule setting."""
        await self.db.execute(
            """
            INSERT INTO automod_rules (guild_id, rule_type, enabled, extra_data)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id, rule_type) DO UPDATE SET
                enabled = excluded.enabled,
                extra_data = COALESCE(excluded.extra_data, automod_rules.extra_data)
            """,
            (guild_id, rule_type, 1 if enabled else 0, extra_data),
        )
        await self.db.commit()

    async def get_all_automod_rules(self, guild_id: int) -> dict[str, dict[str, Any]]:
        """Get all automod rules configured for a guild."""
        async with self.db.execute(
            "SELECT * FROM automod_rules WHERE guild_id = ?", (guild_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return {r["rule_type"]: dict(r) for r in rows}

    # =========================================================================
    # TICKETS
    # =========================================================================

    async def create_ticket(
        self, guild_id: int, channel_id: int, user_id: int, reason: str = "General Support"
    ) -> int:
        """Record a new open ticket."""
        now = int(time.time())
        cursor = await self.db.execute(
            """
            INSERT INTO tickets (guild_id, channel_id, user_id, status, created_at, reason)
            VALUES (?, ?, ?, 'open', ?, ?)
            """,
            (guild_id, channel_id, user_id, now, reason),
        )
        await self.db.commit()
        return cursor.lastrowid or 0

    async def get_ticket_by_channel(self, channel_id: int) -> dict[str, Any] | None:
        """Find ticket entry for a specific channel."""
        async with self.db.execute(
            "SELECT * FROM tickets WHERE channel_id = ?", (channel_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_open_ticket_by_user(self, guild_id: int, user_id: int) -> dict[str, Any] | None:
        """Check if a user already has an active open ticket."""
        async with self.db.execute(
            "SELECT * FROM tickets WHERE guild_id = ? AND user_id = ? AND status = 'open'",
            (guild_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def close_ticket(self, channel_id: int, closed_by: int) -> None:
        """Mark a ticket as closed."""
        now = int(time.time())
        await self.db.execute(
            """
            UPDATE tickets
            SET status = 'closed', closed_at = ?, closed_by = ?
            WHERE channel_id = ?
            """,
            (now, closed_by, channel_id),
        )
        await self.db.commit()

    # =========================================================================
    # SELF ROLES
    # =========================================================================

    async def add_self_role(
        self, guild_id: int, role_id: int, label: str, emoji: str | None = None, description: str | None = None, category: str = "General"
    ) -> int:
        """Add a role to the self-assignable catalogue."""
        cursor = await self.db.execute(
            """
            INSERT INTO self_roles (guild_id, role_id, emoji, label, description, category)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (guild_id, role_id, emoji, label, description, category),
        )
        await self.db.commit()
        return cursor.lastrowid or 0

    async def remove_self_role(self, guild_id: int, role_id: int) -> int:
        """Remove a self role from catalog."""
        cursor = await self.db.execute(
            "DELETE FROM self_roles WHERE guild_id = ? AND role_id = ?",
            (guild_id, role_id),
        )
        await self.db.commit()
        return cursor.rowcount

    async def get_self_roles(self, guild_id: int) -> list[dict[str, Any]]:
        """Fetch all self roles registered in guild."""
        async with self.db.execute(
            "SELECT * FROM self_roles WHERE guild_id = ? ORDER BY id ASC", (guild_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # =========================================================================
    # LEVELS / XP
    # =========================================================================

    async def get_user_level(self, guild_id: int, user_id: int) -> dict[str, Any]:
        """Fetch user XP and level data or default row."""
        async with self.db.execute(
            "SELECT * FROM user_levels WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)

        # Default initialization
        await self.db.execute(
            "INSERT OR IGNORE INTO user_levels (guild_id, user_id, xp, level, last_xp_time) VALUES (?, ?, 0, 0, 0)",
            (guild_id, user_id),
        )
        await self.db.commit()
        return {"guild_id": guild_id, "user_id": user_id, "xp": 0, "level": 0, "last_xp_time": 0}

    async def add_xp(
        self, guild_id: int, user_id: int, xp_amount: int, new_level: int, current_timestamp: int
    ) -> None:
        """Update user XP, level, and interaction timestamp."""
        await self.db.execute(
            """
            INSERT INTO user_levels (guild_id, user_id, xp, level, last_xp_time)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET
                xp = user_levels.xp + excluded.xp,
                level = excluded.level,
                last_xp_time = excluded.last_xp_time
            """,
            (guild_id, user_id, xp_amount, new_level, current_timestamp),
        )
        await self.db.commit()

    async def get_level_leaderboard(self, guild_id: int, limit: int = 10) -> list[dict[str, Any]]:
        """Return top users ordered by experience points."""
        async with self.db.execute(
            "SELECT * FROM user_levels WHERE guild_id = ? ORDER BY xp DESC LIMIT ?",
            (guild_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_user_rank(self, guild_id: int, user_id: int) -> int:
        """Calculate leaderboard rank position for a specific user."""
        user = await self.get_user_level(guild_id, user_id)
        user_xp = user["xp"]
        async with self.db.execute(
            "SELECT COUNT(*) as rank_above FROM user_levels WHERE guild_id = ? AND xp > ?",
            (guild_id, user_xp),
        ) as cursor:
            row = await cursor.fetchone()
            return (row["rank_above"] + 1) if row else 1

    # =========================================================================
    # ECONOMY
    # =========================================================================

    async def get_economy(self, guild_id: int, user_id: int) -> dict[str, Any]:
        """Fetch bank and wallet account balances."""
        async with self.db.execute(
            "SELECT * FROM economy WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)

        await self.db.execute(
            """
            INSERT OR IGNORE INTO economy (guild_id, user_id, wallet, bank, last_daily, last_work, last_beg, last_rob)
            VALUES (?, ?, 100, 0, 0, 0, 0, 0)
            """,
            (guild_id, user_id),
        )
        await self.db.commit()
        return {
            "guild_id": guild_id,
            "user_id": user_id,
            "wallet": 100,
            "bank": 0,
            "last_daily": 0,
            "last_work": 0,
            "last_beg": 0,
            "last_rob": 0,
        }

    async def update_economy(self, guild_id: int, user_id: int, **fields: Any) -> None:
        """Update currency values or cooldown timestamps."""
        await self.get_economy(guild_id, user_id)  # Ensure row exists
        set_clause = ", ".join(f"{k} = ?" for k in fields.keys())
        values = list(fields.values()) + [guild_id, user_id]
        await self.db.execute(
            f"UPDATE economy SET {set_clause} WHERE guild_id = ? AND user_id = ?",
            values,
        )
        await self.db.commit()

    async def get_economy_leaderboard(self, guild_id: int, limit: int = 10) -> list[dict[str, Any]]:
        """Return top wealthiest users in server."""
        async with self.db.execute(
            """
            SELECT *, (wallet + bank) as net_worth
            FROM economy
            WHERE guild_id = ?
            ORDER BY net_worth DESC
            LIMIT ?
            """,
            (guild_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # =========================================================================
    # POLLS
    # =========================================================================

    async def create_poll(
        self,
        guild_id: int,
        channel_id: int,
        message_id: int,
        question: str,
        options: list[str],
        author_id: int,
    ) -> int:
        """Save a new interactive poll record."""
        now = int(time.time())
        options_json = json.dumps(options)
        votes_json = json.dumps({})
        cursor = await self.db.execute(
            """
            INSERT INTO polls (guild_id, channel_id, message_id, question, options_json, votes_json, author_id, closed, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (guild_id, channel_id, message_id, question, options_json, votes_json, author_id, now),
        )
        await self.db.commit()
        return cursor.lastrowid or 0

    async def get_poll_by_message(self, message_id: int) -> dict[str, Any] | None:
        """Retrieve poll record by target Discord message ID."""
        async with self.db.execute(
            "SELECT * FROM polls WHERE message_id = ?", (message_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_poll_votes(self, message_id: int, votes: dict[str, int]) -> None:
        """Update votes mapping on an active poll."""
        await self.db.execute(
            "UPDATE polls SET votes_json = ? WHERE message_id = ?",
            (json.dumps(votes), message_id),
        )
        await self.db.commit()

    async def close_poll(self, message_id: int) -> None:
        """Close poll to prevent further votes."""
        await self.db.execute(
            "UPDATE polls SET closed = 1 WHERE message_id = ?", (message_id,)
        )
        await self.db.commit()
