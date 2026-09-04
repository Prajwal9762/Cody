"""Helper functions for time parsing, level formulas, string rendering, and numbers."""

import math
import re

DURATION_REGEX = re.compile(r"(\d+)\s*([smhdw])", re.IGNORECASE)

TIME_MULTIPLIERS = {
    "s": 1,
    "m": 60,
    "h": 3600,
    "d": 86400,
    "w": 604800,
}


def parse_duration(time_str: str) -> int:
    """
    Parse a human-readable duration string into total seconds.
    Examples: '10m', '2h30m', '1d', '45s'.
    Raises ValueError if invalid.
    """
    matches = DURATION_REGEX.findall(time_str.strip())
    if not matches:
        raise ValueError(f"Invalid duration format: '{time_str}'. Use e.g. '10m', '2h', '1d'.")

    total_seconds = 0
    for value, unit in matches:
        unit_lower = unit.lower()
        if unit_lower in TIME_MULTIPLIERS:
            total_seconds += int(value) * TIME_MULTIPLIERS[unit_lower]

    return total_seconds


def format_duration(seconds: int) -> str:
    """Format seconds into human-readable string like '2d 4h 15m 30s'."""
    if seconds <= 0:
        return "0s"

    parts = []
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)

    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)


def xp_for_level(level: int) -> int:
    """Calculate cumulative XP required to reach a specific level."""
    if level <= 0:
        return 0
    return int(100 * (level ** 1.5))


def calculate_level(xp: int) -> int:
    """Calculate current level from cumulative XP."""
    if xp <= 0:
        return 0
    return int((xp / 100) ** (1 / 1.5))


def render_progress_bar(current: int, total: int, length: int = 12) -> str:
    """Generate a Unicode visual progress bar [████░░░░░░░░]."""
    if total <= 0:
        total = 1
    fraction = max(0.0, min(1.0, current / total))
    filled = int(round(length * fraction))
    empty = length - filled
    return "█" * filled + "░" * empty


def format_number(amount: int) -> str:
    """Format integers with commas for thousands separation."""
    return f"{amount:,}"


def truncate_string(text: str, max_length: int = 1024, suffix: str = "...") -> str:
    """Safely truncate text so it never violates Discord embed length constraints."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix
