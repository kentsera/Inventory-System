import sqlite3

def create_manufacture_table():
    conn = sqlite3.connect('inventory.db')  # データベースのパスを確認
    c = conn.cursor()

    # Manufactureテーブルを作成
    c.execute('''
    CREATE TABLE IF NOT EXISTS manufactures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        drink_name TEXT NOT NULL,
        manufacture_date TEXT NOT NULL,
        expiration_date TEXT NOT NULL,
        quantity INTEGER NOT NULL
        unit TEXT NOT NULL,                 -- 単位のカラムを追加
        lot_number TEXT NOT NULL
    )
    ''')

    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_manufacture_table()
