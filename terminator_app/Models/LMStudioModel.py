import lmstudio as lms
from lmstudio.history import Chat

class LMStudioModel():
    def __init__(self, model_name: str):
        """
        Initialize the LMStudio model client.

        Args:
            model_name (str): The name of the loaded model in LM Studio.
        """
        # Get the model object from LM Studio
        self.client = lms.llm(model_name)
        self.chat = None  # Initialize chat as None


    def create_chat(self, history_data):
        """
        Initializes the chat object and injects the message history.
        Accepts either a dict {"messages": []} or a raw list of messages.
        """
        self.chat = Chat("you're an AI assistant, try to be as helpful as possible.")

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
                self.chat.add_assistant_response(content)
            elif role == "user":
                self.chat.add_user_message(content)
            elif role in ["assistant", "model"]:
                self.chat.add_assistant_response(content)
        
        print(f"Chat created with {len(messages)} past messages injected.")
        return self.chat

    def send_message(self, prompt: str) -> str:
        if not self.chat:
            raise ValueError("Chat object is not initialized. Call create_chat first.")
        self.chat.add_user_message(prompt)
        response = self.client.respond(self.chat)
        return response

    def send_message_stream(self, prompt: str):
        self.chat.add_user_message(prompt)
        for token in self.client.respond_stream(self.chat):
            yield token

    def generate_content(self, contents: str) -> str:
        return self.client.complete(contents)

    def deserialize_history(self, flat_msgs: list) -> list:
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


@staticmethod
def flatten_conversation_messages(messages: list) -> list:
    """Flatten greeting + user/model pairs into a flat list of messages."""
    if not messages:
        return []
    flat_msgs = []
    for pair in messages[1:]:  # Skip greeting at index 0
        if isinstance(pair, dict) and 'user' in pair and 'model' in pair:
            if pair['user']:
                flat_msgs.append(pair['user'])
            if pair['model']:
                flat_msgs.append(pair['model'])
        else:
            flat_msgs.append(pair)
    return flat_msgs

def main(sample_history):
    # Initialize the model
    model_name = "openai/gpt-oss-20b"
    lm_model = LMStudioModel(model_name)
    flat_msg = flatten_conversation_messages(sample_history.get("messages", []))
    sample_history = lm_model.deserialize_history(flat_msg)
    lm_model.create_chat(sample_history)

    print("LM Studio Terminal Chat (type 'exit' or 'quit' to leave)")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Exiting...")
            # Optional: unload model to free memory
            lm_model.client.unload()
            break

        # Stream the response token by token
        print("AI: ", end="", flush=True)
        print(f"AI: {lm_model.send_message(user_input)}", end="", flush=True)
        # for token in lm_model.send_message_stream(user_input):
        #     print(token, end="", flush=True)
        print()  # newline after the response
