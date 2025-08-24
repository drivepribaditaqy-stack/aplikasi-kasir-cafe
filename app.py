import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import plotly.graph_objects as go
import urllib.parse

# --- KONFIGURASI DAN INISIALISASI ---
DB = "pos.db"
st.set_page_config(layout="wide", page_title="Cafe POS App")

# =====================================================================
# --- FUNGSI MIGRASI & INISIALISASI DATABASE ---
# =====================================================================
def update_db_schema(conn):
    """Memeriksa dan memperbarui skema database jika diperlukan."""
    c = conn.cursor()
    
    # Periksa kolom 'payment_method' di tabel 'sales'
    c.execute("PRAGMA table_info(sales)")
    columns = [info[1] for info in c.fetchall()]
    if 'payment_method' not in columns:
        try:
            c.execute("ALTER TABLE sales ADD COLUMN payment_method TEXT")
            st.toast("Database 'sales' diperbarui.")
            conn.commit()
        except sqlite3.OperationalError:
            pass

    # Periksa kolom di tabel 'employees'
    c.execute("PRAGMA table_info(employees)")
    columns = [info[1] for info in c.fetchall()]
    if 'hourly_wage' in columns:
        try:
            c.execute("ALTER TABLE employees RENAME TO employees_old")
            c.execute("""CREATE TABLE employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                name TEXT UNIQUE, 
                wage_amount REAL, 
                wage_period TEXT
            )""")
            c.execute("""INSERT INTO employees (id, name, wage_amount, wage_period) 
                         SELECT id, name, hourly_wage, 'Per Jam' FROM employees_old""")
            c.execute("DROP TABLE employees_old")
            st.toast("Database 'employees' diperbarui.")
            conn.commit()
        except sqlite3.OperationalError:
            pass
    
    conn.commit()

