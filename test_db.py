iort sqlite3

conn = sqlite3.connect('model.db')
c = conn.cursor()
# Create tables
c.execute('''CREATE TABLE IF NOT EXISTS nodes (
    id INTEGER PRIMARY KEY, name TEXT, maturity INTEGER, ego_state TEXT, 
    role TEXT, metacognition BOOLEAN, history TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS edges (
    source_id INTEGER, target_id INTEGER, polarity REAL, light_shadow TEXT, 
    role TEXT, consent BOOLEAN, description TEXT)''')
c.execute("INSERT OR IGNORE INTO nodes (name, maturity, ego_state, role, metacognition, history) VALUES (?, ?, ?, ?, ?, ?)",
          ("Test", 3, "Adult", "Creator", True, ""))
c.execute("SELECT id FROM nodes WHERE name=?", ("Test",))
result = c.fetchone()
print(f"Result: {result}")
conn.commit()
conn.close(import sqlite3
conn = sqlite3.connect('model.db')
c = conn.cursor()
# Create tables
c.execute('''CREATE TABLE IF NOT EXISTS nodes (
    id INTEGER PRIMARY KEY, name TEXT, maturity INTEGER, ego_state TEXT, 
    role TEXT, metacognition BOOLEAN, history TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS edges (
    source_id INTEGER, target_id INTEGER, polarity REAL, light_shadow TEXT, 
    role TEXT, consent BOOLEAN, description TEXT)''')
c.execute("INSERT OR IGNORE INTO nodes (name, maturity, ego_state, role, metacognition, history) VALUES (?, ?, ?, ?, ?, ?)",
          ("Test", 3, "Adult", "Creator", True, ""))
c.execute("SELECT id FROM nodes WHERE name=?", ("Test",))
result = c.fetchone()
print(f"Result: {result}")
conn.commit()
conn.close()import sqlite3
conn = sqlite3.connect('model.db')
c = conn.cursor()
# Create tables
c.execute('''CREATE TABLE IF NOT EXISTS nodes (
    id INTEGER PRIMARY KEY, name TEXT, maturity INTEGER, ego_state TEXT, 
    role TEXT, metacognition BOOLEAN, history TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS edges (
    source_id INTEGER, target_id INTEGER, polarity REAL, light_shadow TEXT, 
    role TEXT, consent BOOLEAN, description TEXT)''')
c.execute("INSERT OR IGNORE INTO nodes (name, maturity, ego_state, role, metacognition, history) VALUES (?, ?, ?, ?, ?, ?)",
          ("Test", 3, "Adult", "Creator", True, ""))
c.execute("SELECT id FROM nodes WHERE name=?", ("Test",))
result = c.fetchone()
print(f"Result: {result}")
conn.commit()
conn.close()import sqlite3
conn = sqlite3.connect('model.db')
c = conn.cursor()
# Create tables
c.execute('''CREATE TABLE IF NOT EXISTS nodes (
    id INTEGER PRIMARY KEY, name TEXT, maturity INTEGER, ego_state TEXT, 
    role TEXT, metacognition BOOLEAN, history TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS edges (
    source_id INTEGER, target_id INTEGER, polarity REAL, light_shadow TEXT, 
    role TEXT, consent BOOLEAN, description TEXT)''')
c.execute("INSERT OR IGNORE INTO nodes (name, maturity, ego_state, role, metacognition, history) VALUES (?, ?, ?, ?, ?, ?)",
          ("Test", 3, "Adult", "Creator", True, ""))
c.execute("SELECT id FROM nodes WHERE name=?", ("Test",))
result = c.fetchone()
print(f"Result: {result}")
conn.commit()
conn.close()import sqlite3
conn = sqlite3.connect('model.db')
c = conn.cursor()
c.execute("INSERT OR IGNORE INTO nodes (name, maturity, ego_state, role, metacognition, history) VALUES (?, ?, ?, ?, ?, ?)",
          ("Test", 3, "Adult", "Creator", True, ""))
c.execute("SELECT id FROM nodes WHERE name=?", ("Test",))
result = c.fetchone()
print(f"Result: {resu
