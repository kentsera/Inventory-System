import sqlite3

conn = sqlite3.connect('inventory.db')
c = conn.cursor()

# レシピテーブルの作成
c.execute('''
    CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        drink_name TEXT NOT NULL,
        ingredient_name TEXT NOT NULL,
        quantity REAL NOT NULL
    )
''')

conn.commit()
conn.close()
