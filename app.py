import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import plotly.graph_objects as go
import urllib.parse
import bcrypt
from fpdf import FPDF

# --- KONFIGURASI DAN INISIALISASI ---
DB = "pos.db"
st.set_page_config(layout="wide", page_title="Cafe POS App")

# =====================================================================
# --- FUNGSI MIGRASI & INISIALISASI DATABASE ---
# =====================================================================
def update_db_schema(conn):
    """Memeriksa dan memperbarui skema database jika diperlukan."""
    c = conn.cursor()
    
    # Tabel Karyawan: Tambah kolom password, role, is_active
    c.execute("PRAGMA table_info(employees)")
    columns = [info[1] for info in c.fetchall()]
    if 'password' not in columns: c.execute("ALTER TABLE employees ADD COLUMN password TEXT")
    if 'role' not in columns: c.execute("ALTER TABLE employees ADD COLUMN role TEXT")
    if 'is_active' not in columns: c.execute("ALTER TABLE employees ADD COLUMN is_active BOOLEAN DEFAULT 1")
    
    # Migrasi dari hourly_wage ke wage_amount & wage_period
    if 'hourly_wage' in columns:
         c.execute("ALTER TABLE employees RENAME TO employees_old")
         c.execute("""CREATE TABLE employees (
             id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, wage_amount REAL, 
             wage_period TEXT, password TEXT, role TEXT, is_active BOOLEAN DEFAULT 1
         )""")
         c.execute("""INSERT INTO employees (id, name, wage_amount, wage_period, is_active) 
                      SELECT id, name, hourly_wage, 'Per Jam', 1 FROM employees_old""")
         c.execute("DROP TABLE employees_old")
         st.toast("Skema database karyawan telah diperbarui.")

    conn.commit()

def insert_initial_data(conn):
    """Membuat akun default jika belum ada."""
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM employees WHERE name = 'admin'")
    if c.fetchone()[0] == 0:
        st.info("Akun admin tidak ditemukan, membuat akun default...")
        initial_users = [
            ('admin', bcrypt.hashpw('admin'.encode('utf8'), bcrypt.gensalt()), 'Admin', 0, 'Per Bulan', 1),
            ('manager', bcrypt.hashpw('manager'.encode('utf8'), bcrypt.gensalt()), 'Manager', 0, 'Per Bulan', 1),
            ('operator', bcrypt.hashpw('operator'.encode('utf8'), bcrypt.gensalt()), 'Operator', 0, 'Per Jam', 1)
        ]
        c.executemany("INSERT INTO employees (name, password, role, wage_amount, wage_period, is_active) VALUES (?, ?, ?, ?, ?, ?)", initial_users)
        conn.commit()
        st.success("Akun awal (admin/admin, dll.) berhasil dibuat.")
        st.rerun()

