import os
import logging
import json
import networkx as nx
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests

# Set template folder to project root's templates/
app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'))
CORS(app)
logging.basicConfig(level=logging.DEBUG)

# Log paths at startup
logging.debug(f"Current working directory: {os.getcwd()}")
template_path = os.path.join(app.root_path, '..', 'templates', 'index.html')
logging.debug(f"Looking for template at: {template_path}")
logging.debug(f"File exists: {os.path.exists(template_path)}")

# Env setup
API_KEY = os.getenv('API_KEY')
if not API_KEY:
    logging.warning("API_KEY not set—using mock Grok response")

# Global graph
G = nx.Graph()
history = []

def call_grok_api(prompt):
    if not API_KEY:
        return {
            'entities': [{'id': 'victim', 'label': 'Victim', 'maturity': 1, 'polarity': 'shadow'},
                         {'id': 'rescuer', 'label': 'Rescuer', 'maturity': 3, 'polarity': 'light'}],
            'relations': [{'from': 'victim', 'to': 'rescuer', 'type': 'attraction', 'tension': 0.5}]
        }
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }
    data = {
        'model': 'grok-beta',
        'messages': [{'role': 'system', 'content': 'Parse into polarity-maturity graph: entities (label, maturity 1-5, polarity light/shadow), relations (from/to, type attraction/repulsion, tension 0-1). Output JSON only.'},
                     {'role': 'user', 'content': prompt}],
        'max_tokens': 500
    }
    try:
        response = requests.post('https://api.x.ai/v1/chat/completions', headers=headers, json=data)
        response.raise_for_status()
        parsed = response.json()['choices'][0]['message']['content']
        return json.loads(parsed)
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
        logging.debug(f"Iteration {i+1}: {step}")
    return history[-iterations:]

@app.route('/')
def index():
    logging.debug("Attempting to load template: index.html")
    try:
        if not os.path.exists(template_path):
            logging.error(f"index.html not found at: {template_path}")
            return f"Error: index.html not found at {template_path}.", 500
        return render_template('index.html')
    except Exception as e:
        logging.error(f"Template error: {e}")
        return f"Error: {e}. Ensure {template_path} exists.", 500

@app.route('/generate_graph', methods=['POST'])
def generate_graph():
    try:
        prompt = request.json.get('prompt')
        if not prompt:
            return jsonify({'error': 'No prompt provided'}), 400
        parsed = call_grok_api(prompt)
        if not parsed:
            return jsonify({'error': 'Failed to parse prompt'}), 500
        entities = parsed.get('entities', [])
        relations = parsed.get('relations', [])
        iterations = run_tango_simulation(entities, relations)
        nodes = [{'id': e['id'], 'label': e['label'], 'maturity': e['maturity'], 'polarity': e['polarity']} 
                 for e in entities]
        edges = [{'from': r['from'], 'to': r['to'], 'tension': r['tension']} for r in relations]
        return jsonify({
            'nodes': nodes,
            'edges': edges,
            'iterations': iterations
        })
    except Exception as e:
        logging.error(f"Graph gen error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)