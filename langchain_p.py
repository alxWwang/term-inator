import requests
import re
import datetime
from io import BytesIO
import PyPDF2
from typing import List, Optional

# --- LangChain Modular Imports ---
# This fixes the ModuleNotFoundError by using the explicit package names:
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import CharacterTextSplitter
try:
    # New standalone package for HF embeddings
    from langchain_huggingface import HuggingFaceEmbeddings
except Exception:
    # Fallback for older layouts
    from langchain_community.embeddings import HuggingFaceEmbeddings
import lmstudio as lms
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from pydantic import BaseModel, Field  # FIX: Importing directly from the Pydantic library

# NEW FIX: Importing Agent components from their core locations.
# NOTE: `create_tool_calling_agent` and `AgentExecutor` locations vary between
# LangChain releases. To avoid tight coupling to package layout, use a small
# local agent wrapper that selects and calls tools. This keeps the file
# compatible with the latest packaging layout without depending on internal
# helper locations.

# (We will implement a lightweight `SimpleAgentExecutor` below.)

# Note: we avoid importing ConversationBufferMemory and RetrievalQA from
# langchain packages to remain compatible across versions. The local
# `SimpleAgentExecutor` provides lightweight memory and the PDF RAG tool
# performs retrieval + LLM synthesis directly.
# ---------------------------------


# --- CONFIGURATION ---
LLM_MODEL = "qwen3-14b"
LMSTUDIO_BASE_URL = "http://localhost:1234"
SEARXNG_URL = "http://localhost:8080"
PDF_URL = "https://arxiv.org/pdf/2106.09685.pdf"

# Global placeholder for the FAISS database (will be loaded once in __main__)
GLOBAL_DB = None 

# --- 1. DOCUMENT PROCESSING AND KNOWLEDGE BASE SETUP ---

