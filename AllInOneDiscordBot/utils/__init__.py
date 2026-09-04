"""Utility package containing helpers, embeds, permissions, checks, and error handlers."""

from .embeds import (
    success_embed,
    error_embed,
    warning_embed,
    info_embed,
    mod_embed,
)
from .helpers import (
    parse_duration,
    format_duration,
    calculate_level,
    xp_for_level,
    render_progress_bar,
    format_number,
    truncate_string,
)
from .permissions import can_moderate, bot_has_permissions
from .errors import BotError, ModerationError, HierarchyError

__all__ = [
    "success_embed",
    "error_embed",
    "warning_embed",
    "info_embed",
    "mod_embed",
    "parse_duration",
    "format_duration",
    "calculate_level",
    "xp_for_level",
    "render_progress_bar",
    "format_number",
    "truncate_string",
    "can_moderate",
    "bot_has_permissions",
    "BotError",
    "ModerationError",
    "HierarchyError",
]
