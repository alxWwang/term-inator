from textual.binding import Binding
import json
import os

class DataLoader:
    def load_bindings(filepath: str) -> list[Binding]:
        """Load key bindings from file with error handling."""
        bindings = []
        try:
            with open(filepath, 'r') as file:
                for line in file:
                    parts = line.strip().split()
                    if len(parts) == 3:
                        key, action, description = parts
                        bindings.append(
                            Binding(key, action, description, show=True)
                        )
        except FileNotFoundError:
            print(f"Warning: Bindings file not found: {filepath}")
        except IOError as e:
            print(f"Warning: Error reading bindings file: {e}")
        except Exception as e:
            print(f"Warning: Unexpected error loading bindings: {e}")
        return bindings

    def load_CSS(filepath: str) -> str:
        """Load CSS from file with error handling."""
        try:
            with open(filepath, 'r') as file:
                return file.read()
        except FileNotFoundError:
            print(f"Warning: CSS file not found: {filepath}")
            return ""
        except IOError as e:
            print(f"Warning: Error reading CSS file: {e}")
            return ""
        except Exception as e:
            print(f"Warning: Unexpected error loading CSS: {e}")
            return ""

    @staticmethod
    def load_conversation_history(filepath: str) -> list[dict]:
        if not os.path.exists(filepath):
            with open(filepath, 'w') as file:
                json.dump([], file)
            return []
        try:
            with open(filepath, 'r') as file:
                return json.load(file)
        except Exception:
            # This catches empty files, corrupted JSON, AND permission errors
            # It's much safer than just checking file size.
            return []

    @staticmethod
    def save_conversation_history(filepath: str, conversation_history: list[dict]) -> bool:
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(conversation_history, f, indent=2)
            return True
        except Exception:
            return False

    @staticmethod
    def get_conversation_by_id(conversation_history: list[dict], conversation_id: str) -> dict | None:
        for conversation in conversation_history:
            if conversation.get('id') == conversation_id:
                return conversation
        return None

    @staticmethod
    def save_conversation_title(filepath: str, conversation_id: str, new_title: str) -> bool:
        """Save a new title for a specific conversation.
        
        Args:
            filepath: Path to the conversation history file
            conversation_id: ID of the conversation to update
            new_title: New title to set for the conversation
            
        Returns:
            True if save was successful, False otherwise
        """
        try:
            # Load the conversation history
            conversation_history = DataLoader.load_conversation_history(filepath)
            
            # Find and update the conversation
            conversation = DataLoader.get_conversation_by_id(conversation_history, conversation_id)
            if conversation is None:
                print(f"Warning: Conversation {conversation_id} not found")
                return False
            
            # Update the title
            conversation['title'] = new_title
            
            # Save the entire history
            return DataLoader.save_conversation_history(filepath, conversation_history)
            
        except Exception as e:
            print(f"Error: Failed to save conversation title: {e}")
            return False