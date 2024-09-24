from flask import Flask, request, redirect, url_for, send_from_directory, render_template
import sqlite3
import os
from werkzeug.utils import secure_filename
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

# デバッグ用にデータベースのパスを出力
database_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.db')
print(f"Database path: {database_path}")


# Upload folder configuration
UPLOAD_FOLDER = 'uploads/'  # アップロードフォルダの場所
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}  # 許可するファイル形式

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# アップロードフォルダが存在しない場合、作成
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# ファイルの拡張子をチェックする関数を定義
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ファイル提供用のルート
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# データベース初期化関数
def init_db():
    database_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.db')
    conn = sqlite3.connect(database_path)
    c = conn.cursor()

    # Inventory テーブルの作成
    c.execute('''
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        lot_number TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit TEXT NOT NULL,
        received_date TEXT NOT NULL
    )''')

    # `receipt_file` カラムがない場合に追加
    c.execute('''PRAGMA table_info(inventory)''')
    columns = [col[1] for col in c.fetchall()]
    if 'receipt_file' not in columns:
        c.execute('ALTER TABLE inventory ADD COLUMN receipt_file TEXT')

    # Recipes テーブルの作成
    c.execute('''
    CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        drink_name TEXT NOT NULL
    )''')

    # Ingredients テーブルの作成
    c.execute('''
    CREATE TABLE IF NOT EXISTS ingredients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipe_id INTEGER NOT NULL,
        ingredient_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit TEXT NOT NULL
    )''')

    # Manufactures テーブルの作成
    c.execute('''
    CREATE TABLE IF NOT EXISTS manufactures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        drink_name TEXT NOT NULL,
        manufacture_date TEXT NOT NULL,
        expiration_date TEXT NOT NULL,
        quantity REAL NOT NULL,
        unit TEXT NOT NULL
    )''')

    # History テーブルの作成
    c.execute('''
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action_type TEXT NOT NULL,
        details TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )''')

    conn.commit()
    conn.close()

# Flaskアプリケーション開始前にデータベースを初期化する
init_db()


@app.route('/', methods=['GET', 'POST'])
def home():
    database_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.db')
    print("Database path:", database_path)  # デバッグ用
    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()

    query = "SELECT * FROM inventory"
    search_term = ""

    if request.method == 'POST':
        search_term = request.form['search']
        query += " WHERE product_name LIKE ? OR lot_number LIKE ?"
        c.execute(query, ('%' + search_term + '%', '%' + search_term + '%'))
    else:
        print("Executing query:", query)
        c.execute(query)

    inventory = c.fetchall()



    # 最新5件の履歴を取得
    c.execute("SELECT * FROM history ORDER BY timestamp DESC LIMIT 5")
    history = c.fetchall()
    print(history)  # デバッグ用に履歴の内容を出力

    history_list = ''
    for entry in history:
        # 'timestamp'から日付のみを取り出す（YYYY-MM-DD形式）
        timestamp = entry[3][:10]
        history_list += f'<p>{entry[1]}: {entry[2]} on {timestamp}</p>'

    conn.close()

    inventory_list = ''
    for item in inventory:
        inventory_list += f'<p>{item[1]} (Lot: {item[2]}), Quantity: {item[3]} {item[4]}, Received Date: {item[5]} <a href="/edit/{item[0]}">Edit</a></p>'
        inventory_list += f'<form action="/delete/{item[0]}" method="post" style="display:inline;"><button type="submit">Delete</button></form>'

    history_list = ''
    for entry in history:
        history_list += f'<p>{entry[1]}: {entry[2]} at {entry[3]}</p>'

    return f'''
        <h1>Shroomworks Inventory System</h1>
        <form method="post">
            Search: <input type="text" name="search" value="{search_term}">
            <input type="submit" value="Search">
        </form>
        {inventory_list}
        <a href="/add">Add Inventory</a><br>
        <a href="/manufacture/{{ recipe_id }}">Manufacture Products</a>
        <a href="/inventory_chart">View Inventory Chart</a><br>
        <a href="/view_recipes">Manage Recipes</a><br>
        
        <h2>History</h2>
        {history_list}
        <a href="/more_history">More History</a>
        
        <!-- CSVエクスポートのボタンを追加 -->
        <h2>Export Data</h2>
        <a href="/export_inventory"><button>Export Inventory to CSV</button></a><br>
        <a href="/export_recipes"><button>Export Recipes to CSV</button></a><br>

    '''

