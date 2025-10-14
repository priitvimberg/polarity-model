import sqlite3
conn = sqlite3.connect('model.db')
c = conn.cursor()
c.execute("INSERT OR IGNORE INTO nodes (name, maturity, ego_state, role, metacognition, history) VALUES (?, ?, ?, ?, ?, ?)",
          ("Test", 3, "Adult", "Creator", True, ""))
c.execute("SELECT id FROM nodes WHERE name=?", ("Test",))
result = c.fetchone()
print(f"Result: {result}")
conn.commit()
conn.close()
