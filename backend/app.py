from flask import Flask, request, jsonify
import sqlite3
import networkx as nx
import json
import requests

app = Flask(__name__)

# Database: Add role, metacognition, history to nodes; role, consent to edges
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

# xAI Grok API (replace with your key from https://x.ai/api)
GROK_API_URL = "https://api.x.ai/v1/chat/completions"
API_KEY = "your_api_key_here"

def interpret_input_with_grok(user_prompt):
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
    response = requests.post(GROK_API_URL, headers=headers, json=data)
    if response.status_code == 200:
        return json.loads(response.json()['choices'][0]['message']['content'])
    return {"error": "API call failed"}

# Interaction logic: Tension Triangle, metacognition, tango steps
def apply_interactions(graph, iterations=5, mode='tango'):
    ego_states = {'Free Child': 1, 'Adapted Child': 2, 'Adult': 3, 'Nurturing Parent': 4, 'Controlling Parent': 5}
    roles = {'Victim': -1, 'Rescuer': 0, 'Persecutor': -1, 'Creator': 1, 'Coach': 1, 'Challenger': 1}
    for _ in range(iterations):
        for u, v, data in list(graph.edges(data=True)):
            polarity = data['polarity']
            light_shadow = data.get('light_shadow', 'light')
            edge_role = data.get('role', '')
            consent = data.get('consent', False)

            # Polarity flip: Shadow or extreme polarity triggers
            if abs(polarity) > 0.7 or light_shadow == 'shadow':
                data['polarity'] = -polarity
                data['light_shadow'] = 'shadow' if light_shadow == 'light' else 'light'
                data['description'] += f" (flipped to {data['light_shadow']}—tango spin!)"

            # Node updates: Maturity, roles, metacognition
            node_u, node_v = graph.nodes[u], graph.nodes[v]
            mat_u, mat_v = node_u.get('maturity', 3), node_v.get('maturity', 3)
            state_u, state_v = node_u.get('ego_state', 'Adult'), node_v.get('ego_state', 'Adult')
            role_u, role_v = node_u.get('role', ''), node_v.get('role', '')
            meta_u, meta_v = node_u.get('metacognition', False), node_v.get('metacognition', False)

            # Tension Triangle logic
            avg_mat = (mat_u + mat_v) / 2
            if polarity < 0 and light_shadow == 'shadow' and edge_role in ['Victim-Rescuer', 'Victim-Persecutor']:
                # Damage propagates unless dampened
                reduction = 0.3 if (meta_u or meta_v or consent) else 1  # Metacognition/consent dampens 70%
                new_mat_u = max(1, mat_u - abs(polarity) * reduction)
                new_mat_v = max(1, mat_v - abs(polarity) * reduction)
                if avg_mat < 3:
                    node_u['role'] = 'Victim' if roles.get(role_u, 0) <= 0 else role_u
                    node_v['role'] = 'Victim' if roles.get(role_v, 0) <= 0 else role_v
                else:
                    # Flip to Empowerment Dynamic
                    flip_map = {'Victim': 'Creator', 'Rescuer': 'Coach', 'Persecutor': 'Challenger'}
                    node_u['role'] = flip_map.get(role_u, role_u)
                    node_v['role'] = flip_map.get(role_v, role_v)
                    data['role'] = f"{node_u['role']}-{node_v['role']}"
                node_u['maturity'], node_v['maturity'] = new_mat_u, new_mat_v
                node_u['history'] = (node_u.get('history', '') + f"; {state_u}→{node_u['role']}").strip('; ')
                node_v['history'] = (node_v.get('history', '') + f"; {state_v}→{node_v['role']}").strip('; ')
            else:
                # Positive/light/consent: Boost maturity, ego-state
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

                # Fractal ripple: Propagate to neighbors, damped by high maturity
                for neighbor in graph.neighbors(u):
                    if graph.nodes[neighbor].get('maturity', 3) > 4:
                        continue
                    graph.nodes[neighbor]['maturity'] = min(5, graph.nodes[neighbor]['maturity'] + boost * 0.4)
    return graph

@app.route('/add', methods=['POST'])
def add_to_model():
    user_prompt = request.json.get('prompt')
    interpreted = interpret_input_with_grok(user_prompt)
    if 'error' in interpreted:
        return jsonify(interpreted), 500

    conn = sqlite3.connect('model.db')
    c = conn.cursor()

    # Add/update nodes
    node_ids = []
    for node_data in interpreted['nodes']:
        c.execute("INSERT OR IGNORE INTO nodes (name, maturity, ego_state, role, metacognition, history) VALUES (?, ?, ?, ?, ?, ?)",
                  (node_data['name'], node_data['maturity'], node_data['ego_state'], node_data['role'],
                   node_data['metacognition'], node_data.get('history', '')))
        c.execute("SELECT id FROM nodes WHERE name=?", (node_data['name'],))
        node_ids.append(c.fetchone()[0])

    # Add edge
    if len(node_ids) == 2:
        c.execute("INSERT INTO edges (source_id, target_id, polarity, light_shadow, role, consent, description) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (node_ids[0], node_ids[1], interpreted['polarity'], interpreted['light_shadow'], interpreted['role'],
                   interpreted['consent'], interpreted['description']))

    conn.commit()
    conn.close()

    # Build and simulate
    graph = build_graph_from_db()
    graph = apply_interactions(graph, iterations=5, mode='tango')

    return jsonify(nx.node_link_data(graph))

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

if __name__ == '__main__':
    app.run(debug=True)
