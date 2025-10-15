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

# xAI API call with stronger system prompt for JSON only
def xai_api_call(prompt):
    api_key = os.environ.get('API_KEY')
    if not api_key:
        raise ValueError("API_KEY not set")
    headers = {'Authorization': f'Bearer {api_key}'}
    payload = {
        'model': 'grok-4-0709',
        'messages': [
            {'role': 'system', 'content': 'You are an assistant that provides structured JSON output for polarity and maturity model graphs. Return ONLY a JSON object with "nodes" (array of {id, name, maturity, ego_state, role, metacognition, history}) and "edges" (array of {source, target, polarity, light_shadow, role, consent, description}). No other text, explanation, or formatting.'},
            {'role': 'user', 'content': prompt}
        ]
    }
    print(f"DEBUG: Sending request to Grok API with payload: {json.dumps(payload)[:100]}...")
    response = requests.post('https://api.x.ai/v1/chat/completions', json=payload, headers=headers, timeout=60)  # Increased timeout
    print(f"DEBUG: Grok API response status: {response.status_code}, body: {response.text[:200]}...")
    response.raise_for_status()
    return response.json()

# Process API response with fallback
def process_response(api_response):
    try:
        content = api_response['choices'][0]['message']['content']
        print(f"DEBUG: Interpreted response: {content[:200]}...")
        try:
            parsed = json.loads(content)
            nodes = parsed.get('nodes', [])
            edges = parsed.get('edges', [])
            if not nodes or not edges:
                raise ValueError("Empty nodes or edges in parsed response")
        except json.JSONDecodeError:
            print("DEBUG: API returned non-JSON response, using fallback graph")
            nodes = [
                {'id': 1, 'name': 'Pole 1', 'maturity': 1, 'ego_state': 'Adapted Child', 'role': 'Victim', 'metacognition': False, 'history': ''},
                {'id': 2, 'name': 'Pole 2', 'maturity': 2, 'ego_state': 'Controlling Parent', 'role': 'Persecutor', 'metacognition': False, 'history': ''}
            ]
            edges = [{'source': 1, 'target': 2, 'polarity': 0.5, 'light_shadow': 'shadow', 'role': 'Victim-Persecutor', 'consent': False, 'description': 'Fallback edge'}]
        print(f"DEBUG: Graph data: {json.dumps({'nodes': nodes, 'edges': edges})[:200]}...")
        return nodes, edges
    except KeyError as e:
        raise ValueError(f"Invalid API response structure: {str(e)}")
    except Exception as e:
        print(f"DEBUG: Error processing response, using fallback: {str(e)}")
        nodes = [
            {'id': 1, 'name': 'Pole 1', 'maturity': 1, 'ego_state': 'Adapted Child', 'role': 'Victim', 'metacognition': False, 'history': ''},
            {'id': 2, 'name': 'Pole 2', 'maturity': 2, 'ego_state': 'Controlling Parent', 'role': 'Persecutor', 'metacognition': False, 'history': ''}
        ]
        edges = [{'source': 1, 'target': 2, 'polarity': 0.5, 'light_shadow': 'shadow', 'role': 'Victim-Persecutor', 'consent': False, 'description': 'Fallback edge'}]
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
        api_response = xai_api_call(prompt)
        nodes, edges = process_response(api_response)
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('INSERT INTO prompts (prompt, nodes, edges) VALUES (?, ?, ?)',
                      (prompt, json.dumps(nodes), json.dumps(edges)))
            conn.commit()
        return jsonify({'nodes': nodes, 'edges': edges})
    except Exception as e:
        print(f"ERROR: Exception in /add: {str(e)}")
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
        print(f"ERROR: Exception in /reset: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)