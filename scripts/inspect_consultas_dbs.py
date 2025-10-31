import sqlite3, os
BASE = os.path.dirname(os.path.dirname(__file__))
paths = [os.path.join(BASE, 'usuarios.db'), os.path.join(BASE, 'instance', 'usuarios.db')]
for p in paths:
    print('\nDB:', p)
    if not os.path.exists(p):
        print('  Not found')
        continue
    conn = sqlite3.connect(p)
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, user_id, titulo, created_at, query_text, summary FROM consultas ORDER BY created_at ASC")
        rows = cur.fetchall()
        print('  Total consultas:', len(rows))
        for r in rows:
            id_, uid, title, created_at, q, summary = r
            print('   ', id_, uid, title, created_at, 'summary:', (summary[:80]+'...') if summary else None)
    except Exception as e:
        print('  Error reading consultas:', e)
    finally:
        conn.close()
