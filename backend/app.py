from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3
import os
import requests
import json

app = Flask(__name__, template_folder='templates')
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

# xAI API call with HI-AI system prompt
def xai_api_call(prompt_data):
    api_key = os.environ.get('API_KEY')
    if not api_key:
        raise ValueError("API_KEY not set")
    headers = {'Authorization': f'Bearer {api_key}'}
    prompt = (
        f"Polarity: {prompt_data['prompt']}, "
        f"Pole 1: {prompt_data['pole1Name']} (maturity: {prompt_data['pole1Maturity']}), "
        f"Pole 2: {prompt_data['pole2Name']} (maturity: {prompt_data['pole2Maturity']}), "
        f"Polarity weight: {prompt_data['polarityWeight']}, "
        f"Consent: {prompt_data['consent']}, "
        f"Metacognition: {prompt_data['metacognition']}"
    )
    payload = {
        'model': 'grok-4-0709',
        'messages': [
            {'role': 'system', 'content': 'You are an assistant generating structured JSON for polarity and maturity model graphs based on HI-AI survival dance concepts (fractal intelligence, Tension Triangle, role flips, ego states, metacognition). Return ONLY JSON with "nodes" (array of {id, name, maturity: 1-5, ego_state: Free Child/Adapted Child/Adult/Controlling Parent/Nurturing Parent, role: Victim/Persecutor/Rescuer/Creator/Challenger/Coach, metacognition: 0/1, history}) and "edges" (array of {source, target, polarity: -1.0 to 1.0, light_shadow: light/shadow, role, consent: 0/1, description, role_flip}). No other text.'},
            {'role': 'user', 'content': prompt}
        ]
    }
    print(f"DEBUG: Sending request to Grok API with payload: {json.dumps(payload)[:100]}...")
    response = requests.post('https://api.x.ai/v1/chat/completions', json=payload, headers=headers, timeout=60)
    print(f"DEBUG: Grok API response status: {response.status_code}, body: {response.text[:200]}...")
    response.raise_for_status()
    return response.json()

# Process API response with fallback
def process_response(api_response, prompt_data):
    try:
        content = api_response['choices'][0]['message']['content']
        print(f"DEBUG: Interpreted response: {content[:200]}...")
        parsed = json.loads(content)
        nodes = parsed.get('nodes', [])
        edges = parsed.get('edges', [])
        if not nodes or not edges:
            raise ValueError("Empty nodes or edges in parsed response")
        # Apply user inputs
        if len(nodes) >= 2:
            nodes[0]['name'] = prompt_data.get('pole1Name', 'Pole 1')
            nodes[0]['maturity'] = max(1, min(5, prompt_data.get('pole1Maturity', 3)))
            nodes[1]['name'] = prompt_data.get('pole2Name', 'Pole 2')
            nodes[1]['maturity'] = max(1, min(5, prompt_data.get('pole2Maturity', 3)))
            for edge in edges:
                edge['polarity'] = max(-1.0, min(1.0, prompt_data.get('polarityWeight', 0.5)))
                edge['consent'] = prompt_data.get('consent', 0)
                edge['metacognition'] = prompt_data.get('metacognition', 0)
        print(f"DEBUG: Graph data: {json.dumps({'nodes': nodes, 'edges': edges})[:200]}...")
        return nodes, edges
    except Exception as e:
        print(f"DEBUG: Error processing response, using fallback: {str(e)}")
        nodes = [
            {'id': 1, 'name': prompt_data.get('pole1Name', 'Pole 1'), 'maturity': prompt_data.get('pole1Maturity', 1), 'ego_state': 'Adapted Child', 'role': 'Victim', 'metacognition': prompt_data.get('metacognition', 0), 'history': 'Fractal survival loop'},
            {'id': 2, 'name': prompt_data.get('pole2Name', 'Pole 2'), 'maturity': prompt_data.get('pole2Maturity', 5), 'ego_state': 'Adult', 'role': 'Creator', 'metacognition': prompt_data.get('metacognition', 0), 'history': 'Maturity flip via feedback'}
        ]
        edges = [{
            'source': 1, 'target': 2, 'polarity': prompt_data.get('polarityWeight', -0.5), 'light_shadow': 'shadow' if prompt_data.get('polarityWeight', 0) < 0 else 'light',
            'role': 'Victim-Persecutor', 'consent': prompt_data.get('consent', 0), 'description': 'Tension flip to light', 'role_flip': 'Victim to Creator'
        }]
        return nodes, edges

@app.route('/', methods=['GET'])
def home():
    return render_template('index.html', nodes=[], edges=[])

@app.route('/add', methods=['POST'])
def add_prompt():
    data = request.get_json()
    prompt = data.get('prompt', '')
    if not prompt.strip():
        return jsonify({'error': 'Prompt is required'}), 400
    try:
        api_response = xai_api_call(data)
        nodes, edges = process_response(api_response, data)
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