@app.route('/add', methods=['GET', 'POST'])
def add_inventory():
    if request.method == 'POST':
        product_name = request.form['product_name']
        lot_number = request.form['lot_number']

        # ファイルがリクエストにあるか確認
        if 'file' not in request.files or request.files['file'].filename == '':
            filename = None  # ファイルがない場合はNoneに設定
        else:
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)  # ファイル名の安全性を確保
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))  # ファイルを保存

        # Quantityの入力処理
        unit = request.form['unit']
        if unit == 'lbs_oz':
            quantity_lbs = int(request.form.get('quantity_lbs', 0))
            quantity_oz = int(request.form.get('quantity_oz', 0))
            quantity = (quantity_lbs * 16) + quantity_oz
        else:
            quantity = float(request.form['quantity'])

        received_date = request.form['received_date']

        conn = sqlite3.connect('inventory.db')
        c = conn.cursor()
        c.execute("INSERT INTO inventory (product_name, lot_number, quantity, unit, received_date, receipt_file) VALUES (?, ?, ?, ?, ?, ?)",
                  (product_name, lot_number, quantity, unit, received_date,  filename))
        
         # History に記録を追加
        action_details = f"Added {quantity} {unit} of {product_name} (Lot: {lot_number}) on {received_date}"
        c.execute("INSERT INTO history (action_type, details, timestamp) VALUES (?, ?, datetime('now'))",
                  ('Add Inventory', action_details))
        
        conn.commit()
        conn.close()
        return redirect(url_for('home'))

    return '''
        <form method="post">
            Product Name: <input type="text" name="product_name"><br>
            Lot Number: <input type="text" name="lot_number"><br>
            Unit: 
            <select name="unit" id="unitSelect" onchange="toggleLbsOzFields()">
                <option value="g">g</option>
                <option value="kg">kg</option>
                <option value="ml">ml</option>
                <option value="L">L</option>
                <option value="lbs_oz">Lbs & Oz</option>
            </select><br>
            
            <div id="lbsOzFields" style="display: none;">
                Quantity: 
                <input type="text" name="quantity_lbs"> lbs
                <input type="text" name="quantity_oz"> oz
            </div>
            
            Quantity: <input type="text" name="quantity"><br>
            Received Date: <input type="text" name="received_date"><br>
            Receipt: <input type="file" name="file"><br>
            <input type="submit" value="Add Inventory">
        </form>
        <script>
            function toggleLbsOzFields() {
                const unitSelect = document.getElementById('unitSelect');
                const lbsOzFields = document.getElementById('lbsOzFields');
                if (unitSelect.value === 'lbs_oz') {
                    lbsOzFields.style.display = 'block';
                } else {
                    lbsOzFields.style.display = 'none';
                }
            }
        </script>
    '''