def init_db():
    """Inisialisasi koneksi dan struktur database."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Tabel Utama
    c.execute("""CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, wage_amount REAL, 
        wage_period TEXT, password TEXT, role TEXT, is_active BOOLEAN DEFAULT 1
    )""")
    update_db_schema(conn)
    c.execute("""CREATE TABLE IF NOT EXISTS ingredients (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, unit TEXT,
        cost_per_unit REAL, stock REAL, pack_weight REAL DEFAULT 0.0, pack_price REAL DEFAULT 0.0
    )""")
    c.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, price REAL)")
    c.execute("""CREATE TABLE IF NOT EXISTS recipes (
        product_id INTEGER, ingredient_id INTEGER, qty_per_unit REAL, PRIMARY KEY (product_id, ingredient_id)
    )""")
    
    # Tabel Transaksi Baru
    c.execute("""CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, transaction_date TEXT, total_amount REAL, 
        payment_method TEXT, employee_id INTEGER
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS transaction_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, transaction_id INTEGER, product_id INTEGER, 
        quantity INTEGER, price_per_unit REAL
    )""")

    # Tabel Pengeluaran
    c.execute("""CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        date TEXT, 
        category TEXT, 
        description TEXT, 
        amount REAL, 
        payment_method TEXT
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER, check_in TEXT, check_out TEXT
    )""")
    
    conn.commit()
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
            for key in st.session_state.keys(): del st.session_state[key]
            st.rerun()
        run_main_app()
    else:
        st.title("🔐 Login - Aplikasi Kasir Cafe")
        with st.form("login_form"):
            username = st.text_input("Username").lower()
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                conn = sqlite3.connect(DB)
                c = conn.cursor()
                c.execute("SELECT id, password, role FROM employees WHERE name = ? AND is_active = 1", (username,))
                user_data = c.fetchone()
                conn.close()
                
                if user_data and user_data[1] is not None:
                    user_id, hashed_password_from_db, role = user_data
                    if bcrypt.checkpw(password.encode('utf8'), hashed_password_from_db):
                        st.session_state.logged_in = True
                        st.session_state.user_id = user_id
                        st.session_state.username = username
                        st.session_state.role = role
                        st.rerun()
                    else: st.error("Password salah!")
                else: st.error("Username tidak ditemukan atau akun tidak aktif!")

# =====================================================================
# --- APLIKASI UTAMA ---
# =====================================================================
def run_main_app():
    def run_query(query, params=(), fetch=None):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute(query, params)
        if fetch == 'one': result = c.fetchone()
        elif fetch == 'all': result = c.fetchall()
        else: result = None
        last_id = c.lastrowid
        conn.commit()
        conn.close()
        return (result, last_id) if fetch is None else result

    def get_df(query, params=()):
        conn = sqlite3.connect(DB)
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df

    def process_atomic_sale(cart, payment_method, employee_id):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        try:
            c.execute("BEGIN TRANSACTION")
            insufficient_items = []
            products_map = {row['name']: {'id': row['id'], 'price': row['price']} for _, row in get_df("SELECT id, name, price FROM products").iterrows()}
            
            for product_name, qty in cart.items():
                product_id = products_map[product_name]['id']
                c.execute("SELECT i.name, i.stock, r.qty_per_unit FROM recipes r JOIN ingredients i ON r.ingredient_id = i.id WHERE r.product_id=?", (product_id,))
                for ing_name, stock, qty_per_unit in c.fetchall():
                    if stock < qty_per_unit * qty:
                        insufficient_items.append(f"{ing_name} untuk {product_name}")
            
            if insufficient_items:
                raise ValueError(f"Stok tidak cukup: {', '.join(insufficient_items)}")

            total_amount = sum(products_map[name]['price'] * qty for name, qty in cart.items())
            c.execute("INSERT INTO transactions (transaction_date, total_amount, payment_method, employee_id) VALUES (?, ?, ?, ?)",
                      (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), total_amount, payment_method, employee_id))
            transaction_id = c.lastrowid

            for product_name, qty in cart.items():
                product_info = products_map[product_name]
                c.execute("INSERT INTO transaction_items (transaction_id, product_id, quantity, price_per_unit) VALUES (?, ?, ?, ?)",
                          (transaction_id, product_info['id'], qty, product_info['price']))
                c.execute("SELECT ingredient_id, qty_per_unit FROM recipes WHERE product_id=?", (product_info['id'],))
                for ing_id, qty_per_unit in c.fetchall():
                    c.execute("UPDATE ingredients SET stock = stock - ? WHERE id=?", (qty_per_unit * qty, ing_id))
            
            conn.commit()
            return True, "Pesanan berhasil diproses!", transaction_id
        except Exception as e:
            conn.rollback()
            return False, str(e), None
        finally:
            conn.close()

    def generate_receipt_pdf(transaction_id):
        transaction = run_query("SELECT * FROM transactions WHERE id = ?", (transaction_id,), fetch='one')
        items_df = get_df("""
            SELECT p.name, ti.quantity, ti.price_per_unit
            FROM transaction_items ti JOIN products p ON ti.product_id = p.id
            WHERE ti.transaction_id = ?
        """, (transaction_id,))

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, 'Struk Pembayaran', 0, 1, 'C')
        pdf.set_font("Arial", '', 12)
        pdf.cell(0, 10, f"No. Transaksi: {transaction[0]}", 0, 1)
        pdf.cell(0, 10, f"Tanggal: {transaction[1]}", 0, 1)
        pdf.ln(10)

        pdf.set_font("Arial", 'B', 12)
        pdf.cell(100, 10, 'Produk', 1)
        pdf.cell(30, 10, 'Qty', 1)
        pdf.cell(50, 10, 'Subtotal', 1, 1)

        pdf.set_font("Arial", '', 12)
        for _, item in items_df.iterrows():
            pdf.cell(100, 10, item['name'], 1)
            pdf.cell(30, 10, str(item['quantity']), 1)
            pdf.cell(50, 10, f"Rp {item['quantity'] * item['price_per_unit']:,.0f}", 1, 1)
        
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(130, 10, 'Total', 1)
        pdf.cell(50, 10, f"Rp {transaction[2]:,.0f}", 1, 1)
        pdf.cell(130, 10, 'Metode Bayar', 1)
        pdf.cell(50, 10, transaction[3], 1, 1)

        # PERBAIKAN: Mengembalikan byte langsung
        return bytes(pdf.output())

    def add_employee(name, wage_amount, wage_period, password, role):
        hashed_pw = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())
        run_query("INSERT INTO employees (name, wage_amount, wage_period, password, role, is_active) VALUES (?, ?, ?, ?, ?, 1)", (name, wage_amount, wage_period, hashed_pw, role))
    def update_employee(id, name, wage_amount, wage_period, role):
        run_query("UPDATE employees SET name=?, wage_amount=?, wage_period=?, role=? WHERE id=?", (name, wage_amount, wage_period, role, id))
    def set_employee_active_status(id, is_active):
        run_query("UPDATE employees SET is_active=? WHERE id=?", (is_active, id))
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
            if qty > 0: run_query("INSERT INTO recipes (product_id, ingredient_id, qty_per_unit) VALUES (?, ?, ?)", (product_id, ing_id, qty))
    def check_in(employee_id):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S"); run_query("INSERT INTO attendance (employee_id, check_in) VALUES (?, ?)", (employee_id, now))
    def check_out(attendance_id):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S"); run_query("UPDATE attendance SET check_out=? WHERE id=?", (now, attendance_id))
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
    def add_expense(date, category, description, amount, payment_method):
        run_query("INSERT INTO expenses (date, category, description, amount, payment_method) VALUES (?, ?, ?, ?, ?)", (date, category, description, amount, payment_method))
    def update_expense(id, date, category, description, amount, payment_method):
        run_query("UPDATE expenses SET date=?, category=?, description=?, amount=?, payment_method=? WHERE id=?", (date, category, description, amount, payment_method, id))
    def delete_expense(id):
        run_query("DELETE FROM expenses WHERE id=?", (id,))

    st.sidebar.title("MENU NAVIGASI")
    user_role = st.session_state.get("role", "Operator")
    menu_options = ["🏠 Kasir", "📦 Manajemen Stok", "🍽️ Manajemen Produk", "📈 Laporan", "🧾 Riwayat Transaksi", "💸 Pengeluaran", "💰 HPP"]
    if user_role in ["Admin", "Manager"]:
        menu_options.extend(["👨‍💼 Manajemen Karyawan", "⏰ Riwayat Absensi"])
    menu = st.sidebar.radio("Pilih Halaman:", menu_options)

    if menu == "🏠 Kasir":
        st.title("🏠 Aplikasi Kasir")
        st.markdown("""<style>.product-card { border: 1px solid #ddd; border-radius: 10px; padding: 10px; text-align: center; margin-bottom: 10px; background-color: #f9f9f9; display: flex; flex-direction: column; justify-content: space-between; height: 130px; } .product-card .product-name { font-size: 14px; font-weight: bold; flex-grow: 1; color: #333; } .product-card .price { font-size: 13px; color: #007bff; font-weight: bold; margin-bottom: 8px; } .product-card .stButton button { width: 100%; background-color: #007bff; color: white; font-size: 14px; padding: 5px; }</style>""", unsafe_allow_html=True)
        products_df = get_df("SELECT * FROM products ORDER BY name ASC")
        if products_df.empty: st.warning("Belum ada produk.")
        else:
            if 'cart' not in st.session_state: st.session_state.cart = {}
            if 'last_transaction_id' not in st.session_state: st.session_state.last_transaction_id = None
            
            if st.session_state.last_transaction_id:
                st.success("Transaksi sebelumnya berhasil!")
                pdf_data = generate_receipt_pdf(st.session_state.last_transaction_id)
                st.download_button(
                    label="📄 Cetak Struk Terakhir",
                    data=pdf_data,
                    file_name=f"struk_{st.session_state.last_transaction_id}.pdf",
                    mime="application/pdf"
                )
                if st.button("Transaksi Baru"):
                    st.session_state.last_transaction_id = None
                    st.rerun()
                st.write("---")

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
                        success, message, transaction_id = process_atomic_sale(st.session_state.cart, payment_method, st.session_state.user_id)
                        if success:
                            st.session_state.cart = {}
                            st.session_state.last_transaction_id = transaction_id
                            st.rerun()
                        else:
                            st.error(f"Gagal: {message}")
                    if st.button("Kosongkan Keranjang", use_container_width=True):
                        st.session_state.cart = {}; st.rerun()

    elif menu == "📦 Manajemen Stok":
        st.title("📦 Manajemen Stok Bahan Baku")
        df = get_df("SELECT * FROM ingredients")
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
        with st.expander("Tambah / Edit Bahan Baku"):
            selected_id = st.selectbox("Pilih bahan untuk diedit", [""] + df['id'].tolist(), format_func=lambda x: df[df['id']==x]['name'].iloc[0] if x else "Tambah Baru")
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
        with st.expander("Hapus Bahan Baku"):
            if not df.empty:
                del_id = st.selectbox("Pilih bahan untuk dihapus", df['id'].tolist(), key="del_ing_id", format_func=lambda x: df[df['id']==x]['name'].iloc[0])
                if st.button("Hapus Bahan Terpilih", type="primary"):
                    delete_ingredient(del_id); st.warning("Bahan dihapus."); st.rerun()

    elif menu == "🍽️ Manajemen Produk":
        st.title("🍽️ Manajemen Produk & Resep")
        products_df = get_df("SELECT * FROM products")
        ingredients_df = get_df("SELECT id, name, unit FROM ingredients")
        st.subheader("Daftar Produk")
        st.dataframe(products_df, use_container_width=True)
        with st.expander("Tambah / Edit Produk"):
            selected_prod_id = st.selectbox("Pilih produk untuk diedit (kosongkan untuk menambah)", [""] + products_df['id'].tolist(), key="edit_prod", format_func=lambda x: products_df[products_df['id']==x]['name'].iloc[0] if x else "Tambah Baru")
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
                del_prod_id = st.selectbox("Pilih produk untuk dihapus", products_df['id'].tolist(), key="del_prod_id", format_func=lambda x: products_df[products_df['id']==x]['name'].iloc[0])
                if st.button("Hapus Produk Terpilih", type="primary"):
                    delete_product(del_prod_id); st.warning("Produk dihapus."); st.rerun()
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
        sales_query = "SELECT t.id, t.transaction_date as date, p.name as product_name, ti.quantity as qty, ti.price_per_unit as price, (ti.quantity * ti.price_per_unit) as total_revenue, t.payment_method FROM transaction_items ti JOIN transactions t ON ti.transaction_id = t.id JOIN products p ON ti.product_id = p.id ORDER BY t.transaction_date DESC"
        sales_df = get_df(sales_query)
        st.subheader("Filter Laporan")
        col1, col2 = st.columns(2)
        with col1: start_date = st.date_input("Tanggal Mulai", value=date.today().replace(day=1))
        with col2: end_date = st.date_input("Tanggal Akhir", value=date.today())
        sales_df['date'] = pd.to_datetime(sales_df['date']).dt.date
        filtered_df = sales_df[(sales_df['date'] >= start_date) & (sales_df['date'] <= end_date)]
        st.subheader(f"Laporan dari {start_date.strftime('%d %B %Y')} sampai {end_date.strftime('%d %B %Y')}")
        if filtered_df.empty: st.info("Tidak ada data penjualan pada periode ini.")
        else:
            total_revenue = filtered_df['total_revenue'].sum()
            total_items_sold = filtered_df['qty'].sum()
            st.metric("Total Pendapatan", f"Rp {total_revenue:,.2f}")
            st.metric("Total Item Terjual", f"{total_items_sold} pcs")
            st.dataframe(filtered_df.style.format({'price': 'Rp {:,.2f}', 'total_revenue': 'Rp {:,.2f}'}), use_container_width=True)
            st.write("---")
            st.subheader("📊 Analisa Penjualan")
            col1, col2 = st.columns(2)
            with col1:
                best_seller_rev_series = filtered_df.groupby('product_name')['total_revenue'].sum()
                best_seller_rev_name = best_seller_rev_series.idxmax()
                best_seller_rev_value = best_seller_rev_series.max()
                rev_percentage = (best_seller_rev_value / total_revenue) * 100 if total_revenue > 0 else 0
                st.info(f"""
                **Produk Paling Untung:** {best_seller_rev_name}  
                (Menyumbang {rev_percentage:.2f}% dari total pendapatan)
                """)
            with col2:
                payment_method_counts = filtered_df['payment_method'].value_counts()
                fig_payment = go.Figure(data=[go.Pie(labels=payment_method_counts.index, values=payment_method_counts.values, hole=.3)])
                fig_payment.update_layout(title_text='Pendapatan per Metode Pembayaran')
                st.plotly_chart(fig_payment, use_container_width=True)

            st.subheader("Top 5 Produk Terlaris (Berdasarkan Pendapatan)")
            top_5_products = best_seller_rev_series.nlargest(5)
            fig_top5 = go.Figure(data=[go.Bar(x=top_5_products.index, y=top_5_products.values)])
            fig_top5.update_layout(xaxis_title="Produk", yaxis_title="Total Pendapatan (Rp)")
            st.plotly_chart(fig_top5, use_container_width=True)
            
            st.write("---")
            st.subheader("💡 Saran Manajemen")
            if st.button("Dapatkan Saran"):
                with st.spinner("Menganalisa data..."):
                    least_seller_qty = filtered_df.groupby('product_name')['qty'].sum().idxmin()
                    payment_mode = filtered_df['payment_method'].mode()[0] if not filtered_df['payment_method'].empty and filtered_df['payment_method'].notna().any() else "Tidak ada"
                    st.success("Analisa Selesai!")
                    st.markdown(f"""
                    - **Fokus pada Pemenang**: Produk **{best_seller_rev_name}** adalah bintang utama Anda, menyumbang **{rev_percentage:.2f}%** pendapatan. Pertimbangkan untuk menempatkannya di posisi strategis atau membuat paket promo (misal: `{best_seller_rev_name} + Snack`) untuk meningkatkan nilai transaksi rata-rata.
                    - **Evaluasi & Inovasi**: Produk **{least_seller_qty}** terjual paling sedikit. Apakah harganya terlalu tinggi? Rasanya kurang pas? Atau kurang promosi? Coba tawarkan sebagai bonus atau buat versi baru yang lebih menarik.
                    - **Optimalkan Pembayaran**: Metode pembayaran favorit pelanggan adalah **{payment_mode}**. Pastikan prosesnya cepat dan tidak pernah ada kendala. Jika banyak yang menggunakan Cash, selalu siapkan uang kembalian pecahan kecil di pagi hari.
                    - **Manajemen Stok**: Perhatikan bahan baku untuk **{best_seller_rev_name}**. Pastikan stoknya selalu aman dan jangan sampai kehabisan di jam sibuk. Pertimbangkan untuk negosiasi harga dengan supplier untuk bahan ini karena volume pembelian yang tinggi.
                    """)
            st.write("---")
            st.subheader("Kirim Ringkasan Laporan via WhatsApp")
            phone_number = st.text_input("Nomor WhatsApp Tujuan (format: 628xxxx)")
            if st.button("Buat Link Laporan WhatsApp"):
                if phone_number.isdigit() and len(phone_number) > 9:
                    report_string = f"*Ringkasan Laporan Penjualan*\nPeriode: {start_date.strftime('%d %b %Y')} - {end_date.strftime('%d %b %Y')}\n\n*Total Pendapatan:* Rp {total_revenue:,.0f}\n*Total Item Terjual:* {total_items_sold} pcs\n\nTerima kasih."
                    message = urllib.parse.quote(report_string)
                    link = f"https://wa.me/{phone_number}?text={message}"
                    st.markdown(f'<a href="{link}" target="_blank" style="background-color: #25D366; color: white; padding: 10px 20px; text-align: center; text-decoration: none; display: inline-block; border-radius: 5px;">Buka WhatsApp</a>', unsafe_allow_html=True)
                else:
                    st.error("Format nomor WhatsApp salah.")

    elif menu == "🧾 Riwayat Transaksi":
        st.title("🧾 Riwayat Transaksi")
        transactions_df = get_df("""
            SELECT t.id, t.transaction_date, t.total_amount, t.payment_method, e.name as employee_name
            FROM transactions t JOIN employees e ON t.employee_id = e.id
            ORDER BY t.transaction_date DESC
        """)
        if transactions_df.empty:
            st.info("Belum ada transaksi yang tercatat.")
        else:
            st.dataframe(transactions_df, use_container_width=True)
            selected_trans_id = st.selectbox("Pilih Transaksi untuk Lihat Detail/Cetak", transactions_df['id'])
            if selected_trans_id:
                pdf_data = generate_receipt_pdf(selected_trans_id)
                st.download_button(
                    label="📄 Unduh Struk PDF",
                    data=pdf_data,
                    file_name=f"struk_{selected_trans_id}.pdf",
                    mime="application/pdf"
                )

    elif menu == "💸 Pengeluaran":
        st.title("💸 Manajemen Pengeluaran")
        
        with st.expander("Tambah atau Edit Pengeluaran"):
            expenses_df = get_df("SELECT * FROM expenses ORDER BY date DESC")
            selected_expense_id = st.selectbox("Pilih pengeluaran untuk diedit (kosongkan untuk menambah)", [""] + expenses_df['id'].tolist(), format_func=lambda x: f"ID {x}: {expenses_df[expenses_df['id']==x]['description'].iloc[0]}" if x else "Tambah Baru")
            selected_expense = expenses_df[expenses_df['id'] == selected_expense_id].iloc[0] if selected_expense_id else None

            with st.form("expense_form", clear_on_submit=True):
                exp_date = st.date_input("Tanggal", value=pd.to_datetime(selected_expense['date']) if selected_expense is not None else date.today())
                exp_category = st.selectbox("Kategori", ["Bahan Baku", "Gaji", "Sewa", "Listrik & Air", "Marketing", "Lainnya"], index=["Bahan Baku", "Gaji", "Sewa", "Listrik & Air", "Marketing", "Lainnya"].index(selected_expense['category']) if selected_expense is not None else 0)
                exp_desc = st.text_input("Deskripsi", value=selected_expense['description'] if selected_expense is not None else "")
                exp_amount = st.number_input("Jumlah (Rp)", min_value=0.0, format="%.2f", value=selected_expense['amount'] if selected_expense is not None else 0.0)
                exp_payment = st.selectbox("Metode Pembayaran", ["Cash", "Transfer"], index=["Cash", "Transfer"].index(selected_expense['payment_method']) if selected_expense is not None else 0)

                if st.form_submit_button("Simpan Pengeluaran"):
                    if selected_expense_id:
                        update_expense(selected_expense_id, exp_date.strftime("%Y-%m-%d"), exp_category, exp_desc, exp_amount, exp_payment)
                        st.success("Pengeluaran berhasil diperbarui!")
                    else:
                        add_expense(exp_date.strftime("%Y-%m-%d"), exp_category, exp_desc, exp_amount, exp_payment)
                        st.success("Pengeluaran baru berhasil dicatat!")
                    st.rerun()

        st.write("---")
        st.subheader("Riwayat Pengeluaran")
        all_expenses_df = get_df("SELECT * FROM expenses ORDER BY date DESC")
        if all_expenses_df.empty:
            st.info("Belum ada data pengeluaran.")
        else:
            st.dataframe(all_expenses_df, use_container_width=True)
            total_expenses = all_expenses_df['amount'].sum()
            st.metric("Total Seluruh Pengeluaran Tercatat", f"Rp {total_expenses:,.2f}")

            st.subheader("Analisa Pengeluaran per Kategori")
            expense_by_cat = all_expenses_df.groupby('category')['amount'].sum()
            fig_exp = go.Figure(data=[go.Pie(labels=expense_by_cat.index, values=expense_by_cat.values, hole=.3)])
            st.plotly_chart(fig_exp, use_container_width=True)

    elif menu == "👨‍💼 Manajemen Karyawan":
        st.title("👨‍💼 Manajemen Data Karyawan")
        df_emp = get_df("SELECT id, name, wage_amount, wage_period, role, is_active FROM employees")
        st.dataframe(df_emp.drop(columns=['id']), use_container_width=True, column_config={"wage_amount": st.column_config.NumberColumn("Gaji (Rp)", format="Rp %d"), "is_active": "Status Aktif"})
        
        col1, col2 = st.columns(2)
        with col1:
            with st.expander("Tambah / Edit Karyawan"):
                selected_emp_id = st.selectbox("Pilih karyawan untuk diedit", [""] + df_emp['id'].tolist(), format_func=lambda x: df_emp[df_emp['id']==x]['name'].iloc[0] if x else "Tambah Baru")
                selected_employee = df_emp.loc[df_emp['id'] == selected_emp_id].iloc[0] if selected_emp_id else None
                with st.form("employee_form", clear_on_submit=True):
                    emp_name = st.text_input("Nama Karyawan (Username)", value=selected_employee['name'] if selected_employee is not None else "")
                    role = st.selectbox("Peran (Role)", ["Operator", "Manager", "Admin"], index=["Operator", "Manager", "Admin"].index(selected_employee['role']) if selected_employee is not None and selected_employee['role'] else 0)
                    c1, c2 = st.columns(2)
                    with c1: wage_amount = st.number_input("Jumlah Gaji (Rp)", min_value=0.0, format="%.2f", value=selected_employee['wage_amount'] if selected_employee is not None else 0.0)
                    with c2:
                        wage_periods = ["Per Jam", "Per Hari", "Per Minggu", "Per Bulan"]
                        default_index = wage_periods.index(selected_employee['wage_period']) if selected_employee is not None and selected_employee['wage_period'] in wage_periods else 0
                        wage_period = st.selectbox("Periode Gaji", wage_periods, index=default_index)
                    password = st.text_input("Password (isi untuk user baru/mengubah)", type="password")
                    if st.form_submit_button("Simpan Karyawan"):
                        if selected_emp_id:
                            update_employee(selected_emp_id, emp_name, wage_amount, wage_period, role)
                            if password:
                                hashed_pw = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())
                                run_query("UPDATE employees SET password=? WHERE id=?", (hashed_pw, selected_emp_id))
                            st.success("Data karyawan diperbarui!")
                        else:
                            if not password: st.error("Password wajib diisi untuk karyawan baru!")
                            else: add_employee(emp_name, wage_amount, wage_period, password, role); st.success("Karyawan baru ditambahkan!")
                        st.rerun()
        with col2:
            with st.expander("Aktifkan / Nonaktifkan Karyawan"):
                if not df_emp.empty:
                    toggle_emp_id = st.selectbox("Pilih karyawan", df_emp['id'].tolist(), format_func=lambda x: df_emp[df_emp['id']==x]['name'].iloc[0], key="toggle_emp")
                    current_status = df_emp.loc[df_emp['id'] == toggle_emp_id, 'is_active'].iloc[0]
                    button_text = "Nonaktifkan" if current_status else "Aktifkan"
                    if st.button(button_text, use_container_width=True):
                        set_employee_active_status(toggle_emp_id, not current_status)
                        st.success(f"Status karyawan berhasil diubah!")
                        st.rerun()

    elif menu == "⏰ Riwayat Absensi":
        st.title("⏰ Riwayat Absensi")
        employees_df = get_df("SELECT id, name FROM employees WHERE is_active = 1")
        if employees_df.empty: st.warning("Belum ada data karyawan aktif.")
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
                else: st.info("Tidak ada karyawan yang sedang bekerja.")
            st.subheader("Riwayat Absensi")
            df_att = get_df("SELECT a.id, e.name, a.check_in, a.check_out FROM attendance a JOIN employees e ON a.employee_id = e.id ORDER BY a.check_in DESC")
            st.dataframe(df_att, use_container_width=True)
            with st.expander("✏️ Edit / Hapus Riwayat Absensi"):
                if not df_att.empty:
                    edit_id = st.selectbox("Pilih ID Absensi untuk Diedit", df_att['id'].tolist(), key="edit_att_id")
                    selected_att = df_att[df_att['id'] == edit_id].iloc[0]
                    new_check_in = st.text_input("Waktu Check-in", value=selected_att['check_in'])
                    new_check_out = st.text_input("Waktu Check-out", value=selected_att['check_out'] or "")
                    c1, c2 = st.columns(2)
                    if c1.button("Simpan Perubahan"):
                        success, message = update_attendance(edit_id, new_check_in, new_check_out)
                        if success: st.success(message); st.rerun()
                        else: st.error(message)
                    if c2.button("Hapus Absensi Ini", type="primary"):
                        delete_attendance(edit_id); st.warning("Riwayat absensi dihapus!"); st.rerun()

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
    init_db()
    check_login()
