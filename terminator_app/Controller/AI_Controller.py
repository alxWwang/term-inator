import os

from terminator_app.config import Config

# try:
from terminator_app.Models import GoogleModel as gm
from terminator_app.Models import LMStudioModel as lm
from terminator_app.Interfaces.ModelInterface import ModelInterface
from terminator_app.Data import load
from terminator_app.config import Prompts
# except ImportError:
#     from Interfaces.ModelInterface import ModelInterface
#     from config import Prompts
import threading

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv()

GENAI_API_KEY = os.environ.get("GENAI_API_KEY")

class AIController:
    # Prompt templates
    TITLE_PROMPT_TEMPLATE = Prompts.TITLE_PROMPT_TEMPLATE

    def __init__(self, model_class: type[ModelInterface], model_config: dict):
        """
        Initialize the AIController with a specific model class and configuration.

        Args:
            model_class (type[ModelInterface]): The class of the model to instantiate.
            model_config (dict): Configuration parameters for the model.
        """
        self.model_class = model_class or lm.LMStudioModel or gm.GoogleModel
        self.model_config = model_config or {"model_name": "qwen/qwen3-14b"} or {"api_key": GENAI_API_KEY}
        self.model = self.model_class(**self.model_config)
        self.sessions = {}

    @staticmethod
    def flatten_conversation_messages(messages: list) -> list:
        """Flatten greeting + user/model pairs into a flat list of messages."""
        if not messages:
            return []
        flat_msgs = []
        for pair in messages[1:]:  # Skip greeting at index 0
            if isinstance(pair, dict) and 'user' in pair and 'model' in pair:
                if pair['user']:
                    flat_msgs.append(pair['user'])
                if pair['model']:
                    flat_msgs.append(pair['model'])
            else:
                flat_msgs.append(pair)
        return flat_msgs

    def open_session(self, conv_id: str, new: bool = False):
        """Open a new session or load an existing one.

        Args:
            conv_id (str): The conversation ID.
            new (bool): Whether to create a new session explicitly.
        """
        if conv_id in self.sessions and not new:
            return

        history = self.deserialize_history(conv_id) if not new else None
        self.sessions[conv_id] = self.model.create_chat(history)

    # Databse -> what the model understands
    def deserialize_history(self, conv_id: str) -> list | None:
        """Loads a list of standard dictionaries into the chat history, flattening pairs."""
        conversation_history = load.DataLoader.load_conversation_history(Config.CONVERSATION_HISTORY_PATH)
        loaded_history = load.DataLoader.get_conversation_by_id(conversation_history, conv_id)

        serialized_history = loaded_history.get("messages") if loaded_history else None
        if not serialized_history:
            return None

        flat_msgs = AIController.flatten_conversation_messages(serialized_history)

        return self.model.deserialize_history(flat_msgs)

    def get_response(self, conv_id: str, prompt: str, streaming: bool = False) -> str:
        """Get a response from the model for a given conversation ID."""
        try:
            session = self.sessions.get(conv_id)
            if not session:
                raise ValueError(f"Session {conv_id} does not exist.")

            # Use the model's send_message method instead of the Chat object
            if streaming:
                return session.send_message_stream(prompt)
            return session.send_message(prompt)
        except Exception as e:
            return self._handle_error(e)

    def get_static_response(self, prompt: str) -> str:
        """Get a single response without maintaining conversation history."""
        try:
            response = self.model.generate_content(prompt)
            return response
        except Exception as e:
            return self._handle_error(e)

    def generate_title_from_conversation(self, conv: dict, callback=None) -> str:
        """Generate a concise title based on the conversation's messages."""
        def _generate_title():
            try:
                messages = conv.get('messages', [])
                flat_msgs = self.flatten_conversation_messages(messages)
                if not flat_msgs:
                    return "New Conversation"

                conversation_text = self._build_conversation_text(flat_msgs[:6])
                prompt = self.TITLE_PROMPT_TEMPLATE.format(conversation_text=conversation_text)
                response_text = self.get_static_response(prompt)
                return response_text.strip()
            except Exception as e:
                return self._handle_title_error(e, default="Untitled Conversation")

        if callback:
            thread = threading.Thread(target=lambda: callback(conv.get('id'), _generate_title()), daemon=True)
            thread.start()
            return "Generating..."
        return _generate_title()

    def _build_conversation_text(self, messages: list[dict]) -> str:
        """Build a formatted conversation text from messages."""
        return "\n".join(
            f"{msg.get('role', '')}: {' '.join(p.get('text', '') for p in msg.get('parts', []))}"
            for msg in messages
        )

    def _handle_error(self, error: Exception, default: str = "") -> str:
        """Handle errors and return a formatted error message."""
        print(f"An error occurred: {error}")
        return Prompts.ERROR_UNEXPECTED_RESPONSE_TEMPLATE.format(error=error) or default
    
    def _handle_title_error(self, error: Exception, default: str = "") -> str:
        """Handle errors and return a formatted error message."""
        print(f"An error occurred: {error}")
        return ""