@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_inventory(id):
    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()
    c.execute("SELECT * FROM inventory WHERE id=?", (id,))
    item = c.fetchone()

    print(f"取得したitemの内容: {item}", flush=True)

    if request.method == 'POST':
        print(f"POSTリクエストを受け取りました。", flush=True)

        product_name = request.form['product_name']
        lot_number = request.form['lot_number']
        quantity = float(request.form['quantity'])
        unit = request.form['unit']
        received_date = request.form['received_date'] 

        # ファイルがリクエストにあるか確認
        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            filename = item[6]  # 元のファイル名を使用

        print(f"ファイル名: {filename}", flush=True)

        # エラーハンドリングの追加
        unit = request.form['unit']
        if unit == 'lbs_oz':  # Lbs & Ozの場合は分割処理
            try:
                quantity_lbs = int(request.form.get('quantity_lbs', 0))
                quantity_oz = int(request.form.get('quantity_oz', 0))
                quantity = (quantity_lbs * 16) + quantity_oz  # lbsをozに変換して合計
            except ValueError:
                return "Error: Invalid quantity values.", 400
        else:  # その他の単位の場合は通常通り処理
            try:
                quantity = float(request.form['quantity'])
            except ValueError:
                return "Error: Invalid quantity.", 400

        c.execute("UPDATE inventory SET product_name=?, lot_number=?, quantity=?, unit=?, receipt_file=? WHERE id=?",
                  (product_name, lot_number, quantity, unit, filename, id))
        conn.commit()
        conn.close()
        return redirect(url_for('home'))

    # ファイルがある場合に、ファイルを開くリンクを表示
    file_link = ""
    if item[6]:  # item[5]がファイル名であると仮定
        print(f"ファイル名: {item[6]}")
        if allowed_file(item[6]):  # allowed_file() 関数でファイル形式を確認
        # 画像ファイルなら表示
            if item[6].lower().endswith(('png', 'jpg', 'jpeg')):
                file_link = f'<img src="/uploads/{item[6]}" alt="Attached image" style="max-width:200px;"><br>'
        # 画像以外ならリンクを表示
        else:
            file_link = f'<a href="/uploads/{item[6]}" target="_blank">Open existing file</a><br>'
        print(f"生成されたfile_link: {file_link}", flush=True)

    
    # Quantityをlbsとozに分割する処理
    unit = item[4]
    if unit == 'lbs_oz':  # Lbs & Ozの場合、lbsとozに分割
        quantity_lbs = item[3] // 16
        quantity_oz = item[3] % 16
    else:
        quantity_lbs = 0
        quantity_oz = 0

    return f'''
        <form method="post" enctype="multipart/form-data">
            Product Name: <input type="text" name="product_name" value="{item[1]}"><br>
            Lot Number: <input type="text" name="lot_number" value="{item[2]}"><br>
            
            <!-- 修正: 通常のQuantity入力 -->
            Quantity: <input type="text" name="quantity" value="{item[3]}"><br>

            Unit: 
            <select name="unit" id="unitSelect" onchange="toggleLbsOzFields()">
                <option value="g" {"selected" if unit == "g" else ""}>g</option>
                <option value="kg" {"selected" if unit == "kg" else ""}>kg</option>
                <option value="ml" {"selected" if unit == "ml" else ""}>ml</option>
                <option value="L" {"selected" if unit == "L" else ""}>L</option>
                <option value="lbs_oz" {"selected" if unit == "lbs_oz" else ""}>Lbs & Oz</option>
            </select><br>

            <!-- 修正: Lbs & Oz入力フィールドを隠しておく -->
            <div id="lbsOzFields" style="display: none;">
                Lbs: <input type="text" name="quantity_lbs" value="{quantity_lbs}"> 
                Oz: <input type="text" name="quantity_oz" value="{quantity_oz}"><br>
            </div>
            Received Date: <input type="text" name="received_date" value="{item[5]}"><br>
            
             {file_link}
            
            Receipt: <input type="file" name="file"><br>
            <input type="submit" value="Update">
        </form>

        <!-- JavaScript修正: Unit選択に応じてLbs & Oz入力欄を表示 -->
        <script>
            function toggleLbsOzFields() {{
                const unitSelect = document.getElementById('unitSelect');
                const lbsOzFields = document.getElementById('lbsOzFields');
                const quantityField = document.getElementsByName('quantity')[0];

                if (unitSelect.value === 'lbs_oz') {{
                    lbsOzFields.style.display = 'block';  // Lbs & Oz入力欄を表示
                    quantityField.disabled = true;  // 通常のQuantity入力を無効化
                }} else {{
                    lbsOzFields.style.display = 'none';  // Lbs & Oz入力欄を非表示
                    quantityField.disabled = false;  // 通常のQuantity入力を有効化
                }}
            }}
            
            // ページ読み込み時に現在のUnitに応じて表示を切り替える
            window.onload = toggleLbsOzFields;
        </script>
    '''
















@app.route('/delete/<int:id>', methods=['POST'])
def delete_inventory(id):
    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()
    c.execute("DELETE FROM inventory WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))




@app.route('/inventory_chart')
def inventory_chart():
    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()

    # 各原料の名前、数量、単位を取得
    c.execute("SELECT product_name, SUM(quantity), unit FROM inventory GROUP BY product_name, unit")
    data = c.fetchall()
    conn.close()

    product_names = [row[0] for row in data]
    quantities = [row[1] for row in data]
    units = [row[2] for row in data]

    plt.figure(figsize=(10, 6))

    # bars変数に棒グラフのバーの情報を保存
    bars = plt.bar(product_names, quantities)

     # グラフの天辺に数量と単位を表示
    for bar, quantity, unit in zip(bars, quantities, units):
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval, f'{quantity} {unit}', va='bottom', ha='center')

    plt.xlabel('Product Name')
    plt.ylabel('Quantity')
    plt.title('Inventory Visualization')

    # Save the image to memory and prepare it for display in the browser
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    graph_url = base64.b64encode(img.getvalue()).decode()


    print(f"Rendering inventory_chart.html with graph_url: {graph_url} and product_names: {product_names}")

    # Flaskテンプレートに商品名とグラフのデータを渡して表示
    return render_template('inventory_chart.html', graph_url=graph_url, product_names=product_names)

    





