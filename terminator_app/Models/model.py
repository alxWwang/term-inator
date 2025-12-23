from collections import deque
from io import BytesIO
import re
import threading
from time import time
import unicodedata
import PyPDF2
import feedparser
import lmstudio as lms
from lmstudio.history import Chat
from pathlib import Path
import requests
import time
import webbrowser
# --- Tools --- #

# --- LocalConversation wrapper --- #

class LocalConversation:
    def __init__(self, system_prompt: str, model_client: lms.llm):
        self.chat = Chat(system_prompt)
        self.model: lms.llm = model_client

    def _sanitize_msg(self, msg: str) -> str:
        if not msg:
            return ""
        msg = unicodedata.normalize('NFKC', msg)
        msg = "".join(c for c in msg if c.isprintable())
        msg = re.sub(r"\s+", " ", msg)
        msg = msg.strip()
        return msg

    def add_user_message(self, msg: str):
        self.chat.add_user_message(msg)

    def add_assistant_message(self, msg: str):
        self.chat.add_assistant_response(msg)
    
    def send_message_stream(self, msg: str):
        # sanitize incoming message before adding to chat
        safe_msg = self._sanitize_msg(msg)
        self.add_user_message(safe_msg)
        fragments = deque()
        finished = threading.Event()

        def on_fragment(fragment, *args, **kwargs):
            fragments.append(fragment.content)

        def run_act():
            self.model.act(
                self.chat,
                [self.create_file, self.search_online, self.search_arxiv, self.open_link],
                on_message=self.chat.append,
                on_prediction_fragment=on_fragment
            )
            finished.set()  # Signal when act is done

        # Run act in a separate thread so we can yield as fragments come
        t = threading.Thread(target=run_act)
        t.start()

        while not finished.is_set() or fragments:
            while fragments:
                yield fragments.popleft()
            time.sleep(0.001)  # tiny sleep to prevent busy waiting

        t.join()


    def create_file(self, name: str, content: str):
        """Create a file with the given name and content. Creates parent folders if needed."""
        print(f"Creating file: {name}")
        path = Path("/home/wang/AI_base") / name
        if path.exists():
            return "Error: File already exists."
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        except Exception as e:
            return f"Error: {e!r}"
        return "File created."
    
    def open_link(self, url: str):
        """Open a link in the default web browser and return a status message.
        """
        print(f"Opening link: {url}")
        if not isinstance(url, str) or not url:
            return "Error: invalid URL"

        # Normalize scheme if missing
        if url.startswith("//"):
            url = f"https:{url}"
        elif not url.startswith("http://") and not url.startswith("https://"):
            url = "http://" + url

        print(f"Opening link: {url}")
        try:
            opened = webbrowser.open(url, new=2, autoraise=True)
            return f"Browser open called (success={opened}) for {url}"
        except Exception as e:
            return f"Error opening link with webbrowser: {e!r}"

    def search_online(self, query: str):
        """Search using a local SearXNG instance and return results."""
        searxng_url = "http://localhost:8888/searxng"  # adjust your SearXNG URL
        params = {"q": query, "format": "json"}
        print(f"Searching online for: {query}")
        try:
            response = requests.get(f"{searxng_url}/search", params=params, timeout=10)
            response.raise_for_status()
            results = response.json().get("results", [])
        except Exception as e:
            return f"Error contacting SearXNG: {e}"
        
        # Combine results
        output = ""
        for r in results[:5]:  # limit to top 5 results
            output += f"{r.get('title','')} - {r.get('url','')}\n{r.get('content','')}\n\n"
        return output or "No results found."
    
    def web_scraper(self, url):
        """Fetch and return the text content of a web page."""
        print(f"Scraping URL: {url}")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            return f"Error fetching URL: {e}"

    def search_arxiv(self,query: str):
        """Search arXiv for academic papers related to the query."""
        arxiv_api_url = "http://export.arxiv.org/api/query"
        params = {
            "search_query": query,
            "start": 0,
            "max_results": 5,
            "sort_by": "submittedDate",
            "sort_order": "descending"
        }
        print(f"Searching arXiv for: {query}")
        try:
            response = requests.get(arxiv_api_url, params=params, timeout=10)
            text = self.parse_arxiv_feed_xml(response.content)
            results = []
            for entry in text:
                results.append({
                    "title": entry.get("title"),
                    "authors": entry.get("authors"),
                    "summary": entry.get("summary"),
                    "link": entry.get("id")
                })
            
            # Return a formatted list of articles
            formatted = "\n".join(
                [f"{i+1}. {r['title']} by {', '.join(r['authors'])} ({r['link']})"
                for i, r in enumerate(results)]
            )
            return formatted
        except Exception as e:
            return f"Error contacting arXiv: {e}"
        
    def parse_arxiv_feed_xml(self, xml_string, download_pdfs=False):
        feed = feedparser.parse(xml_string)
        results = []
        for entry in feed.entries:
            pdf_link = next(
                (l.href for l in entry.links
                if l.get('type') == 'application/pdf' or l.get('title') == 'pdf'),
                None
            )
            item = {
                "id": entry.get("id"),
                "title": entry.get("title"),
                "summary": entry.get("summary"),
                "updated": entry.get("updated"),
                "published": entry.get("published"),
                "authors": [a.get("name") for a in entry.get("authors", [])],
                "categories": [c.get("term") for c in entry.get("tags", [])],
                "pdf_link": pdf_link,
            }

            if download_pdfs and pdf_link:
                r = requests.get(pdf_link, timeout=10)
                r.raise_for_status()
                pdf_file = BytesIO(r.content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                text = "".join((p.extract_text() or "") for p in pdf_reader.pages)
                item["pdf_text"] = text

            results.append(item)
        return results

# --- Example usage --- #

if __name__ == "__main__":

    conversation = LocalConversation(
        """
        ## Role
        You are a helpful assistant for the user, Wang. 
        Provide clear, concise, and friendly responses. Use emojis where appropriate.
        For complex tasks:
        1. Break them into clear, numbered steps.
        2. Identify which steps require tools (e.g., search_online, create_file) and which can be done from your knowledge.
        3. Avoid overthinking or looping — if a step can be done without a tool, do it immediately.
        Always invite follow-up questions.
        """,
        model_client=lms.llm(
            "openai/gpt-oss-20b",
            config={"contextLength": 16000, "numExperts": 8, "temperature": 0.2, "topP": 0.9}
            )
    )

    print("Type your commands (leave blank to exit).")
    while True:
        user_input = input("You: ")
        if not user_input:
            break
        print("Assistant: ", end="", flush=True)
        for i in conversation.send_message_stream(user_input):
            print(i, end="", flush=True)
        context_length = conversation.model.get_context_length()
        print(f"\n[Context length used: {context_length} tokens]")
        print("\n")
        print("----------------------------------------------------------------------------------------")
