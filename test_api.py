import requests
import os

GROK_API_URL = "https://api.x.ai/v1/chat/completions"
API_KEY = os.getenv("API_KEY")

if not API_KEY:
    print("Error: API_KEY environment variable not set")
    exit(1)

headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
data = {
    "model": "grok-4",
    "messages": [{
        "role": "system",
        "content": """Interpret inputs for a polarity-maturity model using Wheel of Consent, Tension Triangle (Victim-Rescuer-Persecutor or Creator-Coach-Challenger), and ego states. Extract: 
        - Nodes: name, ego_state ('Free Child', 'Adapted Child', 'Adult', etc.), maturity (1-5), role (Victim, Creator, etc.), metacognition (true/false).
        - Edge: polarity (-1 to 1), light_shadow ('light'/'shadow'), role (Victim-Rescuer, etc.), consent (true/false).
        - Suggest role flip (e.g., Victim to Creator) if applicable.
        Output JSON: {
            'nodes': [{'name': 'A', 'ego_state': 'Adult', 'maturity': 3, 'role': 'Creator', 'metacognition': true, 'history': ''}],
            'polarity': 0.5, 'light_shadow': 'light', 'role': 'Creator-Coach', 'consent': true, 'description': '...', 'role_flip': 'Victim to Creator'
        }"""
    }, {"role": "user", "content": "Add shadow polarity between AI Startup (Victim, Adapted Child, mat 2) and Ethics Board (Persecutor, Controlling Parent, mat 3) with Victim-Persecutor role, no consent."}]
}

try:
    print(f"Sending request to {GROK_API_URL}...")
    response = requests.post(GROK_API_URL, headers=headers, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}")
    if response.status_code == 200:
        print(f"Parsed JSON: {response.json()}")
except Exception as e:
    print(f"Error: {str(e)}")
