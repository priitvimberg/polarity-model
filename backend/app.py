import os
import logging
import json
import networkx as nx
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
from dotenv import load_dotenv

# Load .env file
load_dotenv()

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'))
CORS(app)
logging.basicConfig(level=logging.DEBUG)

template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'index.html')
logging.debug(f"Looking for template at: {template_path}")
logging.debug(f"File exists: {os.path.exists(template_path)}")

API_KEY = os.getenv('API_KEY')
USE_MOCK_LOCAL = os.getenv('USE_MOCK_LOCAL', 'False').lower() == 'true'
if API_KEY:
    logging.debug(f"API_KEY loaded: {API_KEY[:4]}...{API_KEY[-4:]}")
else:
    logging.warning("API_KEY not set")
if USE_MOCK_LOCAL:
    logging.warning("USE_MOCK_LOCAL enabled—using mock Grok response")

G = nx.Graph()
history = []

def call_grok_api(prompt):
    if not API_KEY or USE_MOCK_LOCAL:
        logging.info("Using mock data")
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
        logging.debug(f"Raw Grok response: {parsed_text[:200]}...")
        
        parsed_text = parsed_text.strip()
        if parsed_text.startswith('```json'):
            parsed_text = parsed_text[7:].strip()
        if parsed_text.endswith('```'):
            parsed_text = parsed_text[:-3].strip()
        
        parsed_data = json.loads(parsed_text)
        for entity in parsed_data.get('entities', []):
            if 'id' not in entity:
                entity['id'] = entity['label']
        logging.debug(f"Processed entities: {parsed_data.get('entities', [])}")
        return parsed_data
    except requests.exceptions.HTTPError as e:
        logging.error(f"Grok HTTP error: {e} (Status: {e.response.status_code})")
    except json.JSONDecodeError as e:
        logging.error(f"JSON parse error: {e}. Raw response: {parsed_text[:200]}...")
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
        e['maturity'] = maturity if e['polarity'] == 'light' else max(1, maturity - 1)
        G.add_node(e['id'], **e)
    for r in relations:
        r['tension'] = min(1.0, r.get('tension', 0.5) + fear * 0.3 + extremity * 0.2)
        G.add_edge(r['from'], r['to'], **r)
    history = []
    for i in range(iterations):
        step = {'iteration': i+1, 'changes': [], 'extremity': extremity}
        for u, v, data in list(G.edges(data=True)):
            tension = data.get('tension', 0.5)
            state_score = G.nodes[u]['maturity'] - (fear * extremity * 2)
            if state_score < 0:
                old_polarity = G.nodes[u]['polarity']
                G.nodes[u]['polarity'] = 'light' if old_polarity == 'shadow' else 'shadow'
                step['changes'].append(f"Flipped {u} from {old_polarity} to {G.nodes[u]['polarity']} (Score: {state_score:.2f})")
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
        polarity_light = next((e['polarity'] for e in entities if e['label'] == light), 'light')
        polarity_shadow = next((e['polarity'] for e in entities if e['label'] == shadow), 'shadow')
        tension = relations[0].get('tension', 0.5) if relations else 0.5
        
        state = f"Added {light} (light, maturity {maturity_light}) vs {shadow} (shadow, maturity {maturity_shadow})"
        return jsonify({
            'maturity_light': maturity_light,
            'maturity_shadow': maturity_shadow,
            'polarity_light': polarity_light,
            'polarity_shadow': polarity_shadow,
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
        polarity_light = next((e['polarity'] for e in entities if e['label'] == light), 'light')
        polarity_shadow = next((e['polarity'] for e in entities if e['label'] == shadow), 'shadow')
        tension = relations[0].get('tension', 0.5 + fear * 0.3 + extremity * 0.2) if relations else 0.5
        
        state = f"Light ({light}): Maturity {maturity_light}, Fear {fear:.1f}, Extremity {extremity:.1f}, Polarity {polarity_light}. "
        state += f"Shadow ({shadow}): Maturity {maturity_shadow}, Polarity {polarity_shadow}. Tension: {tension:.2f}"
        if fear > 0.7 and extremity > 0.7:
            state += " (High fear and extremity triggered flip)"
        elif maturity > 4:
            state += " (High maturity stabilizes polarity)"
        
        return jsonify({
            'maturity_light': maturity_light,
            'maturity_shadow': maturity_shadow,
            'polarity_light': polarity_light,
            'polarity_shadow': polarity_shadow,
            'tension': tension,
            'iterations': iterations,
            'fear': fear,
            'extremity': extremity,
            'state': state
        })
    except Exception as e:
        logging.error(f"Update polarity error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)