@app.route('/inventory_history/<product_name>')
def inventory_history(product_name):
    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()

    # 指定された商品の履歴を取得
    c.execute("SELECT timestamp, details FROM history WHERE details LIKE ? ORDER BY timestamp", ('%' + product_name + '%',))
    data = c.fetchall()
    conn.close()

    # データを解析して数量の変動を抽出
    timestamps = []
    quantity_changes = []
    total_quantities = []
    current_total = 0

    for row in data:
        timestamp, details = row
        # "Added 1000.0 g of Termeric" というような文字列から数量を抽出
        if 'Added' in details:
            quantity = float(details.split(' ')[1])  # "1000.0"の部分を取得
        elif 'Manufactured' in details:
            quantity = -float(details.split(' ')[1])  # 製造は在庫が減るためマイナス
        else:
            continue

        # タイムスタンプと数量の変化をリストに追加
        timestamps.append(timestamp)
        current_total += quantity  # 在庫の累計を計算
        total_quantities.append(current_total)

    # グラフを描画
    plt.figure(figsize=(10, 6))
    plt.plot(timestamps, total_quantities, marker='o')

    plt.xlabel('Time')
    plt.ylabel('Total Quantity')
    plt.title(f'Inventory History for {product_name}')

    # グラフをブラウザに表示するために画像をメモリに保存
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    graph_url = base64.b64encode(img.getvalue()).decode()

    return f'<img src="data:image/png;base64,{graph_url}"/>'






@app.route('/add_recipe', methods=['GET', 'POST'])
def add_recipe():
    if request.method == 'POST':
        drink_name = request.form['drink_name']
        
        conn = sqlite3.connect('inventory.db')
        c = conn.cursor()
        c.execute("INSERT INTO recipes (drink_name) VALUES (?)", (drink_name,))
        recipe_id = c.lastrowid

        # 複数の材料を登録
        ingredients = request.form.getlist('ingredient_name')
        quantities = request.form.getlist('quantity')
        units = request.form.getlist('unit')

        for i in range(len(ingredients)):
            if units[i] == 'lbs_oz':
                quantity_lbs = int(request.form.getlist('quantity_lbs')[i])
                quantity_oz = int(request.form.getlist('quantity_oz')[i])
                quantity = (quantity_lbs * 16) + quantity_oz
            else:
                quantity = float(quantities[i])
            c.execute("INSERT INTO ingredients (recipe_id, ingredient_name, quantity, unit) VALUES (?, ?, ?, ?)",
                      (recipe_id, ingredients[i], quantity, units[i]))

        conn.commit()
        conn.close()
        return redirect(url_for('view_recipes'))

    return '''
        <form method="post" id="recipeForm">
            Drink Name: <input type="text" name="drink_name"><br>
            <div id="ingredientContainer">
                <div>
                    Ingredient 1: <input type="text" name="ingredient_name"><br>
                    Quantity 1: <input type="text" name="quantity"><br>
                    Unit: 
                    <select name="unit" id="unitSelect" onchange="toggleLbsOzFields()">
                        <option value="g">g</option>
                        <option value="kg">kg</option>
                        <option value="ml">ml</option>
                        <option value="L">L</option>
                        <option value="lbs_oz">Lbs & Oz</option>
                    </select><br>

                    <div id="lbsOzFields" style="display: none;">
                        Quantity: 
                        <input type="text" name="quantity_lbs"> lbs
                        <input type="text" name="quantity_oz"> oz
                    </div>
                </div>
            </div>
            <button type="button" onclick="addIngredient()">Add Ingredient</button><br>
            <input type="submit" value="Add Recipe">
        </form>
        <script>
            function toggleLbsOzFields() {
                const unitSelect = document.getElementById('unitSelect');
                const lbsOzFields = document.getElementById('lbsOzFields');
                if (unitSelect.value === 'lbs_oz') {
                    lbsOzFields.style.display = 'block';
                } else {
                    lbsOzFields.style.display = 'none';
                }
            }

            function addIngredient() {
                const container = document.getElementById('ingredientContainer');
                const newIngredient = document.createElement('div');
                newIngredient.innerHTML = `
                    Ingredient <input type="text" name="ingredient_name"><br>
                    Quantity <input type="text" name="quantity"><br>
                    Unit: 
                    <select name="unit" onchange="toggleLbsOzFields()">
                        <option value="g">g</option>
                        <option value="kg">kg</option>
                        <option value="ml">ml</option>
                        <option value="L">L</option>
                        <option value="oz">oz</option>
                        <option value="lbs">lbs</option>
                        <option value="lbs_oz">Lbs & Oz</option>
                    </select><br>
                    <div id="lbsOzFields" style="display: none;">
                        Quantity: 
                        <input type="text" name="quantity_lbs"> lbs
                        <input type="text" name="quantity_oz"> oz
                    </div>
                `;
                container.appendChild(newIngredient);
            }
        </script>
    '''











