import os
import logging
import json
import networkx as nx
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'))
CORS(app)
logging.basicConfig(level=logging.DEBUG)

template_path = os.path.join(app.root_path, '..', 'templates', 'index.html')
logging.debug(f"Looking for template at: {template_path}")
logging.debug(f"File exists: {os.path.exists(template_path)}")

API_KEY = os.getenv('API_KEY')
if not API_KEY:
    logging.warning("API_KEY not set—using mock Grok response")

G = nx.Graph()
history = []

def call_grok_api(prompt):
    if not API_KEY:
        return {'entities': [{'id': 'light', 'label': prompt.split(' vs ')[0], 'maturity': 3, 'polarity': 'light'},
                             {'id': 'shadow', 'label': prompt.split(' vs ')[1], 'maturity': 2, 'polarity': 'shadow'}],
                'relations': [{'from': 'light', 'to': 'shadow', 'type': 'attraction', 'tension': 0.5}]}
    
    headers = {'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'}
    data = {
        'model': 'grok-beta',
        'messages': [{'role': 'system', 'content': 'Parse polarity pair into graph: entities (label, maturity 1-5, polarity light/shadow), relations (from/to, type attraction/repulsion, tension 0-1). Output JSON only.'},
                     {'role': 'user', 'content': prompt}],
        'max_tokens': 500
    }
    try:
        response = requests.post('https://api.x.ai/v1/chat/completions', headers=headers, json=data)
        response.raise_for_status()
        parsed = json.loads(response.json()['choices'][0]['message']['content'])
        return parsed
    except Exception as e:
        logging.error(f"Grok API error: {e}")
        return None

def run_tango_simulation(entities, relations, iterations=5):
    global G, history
    G.clear()
    for e in entities:
        G.add_node(e['id'], **e)
    for r in relations:
        G.add_edge(r['from'], r['to'], **r)
    history = []
    for i in range(iterations):
        step = {'iteration': i+1, 'changes': []}
        for u, v, data in G.edges(data=True):
            tension = data.get('tension', 0.5)
            if tension > 0.5:
                flip_prob = G.nodes[u].get('maturity', 1) / 5.0
                if flip_prob > 0.3:
                    old_p = G.nodes[u]['polarity']
                    G.nodes[u]['polarity'] = 'light' if old_p == 'shadow' else 'shadow'
                    step['changes'].append(f"Flipped {u} from {old_p}")
        history.append(step)
    return history

@app.route('/')
def index():
    try:
        if not os.path.exists(template_path):
            return f"Error: index.html not found at {template_path}.", 500
        return render_template('index.html')
    except Exception as e:
        return f"Error: {e}.", 500

@app.route('/generate_graph', methods=['POST'])
def generate_graph():
    # Existing full prompt route (keep for compatibility)
    try:
        prompt = request.json.get('prompt')
        parsed = call_grok_api(prompt)
        if not parsed:
            return jsonify({'error': 'Failed to parse'}), 500
        entities = parsed.get('entities', [])
        relations = parsed.get('relations', [])
        iterations = run_tango_simulation(entities, relations)
        nodes = [{'id': e['id'], 'label': e['label'], 'maturity': e['maturity'], 'polarity': e['polarity']} for e in entities]
        edges = [{'from': r['from'], 'to': r['to'], 'tension': r['tension']} for r in relations]
        return jsonify({'nodes': nodes, 'edges': edges, 'iterations': iterations})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/add_polarity', methods=['POST'])
def add_polarity():
    try:
        data = request.json
        light = data.get('light')
        shadow = data.get('shadow')
        if not light or not shadow:
            return jsonify({'error': 'Missing light or shadow'}), 400
        
        prompt = f"{light} vs {shadow} polarity in relationship, assign maturity and tension"
        parsed = call_grok_api(prompt)
        if not parsed:
            return jsonify({'error': 'Failed to parse pair'}), 500
        
        entities = parsed.get('entities', [])
        relations = parsed.get('relations', [])
        iterations = run_tango_simulation(entities, relations)
        
        # Extract for response
        maturity_light = next((e['maturity'] for e in entities if e['polarity'] == 'light'), 3)
        maturity_shadow = next((e['maturity'] for e in entities if e['polarity'] == 'shadow'), 2)
        tension = relations[0].get('tension', 0.5) if relations else 0.5
        
        return jsonify({
            'maturity_light': maturity_light,
            'maturity_shadow': maturity_shadow,
            'tension': tension,
            'iterations': iterations
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)