def get_pdf_text(url: str) -> str:
    """Downloads a PDF and extracts all text content."""
    print(f"Downloading PDF from: {url}")
    try:
        response = requests.get(url, timeout=10)
        pdf_file = BytesIO(response.content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        print(f"Error fetching or reading PDF: {e}")
        return ""

def process_text_and_get_vectorstore(text: str) -> FAISS:
    """Splits text, creates embeddings, and builds the FAISS vector store."""
    print("Building Vector Store (FAISS)...")
    
    text_splitter = CharacterTextSplitter(
        separator="\n", 
        chunk_size=512,
        chunk_overlap=128,
        length_function=len
    )
    chunks = text_splitter.split_text(text)

    # Use a high-quality, local-first embedding model
    # This relies on your previous successful installation of sentence-transformers
    embeddings = HuggingFaceEmbeddings(model_name='sentence-transformers/all-mpnet-base-v2')
    
    knowledgeBase = FAISS.from_texts(chunks, embeddings)
    print(f"Vector Store built with {len(chunks)} chunks.")
    return knowledgeBase

# --- 2. TOOL DEFINITIONS (The Agent's Capabilities) ---

class SearchInput(BaseModel):
    """Input for the WebSearchTool."""
    query: str = Field(description="A precise, factual question about a person, current event, price, or general knowledge.")

def web_search_tool(query: str) -> str:
    """
    Performs a real-time web search for volatile or general knowledge questions 
    that are not contained in the PDF document.
    """
    print(f"\n[Tool Activated] Searching Web for: '{query}'")
    headers = {"User-Agent": "Mozilla/5.0"}
    params = {"q": query, "format": "json"}
    
    try:
        response = requests.get(f"{SEARXNG_URL}/search", params=params, headers=headers, timeout=5)
        results = response.json().get("results", [])
        
        context_str = f"SYSTEM TIME: {datetime.datetime.now().strftime('%Y-%m-%d')}. "
        snippets = []
        
        for result in results[:3]:
            title = result.get("title", "Unknown Source")
            snippet = result.get("content", "No Snippet")
            snippet = re.sub(r'\s+', ' ', snippet).strip()
            if len(snippet) > 20:
                 snippets.append(f"[{title}]: {snippet}")

        if not snippets:
            return f"No relevant web search results found for query: {query}"
        
        return context_str + " | ".join(snippets)

    except Exception as e:
        return f"Search Error: Could not connect to external search service. ({e})"


def pdf_rag_tool(query: str) -> str:
    """
    Queries the locally loaded LoRA PDF document for technical information.
    Use ONLY for questions about LoRA, fine-tuning, or related concepts.
    """

    global GLOBAL_DB
    if GLOBAL_DB is None:
        return "PDF database is not loaded. Cannot answer document-specific questions."

    print(f"\n[Tool Activated] Querying LoRA PDF RAG for: '{query}'")
    
    # Manual retrieval + LLM synthesis (avoids requiring RetrievalQA import)
    try:
        llm = lms.llm(LLM_MODEL)
        # Retrieve top-k similar chunks from the FAISS DB
        docs = []
        try:
            docs = GLOBAL_DB.similarity_search(query, k=4)
        except Exception:
            # As a fallback, try as_retriever then get docs
            try:
                retr = GLOBAL_DB.as_retriever(search_kwargs={"k": 4})
                docs = retr.get_relevant_documents(query)
            except Exception:
                docs = []

        if not docs:
            return f"Answer from PDF: No relevant document passages found for query: {query}"

        # Build the context and ask the LLM to synthesize an answer using only the context
        context = "\n\n".join(getattr(d, 'page_content', str(d)) for d in docs[:4])
        prompt = (
            "### CONTEXT:\n"
            f"{context}\n\n"
            "### QUESTION:\n"
            f"{query}\n\n"
            "Answer concisely using ONLY the CONTEXT above. If the answer is not present, say 'Not found in document'."
        )
        # Prefer streaming APIs when available so the caller can stream tokens.
        # We return a generator when streaming; otherwise return the full string.
        def stream_generator():
            # Try common LMStudio streaming methods in order
            stream_fn = None
            for name in ("respond_stream", "complete_stream", "stream", "astream"):
                if hasattr(llm, name):
                    stream_fn = getattr(llm, name)
                    break

            if stream_fn is not None:
                try:
                    for chunk in stream_fn(prompt):
                        # chunk may be an object with .content or a raw string
                        text = getattr(chunk, 'content', None) or getattr(chunk, 'text', None) or str(chunk)
                        yield text
                    return
                except Exception:
                    # Fall through to non-streaming fallback
                    pass

            # Non-streaming fallback
            try:
                complete_result = llm.complete(prompt)
                answer = getattr(complete_result, 'parsed', None) or str(complete_result)
                yield answer
                return
            except Exception:
                try:
                    resp = llm.respond(prompt)
                    answer = getattr(resp, 'content', str(resp))
                    yield answer
                    return
                except Exception as e:
                    yield f"PDF RAG Tool Error (LLM invocation failed): {e}"

        # Return the generator so the caller can stream the answer.
        return stream_generator()
    except Exception as e:
        return f"PDF RAG Tool Error: {e}"


# --- 3. AGENT ORCHESTRATION SETUP ---

def create_multi_tool_agent(llm, tools: List[callable]):
    """Creates a minimal agent executor that selects between provided tools.

    This lightweight executor avoids relying on internal LangChain locations
    which can vary between package versions. It returns an object with an
    `invoke` method that accepts `{"input": <str>}` and returns
    `{"output": <str>}` so the rest of the program can remain unchanged.
    """

    class SimpleAgentExecutor:
        def __init__(self, llm, tools: List[callable]):
            self.llm = llm
            # Map tool function names to callables for convenience
            self.tools = {getattr(t, "__name__", str(i)): t for i, t in enumerate(tools)}
            # Preserve original list order as well
            self.tools_list = tools
            self.memory = []

        def choose_tool(self, query: str):
            q = query.lower()
            # Heuristic: prefer PDF_RAG_Tool on LoRA / paper / fine-tune related queries
            if any(k in q for k in ("lora", "lo-ra", "l.o.r.a", "fine-tune", "fine tuning", "paper", "arxiv")):
                # find pdf_rag_tool if present
                for t in self.tools_list:
                    if getattr(t, "__name__", "").lower().startswith("pdf"):
                        return t
            # Otherwise prefer web search
            for t in self.tools_list:
                name = getattr(t, "__name__", "").lower()
                if "search" in name or "web" in name:
                    return t
            # Fallback: return first tool
            return self.tools_list[0] if self.tools_list else None

        def invoke(self, inputs: dict) -> dict:
            user_input = inputs.get("input") if isinstance(inputs, dict) else inputs
            if not user_input:
                return {"output": "No input provided."}

            self.memory.append(user_input)

            tool = self.choose_tool(user_input)
            if tool is None:
                return {"output": "No tools available to handle the request."}

            try:
                # Call tool synchronously; tools may expect a single string argument
                    result = tool(user_input)
            except TypeError:
                # Some tools may expect a dict or named args
                try:
                    result = tool(query=user_input)
                except Exception as e:
                    result = f"Tool invocation failed: {e}"

                # If the tool returned a generator/iterator (streaming LLM), forward it
                is_stream = False
                try:
                    # Strings are iterable too, so ensure we don't treat them as streams
                    if not isinstance(result, (str, bytes)) and hasattr(result, '__iter__'):
                        is_stream = True
                except Exception:
                    is_stream = False

                if is_stream:
                    return result

                return {"output": str(result)}

    return SimpleAgentExecutor(llm, tools)


# --- 4. EXECUTION ---

if __name__ == "__main__":
    # 4a. Initialize LLM Client
    try:
        # We define the LM Studio LLM here, which will be used for agent reasoning AND the RAG chain
        llm_client = lms.llm(LLM_MODEL)
        
        # 4b. Load the PDF knowledge base into the global variable
        paper_text = get_pdf_text(PDF_URL)
        if not paper_text:
            print("Initialization failed: Could not load PDF.")
            exit()
        GLOBAL_DB = process_text_and_get_vectorstore(paper_text)
        
        # 4c. Define the Tools
        tools = [pdf_rag_tool, web_search_tool]
        
        # 4d. Create the Agent
        agent = create_multi_tool_agent(llm_client, tools)

        print("\n--- Conversational Multi-Tool RAG Agent Online ---")
        print("Model: Qwen3-14b | Tools: PDF_RAG_Tool, Web_Search_Tool")
        print("\nExample 1: 'What are the main advantages of LoRA?' (Should use PDF_RAG_Tool)")
        print("Example 2: 'Who is the current CEO of Kellanova?' (Should use Web_Search_Tool)")
        
        while True:
            user_query = input("\nUser: ")
            if user_query.lower() in ["quit", "exit"]:
                print("Exiting RAG agent.")
                break
            
            # The agent handles the full conversation turn
            try:
                result = agent.invoke({"input": user_query})
                # The agent output is the final synthesized answer
                print(f"Assistant: {result['output']}")
            
            except Exception as e:
                print(f"\n[Agent Error] An error occurred: {e}")
                print("Assistant: I apologize, I encountered an issue and cannot continue.")

    except requests.exceptions.ConnectionError:
        print(f"\nCRITICAL ERROR: Could not connect to LM Studio server at {LMSTUDIO_BASE_URL}.")
        print("Please ensure your local LLM server is running.")
    except Exception as e:
        print(f"\nCRITICAL ERROR: An unexpected error occurred during setup: {e}")