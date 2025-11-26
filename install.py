import os
import sys
import subprocess

API_KEY_ENV = "GENAI_API_KEY"
ENV_FILE = ".env"
DEBUG_ENV = "DEBUG_MODE"

# Install dependencies
print("Installing dependencies...")
try:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
except subprocess.CalledProcessError:
    print("Warning: Failed to install some dependencies.")

print("Welcome to Terminator installer!")
api_key = input("Enter your GENAI API key (leave blank for debug mode): ").strip()

if not api_key:
    with open(ENV_FILE, "w") as f:
        f.write(f"{DEBUG_ENV}=True\n")
    print("No API key entered. The app will run in debug mode.")
    print(f"Debug mode enabled and saved to {ENV_FILE}.")
    print("Installation complete. You can now run 'terminator' from the terminal.")
    # Run setup.py to install package
    print("Installing package...")
    subprocess.check_call([sys.executable, "setup.py", "install"])
    sys.exit(0)

# Validate the API key
try:
    from google import genai
    client = genai.Client(api_key=api_key)
    models = client.models.list()
    if not models:
        raise Exception("No models returned.")
except Exception as e:
    print(f"API key validation failed: {e}")
    print("Install failed. Please check your GENAI API key and try again.")
    sys.exit(1)

with open(ENV_FILE, "w") as f:
    f.write(f"{API_KEY_ENV}={api_key}\n{DEBUG_ENV}=False\n")
print(f"API key validated and saved to {ENV_FILE}.")
print("Installation complete. You can now run 'terminator' from the terminal.")
# Run setup.py to install package
print("Installing package...")
subprocess.check_call([sys.executable, "setup.py", "install"])
