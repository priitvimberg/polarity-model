from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
import requests
import json

app = Flask(__name__, static_folder='../frontend/static')
CORS(app)

# Database setup
DB_PATH = 'model.db'

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS prompts
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, prompt TEXT, nodes TEXT, edges TEXT)''')
        conn.commit()

init_db()

# xAI API call (simplified, replace with your actual implementation including DEBUG logs)
def xai_api_call(prompt):
    api_key = os.environ.get('API_KEY')
    if not api_key:
        raise ValueError("API_KEY not set")
    headers = {'Authorization': f'Bearer {api_key}'}
    # Add your DEBUG: print(f"DEBUG:__main__:Sending request to Grok API with prompt: {prompt[:50]}...")
    response = requests.post('https://api.x.ai/v1/chat/completions', json={'prompt': prompt}, headers=headers)  # Updated endpoint based on your logs
    # Add your DEBUG: print(f"DEBUG:urllib3.connectionpool:{response.request.method} ...")
    response.raise_for_status()
    # Add your DEBUG: print(f"DEBUG:__main__:Grok API response status: {response.status_code}, body: {response.text[:50]}...")
    return response.json()

# Process API response to generate nodes and edges (simplified example, add your interpretation logic)
def process_response(api_response):
    # Example: Parse response to create Vis.js-compatible nodes and edges
    # Replace with your actual logic, including DEBUG prints for 'Interpreted response', 'Graph data', etc.
    nodes = [
        {'id': 1, 'label': 'Pole 1', 'maturity': 1, 'ego_state': 'Adapted Child', 'role': 'Victim'},
        {'id': 2, 'label': 'Pole 2', 'maturity': 2, 'ego_state': 'Controlling Parent', 'role': 'Persecutor'}
    ]
    edges = [
        {'from': 1, 'to': 2, 'polarity': 0.8, 'light_shadow': 'shadow'}
    ]
    return nodes, edges

@app.route('/', methods=['GET'])
def home():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/add', methods=['POST'])
def add_prompt():
    data = request.get_json()
    prompt = data.get('prompt', '')
    if not prompt.strip():
        return jsonify({'error': 'Prompt is required'}), 400
    try:
        # Call xAI API
        api_response = xai_api_call(prompt)
        nodes, edges = process_response(api_response)
        # Store in database
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('INSERT INTO prompts (prompt, nodes, edges) VALUES (?, ?, ?)',
                      (prompt, json.dumps(nodes), json.dumps(edges)))
            conn.commit()
        return jsonify({'nodes': nodes, 'edges': edges})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/reset', methods=['POST'])
def reset():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM prompts')
            conn.commit()
        return jsonify({'status': 'Database reset'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)