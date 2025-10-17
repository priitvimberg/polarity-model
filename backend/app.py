import logging
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

@app.route('/')
def index():
    logging.debug("Attempting to load template: index.html")
    try:
        return render_template('index.html')
    except Exception as e:
        logging.error(f"Template error: {e}")
        return "Error: Template not found. Check if templates/index.html exists.", 500

@app.route('/generate_graph', methods=['POST'])
def generate_graph():
    try:
        prompt = request.json.get('prompt')
        if not prompt:
            return jsonify({'error': 'No prompt provided'}), 400
        
        # Placeholder: Replace with your Grok API parsing, NetworkX graph gen, tango sim
        # For now, mock data to test UI
        nodes = [
            {'id': 1, 'label': 'Victim', 'size': 20, 'color': '#ff0000'},
            {'id': 2, 'label': 'Rescuer', 'size': 30, 'color': '#00ff00'}
        ]
        edges = [
            {'from': 1, 'to': 2, 'color': '#0000ff', 'label': 'Polarity'}
        ]
        
        return jsonify({'nodes': nodes, 'edges': edges})
    except Exception as e:
        logging.error(f"Graph generation error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')