if __name__ == "__main__":

    sample_history = {"messages": [
      {
        "role": "model",
        "parts": [
          {
            "text": "Hello! How can I assist you today?"
          }
        ],
        "timestamp": "2025-11-27T00:51:15.401079"
      },
      {
        "user": {
          "role": "user",
          "parts": [
            {
              "text": "Hello gemini give me a sample result"
            }
          ],
          "timestamp": "2025-11-27T00:51:25.838639"
        },
        "model": {
          "role": "model",
          "parts": [
            {
              "text": "Of course! Here is a sample result designed to showcase a few of my capabilities, blending creativity, technical knowledge, and practical information into a single response.\n\n***\n\nHello! I'm Gemini. I can help you brainstorm ideas, write code, plan trips, explain complex topics, and much more. To give you an idea, here is a multi-part demonstration.\n\n### **1. Creative Writing: A Micro-Story**\n\n**Prompt:** *Write a short, evocative story opener about a city where it always rains.*\n\n**Result:**\nThe neon signs of District 4 bled into the perpetual downpour, their vibrant colors running like watercolor on the slick, black asphalt. Elara didn\u2019t own an umbrella; in a city like Aethelburg, that was a statement. It meant you had nowhere dry to be, or you had simply stopped caring about the difference between the rain and the rest of the world. She pulled the collar of her worn trench coat tighter, the rhythmic drumming on the fabric a constant, familiar heartbeat against the city's metallic drone. Tonight, she was hunting for a whisper\u2014a rumor of a place where the sun still remembered to shine.\n\n---\n\n### **2. Technical Explanation & Code**\n\n**Prompt:** *Briefly explain what an API is, using an analogy, and provide a simple Python code example.*\n\n**Result:**\n\nAn **API (Application Programming Interface)** is a set of rules and tools that allows different software applications to communicate with each other.\n\n**Analogy:** Imagine you're at a restaurant. You (an application) want to get food (data) from the kitchen (another application or server). You don't go into the kitchen yourself. Instead, you give your order to a **waiter (the API)**. The waiter takes your request to the kitchen, gets the food, and brings it back to you. The API acts as that intermediary, handling requests and responses in a structured way.\n\n**Python Code Example:**\nHere is a simple Python script that uses the `requests` library to interact with a public API (the JSONPlaceholder API) to get a \"to-do\" item.\n\n```python\n# You need to install the 'requests' library first:\n# pip install requests\n\nimport requests\n\ndef get_todo_item(item_id):\n  \"\"\"\n  Fetches a specific to-do item from the JSONPlaceholder API.\n  \"\"\"\n  # The URL of the API endpoint we want to request data from\n  api_url = f\"https://jsonplaceholder.typicode.com/todos/{item_id}\"\n\n  try:\n    # Send a GET request to the URL\n    response = requests.get(api_url)\n\n    # Raise an exception if the request was unsuccessful (e.g., 404 Not Found)\n    response.raise_for_status()\n\n    # Parse the JSON response into a Python dictionary\n    data = response.json()\n\n    # Print the results in a readable format\n    print(f\"Successfully fetched To-Do Item #{item_id}:\")\n    print(f\"  User ID: {data['userId']}\")\n    print(f\"  Title: {data['title']}\")\n    print(f\"  Completed: {'Yes' if data['completed'] else 'No'}\")\n\n  except requests.exceptions.RequestException as e:\n    print(f\"An error occurred: {e}\")\n\n# Let's get the to-do item with ID 1\nget_todo_item(1)\n```\n\n---\n\n### **3. Structured Information & Planning**\n\n**Prompt:** *Create a 3-day itinerary for a first-time visitor to Rome, Italy.*\n\n**Result:**\n\n#### **A 3-Day Whirlwind Tour of Rome**\n\nThis itinerary balances major historical sites with leisure and food experiences.\n\n**Day 1: Ancient Rome**\n*   **Morning (9:00 AM):** Start at the **Colosseum**. Buy tickets online in advance to skip the long lines. Spend 2-3 hours exploring this iconic amphitheater.\n*   **Lunch (12:30 PM):** Grab a casual lunch (pizza al taglio or a panino) in the Monti neighborhood.\n*   **Afternoon (2:00 PM):** Explore the **Roman Forum** and **Palatine Hill**, located right next to the Colosseum. This was the heart of ancient Rome.\n*   **Evening (7:00 PM):** Enjoy a traditional Roman dinner in the Trastevere district, known for its charming, ivy-covered streets and excellent restaurants.\n\n**Day 2: The Vatican & Renaissance Art**\n*   **Morning (8:30 AM):** Head to **Vatican City**. Start with the **Vatican Museums** and the **Sistine Chapel**. This is another \"book-in-advance\" must.\n*   **Lunch (1:00 PM):** Have lunch near the Vatican in the Prati neighborhood.\n*   **Afternoon (2:30 PM):** Visit **St. Peter's Basilica**. Take time to admire its scale and Michelangelo's dome (you can climb it for an amazing view).\n*   **Evening (6:00 PM):** Walk to **Castel Sant'Angelo** and cross the beautiful Ponte Sant'Angelo at sunset.\n\n**Day 3: Fountains, Piazzas & Farewell**\n*   **Morning (10:00 AM):** Visit the **Pantheon**, an architectural marvel. Entry is free.\n*   **Late Morning (11:30 AM):** Walk to the **Trevi Fountain**. Toss a coin to ensure your return to Rome. Then, head to the **Spanish Steps**.\n*   **Lunch (1:30 PM):** Enjoy a leisurely lunch near Piazza Navona.\n*   **Afternoon (3:00 PM):** Explore the high-end shops around Via del Corso or relax in the **Borghese Gardens** (Villa Borghese).\n*   **Evening (7:30 PM):** Enjoy a farewell dinner with a classic Carbonara or Cacio e Pepe.\n\n***\n\nThis is just a small glimpse. Now, what would you like to create, learn, or explore? Feel free to ask me anything"
            }
          ],
          "timestamp": "2025-11-27T00:51:53.066880"
        },
        "ai_pending": False
      },
      {
        "user": {
          "role": "user",
          "parts": [
            {
              "text": "I want to impelement a  local model on my machine how hard would that be"
            }
          ],
          "timestamp": "2025-11-27T01:27:48.017018"
        },
        "model": {
          "role": "model",
          "parts": [
            {
              "text": "Excellent question! This is a very popular topic right now, and the answer has changed dramatically over the last year.\n\nThe short answer is: **It has become surprisingly easy to get started, but the *quality and speed* of your experience will depend entirely on your computer's hardware.**\n\nLet's break down \"how hard\" it is into a spectrum, from easy to difficult.\n\n---\n\n### Level 1: The \"Easy\" Path (For Everyone)\n\nThis is for users who just want to chat with a powerful AI like ChatGPT, but locally on their own machine, with full privacy.\n\n*   **What it is:** Using a simple, all-in-one desktop application. These apps handle all the complexity of downloading, configuring, and running the models for you.\n*   **How Hard Is It?** **1/10**. If you can install software like a web browser or a game, you can do this.\n*   **What You Need:** A decent modern computer.\n*   **Recommended Tools:**\n    *   **[LM Studio](https://lmstudio.ai/):** Extremely popular. It has a built-in model browser, resource monitor, and a familiar chat interface. You just find a model, click download, and then start chatting.\n    *   **[Ollama](https://ollama.com/) + [Open WebUI](https://github.com/open-webui/open-webui):** Ollama is a fantastic tool that runs in the background. By itself, you use it from the command line, but when you pair it with a web interface like Open WebUI, you get a beautiful, self-hosted ChatGPT-like experience in your browser.\n    *   **[GPT4All](https://gpt4all.io/):** Another great option focused on running models even on less powerful hardware (including just your CPU).\n\n**Verdict:** For basic chatting and experimentation, it's **very easy**.\n\n---\n\n### Level 2: The \"Medium\" Path (For Developers & Hobbyists)\n\nThis is for people who are comfortable with the command line or want to integrate a local model into their own code (e.g., a Python script).\n\n*   **What it is:** Using command-line tools or programming libraries to run and interact with models. This gives you much more control.\n*   **How Hard Is It?** **4/10**. Requires basic programming knowledge or comfort with a terminal.\n*   **What You Need:** Familiarity with concepts like Python, Git, and command-line interfaces.\n*   **Recommended Tools:**\n    *   **Ollama (Command Line):** The base version of Ollama is a command-line tool. A simple command like `ollama run llama3` will download and run Meta's Llama 3 model right in your terminal. It's incredibly powerful and simple for developers.\n    *   **[Llama.cpp](https://github.com/ggerganov/llama.cpp):** The powerhouse of local models. This C++ project is hyper-optimized to run models very efficiently, even on just a CPU. Most of the GUI apps (like LM Studio) use this under the hood. You compile it yourself and run models from the command line.\n    *   **Hugging Face `transformers` library:** The industry-standard Python library for AI. With a few lines of Python code, you can download and run thousands of different models. This is the path you'd take to build a custom application.\n\n**Verdict:** For developers, it's **moderately easy** and incredibly flexible.\n\n---\n\n### Level 3: The \"Hard\" Path (For AI Engineers & Researchers)\n\nThis is for people who want to train or fine-tune their own models.\n\n*   **What it is:** Taking a base model and training it on your own data to make it specialized for a task. This requires deep knowledge of the underlying technology.\n*   **How Hard Is It?** **8/10**. Requires expertise in machine learning, powerful hardware, and a lot of patience.\n*   **What you need:** A deep understanding of Python, ML frameworks (like PyTorch), and a very powerful GPU.\n\n**Verdict:** This is **very difficult** and reserved for specialists.\n\n---\n\n### The Most Important Factor: Your Hardware\n\nThis is the real bottleneck. Models are loaded into your computer's RAM or, ideally, your GPU's Video RAM (VRAM).\n\n*   **VRAM is King:** The more VRAM your graphics card has, the larger and more capable the models you can run at a good speed.\n    *   **Minimal (CPU only):** 16GB of regular RAM. It will be **slow**, but it will work for small models using tools like Llama.cpp or GPT4All.\n    *   **Good Start (GPU):** An NVIDIA GPU with **8 GB - 12 GB of VRAM** (e.g., RTX 3060, 4060 Ti). You can run many popular 7-billion-parameter models very comfortably.\n    *   **Excellent (GPU):** An NVIDIA GPU with **16 GB - 24 GB of VRAM** (e.g., RTX 3090, 4090). This is the sweet spot for enthusiasts. You can run much larger and more powerful models (13B, 34B, and even some 70B models with optimization).\n*   **Apple Silicon (M1/M2/M3):** These are a special case. Their \"unified memory\" is excellent for running LLMs because the CPU and GPU share a large pool of memory. A MacBook Pro with 32GB of unified memory can run models that a PC with a 12GB GPU would struggle with.\n\n### Step-by-Step Guide for the Easiest Method (Ollama)\n\nWant to try it right now? Here's how simple it is:\n\n1.  **Download:** Go to **[ollama.com](https://ollama.com/)** and download the installer for your OS (Mac, Windows, or Linux).\n2.  **Install:** Run the installer. It will set up a background service.\n3.  **Run a Model:** Open your terminal (Terminal on Mac/Linux, PowerShell or Command Prompt on Windows) and type this command:\n    ```bash\n    ollama run llama3\n    ```\n4.  **Wait & Chat:** The first time, it will download the model (a few gigabytes). Once it's done, you'll see a prompt that says `>>> Send a message...`. You are now chatting with a powerful AI running 100% on your machine!\n\nThat's it. You've just implemented a local model."
            }
          ],
          "timestamp": "2025-11-27T01:28:21.109474"
        },
        "ai_pending": False
      }
    ]}
    main(sample_history)