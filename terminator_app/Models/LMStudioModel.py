import lmstudio as lms, tokenize
from lmstudio.history import Chat
import re

import requests

'''
Creates session and adds to history

'''
class LMStudioModel():
    def __init__(self, model_name: str):
        """
        Initialize the LMStudio model client.

        Args:
            model_name (str): The name of the loaded model in LM Studio.
        """
        # Get the model object from LM Studio
        self.client = lms.llm(model_name)

    def create_chat(self, history_data):
        """
        Initializes the chat object and injects the message history.
        Accepts either a dict {"messages": []} or a raw list of messages.
        """
        local_conversation = LocalConversation(system_prompt="You are a helpful assistant, Helping the user: wang. Be helpful and keep the answers concise, if a question needs more preconditions, always ask. Answer in a friendly way, use emoji's if needed. Always ask for a follow up to each question", client=self.client)

        # Handle different input types
        if isinstance(history_data, dict):
            messages = history_data.get("messages", [])
        elif isinstance(history_data, list):
            messages = history_data
        else:
            messages = []

        # Inject messages into the active session
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")

            if role == "system":
                local_conversation.add_assistant_response(content)
            elif role == "user":
                local_conversation.add_user_message(content)
            elif role in ["assistant", "model"]:
                local_conversation.add_assistant_response(content)
        
        print(f"Chat created with {len(messages)} past messages injected.")
        return local_conversation
    
    def generate_content(self, contents: str) -> str:
        return self.extract_true_answer(self.client.complete(contents).parsed)
    
    @staticmethod
    def extract_true_answer(raw_text: str) -> str:
        """
        Parses the model output to separate the internal 'thought process' 
        from the final response.
        
        Target Format: <|channel|>final<|message|>The actual answer...
        """
        # 1. Define the pattern that marks the start of the REAL answer
        # We use re.DOTALL so the (.) wildcard matches newlines too.
        pattern = r"<\|channel\|>final<\|message\|>(.*)"
        
        match = re.search(pattern, raw_text, re.DOTALL)
        
        if match:
            # Found the tag! Return everything after it.
            return match.group(1).strip()
        
        # 2. Fallback for 'DeepSeek-R1' style tags (common in other local models)
        # Some models use <think>...</think>
        if "<think>" in raw_text and "</think>" in raw_text:
            # Remove the thought block entirely
            return re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()

        # 3. If no tags are found, the model probably just replied normally.
        return raw_text.strip()

    @staticmethod
    def deserialize_history(flat_msgs: list) -> list:

        clean_history = []
        
        for msg in flat_msgs:
            # --- 1. Map Roles ---
            role = msg.get("role")
            if role == "model":
                role = "assistant"
            content = ""
            parts = msg.get("parts", [])
            if parts and isinstance(parts, list) and "text" in parts[0]:
                content = parts[0]["text"]
            else:
                content = msg.get("content", "")
            if "<|channel|>final<|message|>" in content:
                import re
                match = re.search(r"<\|channel\|>final<\|message\|>(.*)", content, re.DOTALL)
                if match:
                    content = match.group(1).strip()

            # --- 5. Final Append ---
            if content:
                clean_history.append({"role": role, "content": content})

        return clean_history

