"""Permission checks and Discord role hierarchy safety verifications."""

import discord


def can_moderate(
    moderator: discord.Member, target: discord.Member
) -> tuple[bool, str]:
    """
    Verify whether moderator has permission to perform an action on target based on:
    1. Server owner immunity
    2. Bot cannot moderate itself
    3. Moderator cannot moderate themselves
    4. Discord Role hierarchy (moderator top role > target top role)
    5. Bot's top role > target top role
    """
    # Self check
    if moderator.id == target.id:
        return False, "You cannot moderate yourself."

    # Bot self check
    bot_member = moderator.guild.me
    if target.id == bot_member.id:
        return False, "I cannot moderate myself."

    # Server owner immunity
    if target.id == moderator.guild.owner_id:
        return False, "You cannot moderate the Server Owner."

    # Moderator is server owner -> can moderate anyone
    if moderator.id == moderator.guild.owner_id:
        # Still verify bot's role hierarchy
        if target.top_role >= bot_member.top_role:
            return False, f"My role ({bot_member.top_role.name}) is not high enough to moderate {target.mention}."
        return True, ""

    # Role hierarchy check for moderator
    if target.top_role >= moderator.top_role:
        return (
            False,
            f"You cannot moderate {target.mention} because their highest role ({target.top_role.name}) "
            f"is higher or equal to your highest role ({moderator.top_role.name}).",
        )

    # Role hierarchy check for bot
    if target.top_role >= bot_member.top_role:
        return (
            False,
            f"I cannot moderate {target.mention} because their highest role ({target.top_role.name}) "
            f"is higher or equal to my highest role ({bot_member.top_role.name}).",
        )

    return True, ""


def bot_has_permissions(
    channel: discord.TextChannel | discord.Thread | discord.VoiceChannel,
    **permissions: bool,
) -> tuple[bool, list[str]]:
    """
    Check if the bot possesses specific permissions in a channel.
    Returns (has_all, missing_permissions_list).
    """
    me = channel.guild.me
    perms = channel.permissions_for(me)
    missing = [name for name, value in permissions.items() if getattr(perms, name, None) != value]
    return len(missing) == 0, missing
