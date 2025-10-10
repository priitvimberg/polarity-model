# Polarity-Maturity Model

A web-based interactive tool for exploring polarity (light/shadow attraction/repulsion) and maturity (ego-state growth arcs) in relationships—personal, organizational, or HI-AI. Inspired by philosophical dialogues between Priit Vimberg and Grok (xAI), this app models fractal survival dynamics using graph visualizations: nodes as entities (e.g., "AI Startup" with Victim role, low maturity), edges as polar relations (flipping via Tension Triangle logic), and simulations for tango-like interactions (consent-driven feedback loops).

## Background
This prototype stems from a three-part HI-AI series:
- [Part 1: HI-AI Survival Dance](https://tõekeskus.ee/?p=1214&lang=en) – Fractal intelligence and duality.
- [Part 2: Relational Dynamics](https://tõekeskus.ee/?p=1272&lang=en) – Wheel of Consent, Drama Triangle, ego states.
- [Part 3: Operational Playbook](https://tõekeskus.ee/?p=1291&lang=en) – Metacognition, Tension Triangle flips, fractal feedback.

The app lets users submit natural-language prompts (e.g., "Add shadow polarity between AI Ethics Board and Developer Team at low maturity"), parses them via Grok API, updates the model, and visualizes outcomes (e.g., role flips from Victim-Persecutor to Creator-Challenger).

**Beta Status**: Experimental—expect evolving features like animated tango steps or subgraph zooms. Not for production use yet.

## Quick Start
1. **Local Setup**:
   - Clone: `git clone https://github.com/priitvimberg/polarity-model.git`
   - Install deps: `pip install -r requirements.txt`
   - Run: `python backend/app.py`
   - Open: http://localhost:5000

2. **Usage**:
   - Enter a prompt in the form (e.g., "Map Victim-Rescuer dynamic in an org team, Adapted Child maturity, no consent").
   - Submit: Grok interprets → Model updates (5 tango iterations) → Graph renders (nodes sized by maturity, edges colored by polarity/light-shadow).
   - Interact: Zoom/drag the vis; hover for history/tooltips.

3. **Live Demo**: [Deployed on Render](https://your-render-url.onrender.com) (once set up—see below).

## Tech Stack
- **Backend**: Flask (Python), NetworkX (graphs), SQLite (DB), xAI Grok API (prompt parsing).
- **Frontend**: HTML/JS with Vis.js (interactive graphs).
- **Deployment**: Render (auto-deploys on push to main).

## Deployment to Render
1. Sign up at [render.com](https://render.com) (GitHub auth).
2. New > Web Service > Connect this repo.
3. Env: Python; Build: `pip install -r requirements.txt`; Start: `gunicorn backend.app:app`.
4. Add Env Var: `API_KEY=your_xai_key` (from https://x.ai/api).
5. Enable Auto-Deploy. URL: e.g., `https://polarity-model.onrender.com`.

## Contributing
Personal project for now—no PRs/issues. Ideas? Ping @PriitVimberg on X.

## License
MIT License – see [LICENSE](LICENSE) for details.

© 2025 Priit Vimberg. Built with help from Grok (xAI).
