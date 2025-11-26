from google import genai
from google.genai import types
from google.genai.errors import APIError # Good practice for error handling

import os
try:
    from terminator_app.Data import load
    from terminator_app.config import Config, Prompts
except ImportError:
    from config import Config, Prompts
    from Data import load
import threading

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv()

GENAI_API_KEY = os.environ.get("GENAI_API_KEY")

class AIController:
    # Prompt templates
    TITLE_PROMPT_TEMPLATE = Prompts.TITLE_PROMPT_TEMPLATE
    
    @staticmethod
    def flatten_conversation_messages(messages):
        """Flatten greeting + user/model pairs into a flat list of messages."""
        if not messages:
            return []
        flat_msgs = []
        # Always skip greeting at index 0
        for pair in messages[1:]:
            if isinstance(pair, dict) and 'user' in pair and 'model' in pair:
                if pair['user']:
                    flat_msgs.append(pair['user'])
                if pair['model']:
                    flat_msgs.append(pair['model'])
            else:
                flat_msgs.append(pair)
        return flat_msgs
    def __init__(self, model_name: str = "gemini-2.5-pro"):
        self.client = genai.Client(api_key=GENAI_API_KEY)
        self.model_name = model_name
        self.chat = {}
        
    def open_session(self, conv_id: str, new = False):
        # 1. **Crucial Step:** Create a Chat object to manage the conversation.
        if self.chat.get(conv_id) is not None:
            return
        deserialize_history = self.deserialize_history(conv_id)
        if deserialize_history is not None:
            self.chat[conv_id] = self.client.chats.create(
                model=self.model_name,
                history=deserialize_history
            )
            return
        self.chat[conv_id] = self.client.chats.create(
                model=self.model_name,
        )

    def get_response(self, conv_id: str, prompt: str, streaming: bool = False) -> str:
        try:
            if streaming:
                return self.chat[conv_id].send_message_stream(prompt)
            else:
                return self.chat[conv_id].send_message(prompt).text
        except APIError as e:
            # Handle API-specific errors
            print(f"An API error occurred: {e}")
            return  Prompts.ERROR_API_RESPONSE_TEMPLATE.format(error=e)
        except Exception as e:
            # Handle other potential errors
            print(f"An unexpected error occurred: {e}")
            return  Prompts.ERROR_UNEXPECTED_RESPONSE_TEMPLATE.format(error=e)
    
    def get_static_response(self, conv_id: str, prompt: str) -> str:
        """Get a single response without maintaining conversation history."""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text
        except APIError as e:
            # Handle API-specific errors
            print(f"An API error occurred: {e}")
            return  Prompts.ERROR_API_RESPONSE_TEMPLATE.format(error=e)
        except Exception as e:
            # Handle other potential errors
            print(f"An unexpected error occurred: {e}")
            return  Prompts.ERROR_UNEXPECTED_RESPONSE_TEMPLATE.format(error=e)
    
    def generate_title_from_conversation(self, conv: dict, callback=None) -> str:
        """Generate a concise title based on the conversation's messages.
        
        Args:
            conv: Conversation dictionary with messages
            callback: Optional callback function(conv_id, title) to call when done
            
        Returns:
            Title string if synchronous, or spawns thread and returns immediately
        """
        
        def _generate_title_thread():
            try:
                messages = conv.get('messages', [])
                flat_msgs = AIController.flatten_conversation_messages(messages)
                if not flat_msgs:
                    title = "New Conversation"
                else:
                    conversation_text = ""
                    for msg in flat_msgs[:6]:
                        role = msg.get('role', '')
                        parts = msg.get('parts', [])
                        text = ' '.join(p.get('text', '') for p in parts if isinstance(p, dict))
                        conversation_text += f"{role}: {text}\n"
                    prompt = AIController.TITLE_PROMPT_TEMPLATE.format(conversation_text=conversation_text)
                    response = self.client.models.generate_content(
                        model=self.model_name,
                        contents=prompt
                    )
                    title = response.text.strip()
                if callback:
                    callback(conv.get('id'), title)
                return title
            except Exception as e:
                print(f"Error generating title: {e}")
                title = "Untitled Conversation"
                if callback:
                    callback(conv.get('id'), title)
                return title
        
        # If callback provided, run in thread (async)
        if callback:
            thread = threading.Thread(target=_generate_title_thread, daemon=True)
            thread.start()
            return "Generating..."  # Immediate return
        else:
            # Synchronous execution
            return _generate_title_thread()
        
    

    def serialize_history(self, conv_id: str) -> list[dict]:
        """Converts a list of Content objects to a list of standard dictionaries."""
        history = self.chat[conv_id].history
        serialized = []
        for content in history:
            # Each Content object contains the role and a list of parts
            serialized.append({
                "role": content.role,
                "parts": [
                    # We assume simple text parts for this example
                    {"text": part.text} 
                    for part in content.parts
                    if hasattr(part, 'text')
                ]
            })
        return serialized
    
    def deserialize_history(self, conv_id: str) -> list[types.Content] | None:
        """Loads a list of standard dictionaries into the chat history, flattening pairs."""
        conversation_history = load.DataLoader.load_conversation_history(Config.CONVERSATION_HISTORY_PATH)
        loaded_history = load.DataLoader.get_conversation_by_id(conversation_history, conv_id)

        serialized_history = loaded_history.get("messages") if loaded_history else None
        if not serialized_history:
            return None

        flat_msgs = AIController.flatten_conversation_messages(serialized_history)

        restored_history = []
        for msg in flat_msgs:
            restored_history.append(
                types.Content(
                    role=msg["role"],
                    parts=[types.Part(text=p["text"]) for p in msg["parts"]]
                )
            )
        return restored_history

    def read_content_object(self, content: types.Content) -> dict:
        """
        Reads a types.Content object and extracts data from all its parts 
        into a simple dictionary format.
        """
        if not isinstance(content, types.Content):
            raise TypeError("Input must be a types.Content object.")

        # Initialize a dictionary to hold the extracted information
        extracted_data = {
            "role": content.role,
            "text": [],           # List to hold accumulated text strings
            "function_calls": [], # List to hold structured function call data
            "media_data": [],     # List to hold info about image/audio/video parts
        }

        # Iterate through every part in the message
        for part in content.parts:
            
            # 1. Simple Text
            if part.text:
                extracted_data["text"].append(part.text)
                
            # 2. Function Call (The model is asking the code to run a tool)
            elif hasattr(part, 'function_call') and part.function_call:
                extracted_data["function_calls"].append({
                    "name": part.function_call.name,
                    "args": dict(part.function_call.args)  # Convert args to standard dict
                })
                
            # 3. Function Response (The code is sending tool results back to the model)
            elif hasattr(part, 'function_response') and part.function_response:
                extracted_data["text"].append(
                    f"[FUNCTION RESPONSE: {part.function_response.name} - See code for full result]"
                )
                
            # 4. Inline Multimodal Data (Images, audio, video)
            elif hasattr(part, 'inline_data') and part.inline_data:
                extracted_data["media_data"].append({
                    "mime_type": part.inline_data.mime_type,
                    "size": f"{len(part.inline_data.data) / 1024:.2f} KB"
                })
                
        # Combine text parts into a single string for convenience
        extracted_data["text"] = "".join(extracted_data["text"])
        
        return extracted_data