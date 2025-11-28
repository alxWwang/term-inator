from abc import ABC, abstractmethod

class ModelInterface(ABC):
    @abstractmethod
    def send_message(self, prompt: str) -> str:
        """Send a message to the model and get a response."""
        pass

    @abstractmethod
    def send_message_stream(self, prompt: str):
        """Send a message to the model and get a streaming response."""
        pass

    @abstractmethod
    def generate_content(self, contents: str) -> str:
        """Generate content based on the provided input."""
        pass

    @abstractmethod
    def deserialize_history(self, flat_msgs: list) -> list | None:
        """Deserialize a flat list of messages into the model's history format."""
        pass

    @abstractmethod
    def create_chat(self, history_data):
        pass
