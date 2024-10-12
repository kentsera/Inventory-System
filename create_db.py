import sqlite3

def init_db():
    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()

    # Inventory テーブル
    c.execute('''
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        lot_number TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit TEXT NOT NULL,
        received_date TEXT NOT NULL,
        receipt_file TEXT
    )
    ''')

    # Recipes テーブル
    c.execute('''
    CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        drink_name TEXT NOT NULL
    )
    ''')

    # Ingredients テーブル
    c.execute('''
    CREATE TABLE IF NOT EXISTS ingredients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipe_id INTEGER NOT NULL,
        ingredient_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit TEXT NOT NULL
    )
    ''')

    # Manufactures テーブル
    c.execute('''
    CREATE TABLE IF NOT EXISTS manufactures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        drink_name TEXT NOT NULL,
        manufacture_date TEXT NOT NULL,
        expiration_date TEXT NOT NULL,
        quantity REAL NOT NULL,
        unit TEXT NOT NULL
    )
    ''')

    # History テーブル
    c.execute('''
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action_type TEXT NOT NULL,
        details TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )
    ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
