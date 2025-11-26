# Terminator TUI Chat Application

## Overview
Terminator is a Textual-based terminal chat application supporting AI-powered conversations, conversation history, markdown/code rendering, and responsive UI. The architecture is modular, with controllers for chat, input, and history, and a data layer for fast, thread-safe access.

---

## Application Flow

### Startup
- Dependencies are auto-installed from `requirements.txt`.
- The main app (`Terminator`) initializes controllers and data manager.
- UI is composed with header, footer, chat panel, input, and history panel.
- On mount, a new conversation is started and displayed.

### Main User Flows

#### 1. Start New Conversation
- User clicks "New Conversation".
- `HistoryController.handle_History_button_press` calls `ChatController.switch_conversation` to create a new conversation.
- UI refreshes to show the new conversation and focuses the input field.

#### 2. Switch Conversation
- User selects a conversation from history.
- `HistoryController.handle_History_button_press` calls `ChatController.switch_conversation` to load the selected conversation.
- UI refreshes to show the selected conversation and focuses the input field.

#### 3. Send Message
- User types a message and presses Enter.
- `InputController.chat_input_controller` adds the user message and starts an AI response thread.
- While AI is responding, input is locked and a placeholder is shown.
- When AI response is received, it is added to the conversation and the UI is refreshed.

#### 4. View Conversation Pages
- User clicks "Next" or "Previous".
- `ChatController.view_page` updates the page index.
- UI refreshes to show the selected page of messages.

#### 5. Auto-Complete Incomplete Conversation
- On switching to a conversation waiting for AI response, `InputController.auto_complete_conversation` triggers an AI response automatically.
- UI shows loading/placeholder until response is complete.

---

## Use Cases

### UC1: Open Conversation
- **Actor:** User
- **Goal:** View messages in a selected or new conversation.
- **Flow:**
  1. User selects or creates a conversation.
  2. App calls `switch_conversation` to update the active conversation.
  3. UI refreshes to show the conversation and focuses input.

### UC2: Send Message
- **Actor:** User
- **Goal:** Send a message and receive AI response.
- **Flow:**
  1. User submits input.
  2. Message is added; AI response thread starts.
  3. Input is locked; placeholder shown.
  4. AI response is added; UI refreshed.

### UC3: View Conversation History
- **Actor:** User
- **Goal:** Browse and select past conversations.
- **Flow:**
  1. History panel displays all conversations.
  2. User selects a conversation; app loads and displays it.

### UC4: Paginate Conversation
- **Actor:** User
- **Goal:** View older or newer messages in a conversation.
- **Flow:**
  1. User clicks "Next" or "Previous".
  2. App updates page index and refreshes chat panel.

### UC5: Auto-Complete Incomplete Conversation
- **Actor:** System
- **Goal:** Automatically complete conversations waiting for AI response.
- **Flow:**
  1. On load/switch, if last message is from user, AI response is triggered.
  2. UI shows loading until response is complete.

---

## Configuration & Prompts

All configuration constants, UI identifiers, and prompt templates are centralized in `config.py` under the `Config` class. This includes:
- File paths and UI element IDs
- Button and container identifiers
- Application metadata
- **Prompt templates** for AI responses, error messages, and conversation titles

To update or customize prompts, edit the relevant fields in `Config` (e.g., `TITLE_PROMPT_TEMPLATE`, `DEBUG_AI_RESPONSE_TEMPLATE`).

Example:
```python
class Config:
    TITLE_PROMPT_TEMPLATE = "Based on this conversation, provide a very short title (3-5 words max):\n\n{conversation_text}\n\nTitle:"
    DEBUG_AI_RESPONSE_TEMPLATE = "[DEBUG] AI response to: {prompt}"
    # ...other config...
```

All controllers and AI logic reference these templates for consistent messaging and easy maintenance.

---

## Architecture & Flow

- **Controllers:**
  - `ChatController`: Conversation logic, rendering, paging.
  - `InputController`: Input handling, AI response, input lock.
  - `HistoryController`: History panel, button management.
- **Data Layer:**
  - `DataManager`: Thread-safe, in-memory cache, fast disk I/O.
  - `DataLoader`: Minimal, static methods for JSON load/save.
- **UI:**
  - Textual widgets for chat, input, history, buttons.
  - Responsive updates via `call_from_thread`.
  - Markdown/code/image rendering for rich chat display.

---

## Code Review Summary

- **Strengths:**
  - Modular, maintainable architecture.
  - Responsive UI with proper threading.
  - Fast, thread-safe data access.
  - Extensible for future features (images, files, streaming).
- **Areas for Improvement:**
  - Centralize magic strings/integers in `Config`.
  - Add type hints and more robust error handling.
  - Remove unused code and add unit tests.
  - Document all public APIs and flows.

---

## Features
- AI-powered chat with conversation history
- Markdown/code rendering
- Responsive Textual UI
- **Pagination:** Navigate conversation pages using Next/Previous buttons (already implemented)
- Auto-complete for incomplete conversations
- Modular controller/data architecture

---

## How to Run
1. Install Python 3.10+ and dependencies (`pip install -r requirements.txt`).
2. Run `main.py` in your terminal.
3. Use the UI to start conversations, send messages, and browse history.

## How to Use

1. **Clone the repository:**
   ```sh
   git clone https://github.com/alxWwang/term-inator.git
   cd term-inator
   ```
2. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
3. **Set up your API key:**
   - Create a `.env` file in the project root.
   - Add your Gemini API key:
     ```
     GENAI_API_KEY=your_api_key_here
     ```
4. **Run the application:**
   ```sh
   python main.py
   ```
5. **Interact with the UI:**
   - Start new conversations, send messages, and browse history using the terminal interface.
   - Use the navigation buttons to switch conversations and pages.
   - The app will auto-complete conversations and provide AI responses.

---

## System-wide Installation

To install Terminator system-wide and run it from any terminal, use:
```sh
pip install .
```
After installation, you can type `terminator` in any terminal to launch the app. **The installer works and sets up all necessary files automatically!**

---

## Configuration Files

Terminator uses the following configuration files, located in `~/.terminator/user/config/`:
- **Bindings:** `~/.terminator/user/config/bindings.conf` - Key bindings for the application.
- **CSS:** `~/.terminator/user/config/style.conf` - Styling for the Textual UI.

These files are automatically copied from the package defaults on first run if they don't exist. You can edit them to customize the app's behavior and appearance.

---

## API Key & Debug Mode

- The application requires a `GENAI_API_KEY` for full AI functionality.
- If no API key is provided during installation or in the `.env` file, the app will run in debug mode.
- When running in debug mode, you will be prompted at startup to enter your API key. If you provide a key, it will be saved to `.env` and you can restart the app for full functionality.
- To manually set your API key, add the following to your `.env` file:
  ```
  GENAI_API_KEY=your_api_key_here
  DEBUG_MODE=False
  ```
- To force debug mode, set:
  ```
  DEBUG_MODE=True
  ```

---
add your keys here: ~/.terminator.env

## Future Improvements
- Add streaming AI responses.
- Support for images and file uploads.
- More granular loading/progress indicators.
- Pagination/lazy loading for large histories.
- Improved error handling and configuration.
- Unit and integration tests.

---

## Maintainers
- [Your Name]
- [Contributors]