#SearXNG
class LocalConversation():
    def __init__(self, system_prompt: str, client: lms.LLM):
        self.chat = Chat(system_prompt)
        self.client = client
        self.searxng_url = "http://localhost:8080"  # Replace with your SearXNG instance URL
        self.history_user_prompts = []

    def add_user_message(self, content: str):
        self.history_user_prompts.append(content)
        self.chat.add_user_message(content)
    
    def add_assistant_response(self, content: str):
        self.history
        self.chat.add_assistant_response(content)
    
    def send_message(self, prompt: str) -> str:
        if not self.chat:
            raise ValueError("Chat object is not initialized. Call create_chat first.")
        self.add_user_message(prompt)
        response = self.client.respond(self.chat)
        return LMStudioModel.extract_true_answer(response.content)
    
    def send_message_stream(self, prompt: str):

        param_size = self.should_search(prompt)
        router_decision = param_size > 0
        print(f"Router Decision: {'YES' if router_decision else 'NO'}, {param_size if router_decision else '0'}")
        prompt_text = prompt
        if param_size > 0:
            prompt_to_query = self.rewrite_query(prompt)
            prompt_text, sources_list = self.online_search(prompt_to_query, top_results=5)
            tokenized_input = self.client.tokenize(prompt_text)
            input_count = len(tokenized_input)
            print(f"Injected search context. New prompt token count: {input_count}")
            # In online_search method...
            prompt_text += (
                        "\n---\n"
                        f"**User Request:** \"{prompt}\"\n\n"
                        "### STRICT SOURCES OF TRUTH:\n"
                        "1. **WORLD FACTS** (News, Specs, Prices, Events, People): \n"
                        "   - You must ONLY use the **Search Results** above.\n"
                        "   - If a world fact is not in the Search Results, you MUST state: 'I could not find that information.'\n"
                        "   - **NEVER** use your internal training data to answer questions about World Facts.\n"
                        "\n"
                        "2. **PERSONAL CONTEXT** (User's Name, what we said earlier): \n"
                        "   - You MAY use the **Chat History/System Prompt** for this.\n"
                        "\n"
                        "### TASK:\n"
                        "Combine these sources to answer. If the Search Results are empty or irrelevant to the User Request, STOP and admit you don't know."
                    )
            print(prompt_text)

        for chunk in self._send_message_stream(
            self.sanitize_text(prompt_text), 
            sources_list if param_size > 0 else []
        ):
            yield chunk
    
    def _send_message_stream(self, prompt: str, sources: list = [dict]) :
        self.add_user_message(prompt)
        reponse = ""
        gen_config = {
            "temperature": 0.4,
            "repetition_penalty": 1.0, 
        }

        for token in self.client.respond_stream(self.chat, config=gen_config):
            if token.content:
                reponse += token.content
                yield token.content
        if sources:
            reponse += "\n\nSources:\n"
            yield "\n\nSources:\n"
            for src in sources:
                source = f"{src.get('title')}: {src.get('url')}"
                reponse += f"- {source}\n"
                yield f"- {source}\n"
        self.add_assistant_response(reponse)

    def should_search(self, user_prompt: str) -> bool:
        """
        Optimized Router:
        1. Uses streaming to show the decision in real-time.
        2. Sets max_tokens=5 to force the engine to stop thinking immediately after YES/NO.
        """
        router_prompt = (
            "/no_think\n"
            "Determine level of external information needed to answer this prompt.\n"
            "Respond with a SINGLE integer from 0 to 10.\n"
            f"User prompt: '{user_prompt}'\n\n"
            "Rules:\n"
            "- Return 0 if the prompt is Creative, Coding, Math, **Personal/Session Context** (e.g. 'What is my name?', 'What did we just say?'), or Static Knowledge.\n" # <--- NEW RULE            "- Return 1-3 if asking for a **Specific Data Point** that might change or requires verification (e.g. 'Current Price', 'Weather', 'Release Date').\n" # <--- CHANGED
            "- Return 8-10 if asking for Broad Knowledge, News Summaries, or 'Best of' lists.\n"
            "\n"
            "Answer ONLY Integers between 0 and 10."
        )
        
        # Use a temporary lightweight chat for the router
        # Note: We do NOT add this to the main history
        router_chat = Chat("You are a logic engine. Output ONLY Integers.")
        router_chat.add_user_message(router_prompt)
        
        full_decision = ""
        DEFAULT_DEPTH = 3
        try:
            for token in self.client.respond_stream(router_chat, config={"temperature": 0.0}):
                if token.content:
                    full_decision += token.content
            match = re.search(r"(\d+)", full_decision)
            
            if match:
                val = int(match.group(1))
                final_depth = max(0, min(10, val))
                return final_depth
            print(f" -> [Warn] No number found. Defaulting to {DEFAULT_DEPTH}")
            return DEFAULT_DEPTH

        except Exception as e:
            print(f"\n[Router Error] Defaulting to NO. Details: {e}")
            return False

    def online_search(self, query: str, top_results: int = 5):
        """
        1. Searches SearXNG (with User-Agent to avoid 403 Forbidden).
        2. Injects results into the chat history.
        3. Streams the LLM's summary of those results.
        """
        print(f"DEBUG: Searching SearXNG for: {query}")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        params = {"q": query, "format": "json"}
        
        try:
            response = requests.get(f"{self.searxng_url}/search", params=params, headers=headers, timeout=10)
            response.raise_for_status()
            results = response.json().get("results", [])
            urls = []
            context_str = "### Search Results:\n\n"
            for i, result in enumerate(results[:top_results]):
                title = result.get("title", "Unknown")
                snippet = result.get("content", "")
                url = result.get("url")
                
                # Skip empty/short garbage snippets
                if len(snippet) < 30: 
                    continue
                    
                # Markdown Format
                context_str += (
                    f"### Source {i+1}\n"
                    f"**Title:** {title}\n"
                    f"**Link:** {url}\n"
                    f"**Content:** {snippet}\n\n"
                )
                urls.append({"title": title, "url": url})
            print("DEBUG: Injecting search context into chat history.")

        except Exception as e:
            return f"I searched for '{query}' but found no results.", []

        if not results:
            return f"I searched for '{query}' but found no results.", []

        # Inject context as if the user provided it
        return (context_str, urls)

    def rewrite_query(self, user_prompt: str) -> str:
        """
        Refines the user prompt into a keyword-based Search Query.
        1. Resolves pronouns (it, they) from history.
        2. Strips conversational filler (please, can you).
        """
        # If history is empty, we still want to strip filler (e.g. "Can you find x" -> "x")
        rewriter_prompt = (
            "/no_think\n"
            "You are a Search Engine Optimizer. Your task is to convert the 'Latest User Question' "
            "into a precise, keyword-based search query for SearXNG.\n\n"
            "Rules:\n"
            "1. **Resolve Context:** Replace pronouns (it, he, they, their) with specific names from the History.\n"
            "2. **Optimize:** Remove conversational filler (e.g., 'Can you find', 'I want to know', 'tell me').\n"
            "3. **Format:** Output ONLY the raw search keywords.\n"
            "\n"
            "Examples:\n"
            "- History: [User asked about Nvidia]\n"
            "- User: 'Who is their CEO?'\n"
            "- Output: `Nvidia CEO`\n\n"
            "- History: [None]\n"
            "- User: 'Can you look up the weather in Tokyo?'\n"
            "- Output: `weather Tokyo forecast`\n\n"
            f"History of User Prompts: {self.history_user_prompts}\n"
            f"Latest User Question: '{user_prompt}'\n"
            "Search Query:"
        )
        temp_chat = Chat("You are a precise search query rewriter.")
        # Use a temp chat for this logic task
        temp_chat.add_user_message(rewriter_prompt)
        
        try:
            # Fast, low temp generation
            response = self.client.respond(temp_chat, config={"temperature": 0.0, "max_tokens": 30})
            
            # Clean up quotes or extra spaces
            keywords = response.content.strip().replace('"', '').replace("Search Query:", "")
            
            # Debug print to show you what it's doing
            print("-----------------------------------")
            print(f"[Orchestrator] Optimized Search Query: '{user_prompt}' -> '{keywords}")
            print("-----------------------------------")
            _, parsed_answer = self.parse_thinking_response(keywords)
            return parsed_answer
            
        except Exception as e:
            print(f"[Rewriter Error] {e}")
            return user_prompt
        
    def parse_thinking_response(self, raw_response: str) -> tuple[str | None, str | None]:
        """
        Parses the raw response.
        Returns: (thought_process, final_answer)
        """
        if not raw_response:
            return None, None

        # 1. Check for the END of thinking (The split point)
        # DeepSeek/Qwen style usually ends with </think>
        pattern = r"</think>"
        match = re.search(pattern, raw_response)
        
        if match:
            # Found the split. Separate thoughts from answer.
            # Clean up the opening <think> tag if present
            thought_process = raw_response[:match.start()].replace("<think>", "").strip()
            final_answer = raw_response[match.end():].strip()
            return thought_process, final_answer
        
        # 2. Check if we are currently "Thinking" (Start tag exists, but no End tag)
        if "<think>" in raw_response or "<|channel|>analysis" in raw_response:
             # We are in the middle of thinking.
             # Return the raw thought content so far (stripped of tag) as the first element
             thought_content = raw_response.replace("<think>", "").strip()
             return thought_content, None 

        # 3. Standard Answer (No thinking tags detected)
        return None, raw_response.strip()
    
    def sanitize_text(self, text: str) -> str:
        """
        Removes binary characters, weird whitespace, and invisible tokens 
        that cause model collapse.
        """
        if not text:
            return ""
        # 1. Replace weird whitespace with normal space
        text = re.sub(r'\s+', ' ', text) 
        # 2. Remove non-printable characters (except standard punctuation)
        # This keeps ASCII + common UTF-8, strips binary junk
        text = "".join(ch for ch in text if ch.isprintable())
        return text.strip()
    
    def resolve_context(self, user_prompt: str) -> str:
        """
        Consolidates the user's latest message with the chat history 
        to produce a standalone, unambiguous question.
        
        Example:
        History: "Who is the CEO of Nvidia?" -> "Jensen Huang."
        Input: "What about AMD?"
        Output: "Who is the CEO of AMD?"
        """
        if not self.history_buffer:
            return user_prompt

        # Format history for the prompt
        # We take the last 2-4 turns to keep it relevant but focused
        recent_history = "\n".join(self.history_buffer[-4:])
        
        system_prompt = (
            "You are a Conversation Context Resolver. "
            "Your task is to rewrite the 'Latest User Question' to be a standalone sentence, "
            "resolving any pronouns (he, she, it, they) or implicit references based on the History.\n"
            "Rules:\n"
            "1. Keep the intent exactly the same.\n"
            "2. Replace 'it', 'that', 'him', 'her', 'their' with specific names from history.\n"
            "3. If the question is already standalone, output it exactly as is.\n"
            "4. Output ONLY the rewritten sentence. No quotes, no explanations.\n\n"
            f"--- Chat History ---\n{recent_history}\n\n"
            f"Latest User Question: \"{user_prompt}\"\n"
            "Standalone Question:"
        )
        
        # Use a temporary chat for this logic task
        # We use a very low temp to ensure it sticks to the rules
        temp_chat = Chat("Output ONLY the rewritten sentence.")
        temp_chat.add_user_message(system_prompt)
        
        try:
            # We use max_tokens=60 because the question shouldn't be an essay
            response = self.client.respond(temp_chat, config={"temperature": 0.0, "max_tokens": 60})
            resolved_text = response.content.strip().replace('"', '')
            
            # Simple check: if it failed or returned empty, fallback to original
            if not resolved_text:
                return user_prompt
                
            # Log the transformation for debugging
            if resolved_text.lower() != user_prompt.lower():
                print(f"[Context] Resolved: '{user_prompt}' -> '{resolved_text}'")
            
            return resolved_text

        except Exception as e:
            print(f"[Context Resolution Error] {e}")
            return user_prompt

def main():
    try:
        # Initialize
        lm_model = LMStudioModel('qwen/qwen3-14b')  # Ensure this model is loaded in LM Studio
        conversation = lm_model.create_chat(history_data=[])

        print("\n--- AI Assistant Online (Type 'quit' to exit) ---\n")

        while True:
            user_input = input("\nUser: ")
            if user_input.lower() in ["quit", "exit"]:
                break
            print("\nAssistant: ", end="", flush=True)
            
            # This single call now handles Routing -> Search -> Streaming -> Sourcing
            for chunk in conversation.send_message_stream(user_input):
                print(chunk, end="", flush=True)
            
            print() # End of message newline

    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        print("Ensure LM Studio is running and the model name matches.")

if __name__ == "__main__":
    main()