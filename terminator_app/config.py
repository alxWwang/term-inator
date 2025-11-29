"""

Configuration constants for the Terminator application.
Centralizes all paths, identifiers, and configuration values.
"""

import importlib.resources
import os
import shutil


class Config:
    """Application-wide configuration constants."""

    # Base paths (user home directory)
    USER_BASE_PATH = os.path.expanduser("~/.terminator/user")
    BASE_CONFIG_PATH = os.path.join(USER_BASE_PATH, "config")
    BASE_DATA_PATH = os.path.join(USER_BASE_PATH, "data")

    # File paths
    BINDING_FILE_PATH = os.path.join(BASE_CONFIG_PATH, "bindings.conf")
    CSS_FILE_PATH = os.path.join(BASE_CONFIG_PATH, "style.conf")
    CONVERSATION_HISTORY_PATH = os.path.join(
        BASE_DATA_PATH, "conversation_history.json"
    )
    CLIPBOARD_IMAGE_SAVE_PATH = os.path.join(BASE_DATA_PATH, "clipboard_images")

    # Resource names for package access (for defaults)
    BINDINGS_RESOURCE = ("terminator.user.config", "bindings.conf")
    CSS_RESOURCE = ("terminator.user.config", "style.conf")
    CONVERSATION_HISTORY_RESOURCE = (
        "terminator.user.data",
        "conversation_history.json",
    )

    @staticmethod
    def initialize_user_directories():
        """Initialize user directories and copy default files if they don't exist."""
        # Create directories
        os.makedirs(Config.BASE_CONFIG_PATH, exist_ok=True)
        os.makedirs(Config.BASE_DATA_PATH, exist_ok=True)
        os.makedirs(Config.CLIPBOARD_IMAGE_SAVE_PATH, exist_ok=True)

        # Copy default config files if they don't exist
        config_files = [
            ("bindings.conf", Config.BINDINGS_RESOURCE),
            ("style.conf", Config.CSS_RESOURCE),
        ]

        for filename, resource in config_files:
            user_file = os.path.join(Config.BASE_CONFIG_PATH, filename)
            if not os.path.exists(user_file):
                try:
                    with importlib.resources.files(*resource).open("r") as src:
                        with open(user_file, "w") as dst:
                            dst.write(src.read())
                except Exception as e:
                    print(f"Warning: Could not copy default {filename}: {e}")

        # Copy default data files if they don't exist
        data_files = [
            ("conversation_history.json", Config.CONVERSATION_HISTORY_RESOURCE),
        ]

        for filename, resource in data_files:
            user_file = os.path.join(Config.BASE_DATA_PATH, filename)
            if not os.path.exists(user_file):
                try:
                    with importlib.resources.files(*resource).open("r") as src:
                        with open(user_file, "w") as dst:
                            dst.write(src.read())
                except Exception as e:
                    print(f"Warning: Could not copy default {filename}: {e}")

    # UI identifiers
    CONVERSATION_BUTTON_PREFIX = "terminator_button_conv_"
    NEW_CONVERSATION_BUTTON_ID = "terminator_button_new_conversation"

    # UI Element IDs
    CHAT_PANEL_ID = "chat_panel"
    CHAT_SCROLL_ID = "chat_scroll"
    CHAT_INPUT_ID = "chat_input_container"
    HISTORY_CONTAINER_ID = "history_container"
    MAIN_CONTAINER_ID = "main_container"

    # UI Classes
    CONVERSATION_BUTTON_CLASS = "conversation-button"

    # Containers
    HISTORY_PANEL_CONTAINER_ID = "history_panel_container"
    CHAT_CONTAINER_ID = "chat_container"
    CHAT_SUB_CONTAINER_ID = "chat_sub_container"

    # App metadata
    APP_TITLE = "Terminator Interface"


class Prompts:
    TITLE_PROMPT_TEMPLATE = """Based on this conversation, provide a very short title (3-5 words max):\n\n{conversation_text}\n\nTitle:"""
    DEBUG_AI_RESPONSE_TEMPLATE = "[DEBUG] AI response to: {prompt}"
    ERROR_API_RESPONSE_TEMPLATE = (
        "Error: Could not get a response from the model. {error}"
    )
    ERROR_UNEXPECTED_RESPONSE_TEMPLATE = "Error: An unexpected error occurred. {error}"