def insert_initial_data(conn):
    """Mengisi database dengan data awal jika kosong."""
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        st.info("Database kosong, mengisi dengan data awal...")
        ingredients_data = [
            (1, 'Trieste Blueberry', 'gr', 166.67, 1000, 1000, 166667), (2, 'Trieste Tiramisu', 'gr', 166.67, 1000, 1000, 166667),
            (3, 'Denali Hazelnut', 'gr', 130.0, 1000, 1000, 130000), (4, 'Denali Caramel', 'gr', 130.0, 1000, 1000, 130000),
            (5, 'Denali Salted Caramel', 'gr', 130.0, 1000, 1000, 130000), (6, 'Denali Blue Citrus', 'gr', 130.0, 1000, 1000, 130000),
            (7, 'ABC Squash Lychee', 'gr', 20.0, 1000, 1000, 20000), (8, 'ABC Squash Florida Orange', 'gr', 20.0, 1000, 1000, 20000),
            (9, 'Marjan Squash Mango', 'gr', 15.0, 1000, 1000, 15000), (10, 'Marjan Boudoin Grenadine', 'gr', 25.0, 1000, 1000, 25000),
            (11, 'Marjan Boudoin Moka', 'gr', 25.0, 1000, 1000, 25000), (12, 'Marjan Boudoin Vanilla', 'gr', 25.0, 1000, 1000, 25000),
            (13, 'Marjan Boudoin Lemon', 'gr', 25.0, 1000, 1000, 25000), (14, 'Marjan Boudoin Melon', 'gr', 25.0, 1000, 1000, 25000),
            (15, 'Marjan Boudoin Markisa', 'gr', 25.0, 1000, 1000, 25000), (16, 'Air Galon', 'ml', 0.3, 19000, 19000, 6000),
            (17, 'Kopoe Kopoe Gula Aren', 'gr', 50.0, 1000, 1000, 50000), (18, 'Marjan Squash Mangga', 'gr', 15.0, 1000, 1000, 15000),
            (19, 'Marjan Boudoin Strawberry', 'gr', 25.0, 1000, 1000, 25000), (20, 'Sprite Zero', 'gr', 10.0, 1000, 1000, 10000),
            (21, 'Creamer', 'gr', 80.0, 1000, 1000, 80000), (22, 'SKM', 'gr', 25.0, 1000, 1000, 25000),
            (23, 'UHT', 'gr', 20.0, 1000, 1000, 20000), (24, 'Coffee Beans Samara', 'gr', 100.0, 1000, 1000, 100000)
        ]
        c.executemany("INSERT OR IGNORE INTO ingredients (id, name, unit, cost_per_unit, stock, pack_weight, pack_price) VALUES (?, ?, ?, ?, ?, ?, ?)", ingredients_data)
        products_data = [
            (1, 'Espresso', 10000), (2, 'Americano', 12000), (3, 'Lemon Americano', 15000), (4, 'Orange Americano', 15000),
            (5, 'Cococof (BN Signature)', 20000), (6, 'Coffee Latte', 18000), (7, 'Cappucino', 18000), (8, 'Spanish Latte', 20000),
            (9, 'Caramel Latte', 20000), (10, 'VanillaLatte', 20000), (11, 'Hazelnut Latte', 20000), (12, 'Butterscotch Latte', 22000),
            (13, 'Tiramissu Latte', 20000), (14, 'Mocca Latte', 20000), (15, 'Coffee Chocolate', 22000), (16, 'Taro Coffee Latte', 22000),
            (17, 'Coffee Gula Aren', 22000), (18, 'Lychee Coffe', 20000), (19, 'Markisa Coffee', 20000), (20, 'Raspberry Latte', 20000),
            (21, 'Strawberry Latte', 20000), (22, 'Manggo Latte', 20000), (23, 'Bubblegum Latte', 20000), (24, 'Lemon Tea', 10000),
            (25, 'Lychee Tea', 12000), (26, 'Milk Tea', 15000), (27, 'Green Tea', 15000), (28, 'Thai Tea', 15000),
            (29, 'Melon Susu', 15000), (30, 'Manggo Susu', 18000), (31, 'Mocca Susu', 18000), (32, 'Orange Susu', 18000),
            (33, 'Taro Susu', 18000), (34, 'Coklat Susu', 18000), (35, 'Vanilla Susu', 18000), (36, 'Strawberry Susu', 18000),
            (37, 'Matcha Susu', 20000), (38, 'Blueberry Susu', 20000), (39, 'Bubblegum Susu', 20000), (40, 'Raspberry Susu', 20000),
            (41, 'Grenadine Susu', 20000), (42, 'Banana Susu', 20000), (43, 'Melon Soda', 12000), (44, 'Manggo Soda', 15000),
            (45, 'Orange Soda', 15000), (46, 'Strawberry Soda', 15000), (47, 'Bluesky Soda', 15000), (48, 'Banana Soda', 20000),
            (49, 'Grenadine Soda', 15000), (50, 'Blueberry Soda', 20000), (51, 'Coffee Bear', 20000), (52, 'Mocca Soda', 20000),
            (53, 'Raspberry Soda', 20000), (54, 'Coffe Soda', 15000), (55, 'Strawberry Coffe Soda', 20000), (56, 'Melon Bluesky', 20000),
            (57, 'Blue Manggo Soda', 22000), (58, 'Double Shoot ADD On', 5000), (59, 'Yakult ADD On', 3000),
            (60, 'Mineral Water', 5000), (61, 'Mineral Water Gelas', 1000)
        ]
        c.executemany("INSERT OR IGNORE INTO products (id, name, price) VALUES (?, ?, ?)", products_data)
        employees_data = [(1, 'Taza', 10000, 'Per Jam')]
        c.executemany("INSERT OR IGNORE INTO employees (id, name, wage_amount, wage_period) VALUES (?, ?, ?, ?)", employees_data)
        conn.commit()
        st.success("Data awal berhasil dimuat.")
        st.rerun()

def init_db():
    """Inisialisasi koneksi dan struktur database."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS ingredients (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, unit TEXT,
        cost_per_unit REAL, stock REAL, pack_weight REAL DEFAULT 0.0, pack_price REAL DEFAULT 0.0
    )""")
    c.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, price REAL)")
    c.execute("""CREATE TABLE IF NOT EXISTS recipes (
        product_id INTEGER, ingredient_id INTEGER, qty_per_unit REAL, PRIMARY KEY (product_id, ingredient_id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, qty INTEGER, 
        date TEXT, payment_method TEXT
    )""")
    c.execute("CREATE TABLE IF NOT EXISTS other_expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, description TEXT, amount REAL, date TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS operational_costs (id INTEGER PRIMARY KEY AUTOINCREMENT, description TEXT, amount REAL, date TEXT)")
    c.execute("""CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, wage_amount REAL, wage_period TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER, check_in TEXT, check_out TEXT
    )""")
    conn.commit()
    update_db_schema(conn)
    insert_initial_data(conn)
    conn.close()

