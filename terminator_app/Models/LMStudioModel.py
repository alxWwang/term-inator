from collections import deque
import threading
from time import time
import lmstudio as lms
from lmstudio.history import Chat
import re
import time
from .model import LocalConversation

import requests

'''
Creates session and adds to history

'''
class LMStudioModel():
    def __init__(self, model_name: str, config: dict = None):
        self.client = lms.llm(model_name, config=config)

    def create_chat(self, history_data):
        """
        Initializes the chat object and injects the message history.
        Accepts either a dict {"messages": []} or a raw list of messages.
        """

        sys_prompt = '''
        ## Role
        You are a helpful assistant for the user, Wang. 
        Provide clear, concise, and friendly responses. Use emojis where appropriate.
        For complex tasks:
        1. Break them into clear, numbered steps.
        2. Identify which steps require tools (e.g., search_online, create_file) and which can be done from your knowledge.
        3. Avoid overthinking or looping — if a step can be done without a tool, do it immediately.
        Always invite follow-up questions.
        '''
        local_conversation = LocalConversation(system_prompt=sys_prompt, model_client=self.client)

        # Handle different input types
        if isinstance(history_data, dict):
            messages = history_data.get("messages", [])
        elif isinstance(history_data, list):
            messages = history_data
        else:
            messages = []

        # Inject messages into the active session
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")

            if role == "system":
                local_conversation.add_assistant_message(content)
            elif role == "user":
                local_conversation.add_user_message(content)
            elif role in ["assistant", "model"]:
                local_conversation.add_assistant_message(content)
        
        print(f"Chat created with {len(messages)} past messages injected.")
        return local_conversation
    
    def generate_content(self, contents: str) -> str:
        return self.extract_true_answer(self.client.complete(contents).parsed)
    
    @staticmethod
    def extract_true_answer(raw_text: str) -> str:
        """
        Parses the model output to separate the internal 'thought process' 
        from the final response.
        
        Target Format: <|channel|>final<|message|>The actual answer...
        """
        # 1. Define the pattern that marks the start of the REAL answer
        # We use re.DOTALL so the (.) wildcard matches newlines too.
        pattern = r"<\|channel\|>final<\|message\|>(.*)"
        
        match = re.search(pattern, raw_text, re.DOTALL)
        
        if match:
            # Found the tag! Return everything after it.
            return match.group(1).strip()
        
        # 2. Fallback for 'DeepSeek-R1' style tags (common in other local models)
        # Some models use <think>...</think>
        if "<think>" in raw_text and "</think>" in raw_text:
            # Remove the thought block entirely
            return re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()

        # 3. If no tags are found, the model probably just replied normally.
        return raw_text.strip()

    @staticmethod
    def deserialize_history(flat_msgs: list) -> list:

        clean_history = []
        
        for msg in flat_msgs:
            # --- 1. Map Roles ---
            role = msg.get("role")
            if role == "model":
                role = "assistant"
            content = ""
            parts = msg.get("parts", [])
            if parts and isinstance(parts, list) and "text" in parts[0]:
                content = parts[0]["text"]
            else:
                content = msg.get("content", "")
            if "<|channel|>final<|message|>" in content:
                import re
                match = re.search(r"<\|channel\|>final<\|message\|>(.*)", content, re.DOTALL)
                if match:
                    content = match.group(1).strip()

            # --- 5. Final Append ---
            if content:
                clean_history.append({"role": role, "content": content})

        return clean_history

