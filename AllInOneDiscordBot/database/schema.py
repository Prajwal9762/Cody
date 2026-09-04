"""SQLite database schema definitions."""

SCHEMA_STATEMENTS = """
-- Guild configuration table
CREATE TABLE IF NOT EXISTS guild_config (
    guild_id INTEGER PRIMARY KEY,
    prefix TEXT DEFAULT '!',
    mod_log_channel_id INTEGER,
    server_log_channel_id INTEGER,
    welcome_channel_id INTEGER,
    welcome_message TEXT DEFAULT 'Welcome to {server}, {user}! We now have {count} members.',
    leave_channel_id INTEGER,
    leave_message TEXT DEFAULT '{user} has left {server}. We now have {count} members.',
    ticket_category_id INTEGER,
    ticket_log_channel_id INTEGER,
    autorole_id INTEGER,
    level_up_channel_id INTEGER,
    automod_enabled INTEGER DEFAULT 1,
    xp_rate REAL DEFAULT 1.0
);

-- Member moderation warnings
CREATE TABLE IF NOT EXISTS warns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    moderator_id INTEGER NOT NULL,
    reason TEXT NOT NULL,
    timestamp INTEGER NOT NULL
);

-- Complete moderation action history (kick, ban, mute, warn, etc.)
CREATE TABLE IF NOT EXISTS moderation_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    case_type TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    moderator_id INTEGER NOT NULL,
    reason TEXT,
    duration INTEGER,
    timestamp INTEGER NOT NULL
);

-- Auto-moderation rule toggles and filters per guild
CREATE TABLE IF NOT EXISTS automod_rules (
    guild_id INTEGER NOT NULL,
    rule_type TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    extra_data TEXT,
    PRIMARY KEY (guild_id, rule_type)
);

-- Support ticket system records
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    status TEXT DEFAULT 'open',
    created_at INTEGER NOT NULL,
    closed_at INTEGER,
    closed_by INTEGER,
    reason TEXT
);

-- Self-assignable role panels
CREATE TABLE IF NOT EXISTS self_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    emoji TEXT,
    label TEXT NOT NULL,
    description TEXT,
    category TEXT DEFAULT 'General'
);

-- XP and leveling system
CREATE TABLE IF NOT EXISTS user_levels (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 0,
    last_xp_time INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

-- Virtual economy system
CREATE TABLE IF NOT EXISTS economy (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    wallet INTEGER DEFAULT 0,
    bank INTEGER DEFAULT 0,
    last_daily INTEGER DEFAULT 0,
    last_work INTEGER DEFAULT 0,
    last_beg INTEGER DEFAULT 0,
    last_rob INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

-- Interactive polls
CREATE TABLE IF NOT EXISTS polls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    question TEXT NOT NULL,
    options_json TEXT NOT NULL,
    votes_json TEXT NOT NULL,
    author_id INTEGER NOT NULL,
    closed INTEGER DEFAULT 0,
    created_at INTEGER NOT NULL
);

-- Indexes for lightning fast queries
CREATE INDEX IF NOT EXISTS idx_warns_guild_user ON warns(guild_id, user_id);
CREATE INDEX IF NOT EXISTS idx_cases_guild_user ON moderation_cases(guild_id, user_id);
CREATE INDEX IF NOT EXISTS idx_tickets_channel ON tickets(channel_id);
CREATE INDEX IF NOT EXISTS idx_levels_xp ON user_levels(guild_id, xp DESC);
CREATE INDEX IF NOT EXISTS idx_economy_balance ON economy(guild_id, wallet + bank DESC);
"""