@app.route('/edit_recipe/<int:recipe_id>', methods=['GET', 'POST'])
def edit_recipe(recipe_id):
    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()

    if request.method == 'POST':
        # レシピ名を更新
        c.execute("UPDATE recipes SET drink_name = ? WHERE id = ?", (request.form['drink_name'], recipe_id))
        # 現在の材料を削除して新しい材料を追加
        c.execute("DELETE FROM ingredients WHERE recipe_id = ?", (recipe_id,))

        ingredients = request.form.getlist('ingredient_name')
        quantities = request.form.getlist('quantity')
        units = request.form.getlist('unit')

        for i in range(len(ingredients)):
            if units[i] == 'lbs_oz':
                quantity_lbs = int(request.form.getlist('quantity_lbs')[i])
                quantity_oz = int(request.form.getlist('quantity_oz')[i])
                quantity = (quantity_lbs * 16) + quantity_oz
            else:
                quantity = float(quantities[i])

            c.execute("INSERT INTO ingredients (recipe_id, ingredient_name, quantity, unit) VALUES (?, ?, ?, ?)",
                      (recipe_id, ingredients[i], quantity, units[i]))

        conn.commit()
        conn.close()
        return redirect(url_for('view_recipes'))

    # レシピ名と材料を取得
    c.execute("SELECT drink_name FROM recipes WHERE id = ?", (recipe_id,))
    drink_name = c.fetchone()[0]

    c.execute("SELECT ingredient_name, quantity, unit FROM ingredients WHERE recipe_id = ?", (recipe_id,))
    ingredients = c.fetchall()
    conn.close()

    # 既存の材料フィールドを生成
    ingredient_fields = ''
    for i, (ingredient_name, quantity, unit) in enumerate(ingredients, start=1):
        if unit == 'lbs_oz':
            quantity_lbs = quantity // 16
            quantity_oz = quantity % 16
        else:
            quantity_lbs = 0
            quantity_oz = 0

        ingredient_fields += f'''
            Ingredient {i}: <input type="text" name="ingredient_name" value="{ingredient_name}"><br>
            Quantity: <input type="text" name="quantity" value="{quantity}"><br>
            Unit: 
            <select name="unit" id="unitSelect_{i}" onchange="toggleLbsOzFields({i})">
                <option value="g" {"selected" if unit == "g" else ""}>g</option>
                <option value="kg" {"selected" if unit == "kg" else ""}>kg</option>
                <option value="ml" {"selected" if unit == "ml" else ""}>ml</option>
                <option value="L" {"selected" if unit == "L" else ""}>L</option>
                <option value="oz" {"selected" if unit == "oz" else ""}>oz</option>
                <option value="lbs" {"selected" if unit == "lbs" else ""}>lbs</option>
                <option value="lbs_oz" {"selected" if unit == "lbs_oz" else ""}>Lbs & Oz</option>
            </select><br>
            <div id="lbsOzFields_{i}" style="display: {'block' if unit == 'lbs_oz' else 'none'};">
                Lbs: <input type="text" name="quantity_lbs" value="{quantity_lbs}"> 
                Oz: <input type="text" name="quantity_oz" value="{quantity_oz}"><br>
            </div>
        '''

    return f'''
        <form method="post" id="recipeForm">
            Drink Name: <input type="text" name="drink_name" value="{drink_name}"><br>
            <div id="ingredientContainer">
                {ingredient_fields}
            </div>
            <button type="button" onclick="addIngredient()">Add Ingredient</button><br>
            <input type="submit" value="Update Recipe">
        </form>

        <script>
            function toggleLbsOzFields(index) {{
                const unitSelect = document.getElementById('unitSelect_' + index);
                const lbsOzFields = document.getElementById('lbsOzFields_' + index);
                if (unitSelect.value === 'lbs_oz') {{
                    lbsOzFields.style.display = 'block';
                }} else {{
                    lbsOzFields.style.display = 'none';
                }}
            }}

            // ページ読み込み時にUnitに応じてLbs & Ozフィールドを切り替え
            window.onload = function() {{
                for (let i = 1; i <= {len(ingredients)}; i++) {{
                    toggleLbsOzFields(i);
                }}
            }};
            
            // Add Ingredientの関数（JavaScriptでnewIndexを動的に生成）
            function addIngredient() {{
                const container = document.getElementById('ingredientContainer');
                const newIndex = container.querySelectorAll('input[name="ingredient_name"]').length;  // 正確にインデックスを生成

                const newIngredient = `
                    <div>
                        Ingredient ${newIndex + 1}: <input type="text" name="ingredient_name"><br>
                        Quantity: <input type="text" name="quantity"><br>
                        Unit: 
                        <select name="unit" onchange="toggleLbsOzFields(${newIndex + 1})">
                            <option value="g">g</option>
                            <option value="kg">kg</option>
                            <option value="ml">ml</option>
                            <option value="L">L</option>
                            <option value="oz">oz</option>
                            <option value="lbs">lbs</option>
                            <option value="lbs_oz">Lbs & Oz</option>
                        </select><br>
                        <div id="lbsOzFields_${newIndex + 1}" style="display: none;">
                            Lbs: <input type="text" name="quantity_lbs"> 
                            Oz: <input type="text" name="quantity_oz"><br>
                        </div>
                    </div>
                `;
                container.insertAdjacentHTML('beforeend', newIngredient);
            }}
        </script>
    '''





















