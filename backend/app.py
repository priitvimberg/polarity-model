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

template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'index.html')
logging.debug(f"Looking for template at: {template_path}")
logging.debug(f"File exists: {os.path.exists(template_path)}")

API_KEY = os.getenv('API_KEY')
if not API_KEY:
    logging.warning("API_KEY not set—using mock Grok response")

G = nx.Graph()
history = []

def call_grok_api(prompt):
    if not API_KEY:
        logging.info("Using mock data (no API_KEY)")
        light_label, shadow_label = prompt.split(' vs ') if ' vs ' in prompt else ('light', 'shadow')
        return {
            'entities': [
                {'id': light_label, 'label': light_label, 'maturity': 3, 'polarity': 'light'},
                {'id': shadow_label, 'label': shadow_label, 'maturity': 2, 'polarity': 'shadow'}
            ],
            'relations': [{'from': light_label, 'to': shadow_label, 'type': 'attraction', 'tension': 0.5}]
        }
    
    headers = {'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'}
    data = {
        'model': 'grok-2',  # Updated to current model
        'messages': [
            {'role': 'system', 'content': 'Parse polarity pair into graph: entities (label, maturity 1-5, polarity light/shadow), relations (from/to, type attraction/repulsion, tension 0-1). Output JSON only.'},
            {'role': 'user', 'content': prompt}
        ],
        'max_tokens': 500
    }
    try:
        logging.debug(f"Calling Grok API with prompt: {prompt[:100]}...")
        response = requests.post('https://api.x.ai/v1/chat/completions', headers=headers, json=data)  # Fixed URL
        response.raise_for_status()
        parsed_text = response.json()['choices'][0]['message']['content']
        logging.debug(f"Grok response: {parsed_text[:100]}...")
        return json.loads(parsed_text)
    except requests.exceptions.HTTPError as e:
        logging.error(f"Grok HTTP error: {e} (Status: {e.response.status_code})")
        if e.response.status_code == 404:
            logging.error("404: Check API URL/model. Falling back to mock.")
    except json.JSONDecodeError as e:
        logging.error(f"JSON parse error in Grok response: {e}")
    except Exception as e:
        logging.error(f"Grok API error: {e}")
    
    # Always fallback to mock on any error
    logging.info("Falling back to mock data due to API error")
    light_label, shadow_label = prompt.split(' vs ') if ' vs ' in prompt else ('light', 'shadow')
    return {
        'entities': [
            {'id': light_label, 'label': light_label, 'maturity': 3, 'polarity': 'light'},
            {'id': shadow_label, 'label': shadow_label, 'maturity': 2, 'polarity': 'shadow'}
        ],
        'relations': [{'from': light_label, 'to': shadow_label, 'type': 'attraction', 'tension': 0.5}]
    }

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
        logging.debug(f"Iteration {i+1}: {step}")
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
    try:
        prompt = request.json.get('prompt')
        if not prompt:
            return jsonify({'error': 'No prompt provided'}), 400
        parsed = call_grok_api(prompt)
        entities = parsed.get('entities', [])
        relations = parsed.get('relations', [])
        iterations = run_tango_simulation(entities, relations)
        nodes = [{'id': e['id'], 'label': e['label'], 'maturity': e['maturity'], 'polarity': e['polarity']} for e in entities]
        edges = [{'from': r['from'], 'to': r['to'], 'tension': r['tension']} for r in relations]
        return jsonify({'nodes': nodes, 'edges': edges, 'iterations': iterations})
    except Exception as e:
        logging.error(f"Graph gen error: {e}")
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
        logging.error(f"Add polarity error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)