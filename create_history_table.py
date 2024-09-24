import sqlite3

# データベースへの接続
conn = sqlite3.connect('inventory.db')
c = conn.cursor()

# historyテーブルの作成
c.execute('''
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action_type TEXT NOT NULL,
        details TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
''')

conn.commit()
conn.close()

print("History table created successfully.")
