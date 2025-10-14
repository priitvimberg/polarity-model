from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
import networkx as nx
import json
import requests
import os
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Set static folder
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
STATIC_DIR = os.path.join(PROJECT_ROOT, 'frontend', 'static')
app = Flask(__name__, static_folder=STATIC_DIR)
CORS(app)
logger.debug(f"Project root: {PROJECT_ROOT}, Static folder: {STATIC_DIR}")

# Database setup
def init_db():
    conn = sqlite3.connect('model.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS nodes (
        id INTEGER PRIMARY KEY, name TEXT, maturity INTEGER, ego_state TEXT, 
        role TEXT, metacognition BOOLEAN, history TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS edges (
        source_id INTEGER, target_id INTEGER, polarity REAL, light_shadow TEXT, 
        role TEXT, consent BOOLEAN, description TEXT)''')
    conn.commit()
    conn.close()

init_db()

# xAI Grok API
GROK_API_URL = "https://api.x.ai/v1/chat/completions"
API_KEY = os.getenv("API_KEY")
logger.debug(f"API_KEY prefix: {API_KEY[:5] if API_KEY else 'None'}...")

def interpret_input_with_grok(user_prompt):
    if not API_KEY:
        logger.error("API_KEY environment variable not set")
        return {"error": "API_KEY not set"}
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "grok-4",
        "messages": [{
            "role": "system",
            "content": """Interpret inputs for a polarity-maturity model using Wheel of Consent, Tension Triangle (Victim-Rescuer-Persecutor or Creator-Coach-Challenger), and ego states. Extract: 
            - Nodes: name, ego_state ('Free Child', 'Adapted Child', 'Adult', etc.), maturity (1-5), role (Victim, Creator, etc.), metacognition (true/false).
            - Edge: polarity (-1 to 1), light_shadow ('light'/'shadow'), role (Victim-Rescuer, etc.), consent (true/false).
            - Suggest role flip (e.g., Victim to Creator) if applicable.
            Output JSON: {
                'nodes': [{'name': 'A', 'ego_state': 'Adult', 'maturity': 3, 'role': 'Creator', 'metacognition': true, 'history': ''}],
                'polarity': 0.5, 'light_shadow': 'light', 'role': 'Creator-Coach', 'consent': true, 'description': '...', 'role_flip': 'Victim to Creator'
            }"""
        }, {"role": "user", "content": user_prompt}]
    }
    logger.debug(f"Sending request to Grok API with prompt: {user_prompt[:50]}...")
    try:
        response = requests.post(GROK_API_URL, headers=headers, json=data)
        logger.debug(f"Grok API response status: {response.status_code}, body: {response.text[:200]}...")
        if response.status_code == 200:
            try:
                content = response.json()['choices'][0]['message']['content']
                return json.loads(content)
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"JSON decode or KeyError: {str(e)}, response: {response.text[:200]}")
                return {"error": f"JSON decode or KeyError: {str(e)}"}
        logger.error(f"API call failed: {response.status_code}, body: {response.text[:200]}")
        return {"error": f"API call failed: {response.status_code}"}
    except Exception as e:
        logger.error(f"API call error: {str(e)}")
        return {"error": f"API call error: {str(e)}"}

def apply_interactions(graph, iterations=5, mode='tango'):
    ego_states = {'Free Child': 1, 'Adapted Child': 2, 'Adult': 3, 'Nurturing Parent': 4, 'Controlling Parent': 5}
    roles = {'Victim': -1, 'Rescuer': 0, 'Persecutor': -1, 'Creator': 1, 'Coach': 1, 'Challenger': 1}
    for _ in range(iterations):
        for u, v, data in list(graph.edges(data=True)):
            polarity = data['polarity']
            light_shadow = data.get('light_shadow', 'light')
            edge_role = data.get('role', '')
            consent = data.get('consent', False)
            if abs(polarity) > 0.7 or light_shadow == 'shadow':
                data['polarity'] = -polarity
                data['light_shadow'] = 'shadow' if light_shadow == 'light' else 'light'
                data['description'] += f" (flipped to {data['light_shadow']}—tango spin!)"
            node_u, node_v = graph.nodes[u], graph.nodes[v]
            mat_u, mat_v = node_u.get('maturity', 3), node_v.get('maturity', 3)
            state_u, state_v = node_u.get('ego_state', 'Adult'), node_v.get('ego_state', 'Adult')
            role_u, role_v = node_u.get('role', ''), node_v.get('role', '')
            meta_u, meta_v = node_u.get('metacognition', False), node_v.get('metacognition', False)
            avg_mat = (mat_u + mat_v) / 2
            if polarity < 0 and light_shadow == 'shadow' and edge_role in ['Victim-Rescuer', 'Victim-Persecutor']:
                reduction = 0.3 if (meta_u or meta_v or consent) else 1
                new_mat_u = max(1, mat_u - abs(polarity) * reduction)
                new_mat_v = max(1, mat_v - abs(polarity) * reduction)
                if avg_mat < 3:
                    node_u['role'] = 'Victim' if roles.get(role_u, 0) <= 0 else role_u
                    node_v['role'] = 'Victim' if roles.get(role_v, 0) <= 0 else role_v
                else:
                    flip_map = {'Victim': 'Creator', 'Rescuer': 'Coach', 'Persecutor': 'Challenger'}
                    node_u['role'] = flip_map.get(role_u, role_u)
                    node_v['role'] = flip_map.get(role_v, role_v)
                    data['role'] = f"{node_u['role']}-{node_v['role']}"
                node_u['maturity'], node_v['maturity'] = new_mat_u, new_mat_v
                node_u['history'] = (node_u.get('history', '') + f"; {state_u}→{node_u['role']}").strip('; ')
                node_v['history'] = (node_v.get('history', '') + f"; {state_v}→{node_v['role']}").strip('; ')
            else:
                boost = polarity * (avg_mat / 5) * (1.5 if consent else 1.2)
                new_state_key = max(ego_states.keys(), key=lambda k: ego_states[k] if ego_states.get(state_u, 3) < ego_states[k] else 0)
                if boost > 0.5 or meta_u:
                    node_u['ego_state'] = new_state_key
                    node_u['history'] = (node_u.get('history', '') + f"; {state_u}→{new_state_key}").strip('; ')
                if boost > 0.5 or meta_v:
                    node_v['ego_state'] = new_state_key
                    node_v['history'] = (node_v.get('history', '') + f"; {state_v}→{new_state_key}").strip('; ')
                node_u['maturity'] = min(5, mat_u + boost)
                node_v['maturity'] = min(5, mat_v + boost)
                for neighbor in graph.neighbors(u):
                    if graph.nodes[neighbor].get('maturity', 3) > 4:
                        continue
                    graph.nodes[neighbor]['maturity'] = min(5, graph.nodes[neighbor]['maturity'] + boost * 0.4)
    return graph

def build_graph_from_db():
    graph = nx.Graph()
    conn = sqlite3.connect('model.db')
    c = conn.cursor()
    c.execute("SELECT * FROM nodes")
    for row in c.fetchall():
        graph.add_node(row[0], name=row[1], maturity=row[2], ego_state=row[3], role=row[4], metacognition=row[5], history=row[6])
    c.execute("SELECT * FROM edges")
    for row in c.fetchall():
        graph.add_edge(row[0], row[1], polarity=row[2], light_shadow=row[3], role=row[4], consent=row[5], description=row[6])
    conn.close()
    return graph

@app.route('/add', methods=['POST'])
def add_to_model():
    try:
        user_prompt = request.json.get('prompt')
        logger.debug(f"Received prompt: {user_prompt}")
        if not user_prompt:
            logger.error("No prompt provided")
            return jsonify({"error": "No prompt provided"}), 400
        interpreted = interpret_input_with_grok(user_prompt)
        logger.debug(f"Interpreted response: {interpreted}")
        if 'error' in interpreted:
            logger.error(f"Error in add_to_model: {interpreted['error']}")
            return jsonify(interpreted), 500
        conn = sqlite3.connect('model.db')
        c = conn.cursor()
        node_ids = []
        for node_data in interpreted['nodes']:
            c.execute("INSERT OR IGNORE INTO nodes (name, maturity, ego_state, role, metacognition, history) VALUES (?, ?, ?, ?, ?, ?)",
                      (node_data['name'], node_data['maturity'], node_data['ego_state'], node_data['role'],
                       node_data['metacognition'], node_data.get('history', '')))
            c.execute("SELECT id FROM nodes WHERE name=?", (node_data['name'],))
            result = c.fetchone()
            if result is None:
                logger.error(f"Failed to retrieve node ID for name: {node_data['name']}")
                return jsonify({"error": f"Failed to retrieve node ID for name: {node_data['name']}"}), 500
            node_ids.append(result[0])
        if len(node_ids) == 2:
            c.execute("INSERT INTO edges (source_id, target_id, polarity, light_shadow, role, consent, description) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (node_ids[0], node_ids[1], interpreted['polarity'], interpreted['light_shadow'], interpreted['role'],
                       interpreted['consent'], interpreted['description']))
        conn.commit()
        conn.close()
        graph = build_graph_from_db()
        graph = apply_interactions(graph, iterations=5, mode='tango')
        logger.debug(f"Graph data: {nx.node_link_data(graph)}")
        return jsonify(nx.node_link_data(graph))
    except Exception as e:
        logger.error(f"Error in add_to_model: {str(e)}")
        return jsonify({"error": f"Error in add_to_model: {str(e)}"}), 500

@app.route('/reset', methods=['POST'])
def reset_model():
    try:
        conn = sqlite3.connect('model.db')
        c = conn.cursor()
        c.execute("DELETE FROM nodes")
        c.execute("DELETE FROM edges")
        conn.commit()
        conn.close()
        logger.debug("Database reset: nodes and edges tables cleared")
        return jsonify({"message": "Model reset successfully"})
    except Exception as e:
        logger.error(f"Error resetting model: {str(e)}")
        return jsonify({"error": f"Error resetting model: {str(e)}"}), 500

@app.route('/')
def index():
    try:
        file_path = os.path.join(app.static_folder, 'index.html')
        logger.debug(f"Attempting to serve {file_path}")
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return jsonify({"error": f"File not found: {file_path}"}), 404
        logger.debug(f"File permissions: {oct(os.stat(file_path).st_mode)[-3:]}")
        with open(file_path, 'r') as f:
            content = f.read(100)
            logger.debug(f"File content preview: {content}")
        return send_file(file_path)
    except Exception as e:
        logger.error(f"Error serving index.html: {str(e)}")
        return jsonify({"error": f"Failed to serve index.html: {str(e)}"}), 500

@app.route('/debug/files')
def debug_files():
    try:
        def list_files(startpath):
            file_tree = {}
            for root, dirs, files in os.walk(startpath):
                path = root.replace(startpath, '').lstrip('/')
                file_tree[path or '.'] = files
            return file_tree
        project_files = list_files(PROJECT_ROOT)
        logger.debug(f"Project root contents: {project_files}")
        return jsonify({"project_root": PROJECT_ROOT, "files": project_files})
    except Exception as e:
        logger.error(f"Error listing project root: {str(e)}")
        return jsonify({"error": f"Error listing project root: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))