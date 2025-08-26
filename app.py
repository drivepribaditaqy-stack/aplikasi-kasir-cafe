import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.graph_objects as go
import urllib.parse
import bcrypt
from fpdf import FPDF
import random

# --- KONFIGURASI DAN INISIALISASI ---
DB = "pos.db"
st.set_page_config(layout="wide", page_title="Bali Nice - Dream Coffee & Eatry")

# =====================================================================
# --- FUNGSI MIGRASI & INISIALISASI DATABASE ---
# =====================================================================
def update_db_schema(conn):
    """Memeriksa dan memperbarui skema database jika diperlukan."""
    c = conn.cursor()
    c.execute("PRAGMA table_info(employees)")
    emp_columns = {info[1] for info in c.fetchall()}
    if 'password' not in emp_columns: c.execute("ALTER TABLE employees ADD COLUMN password TEXT")
    if 'role' not in emp_columns: c.execute("ALTER TABLE employees ADD COLUMN role TEXT")
    if 'is_active' not in emp_columns: c.execute("ALTER TABLE employees ADD COLUMN is_active BOOLEAN DEFAULT 1")
    if 'hourly_wage' in emp_columns:
         c.execute("ALTER TABLE employees RENAME TO employees_old")
         c.execute("""CREATE TABLE employees (
             id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, wage_amount REAL, 
             wage_period TEXT, password TEXT, role TEXT, is_active BOOLEAN DEFAULT 1
         )""")
         c.execute("INSERT INTO employees (id, name, wage_amount, wage_period, is_active) SELECT id, name, hourly_wage, 'Per Jam', 1 FROM employees_old")
         c.execute("DROP TABLE employees_old")
         st.toast("Skema database karyawan telah diperbarui.")

    c.execute("PRAGMA table_info(expenses)")
    exp_columns = {info[1] for info in c.fetchall()}
    if 'category' not in exp_columns:
        c.execute("ALTER TABLE expenses ADD COLUMN category TEXT DEFAULT 'Lainnya'")
        st.toast("Skema database pengeluaran telah diperbarui.")
    conn.commit()

def insert_initial_data(conn):
    """Membuat akun default jika belum ada."""
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM employees WHERE name = 'admin'")
    if c.fetchone()[0] == 0:
        st.info("Akun admin tidak ditemukan, membuat akun default...")
        initial_users = [
            ('admin', bcrypt.hashpw('admin'.encode('utf8'), bcrypt.gensalt()), 'Admin', 0, 'Per Bulan', 1),
            ('operator', bcrypt.hashpw('operator'.encode('utf8'), bcrypt.gensalt()), 'Operator', 0, 'Per Jam', 1)
        ]
        c.executemany("INSERT INTO employees (name, password, role, wage_amount, wage_period, is_active) VALUES (?, ?, ?, ?, ?, ?)", initial_users)
        conn.commit()
        st.success("Akun awal (admin/admin, operator/operator) berhasil dibuat.")
        st.rerun()

