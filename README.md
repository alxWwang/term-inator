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

## How to Run
1. Install Python 3.10+ and dependencies (`pip install -r requirements.txt`).
2. Run `main.py` in your terminal.
3. Use the UI to start conversations, send messages, and browse history.

---

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