class UserConfig:
    """User-configurable settings for AI model and conversation management."""

    # ============================================================
    # AI Model Configuration
    # ============================================================

    # Model selection (Gemini models)
    MODEL_NAME = "gemini-2.0-flash-exp"  # Options: "gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"

    # Temperature (0.0 = deterministic, 2.0 = very creative)
    TEMPERATURE = 1.0

    # Maximum tokens in response
    MAX_OUTPUT_TOKENS = 8192

    # Top-p sampling (nucleus sampling)
    TOP_P = 0.95

    # Top-k sampling
    TOP_K = 40

    # Base template for new conversations (timestamps set at creation time)
    BASE_CONVERSATION = {
        "id": None,
        "timestamp": None,
        "title": None,
        "messages": [
            {
                "user": {"role": "user", "parts": [], "timestamp": None},
                "model": {
                    "role": "model",
                    "parts": [
                        {
                            "text": "Hello! How can I assist you today?"}],
                    "timestamp": None,
                },
                "ai_pending": False,
                "gen_id": None,
            }
        ],
    }

    # Maximum messages to keep in conversation history (None = unlimited)
    # Reducing this saves tokens and costs
    MAX_HISTORY_MESSAGES = None  # Set to 50, 100, etc. to limit

    # Maximum messages to send as context to AI (for token cost control)
    # Even if you have 1000 messages, only send last N to API
    MAX_CONTEXT_MESSAGES = 50

    # Auto-complete incomplete conversations on load
    AUTO_COMPLETE_ON_LOAD = True

    # Auto-complete only recent conversations (hours)
    AUTO_COMPLETE_MAX_AGE_HOURS = 24  # Only auto-complete conversations from last 24h

    # ============================================================
    # Session Management (Token Cost Control)
    # ============================================================

    # Maximum number of AI sessions to keep open simultaneously
    MAX_OPEN_SESSIONS = 5

    # Close sessions after this many minutes of inactivity
    SESSION_TIMEOUT_MINUTES = 30

    # Session management strategy
    # "lru" = Least Recently Used (close oldest)
    # "fifo" = First In First Out
    SESSION_EVICTION_STRATEGY = "lru"

    # ============================================================
    # Response Settings
    # ============================================================

    # Enable streaming responses (show text as it's generated)
    STREAMING_ENABLED = False

    # Streaming chunk delay (seconds) - for visual effect
    STREAMING_DELAY = 0.05

    # ============================================================
    # Safety Settings
    # ============================================================

    # Content safety thresholds
    # Options: "BLOCK_NONE", "BLOCK_ONLY_HIGH", "BLOCK_MEDIUM_AND_ABOVE", "BLOCK_LOW_AND_ABOVE"
    SAFETY_HARASSMENT = "BLOCK_MEDIUM_AND_ABOVE"
    SAFETY_HATE_SPEECH = "BLOCK_MEDIUM_AND_ABOVE"
    SAFETY_SEXUALLY_EXPLICIT = "BLOCK_MEDIUM_AND_ABOVE"
    SAFETY_DANGEROUS_CONTENT = "BLOCK_MEDIUM_AND_ABOVE"

    # ============================================================
    # UI/UX Settings
    # ============================================================

    # Messages per page in chat view
    MESSAGES_PER_PAGE = 2

    # Auto-generate titles for conversations
    AUTO_GENERATE_TITLES = True

    # Maximum words in auto-generated titles
    TITLE_MAX_WORDS = 5

    # Show typing indicators
    SHOW_TYPING_INDICATOR = True

    # ============================================================
    # Performance & Caching
    # ============================================================

    # Cache API responses (for debugging/development)
    CACHE_RESPONSES = False

    # Response cache duration (seconds)
    CACHE_DURATION = 3600

    # ============================================================
    # Advanced Settings
    # ============================================================

    # Retry failed API calls
    RETRY_ON_ERROR = True
    MAX_RETRIES = 3

    # Request timeout (seconds)
    REQUEST_TIMEOUT = 60

    # Debug mode (more verbose logging)
    DEBUG_MODE = False