@app.route('/view_recipes')
def view_recipes():
    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()
    c.execute("""
        SELECT r.id, r.drink_name, i.ingredient_name, i.quantity
        FROM recipes r
        JOIN ingredients i ON r.id = i.recipe_id
    """)
    recipes = c.fetchall()
    conn.close()

    recipe_list = ''
    current_drink = ''
    for recipe in recipes:
        if recipe[1] != current_drink:
            current_drink = recipe[1]
            recipe_list += f'<h3>{recipe[1]}</h3>'
        recipe_list += f'<p>{recipe[2]} - {recipe[3]}</p>'
        recipe_list += f'<a href="/edit_recipe/{recipe[0]}">Edit</a>'

        # レシピの削除ボタンを追加
        recipe_list += f'''
            <form action="/delete_recipe/{recipe[0]}" method="post" style="display:inline;">
                <button type="submit">Delete</button>
            </form><br>
        '''

    return f'''
        <h1>Recipe List</h1>
        {recipe_list}
        <a href="/add_recipe">Add New Recipe</a><br>
        <a href="/">Back to Home</a>
    '''

@app.route('/delete_recipe/<int:recipe_id>', methods=['POST'])
def delete_recipe(recipe_id):
    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()
    
    # レシピに関連する材料を削除
    c.execute("DELETE FROM ingredients WHERE recipe_id = ?", (recipe_id,))
    
    # レシピ自体を削除
    c.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    
    conn.commit()
    conn.close()
    return redirect(url_for('view_recipes'))

@app.route('/produce/<int:recipe_id>', methods=['POST'])
def produce(recipe_id):
    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()

    # 該当するレシピの材料を取得
    c.execute("SELECT ingredient_name, quantity FROM ingredients WHERE recipe_id=?", (recipe_id,))
    ingredients = c.fetchall()

    # 在庫から材料を引き算
    for ingredient in ingredients:
        c.execute("UPDATE inventory SET quantity = quantity - ? WHERE product_name = ?",
                  (ingredient[1], ingredient[0]))

    conn.commit()
    conn.close()
    return redirect(url_for('home'))

