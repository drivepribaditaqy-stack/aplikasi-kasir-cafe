import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import plotly.graph_objects as go
import os

# --- KONFIGURASI DAN INISIALISASI ---
DB = "pos.db"
st.set_page_config(layout="wide", page_title="Cafe POS App")

# =====================================================================
# --- FUNGSI UNTUK MENGISI DATA AWAL ---
# =====================================================================
def insert_initial_data(conn):
    """
    Fungsi ini akan memasukkan data awal dari database lama Anda
    ke dalam database baru jika database tersebut kosong.
    """
    c = conn.cursor()

    # Cek apakah tabel 'products' sudah ada isinya atau belum
    c.execute("SELECT COUNT(*) FROM products")
    count = c.fetchone()[0]
    
    # Jika kosong (count == 0), maka masukkan semua data awal
    if count == 0:
        st.info("Database kosong, mengisi dengan data awal...")
        
        try:
            # Data untuk tabel 'ingredients'
            ingredients_data = [
                (1, 'Trieste Blueberry', 'gr', 166.67, 1000, 1000, 166667),
                (2, 'Trieste Tiramisu', 'gr', 166.67, 1000, 1000, 166667),
                (3, 'Denali Hazelnut', 'gr', 130.0, 1000, 1000, 130000),
                (4, 'Denali Caramel', 'gr', 130.0, 1000, 1000, 130000),
                (5, 'Denali Salted Caramel', 'gr', 130.0, 1000, 1000, 130000),
                (6, 'Denali Blue Citrus', 'gr', 130.0, 1000, 1000, 130000),
                (7, 'ABC Squash Lychee', 'gr', 20.0, 1000, 1000, 20000),
                (8, 'ABC Squash Florida Orange', 'gr', 20.0, 1000, 1000, 20000),
                (9, 'Marjan Squash Mango', 'gr', 15.0, 1000, 1000, 15000),
                (10, 'Marjan Boudoin Grenadine', 'gr', 25.0, 1000, 1000, 25000),
                (11, 'Marjan Boudoin Moka', 'gr', 25.0, 1000, 1000, 25000),
                (12, 'Marjan Boudoin Vanilla', 'gr', 25.0, 1000, 1000, 25000),
                (13, 'Marjan Boudoin Lemon', 'gr', 25.0, 1000, 1000, 25000),
                (14, 'Marjan Boudoin Melon', 'gr', 25.0, 1000, 1000, 25000),
                (15, 'Marjan Boudoin Markisa', 'gr', 25.0, 1000, 1000, 25000),
                (16, 'Air Galon', 'ml', 0.3, 19000, 19000, 6000),
                (17, 'Kopoe Kopoe Gula Aren', 'gr', 50.0, 1000, 1000, 50000),
                (18, 'Marjan Squash Mangga', 'gr', 15.0, 1000, 1000, 15000),
                (19, 'Marjan Boudoin Strawberry', 'gr', 25.0, 1000, 1000, 25000),
                (20, 'Sprite Zero', 'gr', 10.0, 1000, 1000, 10000),
                (21, 'Creamer', 'gr', 80.0, 1000, 1000, 80000),
                (22, 'SKM', 'gr', 25.0, 1000, 1000, 25000),
                (23, 'UHT', 'gr', 20.0, 1000, 1000, 20000),
                (24, 'Coffee Beans Samara', 'gr', 100.0, 1000, 1000, 100000)
            ]
            c.executemany("INSERT OR IGNORE INTO ingredients (id, name, unit, cost_per_unit, stock, pack_weight, pack_price) VALUES (?, ?, ?, ?, ?, ?, ?)", ingredients_data)

            # Data untuk tabel 'products'
            products_data = [
                (1, 'Espresso', 10000), (2, 'Americano', 12000), (3, 'Lemon Americano', 15000),
                (4, 'Orange Americano', 15000), (5, 'Cococof (BN Signature)', 20000), (6, 'Coffee Latte', 18000),
                (7, 'Cappucino', 18000), (8, 'Spanish Latte', 20000), (9, 'Caramel Latte', 20000),
                (10, 'VanillaLatte', 20000), (11, 'Hazelnut Latte', 20000), (12, 'Butterscotch Latte', 22000),
                (13, 'Tiramissu Latte', 20000), (14, 'Mocca Latte', 20000), (15, 'Coffee Chocolate', 22000),
                (16, 'Taro Coffee Latte', 22000), (17, 'Coffee Gula Aren', 22000), (18, 'Lychee Coffe', 20000),
                (19, 'Markisa Coffee', 20000), (20, 'Raspberry Latte', 20000), (21, 'Strawberry Latte', 20000),
                (22, 'Manggo Latte', 20000), (23, 'Bubblegum Latte', 20000), (24, 'Lemon Tea', 10000),
                (25, 'Lychee Tea', 12000), (26, 'Milk Tea', 15000), (27, 'Green Tea', 15000),
                (28, 'Thai Tea', 15000), (29, 'Melon Susu', 15000), (30, 'Manggo Susu', 18000),
                (31, 'Mocca Susu', 18000), (32, 'Orange Susu', 18000), (33, 'Taro Susu', 18000),
                (34, 'Coklat Susu', 18000), (35, 'Vanilla Susu', 18000), (36, 'Strawberry Susu', 18000),
                (37, 'Matcha Susu', 20000), (38, 'Blueberry Susu', 20000), (39, 'Bubblegum Susu', 20000),
                (40, 'Raspberry Susu', 20000), (41, 'Grenadine Susu', 20000), (42, 'Banana Susu', 20000),
                (43, 'Melon Soda', 12000), (44, 'Manggo Soda', 15000), (45, 'Orange Soda', 15000),
                (46, 'Strawberry Soda', 15000), (47, 'Bluesky Soda', 15000), (48, 'Banana Soda', 20000),
                (49, 'Grenadine Soda', 15000), (50, 'Blueberry Soda', 20000), (51, 'Coffee Bear', 20000),
                (52, 'Mocca Soda', 20000), (53, 'Raspberry Soda', 20000), (54, 'Coffe Soda', 15000),
                (55, 'Strawberry Coffe Soda', 20000), (56, 'Melon Bluesky', 20000), (57, 'Blue Manggo Soda', 22000),
                (58, 'Double Shoot ADD On', 5000), (59, 'Yakult ADD On', 3000), (60, 'Mineral Water', 5000),
                (61, 'Mineral Water Gelas', 1000)
            ]
            c.executemany("INSERT OR IGNORE INTO products (id, name, price) VALUES (?, ?, ?)", products_data)

            # Data untuk tabel 'employees'
            employees_data = [(1, 'Taza', 10000)]
            c.executemany("INSERT OR IGNORE INTO employees (id, name, hourly_wage) VALUES (?, ?, ?)", employees_data)
            
            # Data untuk tabel 'operational_costs'
            operational_costs_data = [(1, 'Listrik', 500000, '2025-08-24')]
            c.executemany("INSERT OR IGNORE INTO operational_costs (id, description, amount, date) VALUES (?, ?, ?, ?)", operational_costs_data)

            # Data untuk tabel 'other_expenses'
            other_expenses_data = [(1, 'Jajan Bakso', 18000, '2025-08-24')]
            c.executemany("INSERT OR IGNORE INTO other_expenses (id, description, amount, date) VALUES (?, ?, ?, ?)", other_expenses_data)
            
            # Data untuk tabel 'attendance'
            attendance_data = [
                (1, 1, '2025-08-24 05:59:58', None), (2, 1, '2025-08-24 06:00:21', None),
                (3, 1, '2025-08-24 06:03:00', None), (4, 1, '2025-08-24 06:03:07', None),
                (5, 1, '2025-08-24 06:19:06', None), (6, 1, '2025-08-24 06:19:20', None),
                (7, 1, '2025-08-24 19:06:27', None), (8, 1, '2025-08-24 19:09:25', None),
                (9, 1, '2025-08-24 19:09:56', None), (10, 1, '2025-08-24 19:10:00', None),
                (11, 1, '2025-08-24 19:10:04', None),
                (12, 1, '2025-08-24 19:02:36', '2025-08-25 01:02:45'),
                (13, 1, '2025-08-24 06:32:44', '2025-08-24 06:32:47'),
                (14, 1, '2025-08-24 06:45:23', '2025-08-24 06:45:30'),
                (15, 1, '2025-08-24 19:21:00', '2025-08-24 22:21:00')
            ]
            c.executemany("INSERT OR IGNORE INTO attendance (id, employee_id, check_in, check_out) VALUES (?, ?, ?, ?)", attendance_data)

            conn.commit()
            st.success("Data awal berhasil dimuat ke database.")
            st.rerun()
            
        except sqlite3.Error as e:
            st.error(f"Terjadi error saat memasukkan data awal: {e}")

