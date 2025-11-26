from typing import Optional
from datetime import datetime
from textual.widgets import Static
from textual.containers import VerticalScroll
import threading

try:
    from terminator_app.interfaces import ConversationDict
    from terminator_app.Chat.Chat_ui_renderer import ChatUIRenderer
    from terminator_app.Chat.Chat_data_manager import ChatDataManager
except ImportError:
    from interfaces import ConversationDict
    from Chat.Chat_ui_renderer import ChatUIRenderer
    from Chat.Chat_data_manager import ChatDataManager



class ChatController:
    """Handles all chat/conversation-related logic and state."""
    
    def __init__(self, data_manager, AI_controller, debug_mode=False):
        self.ui_renderer = ChatUIRenderer()
        self.chat_data_manager = ChatDataManager(data_manager)
        self.data_manager = data_manager
        self.current_conversation = {}
        self.AI_controller = AI_controller
        self.debug_mode = debug_mode
        self._message_lock = threading.Lock()  # Thread-safe lock for add_message
    
    def display_conversation_at_index(self, conv: ConversationDict, chat_panel: Static, chat_scroll: VerticalScroll) -> None:
        """Display conversation for mixed format: greeting at index 0, user/model pairs at index 1+."""
        self.ui_renderer.display_conversation_at_index(conv, chat_panel, chat_scroll)

    def view_page(self, increment_or_special: int | str, conv: ConversationDict, input_controller=None, app_instance=None) -> bool:
        new_index = self.ui_renderer.view_page(increment_or_special, conv)
        if input_controller and app_instance and new_index != -1:
            self.chat_data_manager.start_auto_response(conv, new_index, input_controller, app_instance)
        return True if new_index != -1 else False
    
    def write_conversation_to_history(self, conv: ConversationDict) -> bool:
        """Write conversation to history using DataManager. Returns True if successful."""
        return self.chat_data_manager.write_conversation_to_history(conv)
    
    def generate_new_conversation_id(self) -> str:
        """Generate a unique conversation ID based on timestamp."""
        return f"conv_{int(datetime.now().timestamp())}"
    
    def switch_conversation(self, conv_id: str, new_conv_id: str = None) -> Optional[ConversationDict]:
        # Check if this is the "new conversation" button
        if new_conv_id and conv_id == new_conv_id:
            self.current_conversation = self.chat_data_manager.create_new_conversation(new_conv_id, self.AI_controller)
            return self.current_conversation
        
        # Try to find existing conversation
        conv = self.data_manager.get_conversation_by_id(conv_id)
        if conv:
            self.current_conversation = conv
            if conv_id not in self.AI_controller.chat:
                self.AI_controller.open_session(conv_id)
            # Reset ai_pending for unfinished prompts on load
            self.chat_data_manager.reset_ai_pending_for_unfinished_prompts(conv)
            return conv
        
        return None

    def refresh_conversation_async(self, conv: ConversationDict, chat_panel: Static, chat_scroll: VerticalScroll, display_method=None):
        """
        Show loading screen in main thread, then run display_method in a background thread and update chat panel using call_from_thread.
        """
        # Show loading screen immediately in main thread
        self.ui_renderer.show_loading_screen(chat_panel, chat_scroll)
        def run_display():
            app = chat_panel.app if hasattr(chat_panel, 'app') else None
            if display_method and app:
                app.call_from_thread(display_method, conv, chat_panel, chat_scroll)
        t = threading.Thread(target=run_display)
        t.start()


