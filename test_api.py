import requests
import os

API_KEY = os.getenv("API_KEY") or "your-xai-api-key-here"  # Replace with your key
GROK_API_URL = "https://api.x.ai/v1/chat/completions"

headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
data = {
    "model": "grok-4",
    "messages": [{"role": "user", "content": "Test prompt"}]
}

response = requests.post(GROK_API_URL, headers=headers, json=data)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:200]}")
