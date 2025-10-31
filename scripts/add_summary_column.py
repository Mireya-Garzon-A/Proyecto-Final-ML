import sqlite3
import os
import shutil

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'usuarios.db')
print('DB path:', DB_PATH)
if not os.path.exists(DB_PATH):
    print('ERROR: DB not found at', DB_PATH)
    raise SystemExit(1)

bak = DB_PATH + '.bak'
try:
    shutil.copyfile(DB_PATH, bak)
    print('Backup created at', bak)
except Exception as e:
    print('Warning: could not create backup:', e)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("PRAGMA table_info(consultas)")
cols = [r[1] for r in cur.fetchall()]
print('Existing columns:', cols)
if 'summary' in cols:
    print('Column "summary" already exists. No action needed.')
else:
    try:
        cur.execute("ALTER TABLE consultas ADD COLUMN summary TEXT;")
        conn.commit()
        print('Column "summary" added successfully.')
    except Exception as e:
        print('ERROR adding column:', e)

conn.close()
