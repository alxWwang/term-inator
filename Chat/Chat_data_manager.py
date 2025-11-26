import copy
from datetime import datetime
from interfaces import ConversationDict
from config import UserConfig

class ChatDataManager:
    def __init__(self, data_manager):
        self.data_manager = data_manager

    def reset_ai_pending_for_unfinished_prompts(self, conv: ConversationDict) -> bool:
        """Reset ai_pending to False for any user/model pair with missing model response and ai_pending True."""
        messages = conv.get('messages', [])
        changed = False
        for i in range(1, len(messages)):
            pair = messages[i]
            if (
                isinstance(pair, dict)
                and 'user' in pair
                and pair.get('model') is None
                and pair.get('ai_pending')
            ):
                pair['ai_pending'] = False
                changed = True
        if changed:
            self.write_conversation_to_history(conv)
        return changed

    def start_auto_response(self, conv: ConversationDict, index: int, input_controller, app_instance):
        """Trigger AI response for a user/model pair at index if model is None and not ai_pending."""
        messages = conv.get('messages', [])
        if 1 <= index < len(messages):
            pair = messages[index]
            if isinstance(pair, dict) and 'user' in pair and pair.get('model') is None:
                user_msg = pair.get('user', {})
                user_text = ''.join(part.get('text', '') for part in user_msg.get('parts', []) if isinstance(part, dict) and 'text' in part)
                if user_text and not pair.get('ai_pending'):
                    pair['ai_pending'] = True
                    self.write_conversation_to_history(conv)
                    input_controller.ai_handler.start_ai_response_thread((user_text, index), conv, app_instance)

    def write_conversation_to_history(self, conv: ConversationDict) -> bool:
        """Write conversation to history using DataManager. Returns True if successful."""
        conv_id = conv.get('id')
        if not conv_id:
            return False
        # Always update the conversation in memory and force save to disk
        existing = self.data_manager.get_conversation_by_id(conv_id)
        if existing is None:
            self.data_manager._conversation_history.append(conv)
            self.data_manager._conversation_dict[conv_id] = conv
        else:
            self.data_manager._conversation_dict[conv_id] = conv
            # Replace in history list
            for i, c in enumerate(self.data_manager._conversation_history):
                if c.get('id') == conv_id:
                    self.data_manager._conversation_history[i] = conv
                    break
        return self.data_manager.save_to_disk()
    
    def create_new_conversation(self, new_conv_id: str, AI_controller) -> ConversationDict:
        """Create a new conversation with a unique ID."""
        "Start new session"
        AI_controller.open_session(new_conv_id, True)

        new_conv = copy.deepcopy(UserConfig.BASE_CONVERSATION)
        now = datetime.now().isoformat()
        new_conv['id'] = new_conv_id
        new_conv['timestamp'] = now
        # Set timestamp for initial assistant message
        if new_conv.get('messages'):
            new_conv['messages'][0]['timestamp'] = now
        return new_conv