from flask import Flask, request, jsonify, send_from_directory
import sqlite3
import networkx as nx
import json
import requests
import os
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Set static folder to match repo: frontend/static
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
STATIC_DIR = os.path.join(PROJECT_ROOT, 'frontend', 'static')
app = Flask(__name__, static_folder=STATIC_DIR)
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

def interpret_input_with_grok(user_prompt):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "grok-4",
        "messages": [{"role": "system", "content": "You are an AI that interprets inputs for a polarity-maturity model. Extract: entities (nodes), relation (edge), polarity (-1 to 1), maturity (1-5). Output as JSON: {'nodes': ['A', 'B'], 'polarity': 0.5, 'maturity': 3, 'description': '...'}"},
                     {"role": "user", "content": user_prompt}]
    }
    try:
        response = requests.post(GROK_API_URL, headers=headers, json=data)
        if response.status_code == 200:
            return json.loads(response.json()['choices'][0]['message']['content'])
        return {"error": "API call failed"}
    except Exception as e:
        return {"error": str(e)}

# Interaction logic (your full apply_interactions, build_graph_from_db, etc. from previous versions - keep as is)
# ... (omit for brevity; copy your existing functions here)

@app.route('/add', methods=['POST'])
def add_to_model():
    # Your existing code
    # ...

@app.route('/')
def index():
    try:
        file_path = os.path.join(app.static_folder, 'index.html')
        logger.debug(f"Attempting to serve {file_path}")
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return jsonify({"error": f"File not found: {file_path}"}), 404
        return send_from_directory('', 'index.html')  # Serve from static_folder root
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
    app.run(debug=True)
