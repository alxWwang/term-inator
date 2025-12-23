from textual.widgets import Static
from textual.containers import VerticalScroll
import re, textwrap
from rich.markdown import Markdown as RichMarkdown
from rich.console import Console
from rich.text import Text

try:
    from terminator_app.interfaces import ConversationDict
except ImportError:
    from interfaces import ConversationDict


class ChatUIRenderer:
    def __init__(self):
        self.chat_position_index = {}

    def display_conversation_at_index(self, conv: ConversationDict, chat_panel: Static, chat_scroll: VerticalScroll) -> None:
        """Display conversation for mixed format: greeting at index 0, user/model pairs at index 1+."""
        text = f"Conversation: {conv.get('id')}\n"
        text += f"Time: {conv.get('timestamp')}\n\n"

        messages = conv.get('messages', [])
        total_length = len(messages)

        pair_count = total_length - 1
        default_index = 0
        index = self.chat_position_index.get(conv.get('id'), default_index)

        if total_length == 0:
            chat_panel.update(text + "[dim]No messages yet[/dim]")
            return
        
        panel_width = chat_panel.size.width if chat_panel.size.width > 0 else chat_scroll.size.width
        box_width = max(20, panel_width - 4)

        # Greeting message
        if index == 0:
            greeting = messages[index].get('model', {})
            text_parts = ''.join(part.get('text', '') for part in greeting.get('parts', []) if isinstance(part, dict) and 'text' in part)
            text += f"[right][magenta]{'─' * (box_width - 13)} ASSISTANT ─┐[/magenta][/right]\n"
            text += f"[right]{self._render_markdown(text_parts, box_width)}[/right]"
            text += f"\n[right][magenta]{'─' * (box_width - 1)}┘[/magenta][/right]\n\n"
        
        # ... inside display_conversation_at_index ...
        
        # User/Model pairs
        elif 1 <= index <= pair_count:
            user_msg = messages[index].get('user', {})
            model_msg = messages[index].get('model', {})
            ai_pending = messages[index].get('ai_pending', False)
            
            user_text = ''.join(part.get('text', '') for part in user_msg.get('parts', []))
            
            model_text = None
            if isinstance(model_msg, dict) and model_msg.get('parts'):
                model_text = ''.join(part.get('text', '') for part in model_msg.get('parts', []))
            
            # Parse text
            thoughts, final_answer = self.parse_thinking_response(model_text) if model_text else (None, None)

            # --- RENDER USER ---
            if user_text:
                text += f"[cyan]┌─ USER {'─' * (box_width - 8)}[/cyan]\n"
                text += self._render_markdown(user_text, box_width)
                text += f"\n[cyan]└{'─' * (box_width - 1)}[/cyan]\n\n"
            
            # --- RENDER ASSISTANT ---
            
            # Case 1: We have the Final Answer (Finished thinking)
            if final_answer:
                # Optional: You can uncomment this if you want to show collapsed thoughts above the answer
                # text += f"[dim]💭 Thought Process: {thoughts[:50]}...[/dim]\n" 
                
                text += f"[right][magenta]{'─' * (box_width - 13)} ASSISTANT ─┐[/magenta][/right]\n"
                text += f"[right]{self._render_markdown(final_answer, box_width)}[/right]"
                text += f"\n[right][magenta]{'─' * (box_width - 1)}┘[/magenta][/right]\n\n"

            # Case 2: We are actively Thinking (Streaming thoughts)
            elif thoughts:
                # Show the live thought stream in a dim box
                text += f"[right][dim]┌─ 🧠 Thinking... {'─' * (box_width - 16)}┐[/dim][/right]\n"
                # Render thoughts (limit length or box height if needed)
                text += f"[right][dim]{self._render_markdown(thoughts, box_width)}[/dim][/right]"
                text += f"\n[right][dim]└{'─' * (box_width - 1)}┘[/dim][/right]\n\n"

            # Case 3: Waiting for first token (Connected, but empty)
            elif ai_pending and not model_text:
                text += f"[bold][yellow]⏳ Waiting for assistant response...[/yellow][/bold]\n\n"

            # Case 4: Finished but empty/error
            elif not ai_pending and not model_text:
                text += f"[bold][red]⚠️ No assistant response available.[/red][/bold]\n\n"
            
            # Case 5: Fallback (Has text, but regex didn't match tags, likely standard model)
            elif model_text and not final_answer:
                 text += f"[right][magenta]{'─' * (box_width - 13)} ASSISTANT ─┐[/magenta][/right]\n"
                 text += f"[right]{self._render_markdown(model_text, box_width)}[/right]"
                 text += f"\n[right][magenta]{'─' * (box_width - 1)}┘[/magenta][/right]\n\n"
        current_page = index + 1
        total_pages = pair_count + 1
        text += f"\n[dim]Page {current_page}/{total_pages}[/dim]"
        chat_panel.update(text)
        chat_scroll.scroll_end(animate=True)

    def parse_thinking_response(self, raw_response: str) -> tuple[str | None, str | None]:
        """
        Parses the raw response.
        Returns: (thought_process, final_answer)
        """
        if not raw_response:
            return None, None

        # 1. Check for completed thinking blocks (<|channel|>analysis ... <|channel|>final)
        analysis_match = re.search(r"<\|channel\|>analysis(.*?)<\|channel\|>final<\|message\|>", raw_response, flags=re.DOTALL)
        if analysis_match:
            thought_process = analysis_match.group(1).strip()
            final_answer = raw_response[analysis_match.end():].strip()
            return thought_process, final_answer

        # 2. Check if we are currently "Thinking" (analysis tag exists, but no final tag)
        if "<|channel|>analysis" in raw_response and "<|channel|>final" not in raw_response:
            idx = raw_response.rfind("<|channel|>analysis")
            thought_content = raw_response[idx + len("<|channel|>analysis"):].strip()
            return thought_content, None

        # 3. Standard Answer (No thinking tags detected)
        return None, raw_response.strip()

    def view_page(self, increment_or_special: int | str, conv: ConversationDict) -> int:
        """Navigate to a different page: greeting at index 0, user/model pairs at index 1+.
        If increment_or_special == 'end', jump to last page.
        If the current page is a user/model pair with None model, trigger AI response once."""
        messages = conv.get('messages', [])
        pair_count = len(messages) - 1
        if increment_or_special == 'end':
            new_index = pair_count
        else:
            new_index = self.chat_position_index.get(conv.get('id'), 0) + increment_or_special
        if new_index < 0:
            return -1
        elif new_index > pair_count:
            return -1
        self.chat_position_index[conv.get('id')] = new_index
        # If on a user/model pair with None model, trigger AI auto-response
        return new_index if 1 <= new_index <= pair_count else -1
    

     # Modular renderers for markdown content
    def _render_code_block(self, lang, code_lines, box_width):
        horizontal = "─" * (box_width - 4)
        top_line = f"[bold][on black]┌{horizontal}┐[/on black][/bold]"
        lang_label = f"[bold][on black]│ {lang + ' code:' if lang else 'code:'}{' ' * (box_width - len(lang + ' code:') - 6)}│[/on black][/bold]"
        code_markup = top_line + "\n" + lang_label + "\n"
        for line in code_lines:
            padded = line.ljust(box_width - 6)
            code_markup += f"[on black]│ {padded} │[/on black]\n"
        bottom_line = f"[bold][on black]└{horizontal}┘[/on black][/bold]"
        code_markup += bottom_line
        return code_markup

    def _render_image(self, alt, url, box_width):
        horizontal = "─" * (box_width - 4)
        top_line = f"[bold][on blue]┌{horizontal}┐[/on blue][/bold]"
        label = f"[bold][on blue]│ Image: {alt}{' ' * (box_width - len('Image: ' + alt) - 6)}│[/on blue][/bold]"
        url_line = f"[on blue]│ {url.ljust(box_width - 6)} │[/on blue]"
        bottom_line = f"[bold][on blue]└{horizontal}┘[/on blue][/bold]"
        return f"{top_line}\n{label}\n{url_line}\n{bottom_line}"

    def _render_markdown(self, content: str, box_width: int = 80) -> str:
        """Render markdown content with modular handlers for code, images, and more."""

        # Patterns for code blocks and images
        code_block_pattern = re.compile(r"```(\w+)?\n([\s\S]*?)```", re.MULTILINE)
        image_pattern = re.compile(r"!\[(.*?)\]\((.*?)\)")
        parts = []
        last_end = 0
        # Process code blocks
        for match in code_block_pattern.finditer(content):
            # Markdown before code block
            if match.start() > last_end:
                md_text = content[last_end:match.start()]
                md_chunks = self._process_images(md_text, box_width)
                parts.extend(md_chunks)
            # Code block
            lang = match.group(1) or ""
            code = match.group(2)
            code_lines = code.splitlines()
            parts.append(self._render_code_block(lang, code_lines, box_width))
            last_end = match.end()
        # Markdown after last code block
        if last_end < len(content):
            md_text = content[last_end:]
            md_chunks = self._process_images(md_text, box_width)
            parts.extend(md_chunks)
        return '\n'.join(parts)

    def _process_images(self, md_text, box_width):
        """Detect and render images in markdown text, return list of markup chunks."""

        image_pattern = re.compile(r"!\[(.*?)\]\((.*?)\)")
        parts = []
        img_last_end = 0
        for img_match in image_pattern.finditer(md_text):
            # Markdown before image
            if img_match.start() > img_last_end:
                md_chunk = md_text[img_last_end:img_match.start()]
                wrapped_md = '\n'.join(textwrap.fill(line, box_width) for line in md_chunk.splitlines())
                console = Console(legacy_windows=False, force_terminal=False, width=box_width)
                md = RichMarkdown(wrapped_md)
                segments = list(console.render(md))
                md_markup = Text.assemble(*[seg.text for seg in segments if hasattr(seg, 'text')]).markup
                parts.append(md_markup)
            # Image block
            alt = img_match.group(1)
            url = img_match.group(2)
            parts.append(self._render_image(alt, url, box_width))
            img_last_end = img_match.end()
        # Markdown after last image
        if img_last_end < len(md_text):
            md_chunk = md_text[img_last_end:]
            wrapped_md = '\n'.join(textwrap.fill(line, box_width) for line in md_chunk.splitlines())
            console = Console(legacy_windows=False, force_terminal=False, width=box_width)
            md = RichMarkdown(wrapped_md)
            segments = list(console.render(md))
            md_markup = Text.assemble(*[seg.text for seg in segments if hasattr(seg, 'text')]).markup
            parts.append(md_markup)
        return parts

    def show_loading_screen(self, chat_panel: Static, chat_scroll: VerticalScroll, message: str = "Loading conversation..."):
        loading_text = f"[bold][yellow]⏳ {message}[/yellow][/bold]\n\n[dim]Please wait while the conversation loads.[/dim]"
        chat_panel.update(loading_text)
        chat_scroll.scroll_end(animate=False)