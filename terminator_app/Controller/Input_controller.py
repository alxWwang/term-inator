
from time import time
from textual.widgets import Input
import threading
import time
from typing import List, Union
try:
    from terminator_app.config import Config
    from terminator_app.interfaces import ConversationDict, UserModelPairDict, MessageDict
except ImportError:
    from config import Config
    from interfaces import ConversationDict, UserModelPairDict, MessageDict


class InputController():

    def __init__(self, chat_controller, AI_controller, debug_mode=False) -> None:
        self.chat_controller = chat_controller
        self.AI_controller = AI_controller  # Placeholder for AI controller if needed
        self.debug_mode = debug_mode
        self.button_container = None  # Reference to button container
        self.buttons_visible = False
        self.is_ai_responding = False  # Track if AI is currently generating response
        self._response_lock = threading.Lock()  # Lock for is_ai_responding flag
        self.ai_handler = AIResponseHandler(self)
    
    def chat_input_controller(self, user_input: str, current_conversation: ConversationDict, input_field: Input, app_instance) -> None:
        """Handle user input submission and coordinate AI response."""
        idx = self._add_user_message(user_input, current_conversation, input_field)
        self.ai_handler.start_ai_response_thread((user_input, idx), current_conversation, app_instance)

    def auto_complete_conversation(self, conversation: ConversationDict) -> bool:
        """
        Automatically complete an incomplete conversation.
        Called when loading a conversation that's waiting for AI response.
        
        Returns:
            True if auto-completion was started, False otherwise
        """
        # Remove blocking logic
        if not self._is_incomplete_conversation(conversation):
            return False
        user_prompt = self._get_last_user_message(conversation)
        if not user_prompt:
            return False
        print(f"[AUTO-COMPLETE] Starting AI response for incomplete conversation...")
        return True

    def focus_to_chat_input(self, input_field: Input) -> None:
        """Set focus to chat input field."""
        input_field.focus()
    
    def _is_incomplete_conversation(self, conversation: ConversationDict) -> bool:
        """Check if conversation is waiting for AI response."""
        messages = conversation.get('messages', [])
        return messages and messages[-1].get('role') == 'user'
    
    def _get_last_user_message(self, conversation: ConversationDict) -> str:
        """Extract text from the last user message."""
        messages = conversation.get('messages', [])
        if not messages:
            return ""
        
        last_message = messages[-1]
        return ''.join(
            part.get('text', '') 
            for part in last_message.get('parts', []) 
            if isinstance(part, dict) and 'text' in part
        )
    
    def _add_user_message(self, user_input: str, conversation: ConversationDict, input_field: Input) -> int:
        """Add user message to conversation and clear input field, pairing with model response. Returns index of user message."""
        import datetime
        input_field.value = ""
        if 'messages' not in conversation:
            conversation['messages'] = []
        user_msg: MessageDict = {
            'role': 'user',
            'parts': [{'text': user_input}],
            'timestamp': datetime.datetime.now().isoformat()
        }
        if len(conversation['messages']) == 0 and conversation.get('id') and user_msg['role'] == 'user':
            pass
        pair: UserModelPairDict = {'user': user_msg, 'model': None, 'ai_pending': False}
        conversation['messages'].append(pair)
        idx = len(conversation['messages']) - 1
        print(f"User input received: {user_input} (index {idx})")
        self.chat_controller.write_conversation_to_history(conversation)
        return idx


# AI response logic is now handled by AIResponseHandler subclass
class AIResponseHandler:
    def __init__(self, parent) -> None:
        self.parent = parent

    def start_ai_response_thread(self, prompt_idx_tuple, conversation: ConversationDict, app_instance) -> None:
        thread = threading.Thread(
            target=self._get_ai_response_thread,
            args=(prompt_idx_tuple, conversation, app_instance),
            daemon=True
        )
        thread.start()

    def _get_ai_response_thread(self, prompt_idx_tuple, current_conversation: ConversationDict, app_instance) -> None:
        print("Starting AI response thread...")
        prompt, idx = prompt_idx_tuple
        messages: List[Union[MessageDict, UserModelPairDict]] = current_conversation.get('messages', [])
        context_parts = self._get_context_from_previous_messages(messages, idx)
        if context_parts:
            prompt = '\n'.join(context_parts) + '\n' + prompt
        response = self._get_response(prompt, current_conversation.get('id'))
        self._add_ai_message(response, current_conversation, idx)
        self._refresh_ui(app_instance)
        self._unlock_input(app_instance)

    def _get_context_from_previous_messages(self, messages: List[Union[MessageDict, UserModelPairDict]], idx: int) -> List[str]:
        """Extract user message texts from previous messages with empty model responses."""
        context_parts = []
        for i in range(1, idx):
            pair = messages[i]
            if isinstance(pair, dict) and 'user' in pair and pair.get('model') is None:
                user_msg: MessageDict = pair.get('user', {})
                user_text = ''.join(part.get('text', '') for part in user_msg.get('parts', []) if isinstance(part, dict) and 'text' in part)
                if user_text:
                    context_parts.append(user_text)
        return context_parts

    def _get_response(self, prompt: str, conv_id: str) -> str:
        if self.parent.debug_mode:
            print("Debug mode: simulating AI response delay...")
            time.sleep(10)
            return Config.Prompts.DEBUG_AI_RESPONSE_TEMPLATE.format(prompt=prompt)
        return self.parent.AI_controller.get_response(conv_id, prompt, streaming=False)

    def _add_ai_message(self, response: str, conversation: ConversationDict, idx: int) -> None:
        import datetime
        messages: List[Union[MessageDict, UserModelPairDict]] = conversation.get('messages', [])
        if 0 <= idx < len(messages):
            msg = messages[idx]
            if isinstance(msg, dict):
                model_msg: MessageDict = {
                    'role': 'model',
                    'parts': [{'text': response}],
                    'timestamp': datetime.datetime.now().isoformat()
                }
                msg['model'] = model_msg
                msg['ai_pending'] = False
        self.parent.chat_controller.write_conversation_to_history(conversation)

    def _refresh_ui(self, app_instance) -> None:
        app_instance.call_from_thread(app_instance.refresh_data, where='inputModel')
        app_instance.call_from_thread(app_instance.refresh_data, where='chat')

    def _unlock_input(self, app_instance) -> None:
        def reset_placeholder() -> None:
            input_field = app_instance.query_one(f"#chat_input_container", Input)
            input_field.placeholder = "Type your message here..."
        app_instance.call_from_thread(reset_placeholder)