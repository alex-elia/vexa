"""
Central location for defining Redis keys and patterns used across services.
"""

# --- Static Keys ---

# Stream where WhisperLive publishes transcription segments and session start events
TRANSCRIPTION_STREAM = "transcription_segments"

# Set used by transcription-collector to track active meetings (based on received segments)
ACTIVE_MEETINGS_SET = "active_meetings"

# Set used by transcription-collector background task to track session UIDs needing DB flush
DIRTY_SESSIONS_SET = "dirty_sessions"


# --- Key Prefixes/Patterns ---

# Prefix for Pub/Sub channels used to send commands from bot-manager to vexa-bot
BOT_COMMAND_PREFIX = "bot_commands:"

# Prefix for Hashes used by transcription-collector to temporarily store segments for a meeting
MEETING_SEGMENTS_PREFIX = "meeting:"
MEETING_SEGMENTS_SUFFIX = ":segments"

# Prefix for Sets used by bot-manager to track active bot containers per user (for concurrency)
ACTIVE_BOTS_PREFIX = "active_bots:"

# Prefix for Hashes used by transcription-collector to cache aggregate usage data per session
SESSION_AGG_PREFIX = "session_agg:"


# --- Helper Functions ---

def get_bot_command_channel(connection_id: str) -> str:
    """Generates the Redis Pub/Sub channel name for sending commands to a specific bot instance."""
    return f"{BOT_COMMAND_PREFIX}{connection_id}"

def get_meeting_segments_key(meeting_id: int) -> str:
    """Generates the Redis Hash key for storing temporary segments for a meeting."""
    return f"{MEETING_SEGMENTS_PREFIX}{meeting_id}{MEETING_SEGMENTS_SUFFIX}"

def get_active_bots_key(user_id: int) -> str:
    """Generates the Redis Set key for tracking active bots for a specific user."""
    return f"{ACTIVE_BOTS_PREFIX}{user_id}"

def get_session_agg_key(session_uid: str) -> str:
    """Generates the Redis Hash key for caching aggregate usage data for a specific session."""
    return f"{SESSION_AGG_PREFIX}{session_uid}" 