import os



@app.route('/manufacture/<int:recipe_id>', methods=['GET', 'POST'])
def manufacture(recipe_id):  # recipe_idを受け取るように修正
    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()

    # 選択したレシピに基づいて原材料を取得
    c.execute("SELECT ingredient_name, quantity FROM ingredients WHERE recipe_id=?", (recipe_id,))
    ingredients = c.fetchall()

    if request.method == 'POST':
        drink_name = request.form['drink_name']
        manufacture_date = request.form['manufacture_date']
        expiration_date = request.form['expiration_date']
        lot_numbers = request.form.getlist('lot_number')  # 各原材料のLOT番号を取得
        quantities = request.form.getlist('quantity')     # 各原材料の使用量を取得

        # 原材料ごとの在庫を更新する処理
        for i, (ingredient_name, recipe_quantity) in enumerate(ingredients):
            lot_number = lot_numbers[i]
            used_quantity = float(quantities[i])  # 使用量をfloat型に変換
            # 在庫から減らす処理
            c.execute("UPDATE inventory SET quantity = quantity - ? WHERE product_name = ? AND lot_number = ?", 
                      (used_quantity, ingredient_name, lot_number))

        # 製造履歴を追加
        c.execute("INSERT INTO manufactures (drink_name, manufacture_date, expiration_date) VALUES (?, ?, ?)",
                  (drink_name, manufacture_date, expiration_date))
        
        # History に記録を追加
        action_details = f"Manufactured {used_quantity} of {drink_name} on {manufacture_date}, Expiry: {expiration_date}"
        c.execute("INSERT INTO history (action_type, details, timestamp) VALUES (?, ?, datetime('now'))",
                  ('Manufacture', action_details))

        conn.commit()
        conn.close()

        return redirect(url_for('home'))

    

    # 原材料ごとにLOT番号と使用量を入力するフォームを生成
    ingredient_fields = ''
    for i, (ingredient_name, recipe_quantity) in enumerate(ingredients):
        ingredient_fields += f'''
            <p>原材料: {ingredient_name} (必要な数量: {recipe_quantity})</p>
            LOT番号: <input type="text" name="lot_number" required><br>
            使用数量: <input type="text" name="quantity" required><br>
        '''

    # Pythonのf文字列を使ってingredient_fieldsをフォーム内に埋め込むように修正
    return f'''
        <h1>Manufacture Products</h1>
        <form method="post">
            Drink Name: <input type="text" name="drink_name" required><br>
            Manufacture Date: <input type="date" name="manufacture_date" required><br>
            Expiration Date: <input type="date" name="expiration_date" required><br>

            <!-- 原材料ごとのLOT番号と使用量を入力 -->
            {ingredient_fields}

            <input type="submit" value="Manufacture">
        </form>
    '''











#Csv fileにして、エクスポートするコード。
import csv
from flask import send_file

# 在庫データのエクスポート
@app.route('/export_inventory')
def export_inventory():
    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()

    # 在庫データを取得
    c.execute("SELECT * FROM inventory")
    inventory_data = c.fetchall()

    # CSVファイルにデータを書き込む
    csv_file_path = 'inventory_export.csv'
    with open(csv_file_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['ID', 'Product Name', 'Lot Number', 'Quantity', 'Received Date'])
        writer.writerows(inventory_data)

    conn.close()

    # ファイルをダウンロードするために送信
    return send_file(csv_file_path, as_attachment=True)

# レシピデータのエクスポート
@app.route('/export_recipes')
def export_recipes():
    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()

    # レシピデータを取得
    c.execute("""
        SELECT r.id, r.drink_name, i.ingredient_name, i.quantity
        FROM recipes r
        JOIN ingredients i ON r.id = i.recipe_id
    """)
    recipe_data = c.fetchall()

    # CSVファイルにデータを書き込む
    csv_file_path = 'recipes_export.csv'
    with open(csv_file_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Recipe ID', 'Drink Name', 'Ingredient Name', 'Quantity'])
        writer.writerows(recipe_data)

    conn.close()

    # ファイルをダウンロードするために送信
    return send_file(csv_file_path, as_attachment=True)











if __name__ == '__main__':
    app.run(debug=True)
