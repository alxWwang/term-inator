from terminator_app.Interfaces.ModelInterface import ModelInterface
from google import genai
from google.genai import types
from google.genai.errors import APIError

class GoogleModel(ModelInterface):
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-pro"):
        """
        Initialize the Google GenAI model client.

        Args:
            api_key (str): The API key for Google GenAI.
            model_name (str): The name of the model to use.
        """
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def send_message(self, prompt: str) -> str:
        """
        Send a message to the Google GenAI model and get a response.

        Args:
            prompt (str): The input prompt for the model.

        Returns:
            str: The model's response.
        """
        try:
            return self.client.chats.create(model=self.model_name).send_message(prompt).text
        except APIError as e:
            raise RuntimeError(f"Google API error: {e}")
        
    def create_chat(self, history_data):
        """
        Create a chat session with optional history.

        Args:
            history_data: The chat history data to initialize the session.

        Returns:
            Chat session object.
        """
        try:
            return self.client.chats.create(model=self.model_name, history=history_data)
        except APIError as e:
            raise RuntimeError(f"Google API error: {e}")

    def send_message_stream(self, prompt: str):
        """
        Send a message to the Google GenAI model and get a streaming response.

        Args:
            prompt (str): The input prompt for the model.

        Yields:
            str: The model's response chunks.
        """
        try:
            chat = self.client.chats.create(model=self.model_name)
            for chunk in chat.send_message_stream(prompt):
                yield chunk
        except APIError as e:
            raise RuntimeError(f"Google API error: {e}")

    def generate_content(self, contents: str) -> str:
        """
        Generate content based on the provided input.

        Args:
            contents (str): The input content for the model.

        Returns:
            str: The generated content.
        """
        try:
            response = self.client.models.generate_content(model=self.model_name, contents=contents)
            return response.text
        except APIError as e:
            raise RuntimeError(f"Google API error: {e}")
        

    def deserialize_history(self, flat_msgs: list) -> list | None:
        restored_history = []
        for msg in flat_msgs:
            restored_history.append(
                types.Content(
                    role=msg["role"],
                    parts=[types.Part(text=p["text"]) for p in msg["parts"]]
                )
            )
        return restored_history