# =====================================================================
# --- BAGIAN LOGIN ---
# =====================================================================
def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if st.session_state.logged_in:
        st.sidebar.success(f"Welcome, {st.session_state.username} ({st.session_state.role})")
        if st.sidebar.button("Logout"):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()
        run_main_app()
    else:
        st.title("🔐 Login - Aplikasi Kasir Cafe")
        USERS = {"admin": {"password": "admin", "role": "Admin"}, "manager": {"password": "manager", "role": "Manager"}, "operator": {"password": "operator", "role": "Operator"}}
        with st.form("login_form"):
            username = st.text_input("Username").lower()
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                user_data = USERS.get(username)
                if user_data and user_data["password"] == password:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.role = user_data["role"]
                    st.rerun()
                else:
                    st.error("Username atau password salah!")

# =====================================================================
# --- APLIKASI UTAMA ---
# =====================================================================
def run_main_app():
    init_db()

    def run_query(query, params=()):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()
        conn.close()

    def get_df(query, params=()):
        conn = sqlite3.connect(DB)
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df

    def record_sale(product_id, qty, payment_method):
        today = date.today().strftime("%Y-%m-%d")
        run_query("INSERT INTO sales (product_id, qty, date, payment_method) VALUES (?, ?, ?, ?)", (product_id, qty, today, payment_method))
        recipe_df = get_df("SELECT ingredient_id, qty_per_unit FROM recipes WHERE product_id=?", params=(product_id,))
        for _, row in recipe_df.iterrows():
            run_query("UPDATE ingredients SET stock = stock - ? WHERE id=?", (row['qty_per_unit'] * qty, row['ingredient_id']))
    
    def add_employee(name, wage_amount, wage_period):
        run_query("INSERT INTO employees (name, wage_amount, wage_period) VALUES (?, ?, ?)", (name, wage_amount, wage_period))
    
    def update_employee(id, name, wage_amount, wage_period):
        run_query("UPDATE employees SET name=?, wage_amount=?, wage_period=? WHERE id=?", (name, wage_amount, wage_period, id))

    def add_ingredient(name, unit, cost, stock, pack_weight, pack_price):
        run_query("INSERT INTO ingredients (name, unit, cost_per_unit, stock, pack_weight, pack_price) VALUES (?, ?, ?, ?, ?, ?)", (name, unit, cost, stock, pack_weight, pack_price))
    def update_ingredient(id, name, unit, cost, stock, pack_weight, pack_price):
        run_query("UPDATE ingredients SET name=?, unit=?, cost_per_unit=?, stock=?, pack_weight=?, pack_price=? WHERE id=?", (name, unit, cost, stock, pack_weight, pack_price, id))
    def delete_ingredient(id):
        run_query("DELETE FROM ingredients WHERE id=?", (id,))
    def add_product(name, price):
        run_query("INSERT INTO products (name, price) VALUES (?, ?)", (name, price))
    def update_product(id, name, price):
        run_query("UPDATE products SET name=?, price=? WHERE id=?", (name, price, id))
    def delete_product(id):
        run_query("DELETE FROM products WHERE id=?", (id,))
    def set_recipe(product_id, ingredients_data):
        run_query("DELETE FROM recipes WHERE product_id=?", (product_id,))
        for ing_id, qty in ingredients_data.items():
            if qty > 0:
                run_query("INSERT INTO recipes (product_id, ingredient_id, qty_per_unit) VALUES (?, ?, ?)", (product_id, ing_id, qty))
    def delete_employee(id):
        run_query("DELETE FROM employees WHERE id=?", (id,))
    def check_in(employee_id):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        run_query("INSERT INTO attendance (employee_id, check_in) VALUES (?, ?)", (employee_id, now))
    def check_out(attendance_id):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        run_query("UPDATE attendance SET check_out=? WHERE id=?", (now, attendance_id))
    def update_attendance(att_id, check_in_str, check_out_str):
        try:
            datetime.strptime(check_in_str, '%Y-%m-%d %H:%M:%S');
            if check_out_str: datetime.strptime(check_out_str, '%Y-%m-%d %H:%M:%S')
            run_query("UPDATE attendance SET check_in=?, check_out=? WHERE id=?", (check_in_str, check_out_str, att_id)); return True, "OK"
        except: return False, "Format tanggal salah"
    def delete_attendance(att_id):
        run_query("DELETE FROM attendance WHERE id=?", (att_id,))
    def get_product_hpp(product_id):
        df = get_df("SELECT SUM(r.qty_per_unit * i.cost_per_unit) as hpp FROM recipes r JOIN ingredients i ON r.ingredient_id = i.id WHERE r.product_id = ?", params=(product_id,)); return df['hpp'].iloc[0] if not df.empty and pd.notna(df['hpp'].iloc[0]) else 0

    # --- UI SIDEBAR ---
    st.sidebar.title("MENU NAVIGASI")
    with st.sidebar.expander("🧮 Kalkulator"):
        if 'calc_expression' not in st.session_state: st.session_state.calc_expression = ""
        st.text_input("Kalkulator", value=st.session_state.calc_expression, key="calc_display", disabled=True)
        buttons = ['7', '8', '9', '/', '4', '5', '6', '*', '1', '2', '3', '-', '0', '.', '=', '+']
        cols = st.columns(4)
        for i, btn in enumerate(buttons):
            if cols[i % 4].button(btn, key=f"calc_btn_{btn}", use_container_width=True):
                if btn == '=':
                    try: st.session_state.calc_expression = str(eval(st.session_state.calc_expression))
                    except: st.session_state.calc_expression = "Error"
                else:
                    if st.session_state.calc_expression == "Error": st.session_state.calc_expression = ""
                    st.session_state.calc_expression += btn
                st.rerun()
        if st.button("Clear", key="calc_clear", use_container_width=True):
            st.session_state.calc_expression = ""; st.rerun()

    user_role = st.session_state.get("role", "Operator")
    menu_options = ["🏠 Kasir", "📦 Manajemen Stok", "🍽️ Manajemen Produk", "📈 Laporan", "💰 HPP"]
    if user_role in ["Admin", "Manager"]:
        menu_options.extend(["👨‍💼 Manajemen Karyawan", "🧾 Riwayat Absensi"])
    menu = st.sidebar.radio("Pilih Halaman:", menu_options)

    # --- HALAMAN-HALAMAN APLIKASI ---
    if menu == "🏠 Kasir":
        st.title("🏠 Aplikasi Kasir")
        st.markdown("""
        <style>
            .product-card { border: 1px solid #ddd; border-radius: 10px; padding: 10px; text-align: center; margin-bottom: 10px; background-color: #f9f9f9; display: flex; flex-direction: column; justify-content: space-between; height: 130px; }
            .product-card .product-name { font-size: 14px; font-weight: bold; flex-grow: 1; color: #333; }
            .product-card .price { font-size: 13px; color: #007bff; font-weight: bold; margin-bottom: 8px; }
            .product-card .stButton button { width: 100%; background-color: #007bff; color: white; font-size: 13px; padding: 5px; }
        </style>
        """, unsafe_allow_html=True)

        products_df = get_df("SELECT * FROM products ORDER BY name ASC")
        if products_df.empty:
            st.warning("Belum ada produk yang ditambahkan.")
        else:
            if 'cart' not in st.session_state: st.session_state.cart = {}
            col_products, col_cart = st.columns([3, 2])
            with col_products:
                st.subheader("Pilih Produk")
                search_query = st.text_input("Cari Produk...", label_visibility="collapsed", placeholder="Cari Produk...")
                filtered_products = products_df[products_df['name'].str.contains(search_query, case=False)] if search_query else products_df
                
                num_columns = 4
                cols = st.columns(num_columns)
                for index, row in filtered_products.iterrows():
                    with cols[index % num_columns]:
                        with st.container():
                            st.markdown(f"""<div class="product-card"><div class="product-name">{row['name']}</div><div class="price">Rp {row['price']:,.0f}</div></div>""", unsafe_allow_html=True)
                            if st.button("Tambah", key=f"add_{row['id']}", use_container_width=True):
                                st.session_state.cart[row['name']] = st.session_state.cart.get(row['name'], 0) + 1
                                st.toast(f"{row['name']} ditambahkan!"); st.rerun()
            with col_cart:
                st.subheader("🛒 Keranjang Pesanan")
                if not st.session_state.cart: st.info("Keranjang kosong.")
                else:
                    cart_df_data = []
                    product_prices = products_df.set_index('name')['price'].to_dict()
                    for item, qty in st.session_state.cart.items():
                        price = product_prices.get(item, 0)
                        cart_df_data.append({"Produk": item, "Qty": qty, "Harga": f"Rp {price:,.0f}", "Subtotal": f"Rp {price * qty:,.0f}"})
                    st.dataframe(pd.DataFrame(cart_df_data), use_container_width=True, hide_index=True)
                    total = sum(product_prices.get(item, 0) * qty for item, qty in st.session_state.cart.items())
                    st.metric("Total Pesanan", f"Rp {total:,.0f}")
                    st.subheader("Pembayaran")
                    payment_method = st.radio("Metode Pembayaran", ["Cash", "QRIS"], horizontal=True)
                    proceed = False
                    if payment_method == "Cash":
                        cash_received = st.number_input("Jumlah Uang Diterima (Rp)", min_value=float(total), step=1000.0, format="%f")
                        if cash_received >= total:
                            st.metric("Kembalian", f"Rp {cash_received - total:,.0f}"); proceed = True
                    else: proceed = True
                    st.write("---")
                    if st.button("Proses & Selesaikan Pesanan", type="primary", use_container_width=True, disabled=not proceed):
                        product_ids = products_df.set_index('name')['id'].to_dict()
                        for item, qty in st.session_state.cart.items():
                            record_sale(product_ids[item], qty, payment_method)
                        st.success(f"Pesanan berhasil diproses!"); st.session_state.cart = {}; st.balloons(); st.rerun()
                    if st.button("Kosongkan Keranjang", use_container_width=True):
                        st.session_state.cart = {}; st.rerun()

    elif menu == "📦 Manajemen Stok":
        st.title("📦 Manajemen Stok Bahan Baku")
        df = get_df("SELECT * FROM ingredients")
        
        # --- FITUR BARU: Notifikasi Stok Rendah ---
        st.subheader("⚠️ Peringatan Stok Rendah")
        low_stock_threshold = st.number_input("Batas Stok Rendah", min_value=1, value=50, step=10)
        low_stock_items = df[df['stock'] <= low_stock_threshold]
        
        if not low_stock_items.empty:
            st.warning(f"Bahan baku berikut berada di bawah batas stok ({low_stock_threshold}):")
            st.dataframe(low_stock_items[['name', 'stock', 'unit']], use_container_width=True)
        else:
            st.success("Semua stok bahan baku dalam kondisi aman.")
        st.write("---")

        st.subheader("Daftar Semua Bahan Baku")
        st.dataframe(df, use_container_width=True)
        st.subheader("Tambah / Edit Bahan Baku")
        selected_id = st.selectbox("Pilih bahan untuk diedit", [""] + df['id'].tolist())
        selected_item = df[df['id'] == selected_id].iloc[0] if selected_id else None
        with st.form("ingredient_form", clear_on_submit=True):
            name = st.text_input("Nama Bahan", value=selected_item['name'] if selected_item is not None else "")
            unit = st.text_input("Satuan", value=selected_item['unit'] if selected_item is not None else "")
            pack_price = st.number_input("Harga per Kemasan (Rp)", min_value=0.0, format="%.2f", value=selected_item['pack_price'] if selected_item is not None else 0.0)
            pack_weight = st.number_input("Berat/Isi per Kemasan", min_value=0.0, format="%.2f", value=selected_item['pack_weight'] if selected_item is not None else 0.0)
            cost_per_unit = (pack_price / pack_weight) if pack_weight > 0 else 0.0
            st.info(f"Harga per satuan: Rp {cost_per_unit:,.2f} / {unit}")
            stock = st.number_input("Stok Saat Ini", min_value=0.0, format="%.2f", value=selected_item['stock'] if selected_item is not None else 0.0)
            if st.form_submit_button("Simpan"):
                if selected_id:
                    update_ingredient(selected_id, name, unit, cost_per_unit, stock, pack_weight, pack_price); st.success("Bahan diperbarui!")
                else:
                    add_ingredient(name, unit, cost_per_unit, stock, pack_weight, pack_price); st.success("Bahan baru ditambahkan!")
                st.rerun()
        st.subheader("Hapus Bahan Baku")
        if not df.empty:
            del_id = st.selectbox("Pilih bahan untuk dihapus", df['id'].tolist(), key="del_ing_id")
            if st.button("Hapus Bahan Terpilih", type="primary"):
                delete_ingredient(del_id); st.warning("Bahan dihapus."); st.rerun()

    elif menu == "🍽️ Manajemen Produk":
        st.title("🍽️ Manajemen Produk & Resep")
        products_df = get_df("SELECT * FROM products")
        ingredients_df = get_df("SELECT id, name, unit FROM ingredients")
        
        st.subheader("Daftar Produk")
        st.dataframe(products_df, use_container_width=True)
        
        with st.expander("Tambah / Edit Produk"):
            selected_prod_id = st.selectbox("Pilih produk untuk diedit (kosongkan untuk menambah)", [""] + products_df['id'].tolist(), key="edit_prod")
            selected_product = products_df[products_df['id'] == selected_prod_id].iloc[0] if selected_prod_id else None
            with st.form("product_form"):
                prod_name = st.text_input("Nama Produk", value=selected_product['name'] if selected_product is not None else "")
                prod_price = st.number_input("Harga Jual (Rp)", min_value=0.0, format="%.2f", value=selected_product['price'] if selected_product is not None else 0.0)
                if st.form_submit_button("Simpan Produk"):
                    if selected_prod_id:
                        update_product(selected_prod_id, prod_name, prod_price); st.success("Produk diperbarui!")
                    else:
                        add_product(prod_name, prod_price); st.success("Produk baru ditambahkan!")
                    st.rerun()
        
        with st.expander("Hapus Produk"):
            if not products_df.empty:
                del_prod_id = st.selectbox("Pilih produk untuk dihapus", products_df['id'].tolist(), key="del_prod_id")
                if st.button("Hapus Produk Terpilih", type="primary"):
                    delete_product(del_prod_id); st.warning("Produk dihapus."); st.rerun()
        
        # --- PERBAIKAN UI: Memberi jarak pemisah ---
        st.write("---")
        st.subheader("Atur Resep")
        if not products_df.empty and not ingredients_df.empty:
            recipe_prod_id = st.selectbox("Pilih Produk untuk Mengatur Resep", products_df['id'], format_func=lambda x: products_df.loc[products_df['id'] == x, 'name'].iloc[0])
            search_ingredient = st.text_input("Cari Bahan Baku...", placeholder="Cari Bahan Baku...")
            filtered_ingredients = ingredients_df[ingredients_df['name'].str.contains(search_ingredient, case=False)] if search_ingredient else ingredients_df
            current_recipe_df = get_df("SELECT ingredient_id, qty_per_unit FROM recipes WHERE product_id=?", params=(recipe_prod_id,))
            current_recipe = dict(zip(current_recipe_df['ingredient_id'], current_recipe_df['qty_per_unit']))
            with st.form("recipe_form"):
                recipe_data = {}
                num_ing_cols = 2
                ing_cols = st.columns(num_ing_cols)
                for index, row in filtered_ingredients.iterrows():
                    with ing_cols[index % num_ing_cols]:
                        default_qty = current_recipe.get(row['id'], 0.0)
                        qty = st.number_input(f"{row['name']} ({row['unit']})", min_value=0.0, value=default_qty, step=0.1, format="%.2f", key=f"ing_{row['id']}")
                        recipe_data[row['id']] = qty
                if st.form_submit_button("Simpan Resep", use_container_width=True, type="primary"):
                    set_recipe(recipe_prod_id, recipe_data); st.success("Resep berhasil disimpan!"); st.rerun()
        else:
            st.warning("Tambahkan produk dan bahan baku dulu.")

    elif menu == "📈 Laporan":
        st.title("📈 Laporan Penjualan")
        sales_query = "SELECT s.id, s.date, p.name as product_name, s.qty, p.price, (s.qty * p.price) as total_revenue, s.payment_method FROM sales s JOIN products p ON s.product_id = p.id ORDER BY s.date DESC"
        sales_df = get_df(sales_query)
        st.subheader("Filter Laporan")
        col1, col2 = st.columns(2)
        with col1: start_date = st.date_input("Tanggal Mulai", value=date.today().replace(day=1))
        with col2: end_date = st.date_input("Tanggal Akhir", value=date.today())
        sales_df['date'] = pd.to_datetime(sales_df['date']).dt.date
        filtered_df = sales_df[(sales_df['date'] >= start_date) & (sales_df['date'] <= end_date)]
        st.subheader(f"Laporan dari {start_date.strftime('%d %B %Y')} sampai {end_date.strftime('%d %B %Y')}")
        if filtered_df.empty:
            st.info("Tidak ada data penjualan pada periode ini.")
        else:
            total_revenue = filtered_df['total_revenue'].sum()
            total_items_sold = filtered_df['qty'].sum()
            st.metric("Total Pendapatan", f"Rp {total_revenue:,.2f}")
            st.metric("Total Item Terjual", f"{total_items_sold} pcs")
            st.dataframe(filtered_df.style.format({'price': 'Rp {:,.2f}', 'total_revenue': 'Rp {:,.2f}'}), use_container_width=True)
            
            # --- FITUR BARU: Analisa Penjualan ---
            st.write("---")
            st.subheader("📊 Analisa Penjualan")
            
            col1, col2 = st.columns(2)
            with col1:
                best_seller_qty = filtered_df.groupby('product_name')['qty'].sum().idxmax()
                st.info(f"**Produk Terlaris (Qty):** {best_seller_qty}")
            with col2:
                best_seller_rev = filtered_df.groupby('product_name')['total_revenue'].sum().idxmax()
                st.info(f"**Produk Paling Untung:** {best_seller_rev}")

            # --- FITUR BARU: Saran Manajemen (Simulasi AI) ---
            st.write("---")
            st.subheader("💡 Saran Manajemen")
            if st.button("Dapatkan Saran"):
                with st.spinner("Menganalisa data..."):
                    least_seller_qty = filtered_df.groupby('product_name')['qty'].sum().idxmin()
                    payment_mode = filtered_df['payment_method'].mode()[0] if not filtered_df['payment_method'].empty else "Tidak ada"

                    st.success("Analisa Selesai!")
                    st.markdown(f"""
                    Berikut adalah beberapa saran berdasarkan data penjualan periode ini:
                    - **Fokus pada Pemenang**: Produk **{best_seller_qty}** dan **{best_seller_rev}** sangat populer. Pertimbangkan untuk membuat paket promo (bundling) yang melibatkan produk ini untuk meningkatkan nilai transaksi.
                    - **Evaluasi Produk Kurang Laku**: Produk **{least_seller_qty}** terjual paling sedikit. Coba evaluasi kembali resep, harga, atau lakukan promo khusus (misal: 'Beli 1 Gratis 1' di hari tertentu) untuk meningkatkan penjualannya.
                    - **Optimalkan Pembayaran**: Metode pembayaran favorit pelanggan adalah **{payment_mode}**. Pastikan metode ini selalu berjalan lancar. Jika banyak yang menggunakan Cash, pastikan uang kembalian selalu tersedia.
                    """)
            
            st.write("---")
            st.subheader("Kirim Ringkasan Laporan via WhatsApp")
            phone_number = st.text_input("Nomor WhatsApp Tujuan (format: 628xxxx)")
            if st.button("Buat Link Laporan WhatsApp"):
                if phone_number.isdigit() and len(phone_number) > 9:
                    report_string = f"*Ringkasan Laporan Penjualan*\nPeriode: {start_date.strftime('%d %b %Y')} - {end_date.strftime('%d %b %Y')}\n\n*Total Pendapatan:* Rp {total_revenue:,.0f}\n*Total Item Terjual:* {total_items_sold} pcs\n\nTerima kasih."
                    message = urllib.parse.quote(report_string)
                    link = f"https://wa.me/{phone_number}?text={message}"
                    st.markdown(f'<a href="{link}" target="_blank" style="background-color: #25D366; color: white; padding: 10px 20px; text-align: center; text-decoration: none; display: inline-block; border-radius: 5px;">Buka WhatsApp untuk Mengirim Laporan</a>', unsafe_allow_html=True)
                else:
                    st.error("Format nomor WhatsApp salah.")

    elif menu == "👨‍💼 Manajemen Karyawan":
        st.title("👨‍💼 Manajemen Data Karyawan")
        df_emp = get_df("SELECT id, name, wage_amount, wage_period FROM employees")
        st.dataframe(df_emp, use_container_width=True, column_config={"wage_amount": st.column_config.NumberColumn("Gaji (Rp)", format="Rp %d")})
        st.subheader("Tambah / Edit Karyawan")
        selected_emp_id = st.selectbox("Pilih karyawan untuk diedit", [""] + df_emp['id'].tolist())
        selected_employee = df_emp.loc[df_emp['id'] == selected_emp_id].iloc[0] if selected_emp_id else None
        with st.form("employee_form", clear_on_submit=True):
            emp_name = st.text_input("Nama Karyawan", value=selected_employee['name'] if selected_employee is not None else "")
            col1, col2 = st.columns(2)
            with col1: wage_amount = st.number_input("Jumlah Gaji (Rp)", min_value=0.0, format="%.2f", value=selected_employee['wage_amount'] if selected_employee is not None else 0.0)
            with col2:
                wage_periods = ["Per Jam", "Per Hari", "Per Minggu", "Per Bulan"]
                default_index = wage_periods.index(selected_employee['wage_period']) if selected_employee is not None and selected_employee['wage_period'] in wage_periods else 0
                wage_period = st.selectbox("Periode Gaji", wage_periods, index=default_index)
            if st.form_submit_button("Simpan Karyawan"):
                if selected_emp_id:
                    update_employee(selected_emp_id, emp_name, wage_amount, wage_period); st.success("Data karyawan diperbarui!")
                else:
                    add_employee(emp_name, wage_amount, wage_period); st.success("Karyawan baru ditambahkan!")
                st.rerun()

    elif menu == "🧾 Riwayat Absensi":
        st.title("🧾 Absensi Karyawan")
        employees_df = get_df("SELECT id, name FROM employees")
        if employees_df.empty:
            st.warning("Belum ada data karyawan.")
        else:
            emp_dict = employees_df.set_index('id')['name'].to_dict()
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Absen Masuk (Check-in)")
                emp_id_in = st.selectbox("Pilih Karyawan", options=list(emp_dict.keys()), format_func=lambda x: emp_dict[x])
                if st.button("Check-in Sekarang", use_container_width=True):
                    check_in(emp_id_in); st.success(f"{emp_dict[emp_id_in]} berhasil check-in!"); st.rerun()
            with col2:
                st.subheader("Absen Pulang (Check-out)")
                att_to_checkout = get_df("SELECT id, employee_id FROM attendance WHERE check_out IS NULL OR check_out = ''")
                if not att_to_checkout.empty:
                    att_to_checkout['emp_name'] = att_to_checkout['employee_id'].map(emp_dict)
                    att_id_out = st.selectbox("Pilih Karyawan untuk Check-out", options=att_to_checkout['id'], format_func=lambda x: att_to_checkout.loc[att_to_checkout['id']==x, 'emp_name'].iloc[0])
                    if st.button("Check-out Sekarang", use_container_width=True):
                        check_out(att_id_out); st.success("Berhasil check-out!"); st.rerun()
                else:
                    st.info("Tidak ada karyawan yang sedang bekerja.")
            st.subheader("Riwayat Absensi")
            df_att = get_df("SELECT a.id, e.name, a.check_in, a.check_out FROM attendance a JOIN employees e ON a.employee_id = e.id ORDER BY a.check_in DESC")
            st.dataframe(df_att, use_container_width=True)
            col1, col2 = st.columns(2)
            with col1:
                with st.expander("✏️ Edit Riwayat Absensi"):
                    if not df_att.empty:
                        edit_id = st.selectbox("Pilih ID Absensi untuk Diedit", df_att['id'].tolist(), key="edit_att_id")
                        selected_att = df_att[df_att['id'] == edit_id].iloc[0]
                        new_check_in = st.text_input("Waktu Check-in", value=selected_att['check_in'])
                        new_check_out = st.text_input("Waktu Check-out", value=selected_att['check_out'] or "")
                        if st.button("Simpan Perubahan"):
                            success, message = update_attendance(edit_id, new_check_in, new_check_out)
                            if success: st.success(message); st.rerun()
                            else: st.error(message)
            with col2:
                with st.expander("🗑️ Hapus Riwayat Absensi"):
                    if not df_att.empty:
                        del_id = st.selectbox("Pilih ID Absensi untuk Dihapus", df_att['id'].tolist(), key="del_att_id")
                        if st.button("Hapus Absensi Terpilih"):
                            delete_attendance(del_id); st.warning("Riwayat absensi dihapus!"); st.rerun()

    elif menu == "💰 HPP":
        st.header("Harga Pokok Penjualan (HPP) per Produk")
        prods_df = get_df("SELECT * FROM products")
        if not prods_df.empty:
            hpp_data = []
            for _, row in prods_df.iterrows():
                hpp = get_product_hpp(row['id'])
                profit = row['price'] - hpp
                hpp_data.append({"Nama Produk": row['name'], "Harga Jual": row['price'], "HPP (Modal Bahan)": hpp, "Profit Kotor": profit})
            df_hpp = pd.DataFrame(hpp_data)
            st.dataframe(df_hpp.style.format({'Harga Jual': 'Rp {:,.2f}', 'HPP (Modal Bahan)': 'Rp {:,.2f}', 'Profit Kotor': 'Rp {:,.2f}'}))
            st.download_button("📥 Download Data HPP", df_hpp.to_csv(index=False), "hpp_data.csv")

# =====================================================================
# --- TITIK MASUK APLIKASI ---
# =====================================================================
if __name__ == "__main__":
    check_login()
