from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
import requests
import json

app = Flask(__name__)
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

# xAI API call (simplified, replace with your actual implementation)
def xai_api_call(prompt):
    api_key = os.environ.get('API_KEY')
    if not api_key:
        raise ValueError("API_KEY not set")
    headers = {'Authorization': f'Bearer {api_key}'}
    response = requests.post('https://api.x.ai/v1/grok', json={'prompt': prompt}, headers=headers)
    response.raise_for_status()
    return response.json()

# Process API response to generate nodes and edges (simplified example)
def process_response(api_response):
    # Example: Parse response to create Vis.js-compatible nodes and edges
    # Replace with your actual logic
    nodes = [
        {'id': 1, 'label': 'Pole 1'},
        {'id': 2, 'label': 'Pole 2'},
        {'id': 3, 'label': f'Maturity {api_response.get("maturity", 3)}'}
    ]
    edges = [
        {'from': 1, 'to': 3},
        {'from': 2, 'to': 3}
    ]
    return nodes, edges

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
    app.run(debug=True)