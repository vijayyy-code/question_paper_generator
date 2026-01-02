import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("Available models:\n")

# Use 'supported_actions' for the latest SDK versions
for m in client.models.list():
    if "generateContent" in m.supported_actions:
        print(f"Model ID: {m.name}")
        print(f"Display Name: {m.display_name}")
        print("-" * 30)