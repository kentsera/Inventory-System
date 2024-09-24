import sqlite3

# データベースに接続
conn = sqlite3.connect('inventory.db')
c = conn.cursor()

# recipesテーブルを作成
c.execute('''
    CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        drink_name TEXT NOT NULL,
        ingredient_name TEXT NOT NULL,
        quantity REAL NOT NULL
    )
''')

# 変更を保存して接続を閉じる
conn.commit()
conn.close()
