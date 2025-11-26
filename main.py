#!/home/wang/Work/terminator/.venv/bin/python
import os
import sys
import subprocess


# Auto-install dependencies if requirements.txt exists
def install_dependencies():
    requirements_file = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(requirements_file):
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', '-r', requirements_file])
        except subprocess.CalledProcessError:
            print("Warning: Failed to install some dependencies")

# Try to install dependencies before importing
install_dependencies()

from textual.app import App, ComposeResult
from textual.widgets import Static, Input, Footer, Header, Button
from textual.containers import Container, VerticalScroll, Horizontal
from textual import work

from Data import load
from Data.DataManager import DataManager
from Controller import AI_Controller, Chat_controller, Input_controller, History_controller
from config import Config

class Terminator(App):
    """Main application class - handles UI composition and event routing only."""

    TITLE = Config.APP_TITLE
    BINDINGS = load.DataLoader.load_bindings(Config.BINDING_FILE_PATH)
    CSS = load.DataLoader.load_CSS(Config.CSS_FILE_PATH)

    def __init__(self, debug=False):
        super().__init__()
        self.debug_mode = debug
        print("Debug mode: " + str(self.debug_mode))
        
        # Initialize DataManager as single source of truth
        self.data_manager = DataManager()
            
        # Initialize controllers with dependency injection
        self.AI_controller = AI_Controller.AIController()
        self.chat_controller = Chat_controller.ChatController(
            self.data_manager,
            self.AI_controller,
            self.debug_mode
        )
        self.input_controller = Input_controller.InputController(
            self.chat_controller, self.AI_controller,
            self.debug_mode
        )

        self.history_controller = History_controller.HistoryController(
            self.data_manager,
            self.chat_controller, 
            self.input_controller,
            self.AI_controller,
            self.debug_mode
        )
        

        if self.debug_mode:
            print("[DEBUG] Debug mode enabled")
            print("[DEBUG] Conversation history:", self.data_manager.get_all_conversations())
            print("CSS Loaded:", self.CSS)
            print("BINDINGS Loaded:", self.BINDINGS)
        

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Container(
                Button(
                    f"New Conversation",
                    id=Config.NEW_CONVERSATION_BUTTON_ID,
                    classes=Config.CONVERSATION_BUTTON_CLASS
                ),
                VerticalScroll(
                    id=Config.HISTORY_CONTAINER_ID
                ),
                id=Config.HISTORY_PANEL_CONTAINER_ID
            ),
            Container(
                VerticalScroll(
                    Static(id=Config.CHAT_PANEL_ID),
                    id=Config.CHAT_SCROLL_ID
                ),
                Horizontal(
                    Button("Stop", id="input_button_stop", classes="input-action-button"),
                    Button("Regenerate", id="input_button_regenerate", classes="input-action-button"),
                    Button("Clear", id="input_button_clear", classes="input-action-button"),
                    id="input_button_container",
                    classes="input-buttons"
                ),
                Input(placeholder="Type your message here...", id=Config.CHAT_INPUT_ID),
                Button("Next", id="input_next_button", classes="input-action-button"),
                Button("Previous", id="input_previous_button", classes="input-action-button"),

                id=Config.CHAT_CONTAINER_ID
            ),
            id=Config.MAIN_CONTAINER_ID,
            classes="horizontal"
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """Called when app is mounted - fill panels with data"""
        new_conv_id = self.chat_controller.generate_new_conversation_id()
        self.chat_controller.switch_conversation(new_conv_id, new_conv_id)

        # Display initial conversation
        chat_panel = self.query_one(f"#{Config.CHAT_PANEL_ID}", Static)
        chat_scroll = self.query_one(f"#{Config.CHAT_SCROLL_ID}",VerticalScroll)

        if self.chat_controller.view_page(0, self.chat_controller.current_conversation):
            self.chat_controller.display_conversation_at_index(self.chat_controller.current_conversation, chat_panel, chat_scroll)

        # Set up button container reference and hide it initially
        button_container = self.query_one("#input_button_container", Horizontal)
        button_container.styles.display = "none"

        # Populate history and focus input
        self._refresh_history_worker()
        input_field = self.query_one(f"#{Config.CHAT_INPUT_ID}", Input)

        # Auto-complete incomplete conversation if needed
        if self.input_controller.auto_complete_conversation(self.chat_controller.current_conversation):
            print("[INFO] Auto-completing incomplete conversation...")
            input_field.placeholder = "⏳ Completing previous request (AUTO_COMPLETE_CONV)..."

        # Check for any unanswered user/model pairs and trigger AI response
        self.input_controller.focus_to_chat_input(input_field)


        
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks - delegate to history controller"""
        button_id = event.button.id
        input_field = self.query_one(f"#{Config.CHAT_INPUT_ID}", Input)
        
        # Let history controller handle the button press
        isHistory = button_id == f"{Config.NEW_CONVERSATION_BUTTON_ID}" or button_id.startswith(Config.CONVERSATION_BUTTON_PREFIX)
        if isHistory and self.history_controller.handle_History_button_press(button_id, Config.CONVERSATION_BUTTON_PREFIX, input_field):
            # Refresh data first
            self.refresh_data(where='all')
            
            # Auto-complete if the switched conversation is incomplete
            if self.input_controller.auto_complete_conversation(self.chat_controller.current_conversation):
                print("[INFO] Auto-completing switched conversation...")
                input_field.placeholder = "⏳ Completing previous request (AUTO_COMPLETE_CONV)..."
        
        if button_id == "input_next_button" and self.chat_controller.view_page(1, self.chat_controller.current_conversation, self.input_controller, self):
            self.refresh_data(where='chat')
        if button_id == "input_previous_button" and self.chat_controller.view_page(-1, self.chat_controller.current_conversation, self.input_controller, self):
            self.refresh_data(where='chat')

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle when user presses Enter in the input field"""
        user_input = event.value.strip()
        if not user_input:
            return
        if event.input.id == Config.CHAT_INPUT_ID:
            input_field = self.query_one(f"#{Config.CHAT_INPUT_ID}", Input)
            # Process input - returns immediately, AI runs in background thread
            self.input_controller.chat_input_controller(
                user_input, 
                self.chat_controller.current_conversation,
                input_field,
                self  # Pass app instance for safe UI updates from thread
            )
            # Move to last page using view_page
            # Move to last page using view_page with 'end'
            if self.chat_controller.view_page('end', self.chat_controller.current_conversation, self.input_controller, self):
                self.refresh_data(where='chat')
                self.refresh_data(where='input')
    
    def on_resize(self, event) -> None:
        """Handle window resize events"""
        # Use set_timer with small delay to let layout stabilize
        self.set_timer(0.1, self._handle_resize)
    
    def _handle_resize(self):
        """Refresh chat display after resize completes"""
        self.refresh_data(where='chat')

    @work(exclusive=True)
    async def _refresh_history_worker(self):
        """Worker to refresh history panel with proper async widget removal."""
        history_container = self.query_one(f"#{Config.HISTORY_CONTAINER_ID}", VerticalScroll)
        await self.history_controller.populate_history_panel(history_container)

    def refresh_data(self, where='all'):
        """Refresh conversation history and current conversation display"""
        # Refresh history panel
        if where in ('all', 'history'):
            self._refresh_history_worker()
        
        if where in ('all', 'chat'):
            # Refresh chat display with loading screen and threading
            chat_panel = self.query_one(f"#{Config.CHAT_PANEL_ID}", Static)
            chat_scroll = self.query_one(f"#{Config.CHAT_SCROLL_ID}")
            self.chat_controller.refresh_conversation_async(
                self.chat_controller.current_conversation,
                chat_panel,
                chat_scroll,
                self.chat_controller.display_conversation_at_index
            )
        
        if where in ('all', 'inputModel'):
            # Focus input
            input_field = self.query_one(f"#{Config.CHAT_INPUT_ID}", Input)
            # go to the last line
            if where != 'inputModel' and self.chat_controller.view_page(0, self.chat_controller.current_conversation):
                self.input_controller.focus_to_chat_input(input_field)
        


if __name__ == "__main__":
    # Check if 'debug' argument is passed
    debug_mode = 'debug' in [arg.lower() for arg in sys.argv[1:]]
    app = Terminator(debug=debug_mode)
    app.run()