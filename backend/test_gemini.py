import os
import sys
from openai import OpenAI

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

if os.path.exists(".env"):
    load_dotenv(".env")
    print("Loaded .env file")

api_key = os.getenv("LLM_API_KEY", "AIzaSyCd3YC4LTiFpsH0p3nZ1SaegDiMAlUGW7A")
base_url = os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")

print(f"Key: {api_key[:5]}... Base URL: {base_url}")

client = OpenAI(
    api_key=api_key,
    base_url=base_url
)

try:
    response = client.chat.completions.create(
        model="gemini-2.5-flash",
        messages=[{"role": "user", "content": "Return JSON with a status field"}],
        max_tokens=100,
        response_format={"type": "json_object"}
    )
    print("SUCCESS 2.5 JSON:", response.choices[0].message.content)
except Exception as e:
    print("ERROR 2.5 JSON:", type(e).__name__, str(e))
