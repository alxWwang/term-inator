import lmstudio as lms
from lmstudio.history import Chat
import re

'''
Creates session and adds to history

'''
class LMStudioModel():
    def __init__(self, model_name: str):
        """
        Initialize the LMStudio model client.

        Args:
            model_name (str): The name of the loaded model in LM Studio.
        """
        # Get the model object from LM Studio
        self.client = lms.llm(model_name)

    def create_chat(self, history_data):
        """
        Initializes the chat object and injects the message history.
        Accepts either a dict {"messages": []} or a raw list of messages.
        """
        local_conversation = LocalConversation(system_prompt="You are a helpful assistant.", client=self.client)

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
                local_conversation.add_assistant_response(content)
            elif role == "user":
                local_conversation.add_user_message(content)
            elif role in ["assistant", "model"]:
                local_conversation.add_assistant_response(content)
        
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

'''
Currently does not add the model response to the 
'''
class LocalConversation():
    def __init__(self, system_prompt: str, client: lms.LLM):
        self.chat = Chat(system_prompt)
        self.client = client

    def add_user_message(self, content: str):
        self.chat.add_user_message(content)
    
    def add_assistant_response(self, content: str):
        self.chat.add_assistant_response(content)
    
    def send_message(self, prompt: str) -> str:
        if not self.chat:
            raise ValueError("Chat object is not initialized. Call create_chat first.")
        self.chat.add_user_message(prompt)
        response = self.client.respond(self.chat)
        return LMStudioModel.extract_true_answer(response.content)
    
    def send_message_stream(self, prompt: str):
        self.chat.add_user_message(prompt)
        reponse = ""
        for token in self.client.respond_stream(self.chat):
            if token.content:
                reponse += token.content
                yield token.content
        self.add_assistant_response(reponse)
        
    