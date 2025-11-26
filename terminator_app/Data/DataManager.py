"""
DataManager - Single source of truth for conversation history data.
Manages loading, saving, and accessing conversation data with thread safety.
"""
import threading
from typing import Optional
try:
    from terminator_app.Data import load
    from terminator_app.config import Config
except ImportError:
    from config import Config
    from Data import load

class DataManager:
    """Centralized manager for conversation history data."""
    
    def __init__(self):
        self._conversation_history: list[dict] = []
        self._lock = threading.RLock()  # Use RLock instead of Lock for reentrant locking
        self._conversation_dict: dict[str, dict] = {}
        self._history_path = Config.CONVERSATION_HISTORY_PATH
        self.load_from_disk()

    def load_from_disk(self) -> None:
        """Reload conversation history from disk."""
        with self._lock:
            self._conversation_history = load.DataLoader.load_conversation_history(self._history_path)
            # Build fast lookup dict
            self._conversation_dict = {
                conv['id']: conv 
                for conv in self._conversation_history 
                if conv.get('id')
            }

    def save_to_disk(self) -> bool:
        """Save conversation history to disk."""
        with self._lock:
            return load.DataLoader.save_conversation_history(self._history_path, self._conversation_history)

    def get_all_conversations(self) -> list[dict]:
        """Get a copy of all conversations from memory cache."""
        with self._lock:
            return list(self._conversation_history)

    def get_conversation_by_id(self, conv_id: str) -> Optional[dict]:
        """Get a conversation by ID from memory cache. Returns None if not found."""
        with self._lock:
            return self._conversation_dict.get(conv_id)

    def add_conversation(self, conversation: dict) -> bool:
        """Add a new conversation."""
        with self._lock:
            conv_id = conversation.get('id')
            if not conv_id or conv_id in self._conversation_dict:
                return False
            
            self._conversation_history.append(conversation)
            self._conversation_dict[conv_id] = conversation
            return self.save_to_disk()

    def update_conversation(self, conv_id: str, conversation: dict) -> bool:
        """Update an existing conversation."""
        with self._lock:
            existing = self._conversation_dict.get(conv_id)
            if not existing:
                return False
            
            # Update in place
            existing.update(conversation)
            return self.save_to_disk()

    def update_conversation_title(self, conv_id: str, title: str) -> bool:
        """Update a conversation's title."""
        with self._lock:
            conversation = self._conversation_dict.get(conv_id)
            if not conversation:
                return False
            
            conversation['title'] = title
            return self.save_to_disk()

    def add_message_to_conversation(self, conv_id: str, message: dict) -> bool:
        """Add a message to a conversation."""
        with self._lock:
            conversation = self._conversation_dict.get(conv_id)
            if not conversation:
                return False
            
            messages = conversation.get('messages', [])
            messages.append(message)
            conversation['messages'] = messages
            return self.save_to_disk()

    def delete_conversation(self, conv_id: str) -> bool:
        """Delete a conversation."""
        with self._lock:
            conversation = self._conversation_dict.get(conv_id)
            if not conversation:
                return False
            
            self._conversation_history.remove(conversation)
            del self._conversation_dict[conv_id]
            return self.save_to_disk()
