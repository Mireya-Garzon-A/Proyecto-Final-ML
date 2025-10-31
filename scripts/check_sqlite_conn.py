import sqlite3
import os
p = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'instance', 'usuarios.db'))
print('path:', p)
print('exists:', os.path.exists(p))
try:
    conn = sqlite3.connect(p)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cur.fetchall()
    print('tables:', tables)
    conn.close()
    print('sqlite open: OK')
except Exception as e:
    print('error opening sqlite:', repr(e))
