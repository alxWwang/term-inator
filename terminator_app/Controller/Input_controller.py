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
        idx, gen_id = self._add_user_message(user_input, current_conversation, input_field)
        self.ai_handler.start_ai_response_thread((user_input, idx), current_conversation, app_instance, gen_id=gen_id)

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
        if 'id' not in conversation:
            conversation['id'] = f"conv_{int(time())}"
        gen_id = f"msg_{conversation.get('id')}"
        user_msg: MessageDict = {
            'role': 'user',
            'parts': [{'text': user_input}],
            'timestamp': datetime.datetime.now().isoformat()
        }
        pair: UserModelPairDict = {
            'user': user_msg, 
            'model': None, 
            'ai_pending': True,
            'gen_id': gen_id
        }
        conversation['messages'].append(pair)
        idx = len(conversation['messages']) - 1
        print(f"User input received: {user_input} (index {idx})")
        self.chat_controller.write_conversation_to_history(conversation)
        return idx, gen_id


class AIResponseHandler:
    def __init__(self, parent) -> None:
        self.parent = parent

    def start_ai_response_thread(self, prompt_idx_tuple, conversation, app_instance, gen_id: str = None) -> None:
        thread = threading.Thread(
            target=self._get_ai_response_thread,
            args=(prompt_idx_tuple, conversation, app_instance, gen_id),
            daemon=True
        )
        thread.start()

    def _get_ai_response_thread(self, prompt_idx_tuple, conversation: ConversationDict, app_instance, gen_id: str) -> None:
        print(f"Starting AI streaming thread (Ticket: {gen_id})...")
        prompt, idx = prompt_idx_tuple
        
        # 1. Build Context
        messages = conversation.get('messages', [])
        context_parts = self._get_context_from_previous_messages(messages, idx)
        full_prompt = ('\n'.join(context_parts) + '\n' + prompt) if context_parts else prompt

        # 2. Init Visuals: Create an empty "Model" bubble immediately
        if not self._init_streaming_message(conversation, idx, gen_id):
            return # Stale ticket, abort
        self._refresh_ui(app_instance)

        # 3. Stream Loop
        conv_id = conversation.get('id')
        accumulated_text = ""
        
        try:
            # Request Streaming Iterator
            stream = self.parent.AI_controller.get_response(conv_id, full_prompt, streaming=True)
            
            for chunk in stream:
                # Check Ticket inside the loop (allows user to cancel/regenerate mid-stream)
                if not self._validate_ticket(conversation, idx, gen_id):
                    print("Stream aborted: Stale ticket.")
                    return

                # Update RAM + UI
                accumulated_text += chunk
                self._update_streaming_text(conversation, idx, accumulated_text)
                self._refresh_ui(app_instance)
                
        except Exception as e:
            accumulated_text += f"\n[Error: {str(e)}]"
            self._update_streaming_text(conversation, idx, accumulated_text)
            self._refresh_ui(app_instance)

        # 4. Finalize: Save to Disk ONLY ONCE at the end
        self._finalize_message(conversation, idx, gen_id)
        self._refresh_ui(app_instance)
        self._unlock_input(app_instance)

    # --- HELPER METHODS ---

    def _init_streaming_message(self, conversation, idx, gen_id):
        """Creates the empty model message structure in memory."""
        import datetime
        messages = conversation.get('messages', [])
        if not (0 <= idx < len(messages)): return False
        
        msg = messages[idx]
        if msg.get('gen_id') != gen_id: return False

        msg['model'] = {
            'role': 'model',
            'parts': [{'text': ""}], # Empty start
            'timestamp': datetime.datetime.now().isoformat()
        }
        # Note: We keep ai_pending=True
        return True

    def _update_streaming_text(self, conversation, idx, text):
        """Updates the text in memory without saving to disk."""
        messages = conversation.get('messages', [])
        if 0 <= idx < len(messages):
            if messages[idx].get('model'):
                messages[idx]['model']['parts'][0]['text'] = text

    def _validate_ticket(self, conversation, idx, gen_id):
        """Returns True if the ticket is still valid."""
        messages = conversation.get('messages', [])
        if 0 <= idx < len(messages):
             return messages[idx].get('gen_id') == gen_id
        return False

    def _finalize_message(self, conversation, idx, gen_id):
        """Marks as done and Saves to Disk."""
        messages = conversation.get('messages', [])
        if 0 <= idx < len(messages):
            msg = messages[idx]
            if msg.get('gen_id') == gen_id:
                msg['ai_pending'] = False
        
        # SAVE TO DISK NOW (Once per response)
        self.parent.chat_controller.write_conversation_to_history(conversation)

    def _get_context_from_previous_messages(self, messages, idx: int) -> List[str]:
        context_parts = []
        for i in range(1, idx):
            pair = messages[i]
            if isinstance(pair, dict) and 'user' in pair and pair.get('model') is None:
                user_msg = pair.get('user', {})
                user_text = ''.join(p.get('text', '') for p in user_msg.get('parts', []))
                if user_text:
                    context_parts.append(user_text)
        return context_parts

    def _refresh_ui(self, app_instance) -> None:
        app_instance.call_from_thread(app_instance.refresh_data, where='inputModel')
        app_instance.call_from_thread(app_instance.refresh_data, where='chat')

    def _unlock_input(self, app_instance) -> None:
        def reset_placeholder() -> None:
            input_field = app_instance.query_one(f"#chat_input_container", Input)
            input_field.placeholder = "Type your message here..."
        app_instance.call_from_thread(reset_placeholder)