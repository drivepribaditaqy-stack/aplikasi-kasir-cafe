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

def insert_initial_products(conn):
    """Memasukkan daftar produk awal jika tabel produk kosong."""
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        st.info("Daftar produk tidak ditemukan, menambahkan produk awal...")
        products = [
            # COFFEE
            ("Espresso", 10000), ("Americano", 11000), ("Orange Americano", 14000),
            ("Lemon Americano", 14000), ("Cocof (BN Signature)", 15000), ("Coffee Latte", 15000),
            ("Cappuccino", 15000), ("Spanish Latte", 16000), ("Caramel Latte", 16000),
            ("Vanilla Latte", 16000), ("Hazelnut Latte", 16000), ("Butterscotch Latte", 16000),
            ("Tiramisu Latte", 16000), ("Mocca Latte", 16000), ("Coffee Chocolate", 18000),
            ("Taro Coffee Latte", 18000), ("Coffee Gula Aren", 18000), ("Lychee Coffee", 20000),
            ("Markisa Coffee", 20000), ("Raspberry Latte", 20000), ("Strawberry Latte", 20000),
            ("Manggo Latte", 20000), ("Bubblegum Latte", 20000),

            # NON-COFFEE
            ("Lemon Tea", 10000), ("Lychee Tea", 10000), ("Milk Tea", 12000),
            ("Green Tea", 14000), ("Thai Tea", 14000), ("Melon Susu", 14000),
            ("Manggo Susu", 15000), ("Mocca Susu", 15000), ("Orange Susu", 15000),
            ("Taro Susu", 15000), ("Coklat Susu", 15000), ("Vanilla Susu", 15000),
            ("Strawberry Susu", 15000), ("Matcha Susu", 18000), ("Blueberry Susu", 18000),
            ("Bubblegum Susu", 18000), ("Raspberry Susu", 18000), ("Grenadine Susu", 14000),
            ("Banana Susu", 16000),

            # MOCKTAIL
            ("Melon Soda", 10000), ("Manggo Soda", 12000), ("Orange Soda", 12000),
            ("Strawberry Soda", 12000), ("Bluesky Soda", 14000), ("Banana Soda", 16000),
            ("Grenadine Soda", 14000), ("Blueberry Soda", 16000), ("Coffee Bear", 16000),
            ("Mocca Soda", 16000), ("Raspberry Soda", 16000), ("Coffee Soda", 17000),
            ("Strawberry Coffee Soda", 18000), ("Melon Blue Sky", 18000), ("Blue Manggo Soda", 18000),

            # NASI GORENG
            ("Nasi Goreng Kampung", 10000), ("Nasi Goreng Biasa", 10000), ("Nasi Goreng Ayam", 18000),

            # NASI AYAM
            ("Nasi Ayam Sambal Matah", 13000), ("Nasi Ayam Penyet", 13000), ("Nasi Ayam Teriyaki", 15000),

            # MIE
            ("Mie Goreng", 12000), ("Mie Rebus", 12000), ("Mie Nyemek", 12000), ("Bihun Goreng", 12000),

            # BURGER & ROTI BAKAR
            ("Burger Telur", 10000), ("Burger Ayam", 12000), ("Burger Telur + Keju", 13000),
            ("Burger Telur + Ayam", 15000), ("Burger Ayam + Telur + Keju", 18000),
            ("Roti Bakar Coklat", 10000), ("Roti Bakar Strawberry", 10000), ("Roti Bakar Srikaya", 10000),
            ("Roti Bakar Coklat Keju", 12000),

            # SNACK
            ("Kentang Goreng", 12000), ("Nugget", 12000), ("Sosis", 12000),
            ("Mix Platter Jumbo", 35000), ("Tahu/Tempe", 5000),
            
            # ADD-ON
            ("Double Shoot", 3000), ("Yakult", 3000), ("Mineral Water", 4000),
            ("Mineral Water Gelas", 500), ("Nasi Putih", 3000), ("Le Mineralle", 4000)
        ]
        c.executemany("INSERT INTO products (name, price) VALUES (?, ?)", products)
        conn.commit()
        st.success("Daftar produk awal berhasil ditambahkan.")
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
    insert_initial_products(conn) # Panggil fungsi untuk menambahkan produk awal
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
        conn = sqlite3.connect(DB)
        transaction = pd.read_sql_query("SELECT * FROM transactions WHERE id = ?", conn, params=(transaction_id,)).iloc[0]
        items_df = pd.read_sql_query("""
            SELECT p.name, ti.quantity, ti.price_per_unit
            FROM transaction_items ti JOIN products p ON ti.product_id = p.id
            WHERE ti.transaction_id = ?
        """, conn, params=(transaction_id,))
        conn.close()

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, 'Struk Pembayaran', 0, 1, 'C')
        pdf.set_font("Arial", '', 12)
        pdf.cell(0, 10, f"No. Transaksi: {transaction['id']}", 0, 1)
        pdf.cell(0, 10, f"Tanggal: {transaction['transaction_date']}", 0, 1)
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
        pdf.cell(50, 10, f"Rp {transaction['total_amount']:,.0f}", 1, 1)
        pdf.cell(130, 10, 'Metode Bayar', 1)
        pdf.cell(50, 10, transaction['payment_method'], 1, 1)

        return bytes(pdf.output())

    # --- PENAMBAHAN FUNGSI UNTUK EDIT/HAPUS TRANSAKSI ---
    def delete_transaction(transaction_id):
        """Menghapus transaksi dan mengembalikan stok bahan baku."""
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        try:
            c.execute("BEGIN TRANSACTION")
            
            # Ambil item untuk mengembalikan stok
            c.execute("SELECT product_id, quantity FROM transaction_items WHERE transaction_id=?", (transaction_id,))
            items_to_restock = c.fetchall()
            
            for product_id, quantity in items_to_restock:
                c.execute("SELECT ingredient_id, qty_per_unit FROM recipes WHERE product_id=?", (product_id,))
                ingredients_to_restock = c.fetchall()
                for ing_id, qty_per_unit in ingredients_to_restock:
                    c.execute("UPDATE ingredients SET stock = stock + ? WHERE id=?", (qty_per_unit * quantity, ing_id))

            # Hapus item dan transaksi
            c.execute("DELETE FROM transaction_items WHERE transaction_id=?", (transaction_id,))
            c.execute("DELETE FROM transactions WHERE id=?", (transaction_id,))
            
            conn.commit()
            return True, "Transaksi berhasil dihapus dan stok dikembalikan."
        except Exception as e:
            conn.rollback()
            return False, f"Gagal menghapus transaksi: {e}"
        finally:
            conn.close()

    def update_transaction_info(transaction_id, new_date, new_payment_method):
        """Memperbarui info dasar transaksi (tanggal dan metode bayar)."""
        try:
            datetime.strptime(new_date, '%Y-%m-%d %H:%M:%S')
            run_query("UPDATE transactions SET transaction_date=?, payment_method=? WHERE id=?", (new_date, new_payment_method, transaction_id))
            return True, "Info transaksi berhasil diperbarui."
        except ValueError:
            return False, "Format tanggal salah. Gunakan YYYY-MM-DD HH:MM:SS"


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
        
        # --- PENAMBAHAN: Logika untuk menampilkan struk setelah transaksi ---
        if 'last_transaction_id' in st.session_state and st.session_state.last_transaction_id:
            st.success(f"Transaksi #{st.session_state.last_transaction_id} berhasil!")
            st.markdown("---")
            
            col1, col2 = st.columns([1,1])
            with col1:
                if st.button("MULAI TRANSAKSI BARU", use_container_width=True, type="primary"):
                    st.session_state.last_transaction_id = None
                    st.rerun()
            with col2:
                pdf_data = generate_receipt_pdf(st.session_state.last_transaction_id)
                st.download_button(
                    label="📥 CETAK STRUK",
                    data=pdf_data,
                    file_name=f"struk_{st.session_state.last_transaction_id}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            st.markdown("---")

        else:
            products_df = get_df("SELECT * FROM products ORDER BY name ASC")
            if products_df.empty:
                st.warning("Belum ada produk.")
            else:
                if 'cart' not in st.session_state: st.session_state.cart = {}
                
                col_products, col_cart_payment = st.columns([2, 1])
                with col_products:
                    search_query = st.text_input("Cari produk...", key="product_search")
                    filtered_products = products_df[products_df['name'].str.contains(search_query, case=False)]
                    
                    num_cols = 4
                    for i in range(0, len(filtered_products), num_cols):
                        cols = st.columns(num_cols)
                        for j in range(num_cols):
                            if i + j < len(filtered_products):
                                product = filtered_products.iloc[i+j]
                                with cols[j]:
                                    st.markdown(f"""
                                    <div class="product-card">
                                        <div class="product-name">{product['name']}</div>
                                        <div class="price">Rp {product['price']:,.0f}</div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    if st.button(f"Tambah", key=f"add_{product['id']}"):
                                        st.session_state.cart[product['name']] = st.session_state.cart.get(product['name'], 0) + 1
                                        st.rerun()

                with col_cart_payment:
                    st.subheader("🛒 Keranjang")
                    if not st.session_state.cart:
                        st.info("Keranjang kosong.")
                    else:
                        total = 0
                        products_map = {row['name']: row['price'] for _, row in products_df.iterrows()}
                        for item, qty in list(st.session_state.cart.items()):
                            price = products_map.get(item, 0)
                            subtotal = price * qty
                            total += subtotal
                            
                            item_col, qty_col, remove_col = st.columns([3,1,1])
                            item_col.write(f"{item} (x{qty})")
                            qty_col.write(f"Rp{subtotal:,.0f}")
                            if remove_col.button("🗑️", key=f"remove_{item}"):
                                st.session_state.cart.pop(item)
                                st.rerun()
                        
                        st.markdown("---")
                        st.metric("Total Belanja", f"Rp {total:,.0f}")
                        
                        with st.form("payment_form"):
                            payment_method = st.selectbox("Metode Pembayaran", ["Cash", "QRIS", "Card"])
                            if st.form_submit_button("Proses Pembayaran", type="primary"):
                                if not st.session_state.cart:
                                    st.warning("Keranjang masih kosong!")
                                else:
                                    success, message, transaction_id = process_atomic_sale(st.session_state.cart, payment_method, st.session_state.user_id)
                                    if success:
                                        st.session_state.last_transaction_id = transaction_id
                                        st.session_state.cart = {}
                                        st.rerun()
                                    else:
                                        st.error(message)

    # --- PERUBAHAN: Menu Riwayat Transaksi dengan Fitur Edit/Hapus ---
    elif menu == "🧾 Riwayat Transaksi":
        st.header("🧾 Riwayat Transaksi")
        
        transactions_df = get_df("""
            SELECT t.id, t.transaction_date, e.name as employee, t.payment_method, t.total_amount
            FROM transactions t LEFT JOIN employees e ON t.employee_id = e.id
            ORDER BY t.id DESC
        """)
        
        if transactions_df.empty:
            st.warning("Belum ada riwayat transaksi.")
        else:
            st.dataframe(transactions_df.style.format({'total_amount': 'Rp {:,.0f}'}), use_container_width=True)
            
            st.markdown("---")
            st.subheader("Kelola Transaksi")
            
            all_ids = [""] + transactions_df['id'].tolist()
            selected_id = st.selectbox("Pilih ID Transaksi untuk dikelola:", options=all_ids)

            if selected_id:
                transaction_details = run_query("SELECT * FROM transactions WHERE id=?", (selected_id,), fetch='one')
                items_df = get_df("""
                    SELECT ti.id as item_id, p.name, ti.quantity, ti.price_per_unit, (ti.quantity * ti.price_per_unit) as subtotal
                    FROM transaction_items ti JOIN products p ON ti.product_id = p.id
                    WHERE ti.transaction_id = ?
                """, (selected_id,))

                st.write(f"**Detail Transaksi #{selected_id}**")
                st.dataframe(items_df.style.format({'price_per_unit': 'Rp {:,.0f}', 'subtotal': 'Rp {:,.0f}'}), use_container_width=True)

                st.markdown("---")
                st.write("**Aksi:**")
                
                action_cols = st.columns(3)
                
                # 1. Cetak Ulang Struk
                pdf_data = generate_receipt_pdf(selected_id)
                action_cols[0].download_button(
                    label="📄 Cetak Ulang Struk", data=pdf_data,
                    file_name=f"struk_{selected_id}.pdf", mime="application/pdf", use_container_width=True
                )

                # 2. Edit Transaksi (Expander)
                with action_cols[1].expander("✏️ Edit Transaksi"):
                    with st.form(f"edit_form_{selected_id}"):
                        st.write("Ubah Info Dasar:")
                        payment_options = ["Cash", "QRIS", "Card"]
                        current_payment_index = payment_options.index(transaction_details[3]) if transaction_details[3] in payment_options else 0
                        
                        new_date = st.text_input("Tanggal & Waktu", value=transaction_details[1])
                        new_payment = st.selectbox("Metode Pembayaran", options=payment_options, index=current_payment_index)
                        
                        if st.form_submit_button("Simpan Perubahan Info"):
                            success, message = update_transaction_info(selected_id, new_date, new_payment)
                            if success: st.success(message); st.rerun()
                            else: st.error(message)
                
                # 3. Hapus Transaksi (Expander)
                with action_cols[2].expander("🗑️ Hapus Transaksi"):
                    st.warning("Aksi ini tidak dapat dibatalkan. Stok bahan baku akan dikembalikan ke inventaris.")
                    if st.checkbox("Saya yakin ingin menghapus transaksi ini", key=f"delete_confirm_{selected_id}"):
                        if st.button("HAPUS SEKARANG", type="primary"):
                            success, message = delete_transaction(selected_id)
                            if success: st.success(message); st.rerun()
                            else: st.error(message)

    elif menu == "📦 Manajemen Stok":
        st.header("📦 Manajemen Stok & Bahan Baku")
        ingredients_df = get_df("SELECT * FROM ingredients")
        
        tab1, tab2 = st.tabs(["Daftar Bahan", "Tambah/Edit Bahan"])
        with tab1:
            st.dataframe(ingredients_df.style.format({'cost_per_unit': 'Rp {:,.2f}', 'pack_price': 'Rp {:,.2f}'}), use_container_width=True)
            st.download_button("📥 Download Data Stok", ingredients_df.to_csv(index=False), "stock_data.csv")

        with tab2:
            edit_id = st.selectbox("Pilih bahan untuk diedit (kosongkan untuk menambah baru):", options=[""] + list(ingredients_df['id']))
            
            ingredient_data = ingredients_df[ingredients_df['id'] == edit_id].iloc[0] if edit_id else None
            
            with st.form("ingredient_form", clear_on_submit=True):
                name = st.text_input("Nama Bahan", value=ingredient_data['name'] if ingredient_data is not None else "")
                unit = st.text_input("Satuan (e.g., gr, ml, pcs)", value=ingredient_data['unit'] if ingredient_data is not None else "")
                stock = st.number_input("Stok Saat Ini", min_value=0.0, value=ingredient_data['stock'] if ingredient_data is not None else 0.0, format="%.2f")
                
                st.markdown("---")
                st.write("**Kalkulator Harga Pokok per Satuan**")
                pack_price = st.number_input("Harga Beli per Kemasan (Rp)", min_value=0.0, value=ingredient_data['pack_price'] if ingredient_data is not None else 0.0, format="%.2f")
                pack_weight = st.number_input("Isi per Kemasan (e.g., 1000 gr, 500 ml)", min_value=0.0, value=ingredient_data['pack_weight'] if ingredient_data is not None else 0.0, format="%.2f")
                cost_per_unit = (pack_price / pack_weight) if pack_weight > 0 else (ingredient_data['cost_per_unit'] if ingredient_data is not None else 0.0)
                st.metric("Harga per Satuan (Otomatis)", f"Rp {cost_per_unit:,.2f}")

                submitted = st.form_submit_button("Simpan Bahan")
                if submitted:
                    if not all([name, unit]): st.error("Nama dan Satuan wajib diisi!")
                    else:
                        if edit_id:
                            update_ingredient(edit_id, name, unit, cost_per_unit, stock, pack_weight, pack_price)
                            st.success(f"Bahan '{name}' berhasil diperbarui.")
                        else:
                            add_ingredient(name, unit, cost_per_unit, stock, pack_weight, pack_price)
                            st.success(f"Bahan '{name}' berhasil ditambahkan.")
                        st.rerun()
            
            if edit_id:
                if st.button("Hapus Bahan Ini", type="primary"):
                    delete_ingredient(edit_id); st.warning(f"Bahan '{ingredient_data['name']}' dihapus!"); st.rerun()

    elif menu == "🍽️ Manajemen Produk":
        st.header("🍽️ Manajemen Produk & Resep")
        products_df = get_df("SELECT * FROM products")
        ingredients_df = get_df("SELECT * FROM ingredients")
        
        tab1, tab2, tab3 = st.tabs(["Daftar Produk", "Tambah/Edit Produk", "Atur Resep"])
        with tab1:
            st.dataframe(products_df.style.format({'price': 'Rp {:,.0f}'}), use_container_width=True)
        with tab2:
            edit_id = st.selectbox("Pilih produk untuk diedit:", options=[""] + list(products_df['id']))
            product_data = products_df[products_df['id'] == edit_id].iloc[0] if edit_id else None
            with st.form("product_form"):
                name = st.text_input("Nama Produk", value=product_data['name'] if product_data is not None else "")
                price = st.number_input("Harga Jual", min_value=0.0, value=product_data['price'] if product_data is not None else 0.0)
                if st.form_submit_button("Simpan Produk"):
                    if edit_id: update_product(edit_id, name, price); st.success("Produk diperbarui!"); st.rerun()
                    else: add_product(name, price); st.success("Produk ditambahkan!"); st.rerun()
            if edit_id:
                if st.button("Hapus Produk Ini", type="primary"): delete_product(edit_id); st.warning("Produk dihapus!"); st.rerun()
        with tab3:
            product_id = st.selectbox("Pilih produk untuk mengatur resep:", options=products_df['id'], format_func=lambda x: products_df[products_df['id'] == x]['name'].iloc[0])
            if product_id:
                recipe_df = get_df("SELECT ingredient_id, qty_per_unit FROM recipes WHERE product_id=?", (product_id,))
                recipe_dict = dict(zip(recipe_df['ingredient_id'], recipe_df['qty_per_unit']))
                
                with st.form("recipe_form"):
                    st.write(f"**Resep untuk: {products_df[products_df['id'] == product_id]['name'].iloc[0]}**")
                    ingredients_data = {}
                    for _, ing in ingredients_df.iterrows():
                        ingredients_data[ing['id']] = st.number_input(f"{ing['name']} ({ing['unit']})", value=recipe_dict.get(ing['id'], 0.0), min_value=0.0, key=f"ing_{ing['id']}")
                    if st.form_submit_button("Simpan Resep"):
                        set_recipe(product_id, ingredients_data); st.success("Resep berhasil disimpan!"); st.rerun()

    elif menu == "📈 Laporan":
        st.header("📈 Laporan Penjualan & Keuangan")
        today = date.today()
        d_start = st.date_input("Dari Tanggal", today.replace(day=1))
        d_end = st.date_input("Sampai Tanggal", today)
        
        if d_start and d_end:
            start_str, end_str = d_start.strftime("%Y-%m-%d"), d_end.strftime("%Y-%m-%d")
            
            sales_df = get_df("""
                SELECT date(transaction_date) as date, SUM(total_amount) as total_sales
                FROM transactions WHERE date(transaction_date) BETWEEN ? AND ? GROUP BY date(transaction_date)
            """, (start_str, end_str))
            
            expenses_df = get_df("""
                SELECT date, SUM(amount) as total_expenses
                FROM expenses WHERE date BETWEEN ? AND ? GROUP BY date
            """, (start_str, end_str))

            if not sales_df.empty:
                fig = go.Figure()
                fig.add_trace(go.Bar(x=sales_df['date'], y=sales_df['total_sales'], name='Penjualan'))
                if not expenses_df.empty:
                    fig.add_trace(go.Bar(x=expenses_df['date'], y=expenses_df['total_expenses'], name='Pengeluaran'))
                st.plotly_chart(fig, use_container_width=True)

                total_sales = sales_df['total_sales'].sum()
                total_expenses = expenses_df['total_expenses'].sum()
                
                kpi1, kpi2, kpi3 = st.columns(3)
                kpi1.metric("Total Omset", f"Rp {total_sales:,.0f}")
                kpi2.metric("Total Pengeluaran", f"Rp {total_expenses:,.0f}")
                kpi3.metric("Profit Kotor", f"Rp {total_sales - total_expenses:,.0f}")

                st.subheader("Produk Terlaris")
                best_selling_df = get_df("""
                    SELECT p.name, SUM(ti.quantity) as total_sold
                    FROM transaction_items ti JOIN products p ON ti.product_id = p.id
                    JOIN transactions t ON ti.transaction_id = t.id
                    WHERE date(t.transaction_date) BETWEEN ? AND ?
                    GROUP BY p.name ORDER BY total_sold DESC LIMIT 10
                """, (start_str, end_str))
                st.dataframe(best_selling_df)
            else:
                st.info("Tidak ada data penjualan pada rentang tanggal yang dipilih.")

    elif menu == "💸 Pengeluaran":
        st.header("💸 Catat Pengeluaran")
        expenses_df = get_df("SELECT * FROM expenses ORDER BY date DESC")
        
        tab1, tab2 = st.tabs(["Riwayat Pengeluaran", "Tambah/Edit Pengeluaran"])
        with tab1:
            st.dataframe(expenses_df.style.format({'amount': 'Rp {:,.0f}'}), use_container_width=True)
            st.download_button("📥 Download Data Pengeluaran", expenses_df.to_csv(index=False), "expenses_data.csv")
        with tab2:
            edit_id = st.selectbox("Pilih pengeluaran untuk diedit:", options=[""] + list(expenses_df['id']))
            expense_data = expenses_df[expenses_df['id'] == edit_id].iloc[0] if edit_id else None
            
            with st.form("expense_form", clear_on_submit=True):
                date_val = datetime.strptime(expense_data['date'], '%Y-%m-%d').date() if expense_data is not None else date.today()
                
                exp_date = st.date_input("Tanggal", value=date_val)
                category = st.text_input("Kategori", value=expense_data['category'] if expense_data is not None else "")
                description = st.text_area("Deskripsi", value=expense_data['description'] if expense_data is not None else "")
                amount = st.number_input("Jumlah (Rp)", min_value=0.0, value=expense_data['amount'] if expense_data is not None else 0.0)
                payment_method = st.selectbox("Metode Bayar", ["Cash", "Transfer"], index=["Cash", "Transfer"].index(expense_data['payment_method']) if expense_data is not None else 0)
                
                if st.form_submit_button("Simpan Pengeluaran"):
                    date_str = exp_date.strftime('%Y-%m-%d')
                    if edit_id:
                        update_expense(edit_id, date_str, category, description, amount, payment_method)
                        st.success("Pengeluaran diperbarui!")
                    else:
                        add_expense(date_str, category, description, amount, payment_method)
                        st.success("Pengeluaran ditambahkan!")
                    st.rerun()

            if edit_id:
                if st.button("Hapus Pengeluaran Ini", type="primary"):
                    delete_expense(edit_id); st.warning("Pengeluaran dihapus!"); st.rerun()
    
    elif menu == "👨‍💼 Manajemen Karyawan" and user_role in ["Admin", "Manager"]:
        st.header("👨‍💼 Manajemen Karyawan")
        employees_df = get_df("SELECT id, name, wage_amount, wage_period, role, is_active FROM employees")
        st.dataframe(employees_df, use_container_width=True)
        
        edit_id = st.selectbox("Pilih karyawan untuk diedit:", options=[""] + list(employees_df['id']))
        emp_data = employees_df[employees_df['id'] == edit_id].iloc[0] if edit_id else None
        
        with st.form("employee_form", clear_on_submit=True):
            name = st.text_input("Nama", value=emp_data['name'] if emp_data is not None else "").lower()
            role = st.selectbox("Role", ["Operator", "Manager", "Admin"], index=["Operator", "Manager", "Admin"].index(emp_data['role']) if emp_data is not None else 0)
            wage_period = st.selectbox("Periode Gaji", ["Per Jam", "Per Hari", "Per Bulan"], index=["Per Jam", "Per Hari", "Per Bulan"].index(emp_data['wage_period']) if emp_data is not None else 0)
            wage_amount = st.number_input("Gaji", min_value=0.0, value=emp_data['wage_amount'] if emp_data is not None else 0.0)
            
            if not edit_id:
                password = st.text_input("Password Baru", type="password")
            
            if st.form_submit_button("Simpan"):
                if edit_id: update_employee(edit_id, name, wage_amount, wage_period, role); st.success("Data diperbarui"); st.rerun()
                else: add_employee(name, wage_amount, wage_period, password, role); st.success("Karyawan ditambahkan"); st.rerun()
        
        if edit_id:
            is_active = emp_data['is_active']
            if st.button("Nonaktifkan" if is_active else "Aktifkan"):
                set_employee_active_status(edit_id, not is_active); st.rerun()

    elif menu == "⏰ Riwayat Absensi" and user_role in ["Admin", "Manager"]:
        st.header("⏰ Riwayat Absensi Karyawan")
        attendance_df = get_df("""SELECT a.id, e.name, a.check_in, a.check_out FROM attendance a JOIN employees e ON a.employee_id = e.id ORDER BY a.id DESC""")
        st.dataframe(attendance_df, use_container_width=True)
        
        edit_id = st.selectbox("Pilih ID Absensi untuk diedit/dihapus:", options=[""] + list(attendance_df['id']))
        if edit_id:
            att_data = attendance_df[attendance_df['id'] == edit_id].iloc[0]
            with st.form(f"att_edit_{edit_id}"):
                st.write(f"Edit Absensi untuk **{att_data['name']}**")
                new_check_in = st.text_input("Check In", value=att_data['check_in'])
                new_check_out = st.text_input("Check Out", value=att_data['check_out'] or "")
                
                c1, c2 = st.columns(2)
                if c1.form_submit_button("Simpan Perubahan"):
                    success, message = update_attendance(edit_id, new_check_in, new_check_out)
                    if success: st.success(message); st.rerun()
                    else: st.error(message)
                
            if st.button("Hapus Absensi Ini", type="primary"):
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
# --- ENTRY POINT ---
# =====================================================================
if __name__ == "__main__":
    init_db()
    check_login()