def insert_initial_products(conn):
    """Memasukkan daftar produk awal jika tabel produk kosong."""
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        st.info("Daftar produk tidak ditemukan, menambahkan produk awal...")
        products = [
            ("Espresso", 10000), ("Americano", 11000), ("Orange Americano", 14000),
            ("Lemon Americano", 14000), ("Cocof (BN Signature)", 15000), ("Coffee Latte", 15000),
            ("Cappuccino", 15000), ("Spanish Latte", 16000), ("Caramel Latte", 16000),
            ("Vanilla Latte", 16000), ("Hazelnut Latte", 16000), ("Butterscotch Latte", 16000),
            ("Tiramisu Latte", 16000), ("Mocca Latte", 16000), ("Coffee Chocolate", 18000),
            ("Taro Coffee Latte", 18000), ("Coffee Gula Aren", 18000), ("Lychee Coffee", 20000),
            ("Markisa Coffee", 20000), ("Raspberry Latte", 20000), ("Strawberry Latte", 20000),
            ("Manggo Latte", 20000), ("Bubblegum Latte", 20000),
            ("Lemon Tea", 10000), ("Lychee Tea", 10000), ("Milk Tea", 12000),
            ("Green Tea", 14000), ("Thai Tea", 14000), ("Melon Susu", 14000),
            ("Manggo Susu", 15000), ("Mocca Susu", 15000), ("Orange Susu", 15000),
            ("Taro Susu", 15000), ("Coklat Susu", 15000), ("Vanilla Susu", 15000),
            ("Strawberry Susu", 15000), ("Matcha Susu", 18000), ("Blueberry Susu", 18000),
            ("Bubblegum Susu", 18000), ("Raspberry Susu", 18000), ("Grenadine Susu", 14000),
            ("Banana Susu", 16000),
            ("Melon Soda", 10000), ("Manggo Soda", 12000), ("Orange Soda", 12000),
            ("Strawberry Soda", 12000), ("Bluesky Soda", 14000), ("Banana Soda", 16000),
            ("Grenadine Soda", 14000), ("Blueberry Soda", 16000), ("Coffee Bear", 16000),
            ("Mocca Soda", 16000), ("Raspberry Soda", 16000), ("Coffee Soda", 17000),
            ("Strawberry Coffee Soda", 18000), ("Melon Blue Sky", 18000), ("Blue Manggo Soda", 18000),
            ("Nasi Goreng Kampung", 10000), ("Nasi Goreng Biasa", 10000), ("Nasi Goreng Ayam", 18000),
            ("Nasi Ayam Sambal Matah", 13000), ("Nasi Ayam Penyet", 13000), ("Nasi Ayam Teriyaki", 15000),
            ("Mie Goreng", 12000), ("Mie Rebus", 12000), ("Mie Nyemek", 12000), ("Bihun Goreng", 12000),
            ("Burger Telur", 10000), ("Burger Ayam", 12000), ("Burger Telur + Keju", 13000),
            ("Burger Telur + Ayam", 15000), ("Burger Ayam + Telur + Keju", 18000),
            ("Roti Bakar Coklat", 10000), ("Roti Bakar Strawberry", 10000), ("Roti Bakar Srikaya", 10000),
            ("Roti Bakar Coklat Keju", 12000),
            ("Kentang Goreng", 12000), ("Nugget", 12000), ("Sosis", 12000),
            ("Mix Platter Jumbo", 35000), ("Tahu/Tempe", 5000),
            ("Double Shoot", 3000), ("Yakult", 3000), ("Mineral Water", 4000),
            ("Mineral Water Gelas", 500), ("Nasi Putih", 3000), ("Le Mineralle", 4000)
        ]
        c.executemany("INSERT INTO products (name, price) VALUES (?, ?)", products)
        conn.commit()
        st.success("Daftar produk awal berhasil ditambahkan.")
        st.rerun()

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, wage_amount REAL, 
        wage_period TEXT, password TEXT, role TEXT, is_active BOOLEAN DEFAULT 1
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS ingredients (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, unit TEXT,
        cost_per_unit REAL, stock REAL, pack_weight REAL DEFAULT 0.0, pack_price REAL DEFAULT 0.0
    )""")
    c.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, price REAL)")
    c.execute("""CREATE TABLE IF NOT EXISTS recipes (
        product_id INTEGER, ingredient_id INTEGER, qty_per_unit REAL, PRIMARY KEY (product_id, ingredient_id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, transaction_date TEXT, total_amount REAL, 
        payment_method TEXT, employee_id INTEGER
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS transaction_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, transaction_id INTEGER, product_id INTEGER, 
        quantity INTEGER, price_per_unit REAL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, category TEXT, 
        description TEXT, amount REAL, payment_method TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER, check_in TEXT, check_out TEXT
    )""")
    update_db_schema(conn)
    conn.commit()
    insert_initial_data(conn)
    insert_initial_products(conn) 
    conn.close()

# =====================================================================
# --- BAGIAN LOGIN ---
# =====================================================================
def check_login():
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    if st.session_state.logged_in:
        st.sidebar.success(f"Welcome, {st.session_state.username} ({st.session_state.role})")
        if st.sidebar.button("Logout"):
            for key in st.session_state.keys(): del st.session_state[key]
            st.rerun()
        run_main_app()
    else:
        st.title("☕ Bali Nice - Dream Coffee & Eatry")
        # --- PERUBAHAN: Variasi Quotes ditambah ---
        quotes = [
            "Rahajeng semeng! Secangkir kopi untuk hari yang penuh inspirasi.",
            "Hidup itu seperti kopi, pahit dan manis harus dinikmati.",
            "Di setiap biji kopi, ada cerita Pulau Dewata yang menanti.",
            "Satu tegukan kopi, sejuta semangat untuk berkarya.",
            "Kopi pagi ini sehangat mentari di Pantai Kuta.",
            "Jangan biarkan kopimu dingin, dan jangan biarkan semangatmu padam.",
            "Temukan ketenangan dalam secangkir kopi, seperti menemukan damai di Ubud.",
            "Kopi adalah caraku mengatakan 'mari kita mulai petualangan hari ini'.",
            "Setiap cangkir adalah kanvas, dan barista adalah senimannya.",
            "Om Swastyastu! Selamat menikmati kopi pilihan terbaik."
        ]
        st.markdown(f"> *{random.choice(quotes)}*")
        st.markdown("---")
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
                        st.session_state.logged_in = True; st.session_state.user_id = user_id
                        st.session_state.username = username; st.session_state.role = role
                        st.rerun()
                    else: st.error("Password salah!")
                else: st.error("Username tidak ditemukan atau akun tidak aktif!")

# =====================================================================
# --- APLIKASI UTAMA ---
# =====================================================================
def run_main_app():
    # --- PERUBAHAN: Injeksi CSS untuk tema Bali ---
    custom_css = """
        <style>
            /* Color Palette */
            :root {
                --primary-color: #FFD100; /* Gold */
                --secondary-color: #FFEE32; /* Yellow */
                --background-color: #202020; /* Dark Gray */
                --text-color: #D6D6D6; /* Light Gray */
                --widget-background: #333533; /* Charcoal */
            }

            /* General Body */
            body {
                color: var(--text-color);
                background-color: var(--background-color);
            }

            /* Sidebar */
            .st-emotion-cache-16txtl3 {
                background-color: var(--widget-background);
            }

            /* Main Content */
            .st-emotion-cache-1y4p8pa {
                background-color: var(--background-color);
            }

            /* Tombol Utama */
            .stButton>button {
                background-color: var(--primary-color);
                color: var(--background-color);
                border: 2px solid var(--primary-color);
                font-weight: bold;
            }
            .stButton>button:hover {
                background-color: var(--secondary-color);
                color: var(--background-color);
                border: 2px solid var(--secondary-color);
            }
            
            /* Tombol Hapus & Aksi Berbahaya */
            .stButton>button[kind="primary"] {
                background-color: #D32F2F; /* Merah Bahaya */
                color: white;
                border: none;
            }
             .stButton>button[kind="primary"]:hover {
                background-color: #B71C1C;
                color: white;
            }

            /* Header dan Subheader */
            h1, h2, h3 {
                color: var(--primary-color);
            }

            /* Widget Styling */
            .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div {
                background-color: var(--widget-background);
                color: var(--text-color);
            }
            
            /* Metric Styling */
            .st-emotion-cache-1g6gooi {
                background-color: var(--widget-background);
                border-radius: 10px;
                padding: 1rem;
            }
        </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)


    # --- Fungsi Helper ---
    def run_query(query, params=(), fetch=None):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute(query, params)
        if fetch == 'one': result = c.fetchone()
        elif fetch == 'all': result = c.fetchall()
        else: result = None
        conn.commit()
        conn.close()
        return result

    def get_df(query, params=()):
        conn = sqlite3.connect(DB)
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df

    # --- Fungsi Logika Bisnis ---
    def process_atomic_sale(cart, payment_method, employee_id, cash_received=0):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        try:
            c.execute("BEGIN TRANSACTION")
            insufficient_items, products_map = [], {row['name']: {'id': row['id'], 'price': row['price']} for _, row in get_df("SELECT id, name, price FROM products").iterrows()}
            for product_name, qty in cart.items():
                product_id = products_map[product_name]['id']
                c.execute("SELECT i.name, i.stock, r.qty_per_unit FROM recipes r JOIN ingredients i ON r.ingredient_id = i.id WHERE r.product_id=?", (product_id,))
                for ing_name, stock, qty_per_unit in c.fetchall():
                    if stock < qty_per_unit * qty: insufficient_items.append(f"{ing_name} untuk {product_name}")
            if insufficient_items: raise ValueError(f"Stok tidak cukup: {', '.join(insufficient_items)}")
            total_amount = sum(products_map[name]['price'] * qty for name, qty in cart.items())
            c.execute("INSERT INTO transactions (transaction_date, total_amount, payment_method, employee_id) VALUES (?, ?, ?, ?)", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), total_amount, payment_method, employee_id))
            transaction_id = c.lastrowid
            for product_name, qty in cart.items():
                product_info = products_map[product_name]
                c.execute("INSERT INTO transaction_items (transaction_id, product_id, quantity, price_per_unit) VALUES (?, ?, ?, ?)", (transaction_id, product_info['id'], qty, product_info['price']))
                c.execute("SELECT ingredient_id, qty_per_unit FROM recipes WHERE product_id=?", (product_info['id'],))
                for ing_id, qty_per_unit in c.fetchall():
                    c.execute("UPDATE ingredients SET stock = stock - ? WHERE id=?", (qty_per_unit * qty, ing_id))
            conn.commit()
            change = cash_received - total_amount if payment_method == 'Cash' and cash_received > 0 else 0
            return True, "Pesanan berhasil diproses!", transaction_id, change
        except Exception as e:
            conn.rollback()
            return False, str(e), None, 0
        finally: conn.close()

    def generate_receipt_pdf(transaction_id):
        conn = sqlite3.connect(DB)
        transaction = pd.read_sql_query("SELECT * FROM transactions WHERE id = ?", conn, params=(transaction_id,)).iloc[0]
        items_df = pd.read_sql_query("SELECT p.name, ti.quantity, ti.price_per_unit FROM transaction_items ti JOIN products p ON ti.product_id = p.id WHERE ti.transaction_id = ?", conn, params=(transaction_id,))
        conn.close()
        pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, 'Bali Nice - Dream Coffee & Eatry', 0, 1, 'C'); pdf.set_font("Arial", '', 10)
        pdf.cell(0, 5, 'Struk Pembayaran', 0, 1, 'C'); pdf.ln(5); pdf.set_font("Arial", '', 12)
        pdf.cell(0, 8, f"No. Transaksi: {transaction['id']}", 0, 1)
        pdf.cell(0, 8, f"Tanggal: {transaction['transaction_date']}", 0, 1); pdf.ln(5); pdf.set_font("Arial", 'B', 12)
        pdf.cell(100, 10, 'Produk', 1); pdf.cell(30, 10, 'Qty', 1); pdf.cell(50, 10, 'Subtotal', 1, 1); pdf.set_font("Arial", '', 12)
        for _, item in items_df.iterrows():
            pdf.cell(100, 10, item['name'], 1); pdf.cell(30, 10, str(item['quantity']), 1); pdf.cell(50, 10, f"Rp {item['quantity'] * item['price_per_unit']:,.0f}", 1, 1)
        pdf.ln(10); pdf.set_font("Arial", 'B', 14)
        pdf.cell(130, 10, 'Total', 1); pdf.cell(50, 10, f"Rp {transaction['total_amount']:,.0f}", 1, 1)
        pdf.cell(130, 10, 'Metode Bayar', 1); pdf.cell(50, 10, transaction['payment_method'], 1, 1)
        return bytes(pdf.output())

    def delete_transaction(transaction_id):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        try:
            c.execute("BEGIN TRANSACTION")
            c.execute("SELECT product_id, quantity FROM transaction_items WHERE transaction_id=?", (transaction_id,))
            for product_id, quantity in c.fetchall():
                c.execute("SELECT ingredient_id, qty_per_unit FROM recipes WHERE product_id=?", (product_id,))
                for ing_id, qty_per_unit in c.fetchall():
                    c.execute("UPDATE ingredients SET stock = stock + ? WHERE id=?", (qty_per_unit * quantity, ing_id))
            c.execute("DELETE FROM transaction_items WHERE transaction_id=?", (transaction_id,))
            c.execute("DELETE FROM transactions WHERE id=?", (transaction_id,))
            conn.commit()
            return True, "Transaksi berhasil dihapus dan stok dikembalikan."
        except Exception as e:
            conn.rollback()
            return False, f"Gagal menghapus transaksi: {e}"
        finally: conn.close()

    # --- Menu Sidebar ---
    # --- PERUBAHAN: Urutan menu ergonomis ---
    menu_options = [
        "🛒 Kasir", 
        "📜 Riwayat Transaksi", 
        "📦 Manajemen Stok", 
        "🍔 Manajemen Produk", 
        "💸 Pengeluaran",
        "📊 Laporan", 
        "💰 HPP", 
        "👥 Manajemen Karyawan"
    ]
    if st.session_state.role == 'Admin':
        menu_options.append("🕒 Riwayat Absensi")
    menu_options.append("🗑️ Kelola & Hapus Data") # Selalu di akhir
    
    menu = st.sidebar.radio("Pilih Menu", menu_options)

    # --- Halaman Kasir (POS) ---
    if menu == "🛒 Kasir":
        st.header("🌺 Kasir (Point of Sale)")
        if 'cart' not in st.session_state: st.session_state.cart = {}
        col1, col2 = st.columns([2, 1.5])
        with col1:
            st.subheader("Katalog Produk")
            search_term = st.text_input("Cari Nama Produk...", key="product_search")
            query, params = ("SELECT name, price FROM products ORDER BY name", ())
            if search_term: query, params = "SELECT name, price FROM products WHERE name LIKE ? ORDER BY name", (f'%{search_term}%',)
            products = run_query(query, params, fetch='all')
            if products:
                cols = st.columns([1,1,1,1]) # Dibuat lebih responsif untuk mobile
                for i, (name, price) in enumerate(products):
                    with cols[i % 4]:
                        if st.button(name, key=f"prod_{name}", use_container_width=True):
                            st.session_state.cart[name] = st.session_state.cart.get(name, 0) + 1
                            st.toast(f"'{name}' ditambahkan!"); st.rerun()
            else: st.info("Produk tidak ditemukan.")
        with col2:
            st.subheader("Keranjang Belanja")
            if not st.session_state.cart: st.info("Keranjang masih kosong.")
            else:
                total_price = 0
                products_df = get_df("SELECT name, price FROM products")
                
                for name, qty in list(st.session_state.cart.items()):
                    price = products_df[products_df['name'] == name]['price'].iloc[0]
                    subtotal = price * qty
                    total_price += subtotal
                    
                    c1, c2, c3 = st.columns([2.5, 1, 1])
                    c1.write(f"{name} (x{qty})")
                    c2.write(f"Rp {subtotal:,.0f}")
                    if c3.button("Hapus", key=f"del_{name}"):
                        del st.session_state.cart[name]
                        st.rerun()

                st.markdown("---"); st.metric("Total Harga", f"Rp {total_price:,.0f}")
                with st.expander("Proses Pembayaran", expanded=True):
                    payment_method = st.selectbox("Metode Pembayaran", ["Cash", "Qris", "Card"])
                    cash_received = 0
                    if payment_method == 'Cash':
                        cash_received = st.number_input("Jumlah Uang Diterima (Rp)", min_value=0, step=1000)
                        if cash_received >= total_price:
                            st.metric("Kembalian", f"Rp {cash_received - total_price:,.0f}")
                        else: st.warning("Uang diterima kurang dari total.")
                    
                    if st.button("✅ Proses Pembayaran", use_container_width=True, disabled=(payment_method == 'Cash' and cash_received < total_price)):
                        success, message, transaction_id, change_amount = process_atomic_sale(st.session_state.cart, payment_method, st.session_state.user_id, cash_received)
                        if success:
                            st.success(f"{message} (ID: {transaction_id})")
                            if payment_method == 'Cash': st.info(f"Kembalian: Rp {change_amount:,.0f}")
                            st.session_state.last_transaction_id = transaction_id; st.session_state.cart = {}
                        else: st.error(f"Gagal: {message}")
                        st.rerun()

            if 'last_transaction_id' in st.session_state and st.session_state.last_transaction_id:
                st.markdown("---"); st.subheader("Opsi Transaksi Terakhir")
                last_id = st.session_state.last_transaction_id
                pdf_bytes = generate_receipt_pdf(last_id)
                st.download_button(label="📄 Cetak Struk (PDF)", data=pdf_bytes, file_name=f"struk_{last_id}.pdf", mime="application/pdf", use_container_width=True)
                if st.button("❌ Batalkan Pesanan", use_container_width=True, type="primary"):
                    success, message = delete_transaction(last_id)
                    if success: st.success(message); del st.session_state['last_transaction_id']
                    else: st.error(message)
                    st.rerun()
                st.caption("Membatalkan pesanan akan menghapus riwayat transaksi dan mengembalikan stok bahan baku.")

    # --- Halaman Manajemen Stok ---
    elif menu == "📦 Manajemen Stok":
        st.header("🌴 Manajemen Stok Bahan")
        low_stock_threshold = 10 
        low_stock_df = get_df(f"SELECT name, stock, unit FROM ingredients WHERE stock <= {low_stock_threshold}")
        if not low_stock_df.empty: st.warning(f"Perhatian! Bahan berikut hampir habis (stok <= {low_stock_threshold}):"); st.dataframe(low_stock_df)
        
        tabs = st.tabs(["📊 Daftar Bahan", "➕ Tambah Bahan", "✏️ Edit Bahan"])
        with tabs[0]:
            st.subheader("Daftar Bahan Saat Ini")
            search_ing = st.text_input("Cari Nama Bahan...", key="ingredient_search")
            query, params = ("SELECT id, name AS 'Nama', unit AS 'Unit', stock AS 'Stok', cost_per_unit AS 'HPP/Unit', pack_price AS 'Harga Kemasan', pack_weight AS 'Berat Kemasan' FROM ingredients", ())
            if search_ing: query += " WHERE name LIKE ?"; params = (f'%{search_ing}%',)
            st.dataframe(get_df(query, params).style.format({'HPP/Unit': 'Rp {:,.2f}', 'Harga Kemasan': 'Rp {:,.2f}'}))
        with tabs[1]:
            st.subheader("Tambah Bahan Baru")
            with st.form("add_ingredient_form"):
                name = st.text_input("Nama Bahan")
                unit = st.text_input("Satuan/Unit (e.g., gr, ml, pcs)")
                stock = st.number_input("Jumlah Stok Awal", value=0.0, format="%.2f")
                st.markdown("---"); st.info("Kalkulator Harga Pokok per Satuan")
                pack_price = st.number_input("Harga Beli per Kemasan (Rp)", value=0.0, format="%.2f")
                pack_weight = st.number_input("Isi/Berat per Kemasan (sesuai satuan)", value=0.0, format="%.2f")
                cost_per_unit = (pack_price / pack_weight) if pack_weight > 0 else 0
                st.metric("Harga Pokok per Satuan", f"Rp {cost_per_unit:,.2f}")
                if st.form_submit_button("Tambah Bahan"):
                    run_query("INSERT INTO ingredients (name, unit, cost_per_unit, stock, pack_weight, pack_price) VALUES (?, ?, ?, ?, ?, ?)", (name, unit, cost_per_unit, stock, pack_weight, pack_price))
                    st.success(f"Bahan '{name}' berhasil ditambahkan."); st.rerun()
        with tabs[2]:
            st.subheader("Edit Bahan")
            search_term = st.text_input("Cari nama bahan untuk diedit", key="edit_ing_search")
            if search_term:
                ingredient_data = run_query("SELECT * FROM ingredients WHERE name LIKE ?", (f'%{search_term}%',), fetch='one')
                if ingredient_data:
                    with st.form("edit_ingredient_form"):
                        st.info(f"Mengedit data untuk: **{ingredient_data[1]}**")
                        name = st.text_input("Nama Bahan", value=ingredient_data[1])
                        unit = st.text_input("Satuan/Unit", value=ingredient_data[2])
                        stock = st.number_input("Jumlah Stok", value=float(ingredient_data[4]), format="%.2f")
                        pack_price = st.number_input("Harga Beli per Kemasan (Rp)", value=float(ingredient_data[6]), format="%.2f")
                        pack_weight = st.number_input("Isi/Berat per Kemasan", value=float(ingredient_data[5]), format="%.2f")
                        cost_per_unit = (pack_price / pack_weight) if pack_weight > 0 else 0
                        st.metric("Harga Pokok per Satuan", f"Rp {cost_per_unit:,.2f}")
                        if st.form_submit_button("Simpan Perubahan"):
                            run_query("UPDATE ingredients SET name=?, unit=?, cost_per_unit=?, stock=?, pack_weight=?, pack_price=? WHERE id=?", (name, unit, cost_per_unit, stock, pack_weight, pack_price, ingredient_data[0]))
                            st.success(f"Bahan '{name}' diperbarui."); st.rerun()
                else:
                    st.warning("Bahan tidak ditemukan. Silakan cek kembali nama yang dimasukkan.")
            else:
                st.info("Ketik nama bahan di atas untuk mulai mengedit.")

    # --- Halaman Manajemen Produk ---
    elif menu == "🍔 Manajemen Produk":
        st.header("🍛 Manajemen Produk & Resep")
        tabs = st.tabs(["Daftar Produk", "➕ Tambah Produk", "✏️ Edit Produk", "🍲 Kelola Resep"])
        with tabs[0]:
            st.dataframe(get_df("SELECT id, name AS 'Nama Produk', price AS 'Harga Jual' FROM products").style.format({'Harga Jual': 'Rp {:,.0f}'}))
        with tabs[1]:
            st.subheader("Tambah Produk Baru")
            with st.form("add_product_form"):
                name = st.text_input("Nama Produk")
                price = st.number_input("Harga Jual", value=0.0, format="%.2f")
                if st.form_submit_button("Tambah Produk"):
                    run_query("INSERT INTO products (name, price) VALUES (?, ?)", (name, price)); st.success(f"Produk '{name}' ditambahkan!"); st.rerun()
        with tabs[2]:
            st.subheader("Edit Produk")
            search_term = st.text_input("Cari nama produk untuk diedit", key="edit_prod_search")
            if search_term:
                prod_data = run_query("SELECT * FROM products WHERE name LIKE ?", (f'%{search_term}%',), fetch='one')
                if prod_data:
                    with st.form("edit_product_form"):
                        st.info(f"Mengedit data untuk: **{prod_data[1]}**")
                        name = st.text_input("Nama Produk", value=prod_data[1])
                        price = st.number_input("Harga Jual", value=float(prod_data[2]), format="%.2f")
                        if st.form_submit_button("Simpan Perubahan"):
                            run_query("UPDATE products SET name=?, price=? WHERE id=?", (name, price, prod_data[0])); st.success("Produk diperbarui!"); st.rerun()
                else:
                    st.warning("Produk tidak ditemukan.")
            else:
                st.info("Ketik nama produk di atas untuk mulai mengedit.")
        with tabs[3]:
            st.subheader("Kelola Resep per Produk")
            products_df = get_df("SELECT id, name FROM products")
            if not products_df.empty:
                product_id = st.selectbox("Pilih Produk", products_df['id'], format_func=lambda x: products_df[products_df['id'] == x]['name'].iloc[0])
                st.write("Resep saat ini:"); st.dataframe(get_df("SELECT i.name, r.qty_per_unit, i.unit FROM recipes r JOIN ingredients i ON r.ingredient_id = i.id WHERE r.product_id=?", (product_id,)))
                with st.form("recipe_form"):
                    ingredients_df = get_df("SELECT id, name FROM ingredients")
                    if not ingredients_df.empty:
                        ingredient_id = st.selectbox("Pilih Bahan", ingredients_df['id'], format_func=lambda x: ingredients_df[ingredients_df['id'] == x]['name'].iloc[0])
                        qty = st.number_input("Jumlah Dibutuhkan", format="%.2f")
                        if st.form_submit_button("Tambah/Update Bahan ke Resep"):
                            run_query("REPLACE INTO recipes (product_id, ingredient_id, qty_per_unit) VALUES (?, ?, ?)", (product_id, ingredient_id, qty)); st.success("Resep diperbarui."); st.rerun()
                    else: st.warning("Tidak ada bahan baku. Tambahkan di menu Manajemen Stok terlebih dahulu.")
            else: st.info("Tidak ada produk untuk dikelola resepnya.")

    # --- Halaman Riwayat Transaksi ---
    elif menu == "📜 Riwayat Transaksi":
        st.header("🌊 Riwayat Transaksi")
        search_id = st.text_input("Cari dengan ID Transaksi...")
        query = "SELECT t.id AS 'ID', t.transaction_date AS 'Waktu', t.total_amount AS 'Total', t.payment_method AS 'Metode', e.name AS 'Kasir' FROM transactions t JOIN employees e ON t.employee_id = e.id"
        params = ()
        if search_id.isdigit(): query += " WHERE t.id = ?"; params = (int(search_id),)
        query += " ORDER BY t.id DESC"
        transactions_df = get_df(query, params)
        st.dataframe(transactions_df.style.format({'Total': 'Rp {:,.0f}'}))
        st.markdown("---"); st.subheader("Kelola Transaksi")
        if not transactions_df.empty:
            selected_id = st.selectbox("Pilih ID dari tabel di atas untuk dikelola", options=transactions_df['ID'].tolist())
            if selected_id:
                col1, col2 = st.columns(2)
                with col1:
                    items_df = get_df("SELECT p.name, ti.quantity, ti.price_per_unit FROM transaction_items ti JOIN products p ON ti.product_id = p.id WHERE ti.transaction_id = ?", (selected_id,))
                    st.write(f"**Detail Item Transaksi #{selected_id}:**"); st.dataframe(items_df)
                with col2:
                    if st.button("Hapus Transaksi Ini", type="primary", key=f"del_{selected_id}"):
                        success, message = delete_transaction(selected_id)
                        if success: st.success(message)
                        else: st.error(message)
                        st.rerun()
        else: st.info("Tidak ada transaksi untuk dikelola.")

    # --- Halaman Laporan (REVISI BESAR) ---
    elif menu == "📊 Laporan":
        st.header("📈 Laporan & Analisa Bisnis")
        today = date.today()
        col1, col2 = st.columns(2)
        start_date = col1.date_input("Tanggal Mulai", today.replace(day=1))
        end_date = col2.date_input("Tanggal Akhir", today)
        start_datetime, end_datetime = datetime.combine(start_date, datetime.min.time()), datetime.combine(end_date, datetime.max.time())
        
        st.subheader("Ringkasan Kinerja Bisnis")
        trans_df = get_df("SELECT * FROM transactions WHERE transaction_date BETWEEN ? AND ?", (start_datetime.strftime("%Y-%m-%d %H:%M:%S"), end_datetime.strftime("%Y-%m-%d %H:%M:%S")))
        expenses_df = get_df("SELECT * FROM expenses WHERE date BETWEEN ? AND ?", (start_date.isoformat(), end_date.isoformat()))
        
        salary_details = []
        total_gaji = 0
        employees_df = get_df("SELECT id, name, wage_amount, wage_period FROM employees WHERE is_active = 1")
        attendance_df = get_df("SELECT * FROM attendance WHERE check_in BETWEEN ? AND ?", (start_datetime.strftime("%Y-%m-%d %H:%M:%S"), end_datetime.strftime("%Y-%m-%d %H:%M:%S")))
        if not attendance_df.empty:
            attendance_df['check_in'] = pd.to_datetime(attendance_df['check_in'])
            attendance_df['check_out'] = pd.to_datetime(attendance_df['check_out'])
            for _, emp in employees_df.iterrows():
                emp_attendance = attendance_df[attendance_df['employee_id'] == emp['id']].copy()
                if not emp_attendance.empty:
                    emp_salary = 0
                    if emp['wage_period'] == 'Per Jam':
                        emp_attendance['duration'] = (emp_attendance['check_out'] - emp_attendance['check_in']).dt.total_seconds() / 3600
                        total_hours = emp_attendance['duration'].sum()
                        emp_salary = total_hours * emp['wage_amount']
                        salary_details.append({'Karyawan': emp['name'], 'Detail': f'{total_hours:.2f} jam kerja', 'Total Gaji': emp_salary})
                    elif emp['wage_period'] == 'Per Hari':
                        work_days = emp_attendance['check_in'].dt.date.nunique()
                        emp_salary = work_days * emp['wage_amount']
                        salary_details.append({'Karyawan': emp['name'], 'Detail': f'{work_days} hari kerja', 'Total Gaji': emp_salary})
                    elif emp['wage_period'] == 'Per Bulan':
                        days_in_range = (end_date - start_date).days + 1
                        emp_salary = (emp['wage_amount'] / 30) * days_in_range
                        salary_details.append({'Karyawan': emp['name'], 'Detail': f'{days_in_range} hari dalam rentang', 'Total Gaji': emp_salary})
                    total_gaji += emp_salary
        salary_df = pd.DataFrame(salary_details)

        total_pendapatan = trans_df['total_amount'].sum()
        total_modal = 0
        if not trans_df.empty:
            items_df = get_df(f"SELECT ti.quantity, r.qty_per_unit, i.cost_per_unit FROM transaction_items ti JOIN recipes r ON ti.product_id = r.product_id JOIN ingredients i ON r.ingredient_id = i.id WHERE ti.transaction_id IN ({','.join(map(str, trans_df['id']))})")
            if not items_df.empty: total_modal = (items_df['quantity'] * items_df['qty_per_unit'] * items_df['cost_per_unit']).sum()
        
        op_expenses_df = expenses_df[expenses_df['category'] == 'Operasional']
        other_expenses_df = expenses_df[expenses_df['category'] == 'Lainnya']
        total_biaya_operasional = op_expenses_df['amount'].sum()
        total_pengeluaran_lainnya = other_expenses_df['amount'].sum()

        laba_kotor = total_pendapatan - total_modal
        laba_bersih = laba_kotor - total_biaya_operasional - total_pengeluaran_lainnya - total_gaji
        margin_laba_kotor = (laba_kotor / total_pendapatan * 100) if total_pendapatan > 0 else 0
        margin_laba_bersih = (laba_bersih / total_pendapatan * 100) if total_pendapatan > 0 else 0
        
        kpi_cols = st.columns(5)
        kpi_cols[0].metric("Total Pendapatan", f"Rp {total_pendapatan:,.0f}")
        kpi_cols[1].metric("Total Modal (HPP)", f"Rp {total_modal:,.0f}")
        kpi_cols[2].metric("Total Gaji Karyawan", f"Rp {total_gaji:,.0f}")
        kpi_cols[3].metric("Biaya Operasional", f"Rp {total_biaya_operasional:,.0f}")
        kpi_cols[4].metric("Pengeluaran Lain", f"Rp {total_pengeluaran_lainnya:,.0f}")
        st.metric("Laba Bersih", f"Rp {laba_bersih:,.0f}", delta=f"{margin_laba_bersih:.1f}% Margin")

        if total_modal > 0 or total_biaya_operasional > 0 or total_pengeluaran_lainnya > 0 or total_gaji > 0:
            fig_pie = go.Figure(data=[go.Pie(labels=['Modal (HPP)', 'Gaji Karyawan', 'Biaya Operasional', 'Pengeluaran Lain'], values=[total_modal, total_gaji, total_biaya_operasional, total_pengeluaran_lainnya], hole=.3)])
            fig_pie.update_layout(title='Komposisi Biaya')
            st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown("---"); st.subheader("💡 Analisa & Saran Manajemen")
        col_an1, col_an2 = st.columns(2)
        with col_an1:
            if not trans_df.empty:
                st.write("**Kinerja Produk**")
                laris_df = get_df(f"SELECT p.name, SUM(ti.quantity) as total_qty FROM transaction_items ti JOIN products p ON ti.product_id = p.id WHERE ti.transaction_id IN ({','.join(map(str, trans_df['id']))}) GROUP BY p.name ORDER BY total_qty DESC LIMIT 5")
                st.dataframe(laris_df, hide_index=True)

                hpp_df = get_df("SELECT p.id, p.name, p.price, IFNULL(SUM(r.qty_per_unit * i.cost_per_unit), 0) as hpp FROM products p LEFT JOIN recipes r ON p.id = r.product_id LEFT JOIN ingredients i ON r.ingredient_id = i.id GROUP BY p.id")
                trans_items_df = get_df(f"SELECT product_id, quantity FROM transaction_items WHERE transaction_id IN ({','.join(map(str, trans_df['id']))})")
                merged_df = pd.merge(trans_items_df, hpp_df, left_on='product_id', right_on='id')
                merged_df['profit'] = (merged_df['price'] - merged_df['hpp']) * merged_df['quantity']
                profit_summary = merged_df.groupby('name')['profit'].sum().reset_index().sort_values(by='profit', ascending=False).head(5)
                st.dataframe(profit_summary.style.format({'profit': 'Rp {:,.0f}'}), hide_index=True)

                st.write("**Tren Pendapatan Harian**")
                trans_df['transaction_date'] = pd.to_datetime(trans_df['transaction_date'])
                daily_revenue = trans_df.set_index('transaction_date').resample('D')['total_amount'].sum().reset_index()
                fig_trend = go.Figure(data=go.Scatter(x=daily_revenue['transaction_date'], y=daily_revenue['total_amount'], mode='lines+markers'))
                fig_trend.update_layout(title='Tren Pendapatan Harian', xaxis_title='Tanggal', yaxis_title='Pendapatan (Rp)')
                st.plotly_chart(fig_trend, use_container_width=True)
            else: st.info("Belum ada data penjualan pada rentang tanggal ini.")
        with col_an2:
            st.write("**Saran Santai**")
            saran = []
            total_biaya = total_modal + total_gaji + total_biaya_operasional + total_pengeluaran_lainnya
            if total_pendapatan > 0:
                if laba_bersih < 0:
                    saran.append(" Waduh, profitnya lagi merah nih. Coba cek lagi harga modal (HPP) atau biaya operasional, mungkin ada yang bisa ditekan. Naikin harga dikit buat produk best seller juga boleh dicoba, lho.")
                if (total_gaji / total_biaya) > 0.5:
                    saran.append(" Gaji karyawan porsinya gede banget, nih. Mungkin bisa dicek lagi jadwalnya, biar jam kerja lebih efisien dan nggak banyak lemburan yang nggak perlu.")
                if not laris_df.empty and not profit_summary.empty:
                    produk_laris = laris_df['name'].iloc[0]
                    produk_untung = profit_summary['name'].iloc[0]
                    if produk_laris != produk_untung:
                        saran.append(f" Eh, tau gak? '{produk_laris}' paling laku, tapi '{produk_untung}' paling untung. Gimana kalau kasir diajarin buat nawarin '{produk_untung}' tiap ada yang beli '{produk_laris}'? Cuan dobel!")
            if not laris_df.empty:
                 saran.append(f" Mantap! '{laris_df['name'].iloc[0]}' lagi naik daun. Stoknya jangan sampai kosong, ya. Mungkin bisa dibikinin varian baru biar makin hits?")
            if total_biaya > 0 and (total_biaya_operasional / total_biaya) > 0.4:
                saran.append(" Biaya operasional kayaknya agak boros. Coba deh ngobrol lagi sama supplier, siapa tau bisa dapet harga lebih miring. Cek juga tagihan listrik sama air, kali aja ada yang bocor.")
            
            if len(saran) < 3:
                saran.extend([
                    " Coba deh, luangin waktu tiap minggu buat liat laporan ini. Biar makin jago baca situasi dan ambil keputusan.",
                    " Produk yang lagi laris itu 'harta karun'. Sering-sering pamerin di sosmed biar makin banyak yang penasaran!",
                    " Penasaran pelanggan maunya apa? Coba deh taruh kotak saran atau bikin polling di Instagram. Siapa tau ada masukan emas!"
                ])

            random.shuffle(saran)
            for i in range(min(3, len(saran))):
                st.info(saran[i])

            summary_text = f"Laporan Bali Nice ({start_date.strftime('%d %b')} - {end_date.strftime('%d %b')})\n- Pendapatan: Rp {total_pendapatan:,.0f}\n- Modal (HPP): Rp {total_modal:,.0f}\n- Gaji: Rp {total_gaji:,.0f}\n- Laba Bersih: Rp {laba_bersih:,.0f}"
            st.link_button("Kirim Ringkasan via WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(summary_text)}")

        st.markdown("---"); st.subheader("🗃️ Detail Data")
        with st.expander("Detail Data Transaksi (Data Mentah)"): st.dataframe(trans_df)
        with st.expander("Detail Gaji Karyawan"): st.dataframe(salary_df.style.format({'Total Gaji': 'Rp {:,.2f}'}))
        with st.expander("Detail Biaya Operasional"): st.dataframe(op_expenses_df)
        with st.expander("Detail Pengeluaran Lainnya"): st.dataframe(other_expenses_df)

    # --- Halaman Pengeluaran ---
    elif menu == "💸 Pengeluaran":
        st.header("💸 Catat Pengeluaran")
        tabs = st.tabs(["Daftar Pengeluaran", "➕ Tambah Pengeluaran", "✏️ Edit Pengeluaran"])
        with tabs[0]:
            st.dataframe(get_df("SELECT id, date, category, description, amount, payment_method FROM expenses").style.format({'amount': 'Rp {:,.2f}'}))
        with tabs[1]:
            st.subheader("Tambah Pengeluaran Baru")
            with st.form("add_expense_form"):
                date_exp = st.date_input("Tanggal", date.today())
                category = st.selectbox("Kategori", ["Operasional", "Lainnya"])
                description = st.text_input("Deskripsi")
                amount = st.number_input("Jumlah", value=0.0, format="%.2f")
                payment_method = st.selectbox("Metode Pembayaran", ["Cash", "Transfer"])
                if st.form_submit_button("Tambah"):
                    run_query("INSERT INTO expenses (date, category, description, amount, payment_method) VALUES (?, ?, ?, ?, ?)", (date_exp.isoformat(), category, description, amount, payment_method)); st.success("Ditambahkan!"); st.rerun()
        with tabs[2]:
            st.subheader("Edit Pengeluaran")
            search_term = st.text_input("Cari deskripsi pengeluaran untuk diedit", key="edit_exp_search")
            if search_term:
                exp_data = run_query("SELECT * FROM expenses WHERE description LIKE ?", (f'%{search_term}%',), fetch='one')
                if exp_data:
                    with st.form("edit_expense_form"):
                        st.info(f"Mengedit data untuk: **{exp_data[3]}**")
                        date_exp = st.date_input("Tanggal", value=datetime.strptime(exp_data[1], '%Y-%m-%d').date())
                        category = st.selectbox("Kategori", ["Operasional", "Lainnya"], index=["Operasional", "Lainnya"].index(exp_data[2] if exp_data[2] else "Lainnya"))
                        description = st.text_input("Deskripsi", value=exp_data[3])
                        amount = st.number_input("Jumlah", value=float(exp_data[4]), format="%.2f")
                        payment_method = st.selectbox("Metode Pembayaran", ["Cash", "Transfer"], index=["Cash", "Transfer"].index(exp_data[5]))
                        if st.form_submit_button("Simpan Perubahan"):
                            run_query("UPDATE expenses SET date=?, category=?, description=?, amount=?, payment_method=? WHERE id=?", (date_exp.isoformat(), category, description, amount, payment_method, exp_data[0])); st.success("Diperbarui!"); st.rerun()
                else:
                    st.warning("Pengeluaran tidak ditemukan.")
            else:
                st.info("Ketik deskripsi pengeluaran di atas untuk mulai mengedit.")

    # --- Halaman HPP ---
    elif menu == "💰 HPP":
        st.header("💰 Harga Pokok Penjualan (HPP)")
        def get_product_hpp(product_id):
            df = get_df("SELECT SUM(r.qty_per_unit * i.cost_per_unit) as hpp FROM recipes r JOIN ingredients i ON r.ingredient_id = i.id WHERE r.product_id=?", (product_id,))
            return df['hpp'].iloc[0] if not df.empty and df['hpp'].iloc[0] is not None else 0
        prods_df = get_df("SELECT * FROM products")
        if not prods_df.empty:
            hpp_data = []
            for _, row in prods_df.iterrows():
                hpp = get_product_hpp(row['id'])
                profit = row['price'] - hpp
                hpp_data.append({"Nama Produk": row['name'], "Harga Jual": row['price'], "HPP (Modal)": hpp, "Profit Kotor": profit})
            df_hpp = pd.DataFrame(hpp_data)
            st.dataframe(df_hpp.style.format({'Harga Jual': 'Rp {:,.0f}', 'HPP (Modal)': 'Rp {:,.2f}', 'Profit Kotor': 'Rp {:,.2f}'}))

    # --- Halaman Manajemen Karyawan ---
    elif menu == "👥 Manajemen Karyawan":
        st.header("👥 Manajemen Karyawan")
        tabs = st.tabs(["Daftar Karyawan", "➕ Tambah Karyawan", "✏️ Edit Karyawan", "🕒 Absensi Hari Ini"])
        with tabs[0]:
            st.dataframe(get_df("SELECT id, name, role, wage_amount, wage_period, is_active FROM employees").style.format({'wage_amount': 'Rp {:,.2f}'}))
        with tabs[1]:
            st.subheader("Tambah Karyawan Baru")
            with st.form("add_employee_form"):
                name = st.text_input("Nama").lower()
                role = st.selectbox("Role", ["Operator", "Admin"])
                wage_period = st.selectbox("Periode Gaji", ["Per Jam", "Per Hari", "Per Bulan"])
                wage_amount = st.number_input("Jumlah Gaji")
                password = st.text_input("Password", type="password")
                is_active = st.checkbox("Aktif", value=True)
                if st.form_submit_button("Tambah"):
                    if name and password:
                        hashed_pw = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())
                        run_query("INSERT INTO employees (name, wage_amount, wage_period, password, role, is_active) VALUES (?, ?, ?, ?, ?, ?)", (name, wage_amount, wage_period, hashed_pw, role, is_active)); st.success("Ditambahkan!"); st.rerun()
                    else: st.error("Nama dan Password tidak boleh kosong.")
        with tabs[2]:
            st.subheader("Edit Karyawan")
            search_term = st.text_input("Cari nama karyawan untuk diedit", key="edit_emp_search")
            if search_term:
                emp_data = run_query("SELECT * FROM employees WHERE name LIKE ?", (f'%{search_term}%',), fetch='one')
                if emp_data:
                    with st.form("edit_employee_form"):
                        st.info(f"Mengedit data untuk: **{emp_data[1]}**")
                        name = st.text_input("Nama", value=emp_data[1]).lower()
                        role = st.selectbox("Role", ["Operator", "Admin"], index=["Operator", "Admin"].index(emp_data[5]))
                        wage_period = st.selectbox("Periode Gaji", ["Per Jam", "Per Hari", "Per Bulan"], index=["Per Jam", "Per Hari", "Per Bulan"].index(emp_data[3]))
                        wage_amount = st.number_input("Jumlah Gaji", value=float(emp_data[2]))
                        password = st.text_input("Password Baru (kosongkan jika tidak diubah)", type="password")
                        is_active = st.checkbox("Aktif", value=bool(emp_data[6]))
                        if st.form_submit_button("Simpan"):
                            if password:
                                hashed_pw = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())
                                run_query("UPDATE employees SET name=?, wage_amount=?, wage_period=?, role=?, is_active=?, password=? WHERE id=?", (name, wage_amount, wage_period, role, is_active, hashed_pw, emp_data[0]))
                            else:
                                run_query("UPDATE employees SET name=?, wage_amount=?, wage_period=?, role=?, is_active=? WHERE id=?", (name, wage_amount, wage_period, role, is_active, emp_data[0]))
                            st.success("Diperbarui!"); st.rerun()
                else:
                    st.warning("Karyawan tidak ditemukan.")
            else:
                st.info("Ketik nama karyawan di atas untuk mulai mengedit.")
        with tabs[3]:
            st.subheader("Absensi Karyawan Hari Ini")
            employees_df = get_df("SELECT id, name FROM employees WHERE is_active = 1")
            if not employees_df.empty:
                employee_id = st.selectbox("Pilih Karyawan", employees_df['id'], format_func=lambda x: employees_df[employees_df['id'] == x]['name'].iloc[0])
                today_str = date.today().isoformat()
                attendance = run_query("SELECT * FROM attendance WHERE employee_id=? AND date(check_in)=?", (employee_id, today_str), fetch='one')
                if not attendance:
                    if st.button("Check In"):
                        run_query("INSERT INTO attendance (employee_id, check_in) VALUES (?, ?)", (employee_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))); st.success("Check in berhasil!"); st.rerun()
                elif not attendance[3]:
                    st.info(f"Sudah check in pada: {attendance[2]}")
                    if st.button("Check Out"):
                        run_query("UPDATE attendance SET check_out=? WHERE id=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), attendance[0])); st.success("Check out berhasil!"); st.rerun()
                else: st.success(f"Sudah check in ({attendance[2]}) dan check out ({attendance[3]}) hari ini.")
            else: st.info("Tidak ada karyawan aktif untuk absensi.")

    # --- Halaman Riwayat Absensi ---
    elif menu == "🕒 Riwayat Absensi":
        st.header("🕒 Riwayat Absensi Karyawan")
        tabs = st.tabs(["Daftar Absensi", "✏️ Edit Absensi"])
        with tabs[0]:
            df = get_df("SELECT a.id, e.name, a.check_in, a.check_out FROM attendance a JOIN employees e ON a.employee_id = e.id ORDER BY a.check_in DESC")
            st.dataframe(df)
        with tabs[1]:
            st.subheader("Edit Data Absensi")
            attendance_df = get_df("SELECT a.id, e.name, a.check_in FROM attendance a JOIN employees e ON a.employee_id = e.id ORDER BY a.check_in DESC")
            if not attendance_df.empty:
                attendance_options = {f"ID: {row['id']} - {row['name']} ({row['check_in']})": row['id'] for _, row in attendance_df.iterrows()}
                selected_att_str = st.selectbox("Pilih absensi untuk diedit", list(attendance_options.keys()), key="edit_att_select")
                if selected_att_str:
                    att_id = attendance_options[selected_att_str]
                    att_data = run_query("SELECT * FROM attendance WHERE id=?", (att_id,), fetch='one')
                    if att_data:
                        with st.form("attendance_form"):
                            check_in_val = datetime.strptime(att_data[2], '%Y-%m-%d %H:%M:%S')
                            check_out_val = datetime.strptime(att_data[3], '%Y-%m-%d %H:%M:%S') if att_data[3] else None
                            new_check_in = st.text_input("Waktu Check In (YYYY-MM-DD HH:MM:SS)", value=check_in_val.strftime('%Y-%m-%d %H:%M:%S'))
                            new_check_out = st.text_input("Waktu Check Out (YYYY-MM-DD HH:MM:SS)", value=check_out_val.strftime('%Y-%m-%d %H:%M:%S') if check_out_val else "")
                            if st.form_submit_button("Simpan Perubahan"):
                                run_query("UPDATE attendance SET check_in=?, check_out=? WHERE id=?", (new_check_in, new_check_out if new_check_out else None, att_id)); st.success("Data diperbarui!"); st.rerun()
            else: st.info("Tidak ada data absensi untuk dikelola.")

    # --- MENU BARU: Kelola & Hapus Data ---
    elif menu == "🗑️ Kelola & Hapus Data":
        st.header("🗑️ Kelola & Hapus Data")
        st.warning("PERHATIAN: Tindakan menghapus data di halaman ini bersifat permanen dan tidak dapat dibatalkan.")
        
        tabs = st.tabs(["Hapus Bahan", "Hapus Produk", "Hapus Pengeluaran", "Hapus Karyawan", "Hapus Absensi"])

        with tabs[0]:
            st.subheader("Hapus Bahan Baku")
            all_ingredients = get_df("SELECT id, name FROM ingredients")
            if not all_ingredients.empty:
                options = all_ingredients['name'].tolist()
                ing_to_delete = st.selectbox("Pilih bahan untuk dihapus", options, key="del_ing_select_main")
                
                if st.button(f"Hapus '{ing_to_delete}'", type="primary", key="del_ing_btn"):
                    ing_id_to_delete = all_ingredients[all_ingredients['name'] == ing_to_delete]['id'].iloc[0]
                    run_query("DELETE FROM ingredients WHERE id=?", (ing_id_to_delete,))
                    st.success(f"Bahan '{ing_to_delete}' telah dihapus."); st.rerun()
            else: st.info("Tidak ada bahan untuk dihapus.")

        with tabs[1]:
            st.subheader("Hapus Produk")
            products_df = get_df("SELECT id, name FROM products")
            if not products_df.empty:
                prod_to_delete = st.selectbox("Pilih produk untuk dihapus", products_df['name'].tolist(), key="del_prod_select_main")
                if st.button(f"Hapus '{prod_to_delete}'", type="primary", key="del_prod_btn"):
                    prod_id_to_delete = products_df[products_df['name'] == prod_to_delete]['id'].iloc[0]
                    run_query("DELETE FROM products WHERE id=?", (prod_id_to_delete,))
                    st.success(f"Produk '{prod_to_delete}' telah dihapus."); st.rerun()
            else: st.info("Tidak ada produk untuk dihapus.")

        with tabs[2]:
            st.subheader("Hapus Pengeluaran")
            expenses_df = get_df("SELECT id, description FROM expenses")
            if not expenses_df.empty:
                exp_to_delete = st.selectbox("Pilih pengeluaran untuk dihapus", expenses_df['description'].tolist(), key="del_exp_select_main")
                if st.button(f"Hapus '{exp_to_delete}'", type="primary", key="del_exp_btn"):
                    exp_id_to_delete = expenses_df[expenses_df['description'] == exp_to_delete]['id'].iloc[0]
                    run_query("DELETE FROM expenses WHERE id=?", (exp_id_to_delete,)); 
                    st.success(f"Pengeluaran '{exp_to_delete}' dihapus.")
                    st.rerun()
            else: st.info("Tidak ada pengeluaran untuk dihapus.")

        with tabs[3]:
            st.subheader("Hapus Karyawan")
            emp_df = get_df("SELECT id, name FROM employees")
            if not emp_df.empty:
                emp_to_delete = st.selectbox("Pilih karyawan untuk dihapus", emp_df['name'].tolist(), key="del_emp_select_main")
                if st.button(f"Hapus '{emp_to_delete}'", type="primary", key="del_emp_btn"):
                    emp_id_to_delete = emp_df[emp_df['name'] == emp_to_delete]['id'].iloc[0]
                    run_query("DELETE FROM employees WHERE id=?", (emp_id_to_delete,)); 
                    st.success(f"Karyawan '{emp_to_delete}' dihapus.")
                    st.rerun()
            else: st.info("Tidak ada karyawan untuk dihapus.")
        
        with tabs[4]:
            st.subheader("Hapus Data Absensi")
            attendance_df = get_df("SELECT a.id, e.name, a.check_in FROM attendance a JOIN employees e ON a.employee_id = e.id ORDER BY a.check_in DESC")
            if not attendance_df.empty:
                attendance_options = {f"ID: {row['id']} - {row['name']} ({row['check_in']})": row['id'] for _, row in attendance_df.iterrows()}
                selected_att_str = st.selectbox("Pilih absensi untuk dihapus", list(attendance_options.keys()), key="del_att_select_main")
                if st.button("Hapus Absensi Ini", type="primary", key="del_att_btn"):
                    att_id = attendance_options[selected_att_str]
                    run_query("DELETE FROM attendance WHERE id=?", (att_id,)); 
                    st.success("Data absensi dihapus.")
                    st.rerun()
            else: st.info("Tidak ada data absensi untuk dihapus.")


# =====================================================================
# --- TITIK MASUK APLIKASI ---
# =====================================================================
if __name__ == "__main__":
    init_db()
    check_login()
