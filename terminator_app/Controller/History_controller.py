from textual.widgets import Button, Static
from textual.containers import VerticalScroll
try:
    from terminator_app.config import Config
    from terminator_app.interfaces import ConversationDict
except ImportError:
    from config import Config
    from interfaces import ConversationDict

class HistoryController:
    """Handles all history panel interactions and state."""
    
    def __init__(self, data_manager, chat_controller, input_controller, AI_controller, debug_mode=False) -> None:
        self.data_manager = data_manager
        self.chat_controller = chat_controller
        self.input_controller = input_controller
        self.AI_controller = AI_controller
        self.debug_mode = debug_mode
        self.selected_button_id = None
        self.button_map = {}  # Map conv_id to button widget for direct updates

    async def populate_history_panel(self, history_container: VerticalScroll) -> None:
        """Update history panel buttons efficiently without recreating everything."""
        history_container.loading = True
        
        # Get fresh conversation history from DataManager
        conversation_history = self.data_manager.get_all_conversations()
        
        if not conversation_history:
            await self._clear_all_buttons(history_container)
            history_container.mount(Static("[dim]No conversation history available[/dim]"))
            history_container.loading = False
            return
        
        # Remove deleted conversations
        current_ids = {conv.get('id') for conv in conversation_history}
        await self._remove_deleted_buttons(current_ids)
        
        # Update or create buttons
        for conv in conversation_history:
            conv_id = conv.get('id', 'N/A')
            timestamp = conv.get('timestamp', 'N/A')
            needs_title = not conv.get('title') and len(conv.get('messages', [])) > 1
            title = "Generating title..." if needs_title else conv.get('title', 'New Conversation')
            
            button = self.button_map.get(conv_id)
            if button:
                self._update_button(button, conv_id, timestamp, title)
            else:
                button = self._create_button(history_container, conv_id, timestamp, title)
            
            if needs_title:
                self._start_title_generation(conv, button, timestamp)
        
        history_container.loading = False
    
    def handle_History_button_press(self, button_id: str, button_prefix: str, input_field) -> bool:
        # Return early if no button ID provided
        if not button_id:
            return False
        
        # Handle new conversation button
        if button_id == f"{Config.NEW_CONVERSATION_BUTTON_ID}":
            new_conv_id = self.chat_controller.generate_new_conversation_id()
            self.selected_button_id = None
            self.chat_controller.switch_conversation(new_conv_id, new_conv_id)
            self.input_controller.focus_to_chat_input(input_field)
            return True
        
        # Handle existing conversation button
        if button_id.startswith(button_prefix):
            conv_id = button_id.replace(button_prefix, "")
            self.selected_button_id = conv_id
            self.chat_controller.switch_conversation(conv_id, None)
            # Move to the end of the conversation
            self.chat_controller.view_page('end', self.chat_controller.current_conversation, self.input_controller, input_field.app)
            self.input_controller.focus_to_chat_input(input_field)
            return True
        
        return False
    async def _clear_all_buttons(self, history_container: VerticalScroll) -> None:
        """Remove all buttons from history panel."""
        for child in list(history_container.children):
            await child.remove()
        self.button_map.clear()
    
    async def _remove_deleted_buttons(self, current_ids: set) -> None:
        """Remove buttons for conversations that no longer exist."""
        for conv_id in list(self.button_map.keys()):
            if conv_id not in current_ids:
                if button := self.button_map.pop(conv_id, None):
                    await button.remove()
    
    def _update_button(self, button: Button, conv_id: str, timestamp: str, title: str) -> None:
        """Update existing button label and selection state."""
        button.label = f"{title}"
        button.set_class(conv_id == self.selected_button_id, "selected_history_button")
    
    def _create_button(self, history_container: VerticalScroll, conv_id: str, timestamp: str, title: str) -> Button:
        """Create and mount a new button."""
        button = Button(
            f"{timestamp}: {title}",
            id=f"{Config.CONVERSATION_BUTTON_PREFIX}{conv_id}",
            classes=Config.CONVERSATION_BUTTON_CLASS
        )
        button.set_class(conv_id == self.selected_button_id, "selected_history_button")
        history_container.mount(button, before=0)
        self.button_map[conv_id] = button
        return button
    
    def _start_title_generation(self, conv: ConversationDict, button: Button, timestamp: str) -> None:
        """Start background title generation for a conversation."""
        def on_title_ready(cid, title):
            try:
                # Update title via DataManager
                self.data_manager.update_conversation_title(cid, title)
                
                # Update button label only if still mounted
                if button and hasattr(button, 'is_mounted') and button.is_mounted:
                    button.label = f"{title}"
            except Exception as e:
                if self.debug_mode:
                    print(f"Error updating title for {cid}: {e}")
        
        # Pass callback directly - button and timestamp are captured by closure
        self.AI_controller.generate_title_from_conversation(conv, callback=on_title_ready)