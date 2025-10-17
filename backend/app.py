import os
import logging
import json
import networkx as nx
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests  # For Grok API

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.DEBUG)

# Env setup
API_KEY = os.getenv('API_KEY')
if not API_KEY:
    logging.warning("API_KEY not set—using mock Grok response")

# Global graph (use SQLite in prod; for now, in-memory)
G = nx.Graph()
history = []  # For tango iterations

def call_grok_api(prompt):
    """Parse prompt with Grok: e.g., extract entities, polarities, maturities."""
    if not API_KEY:
        # Mock for testing (replace with real call)
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
        'model': 'grok-beta',  # Or latest
        'messages': [{'role': 'system', 'content': 'Parse this into polarity-maturity graph: entities (label, maturity 1-5, polarity light/shadow), relations (from/to, type attraction/repulsion, tension 0-1). Output JSON only.'},
                     {'role': 'user', 'content': prompt}],
        'max_tokens': 500
    }
    try:
        response = requests.post('https://api.x.ai/v1/chat/completions', headers=headers, json=data)
        response.raise_for_status()
        parsed = response.json()['choices'][0]['message']['content']
        return json.loads(parsed)  # Assume clean JSON output
    except Exception as e:
        logging.error(f"Grok API error: {e}")
        return None  # Fallback to mock

def run_tango_simulation(entities, relations, iterations=5):
    """5-step consent-driven sim: Update polarities based on tension/maturity."""
    global G, history
    G.clear()
    # Add nodes
    for e in entities:
        G.add_node(e['id'], **e)
    # Add edges
    for r in relations:
        G.add_edge(r['from'], r['to'], **r)
    
    for i in range(iterations):
        step = {'iteration': i+1, 'changes': []}
        for u, v, data in G.edges(data=True):
            tension = data.get('tension', 0.5)
            if tension > 0.5:  # High tension → flip polarity if consent (mock random for now)
                flip_prob = G.nodes[u].get('maturity', 1) / 5.0  # Higher maturity = more flips
                if flip_prob > 0.3:  # Simulate consent
                    old_p = G.nodes[u]['polarity']
                    G.nodes[u]['polarity'] = 'light' if old_p == 'shadow' else 'shadow'
                    step['changes'].append(f"Flipped {u} from {old_p}")
        history.append(step)
        logging.debug(f"Iteration {i+1}: {step}")
    return history[-iterations:]  # Last 5 steps

@app.route('/')
def index():
    logging.debug("Loading index.html")
    try:
        return render_template('index.html')
    except Exception as e:
        logging.error(f"Template error: {e}")
        return f"Error: {e}. Ensure templates/index.html exists.", 500

@app.route('/generate_graph', methods=['POST'])
def generate_graph():
    try:
        prompt = request.json.get('prompt')
        if not prompt:
            return jsonify({'error': 'No prompt provided'}), 400
        
        # Step 1: Parse with Grok
        parsed = call_grok_api(prompt)
        if not parsed:
            return jsonify({'error': 'Failed to parse prompt'}), 500
        
        entities = parsed.get('entities', [])
        relations = parsed.get('relations', [])
        
        # Step 2: Build graph & sim
        iterations = run_tango_simulation(entities, relations)
        
        # Step 3: Format for Vis.js
        nodes = [{'id': e['id'], 'label': e['label'], 'maturity': e['maturity'], 'polarity': e['polarity']} 
                 for e in entities]
        edges = [{'from': r['from'], 'to': r['to'], 'tension': r['tension']} for r in relations]
        
        return jsonify({
            'nodes': nodes,
            'edges': edges,
            'iterations': iterations  # For tooltips/animation
        })
    except Exception as e:
        logging.error(f"Graph gen error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)