# =====================================================================
# --- BAGIAN LOGIN ---
# =====================================================================

def check_login():
    """
    Menampilkan form login dan menjalankan aplikasi utama jika login berhasil.
    """
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if st.session_state.logged_in:
        st.sidebar.success(f"Welcome, {st.session_state.username}!")
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()
        run_main_app()
    else:
        st.title("🔐 Login - Aplikasi Kasir Cafe")
        st.write("---")
        VALID_USERNAME = "admin"
        VALID_PASSWORD = "123"
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            if submitted:
                if username == VALID_USERNAME and password == VALID_PASSWORD:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Username atau password salah!")

# =====================================================================
# --- APLIKASI UTAMA ---
# =====================================================================

def run_main_app():
    def init_db():
        """
        Membuat tabel jika belum ada dan memanggil fungsi untuk mengisi data awal.
        """
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
        c.execute("CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, qty INTEGER, date TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS other_expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, description TEXT, amount REAL, date TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS operational_costs (id INTEGER PRIMARY KEY AUTOINCREMENT, description TEXT, amount REAL, date TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS employees (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, hourly_wage REAL)")
        c.execute("""CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER, check_in TEXT, check_out TEXT
        )""")
        conn.commit()
        
        # Panggil fungsi untuk mengisi data awal
        insert_initial_data(conn)
        
        conn.close()

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

    # --- (Sisa kode Anda dari sini ke bawah tetap sama persis) ---
    # --- FUNGSI-FUNGSI MANAJEMEN DATA ---
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

    def record_sale(product_id, qty):
        today = date.today().strftime("%Y-%m-%d")
        run_query("INSERT INTO sales (product_id, qty, date) VALUES (?, ?, ?)", (product_id, qty, today))
        
        recipe_df = get_df("SELECT ingredient_id, qty_per_unit FROM recipes WHERE product_id=?", params=(product_id,))
        for _, row in recipe_df.iterrows():
            run_query("UPDATE ingredients SET stock = stock - ? WHERE id=?", (row['qty_per_unit'] * qty, row['ingredient_id']))

    def add_employee(name, wage):
        run_query("INSERT INTO employees (name, hourly_wage) VALUES (?, ?)", (name, wage))

    def update_employee(id, name, wage):
        run_query("UPDATE employees SET name=?, hourly_wage=? WHERE id=?", (name, wage, id))

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
            datetime.strptime(check_in_str, '%Y-%m-%d %H:%M:%S')
            if check_out_str:
                datetime.strptime(check_out_str, '%Y-%m-%d %H:%M:%S')
            run_query("UPDATE attendance SET check_in=?, check_out=? WHERE id=?", (check_in_str, check_out_str, att_id))
            return True, "Data absensi berhasil diperbarui."
        except ValueError:
            return False, "Format tanggal atau waktu salah. Gunakan format: YYYY-MM-DD HH:MM:SS"

    def delete_attendance(att_id):
        run_query("DELETE FROM attendance WHERE id=?", (att_id,))

    def get_product_hpp(product_id):
        query = """
        SELECT SUM(r.qty_per_unit * i.cost_per_unit) as total_hpp
        FROM recipes r
        JOIN ingredients i ON r.ingredient_id = i.id
        WHERE r.product_id = ?
        """
        df = get_df(query, params=(product_id,))
        return df['total_hpp'].iloc[0] if not df.empty and pd.notna(df['total_hpp'].iloc[0]) else 0

    # --- UI SIDEBAR ---
    st.sidebar.title("MENU NAVIGASI")
    menu_options = ["🏠 Kasir", "📦 Manajemen Stok", "🍽️ Manajemen Produk", "📈 Laporan", "👨‍💼 Manajemen Karyawan", "🧾 Riwayat Absensi", "💰 HPP"]
    menu = st.sidebar.radio("Pilih Halaman:", menu_options)

    # --- HALAMAN KASIR ---
    if menu == "🏠 Kasir":
        st.title("🏠 Aplikasi Kasir Sederhana")
        products_df = get_df("SELECT id, name, price FROM products")
        
        if products_df.empty:
            st.warning("Belum ada produk yang ditambahkan. Silakan tambahkan produk di halaman 'Manajemen Produk'.")
        else:
            product_prices = products_df.set_index('name')['price'].to_dict()
            product_ids = products_df.set_index('name')['id'].to_dict()
            
            if 'cart' not in st.session_state:
                st.session_state.cart = {}

            col1, col2 = st.columns([2,1])
            with col1:
                st.subheader("Pilih Produk")
                product_name = st.selectbox("Produk", options=list(product_prices.keys()))
                quantity = st.number_input("Jumlah", min_value=1, value=1, step=1)
                
                if st.button("Tambahkan ke Keranjang", use_container_width=True):
                    if product_name in st.session_state.cart:
                        st.session_state.cart[product_name] += quantity
                    else:
                        st.session_state.cart[product_name] = quantity
                    st.success(f"{quantity} x {product_name} ditambahkan ke keranjang.")

            with col2:
                st.subheader("🛒 Keranjang Belanja")
                if not st.session_state.cart:
                    st.info("Keranjang masih kosong.")
                else:
                    total = 0
                    for item, qty in st.session_state.cart.items():
                        price = product_prices[item]
                        total += price * qty
                        st.write(f"- {item} (x{qty}): Rp {price * qty:,.2f}")
                    st.write("---")
                    st.metric("Total Belanja", f"Rp {total:,.2f}")

                    if st.button("Proses Pesanan", type="primary", use_container_width=True):
                        for item, qty in st.session_state.cart.items():
                            record_sale(product_ids[item], qty)
                        st.success("Pesanan berhasil diproses! Stok bahan telah diperbarui.")
                        st.session_state.cart = {}
                        st.balloons()
                        st.rerun()

                    if st.button("Kosongkan Keranjang", use_container_width=True):
                        st.session_state.cart = {}
                        st.rerun()

    # --- (Sisa UI Anda juga tetap sama) ---
    elif menu == "📦 Manajemen Stok":
        st.title("📦 Manajemen Stok Bahan Baku")
        df = get_df("SELECT * FROM ingredients")
        st.dataframe(df, use_container_width=True)

        st.subheader("Tambah / Edit Bahan Baku")
        selected_id = st.selectbox("Pilih bahan untuk diedit (kosongkan untuk menambah baru)", [""] + df['id'].tolist())
        
        selected_item = df[df['id'] == selected_id].iloc[0] if selected_id else None

        with st.form("ingredient_form", clear_on_submit=True):
            name = st.text_input("Nama Bahan", value=selected_item['name'] if selected_item is not None else "")
            unit = st.text_input("Satuan (e.g., gr, ml, pcs)", value=selected_item['unit'] if selected_item is not None else "")
            pack_price = st.number_input("Harga per Kemasan/Beli (Rp)", min_value=0.0, format="%.2f", value=selected_item['pack_price'] if selected_item is not None else 0.0)
            pack_weight = st.number_input("Berat/Isi per Kemasan (dalam satuan di atas)", min_value=0.0, format="%.2f", value=selected_item['pack_weight'] if selected_item is not None else 0.0)
            
            cost_per_unit = (pack_price / pack_weight) if pack_weight > 0 else 0.0
            st.info(f"Harga per satuan: Rp {cost_per_unit:,.2f} / {unit}")

            stock = st.number_input("Stok Saat Ini (dalam satuan)", min_value=0.0, format="%.2f", value=selected_item['stock'] if selected_item is not None else 0.0)
            
            submitted = st.form_submit_button("Simpan")
            if submitted:
                if selected_id:
                    update_ingredient(selected_id, name, unit, cost_per_unit, stock, pack_weight, pack_price)
                    st.success("Bahan berhasil diperbarui!")
                else:
                    add_ingredient(name, unit, cost_per_unit, stock, pack_weight, pack_price)
                    st.success("Bahan baru berhasil ditambahkan!")
                st.rerun()

        st.subheader("Hapus Bahan Baku")
        if not df.empty:
            del_id = st.selectbox("Pilih bahan untuk dihapus", df['id'].tolist(), key="del_ing_id")
            if st.button("Hapus Bahan Terpilih", type="primary"):
                delete_ingredient(del_id)
                st.warning("Bahan telah dihapus.")
                st.rerun()

    elif menu == "🍽️ Manajemen Produk":
        st.title("🍽️ Manajemen Produk & Resep")
        products_df = get_df("SELECT * FROM products")
        ingredients_df = get_df("SELECT id, name, unit FROM ingredients")

        st.dataframe(products_df, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Tambah / Edit Produk")
            selected_prod_id = st.selectbox("Pilih produk untuk diedit (kosongkan untuk menambah baru)", [""] + products_df['id'].tolist())
            selected_product = products_df[products_df['id'] == selected_prod_id].iloc[0] if selected_prod_id else None
            
            with st.form("product_form"):
                prod_name = st.text_input("Nama Produk", value=selected_product['name'] if selected_product is not None else "")
                prod_price = st.number_input("Harga Jual (Rp)", min_value=0.0, format="%.2f", value=selected_product['price'] if selected_product is not None else 0.0)
                
                submitted = st.form_submit_button("Simpan Produk")
                if submitted:
                    if selected_prod_id:
                        update_product(selected_prod_id, prod_name, prod_price)
                        st.success("Produk berhasil diperbarui!")
                    else:
                        add_product(prod_name, prod_price)
                        st.success("Produk baru berhasil ditambahkan!")
                    st.rerun()

            st.subheader("Hapus Produk")
            if not products_df.empty:
                del_prod_id = st.selectbox("Pilih produk untuk dihapus", products_df['id'].tolist(), key="del_prod_id")
                if st.button("Hapus Produk Terpilih", type="primary"):
                    delete_product(del_prod_id)
                    st.warning("Produk telah dihapus.")
                    st.rerun()

        with col2:
            st.subheader("Atur Resep")
            if not products_df.empty and not ingredients_df.empty:
                recipe_prod_id = st.selectbox("Pilih Produk untuk Mengatur Resep", products_df['id'].tolist(), format_func=lambda x: products_df[products_df['id']==x]['name'].iloc[0])
                
                current_recipe_df = get_df("SELECT ingredient_id, qty_per_unit FROM recipes WHERE product_id=?", params=(recipe_prod_id,))
                current_recipe = current_recipe_df.set_index('ingredient_id')['qty_per_unit'].to_dict()

                with st.form("recipe_form"):
                    st.write(f"Resep untuk: **{products_df[products_df['id']==recipe_prod_id]['name'].iloc[0]}**")
                    recipe_data = {}
                    for _, row in ingredients_df.iterrows():
                        default_qty = current_recipe.get(row['id'], 0.0)
                        qty = st.number_input(f"Jumlah {row['name']} ({row['unit']})", min_value=0.0, format="%.3f", value=default_qty, key=f"ing_{row['id']}")
                        recipe_data[row['id']] = qty
                    
                    submitted_recipe = st.form_submit_button("Simpan Resep")
                    if submitted_recipe:
                        set_recipe(recipe_prod_id, recipe_data)
                        st.success("Resep berhasil disimpan!")
                        st.rerun()
            else:
                st.warning("Tambahkan produk dan bahan baku terlebih dahulu untuk bisa mengatur resep.")

    elif menu == "📈 Laporan":
        st.title("📈 Laporan Penjualan")
        
        sales_query = """
        SELECT s.id, s.date, p.name as product_name, s.qty, p.price, (s.qty * p.price) as total_revenue
        FROM sales s
        JOIN products p ON s.product_id = p.id
        ORDER BY s.date DESC
        """
        sales_df = get_df(sales_query)
        
        st.subheader("Filter Laporan")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Tanggal Mulai", value=date.today().replace(day=1))
        with col2:
            end_date = st.date_input("Tanggal Akhir", value=date.today())

        sales_df['date'] = pd.to_datetime(sales_df['date']).dt.date
        filtered_df = sales_df[(sales_df['date'] >= start_date) & (sales_df['date'] <= end_date)]

        st.subheader(f"Laporan dari {start_date.strftime('%d %B %Y')} sampai {end_date.strftime('%d %B %Y')}")
        
        if filtered_df.empty:
            st.info("Tidak ada data penjualan pada rentang tanggal yang dipilih.")
        else:
            total_revenue = filtered_df['total_revenue'].sum()
            total_items_sold = filtered_df['qty'].sum()
            
            st.metric("Total Pendapatan", f"Rp {total_revenue:,.2f}")
            st.metric("Total Item Terjual", f"{total_items_sold} pcs")
            
            st.dataframe(filtered_df.style.format({'price': 'Rp {:,.2f}', 'total_revenue': 'Rp {:,.2f}'}), use_container_width=True)

            st.subheader("Visualisasi Data")
            
            sales_by_product = filtered_df.groupby('product_name')['total_revenue'].sum().sort_values(ascending=False)
            fig_prod = go.Figure(data=[go.Bar(x=sales_by_product.index, y=sales_by_product.values)])
            fig_prod.update_layout(title_text='Pendapatan per Produk', xaxis_title='Produk', yaxis_title='Total Pendapatan (Rp)')
            st.plotly_chart(fig_prod, use_container_width=True)
            
            sales_by_date = filtered_df.groupby('date')['total_revenue'].sum()
            fig_date = go.Figure(data=[go.Scatter(x=sales_by_date.index, y=sales_by_date.values, mode='lines+markers')])
            fig_date.update_layout(title_text='Tren Pendapatan Harian', xaxis_title='Tanggal', yaxis_title='Total Pendapatan (Rp)')
            st.plotly_chart(fig_date, use_container_width=True)

    elif menu == "👨‍💼 Manajemen Karyawan":
        st.title("👨‍💼 Manajemen Data Karyawan")
        df_emp = get_df("SELECT * FROM employees")
        st.dataframe(df_emp.style.format({'hourly_wage': 'Rp {:,.2f}/jam'}), use_container_width=True)

        st.subheader("Tambah / Edit Karyawan")
        selected_emp_id = st.selectbox("Pilih karyawan untuk diedit (kosongkan untuk menambah baru)", [""] + df_emp['id'].tolist())
        selected_employee = df_emp[df_emp['id'] == selected_emp_id].iloc[0] if selected_emp_id else None

        with st.form("employee_form", clear_on_submit=True):
            emp_name = st.text_input("Nama Karyawan", value=selected_employee['name'] if selected_employee is not None else "")
            emp_wage = st.number_input("Upah per Jam (Rp)", min_value=0.0, format="%.2f", value=selected_employee['hourly_wage'] if selected_employee is not None else 0.0)
            
            submitted = st.form_submit_button("Simpan Karyawan")
            if submitted:
                if selected_emp_id:
                    update_employee(selected_emp_id, emp_name, emp_wage)
                    st.success("Data karyawan berhasil diperbarui!")
                else:
                    add_employee(emp_name, emp_wage)
                    st.success("Karyawan baru berhasil ditambahkan!")
                st.rerun()

        st.subheader("Hapus Karyawan")
        if not df_emp.empty:
            del_emp_id = st.selectbox("Pilih karyawan untuk dihapus", df_emp['id'].tolist(), key="del_emp_id")
            if st.button("Hapus Karyawan Terpilih", type="primary"):
                delete_employee(del_emp_id)
                st.warning("Data karyawan telah dihapus.")
                st.rerun()

    elif menu == "🧾 Riwayat Absensi":
        st.title("🧾 Absensi Karyawan")
        
        employees_df = get_df("SELECT id, name FROM employees")
        if employees_df.empty:
            st.warning("Belum ada data karyawan. Silakan tambahkan di halaman 'Manajemen Karyawan'.")
        else:
            emp_dict = employees_df.set_index('id')['name'].to_dict()
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Absen Masuk (Check-in)")
                emp_id_in = st.selectbox("Pilih Karyawan", options=list(emp_dict.keys()), format_func=lambda x: emp_dict[x])
                if st.button("Check-in Sekarang", use_container_width=True):
                    check_in(emp_id_in)
                    st.success(f"{emp_dict[emp_id_in]} berhasil check-in!")
                    st.rerun()

            with col2:
                st.subheader("Absen Pulang (Check-out)")
                att_to_checkout = get_df("SELECT id, employee_id FROM attendance WHERE check_out IS NULL OR check_out = ''")
                if not att_to_checkout.empty:
                    att_to_checkout['emp_name'] = att_to_checkout['employee_id'].map(emp_dict)
                    att_id_out = st.selectbox("Pilih Karyawan untuk Check-out", options=att_to_checkout['id'].tolist(), format_func=lambda x: att_to_checkout[att_to_checkout['id']==x]['emp_name'].iloc[0])
                    if st.button("Check-out Sekarang", use_container_width=True):
                        check_out(att_id_out)
                        st.success("Berhasil check-out!")
                        st.rerun()
                else:
                    st.info("Tidak ada karyawan yang sedang bekerja.")

            st.subheader("Riwayat Absensi")
            query_att = """
            SELECT a.id, e.name, a.check_in, a.check_out
            FROM attendance a
            JOIN employees e ON a.employee_id = e.id
            ORDER BY a.check_in DESC
            """
            df_att = get_df(query_att)
            st.dataframe(df_att, use_container_width=True)

            col1, col2 = st.columns(2)
            with col1:
                with st.expander("✏️ Edit Riwayat Absensi"):
                    if not df_att.empty:
                        edit_id = st.selectbox("Pilih ID Absensi untuk Diedit", df_att['id'].tolist(), key="edit_att_id")
                        selected_att = df_att[df_att['id'] == edit_id].iloc[0]
                        
                        new_check_in = st.text_input("Waktu Check-in", value=selected_att['check_in'])
                        new_check_out = st.text_input("Waktu Check-out", value=selected_att['check_out'] if selected_att['check_out'] else "")

                        if st.button("Simpan Perubahan"):
                            success, message = update_attendance(edit_id, new_check_in, new_check_out)
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)

            with col2:
                with st.expander("🗑️ Hapus Riwayat Absensi"):
                    if not df_att.empty:
                        del_id = st.selectbox("Pilih ID Absensi untuk Dihapus", df_att['id'].tolist(), key="del_att_id")
                        if st.button("Hapus Absensi Terpilih"):
                            delete_attendance(del_id)
                            st.warning("Riwayat absensi dihapus!")
                            st.rerun()

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
