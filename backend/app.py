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
        'model': 'grok-2',
        'messages': [
            {'role': 'system', 'content': 'Parse polarity pair into graph: entities (label, maturity 1-5, polarity light/shadow), relations (from/to, type attraction/repulsion, tension 0-1). Output JSON only.'},
            {'role': 'user', 'content': prompt}
        ],
        'max_tokens': 500
    }
    try:
        logging.debug(f"Calling Grok API with prompt: {prompt[:100]}...")
        response = requests.post('https://api.x.ai/v1/chat/completions', headers=headers, json=data)
        response.raise_for_status()
        parsed_text = response.json()['choices'][0]['message']['content']
        logging.debug(f"Grok response: {parsed_text[:100]}...")
        return json.loads(parsed_text)
    except Exception as e:
        logging.error(f"Grok API error: {e}")
        logging.info("Falling back to mock data")
        light_label, shadow_label = prompt.split(' vs ') if ' vs ' in prompt else ('light', 'shadow')
        return {
            'entities': [
                {'id': light_label, 'label': light_label, 'maturity': 3, 'polarity': 'light'},
                {'id': shadow_label, 'label': shadow_label, 'maturity': 2, 'polarity': 'shadow'}
            ],
            'relations': [{'from': light_label, 'to': shadow_label, 'type': 'attraction', 'tension': 0.5}]
        }

def run_tango_simulation(entities, relations, iterations=5, maturity=3, fear=0.5, extremity=0.5):
    global G, history
    G.clear()
    for e in entities:
        # Adjust maturity based on input (override Grok if provided)
        e['maturity'] = maturity if e['polarity'] == 'light' else max(1, maturity - 1)  # Shadow slightly lower
        G.add_node(e['id'], **e)
    for r in relations:
        # Adjust tension based on fear/extremity
        r['tension'] = min(1.0, r.get('tension', 0.5) + fear * 0.3 + extremity * 0.2)
        G.add_edge(r['from'], r['to'], **r)
    history = []
    for i in range(iterations):
        step = {'iteration': i+1, 'changes': []}
        for u, v, data in G.edges(data=True):
            tension = data.get('tension', 0.5)
            # No flips yet (Step 3); just log state
            step['changes'].append(f"Node {u}: Maturity {G.nodes[u]['maturity']}, Tension {tension:.2f}")
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
        
        maturity_light = next((e['maturity'] for e in entities if e['polarity'] == 'light'), 3)
        maturity_shadow = next((e['maturity'] for e in entities if e['polarity'] == 'shadow'), 2)
        tension = relations[0].get('tension', 0.5) if relations else 0.5
        
        state = f"Added {light} (light, maturity {maturity_light}) vs {shadow} (shadow, maturity {maturity_shadow})"
        return jsonify({
            'maturity_light': maturity_light,
            'maturity_shadow': maturity_shadow,
            'tension': tension,
            'iterations': iterations,
            'state': state
        })
    except Exception as e:
        logging.error(f"Add polarity error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/update_polarity', methods=['POST'])
def update_polarity():
    try:
        data = request.json
        light = data.get('light')
        shadow = data.get('shadow')
        maturity = float(data.get('maturity', 3))
        fear = float(data.get('fear', 0.5))
        extremity = float(data.get('extremity', 0.5))
        if not light or not shadow:
            return jsonify({'error': 'Missing light or shadow'}), 400
        
        prompt = f"{light} vs {shadow} polarity, maturity {maturity}, fear {fear}, extremity {extremity}"
        parsed = call_grok_api(prompt)
        entities = parsed.get('entities', [])
        relations = parsed.get('relations', [])
        iterations = run_tango_simulation(entities, relations, maturity=maturity, fear=fear, extremity=extremity)
        
        maturity_light = next((e['maturity'] for e in entities if e['polarity'] == 'light'), maturity)
        maturity_shadow = next((e['maturity'] for e in entities if e['polarity'] == 'shadow'), max(1, maturity - 1))
        tension = relations[0].get('tension', 0.5 + fear * 0.3 + extremity * 0.2) if relations else 0.5
        
        state = f"Light ({light}): Maturity {maturity_light}, Fear {fear:.1f}, Extremity {extremity:.1f}. "
        state += f"Shadow ({shadow}): Maturity {maturity_shadow}. Tension: {tension:.2f}"
        if fear > 0.7:
            state += " (High fear risks negative influence)"
        elif maturity > 4:
            state += " (High maturity stabilizes polarity)"
        
        return jsonify({
            'maturity_light': maturity_light,
            'maturity_shadow': maturity_shadow,
            'tension': tension,
            'iterations': iterations,
            'state': state
        })
    except Exception as e:
        logging.error(f"Update polarity error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)