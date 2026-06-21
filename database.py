"""
Database FureStore — v2 Digital Store
"""
import aiosqlite, datetime, hashlib

DB_PATH = "furestore.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS produk (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kode TEXT UNIQUE, nama TEXT, harga INTEGER,
            deskripsi TEXT DEFAULT '', kategori TEXT DEFAULT 'Lainnya',
            stok_awal INTEGER DEFAULT 0, terjual INTEGER DEFAULT 0,
            aktif INTEGER DEFAULT 1, populer INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS stok (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produk_id INTEGER, isi TEXT, terjual INTEGER DEFAULT 0,
            FOREIGN KEY (produk_id) REFERENCES produk(id)
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS pesanan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, username TEXT, produk_id INTEGER,
            jumlah INTEGER DEFAULT 1, total INTEGER NOT NULL,
            metode_bayar TEXT DEFAULT '', status TEXT DEFAULT 'menunggu',
            bukti_bayar TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (produk_id) REFERENCES produk(id)
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS deposit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, nominal INTEGER, status TEXT DEFAULT 'menunggu',
            bukti_bayar TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS saldo (
            user_id INTEGER PRIMARY KEY, jumlah INTEGER DEFAULT 0
        )""")
        await db.commit()

# ===== PRODUK =====
async def tambah_produk(kode, nama, harga, deskripsi='', kategori='Lainnya', populer=0):
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("INSERT INTO produk (kode,nama,harga,deskripsi,kategori,populer) VALUES (?,?,?,?,?,?)",
                (kode, nama, harga, deskripsi, kategori, populer))
            await db.commit()
            return True
        except: return False

async def get_produk(kategori=None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        q = "SELECT *, (stok_awal - terjual) as stok FROM produk WHERE aktif=1"
        params = []
        if kategori:
            q += " AND kategori=?"
            params.append(kategori)
        q += " ORDER BY populer DESC, id ASC"
        cursor = await db.execute(q, params)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_produk_by_id(pid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT *, (stok_awal - terjual) as stok FROM produk WHERE id=?", (pid,))
        r = await cursor.fetchone()
        return dict(r) if r else None

async def get_produk_by_kode(kode):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT *, (stok_awal - terjual) as stok FROM produk WHERE kode=? AND aktif=1", (kode,))
        r = await cursor.fetchone()
        return dict(r) if r else None

async def get_kategori():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT DISTINCT kategori FROM produk WHERE aktif=1")
        return [r[0] for r in await cursor.fetchall()]

# ===== STOK =====
async def tambah_stok(produk_id, items: list):
    async with aiosqlite.connect(DB_PATH) as db:
        for item in items:
            await db.execute("INSERT INTO stok (produk_id, isi) VALUES (?, ?)", (produk_id, item.strip()))
            await db.execute("UPDATE produk SET stok_awal = stok_awal + 1 WHERE id=?", (produk_id,))
        await db.commit()
        return len(items)

async def ambil_stok(produk_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id, isi FROM stok WHERE produk_id=? AND terjual=0 LIMIT 1", (produk_id,))
        row = await cursor.fetchone()
        if row:
            await db.execute("UPDATE stok SET terjual=1 WHERE id=?", (row[0],))
            await db.execute("UPDATE produk SET terjual = terjual + 1 WHERE id=?", (produk_id,))
            await db.commit()
            return row[1]
        return None

async def stok_tersedia(produk_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM stok WHERE produk_id=? AND terjual=0", (produk_id,))
        return (await cursor.fetchone())[0]

# ===== PESANAN =====
async def buat_pesanan(user_id, username, produk_id, jumlah, total, metode_bayar):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO pesanan (user_id,username,produk_id,jumlah,total,metode_bayar) VALUES (?,?,?,?,?,?)",
            (user_id, username, produk_id, jumlah, total, metode_bayar))
        await db.commit()
        return cursor.lastrowid

async def get_pesanan_by_id(pid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT p.*, pr.nama as nama_produk, pr.kode as kode_produk FROM pesanan p JOIN produk pr ON p.produk_id=pr.id WHERE p.id=?",
            (pid,))
        r = await cursor.fetchone()
        return dict(r) if r else None

async def get_pesanan_by_user(user_id, limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT p.*, pr.nama as nama_produk FROM pesanan p JOIN produk pr ON p.produk_id=pr.id WHERE p.user_id=? ORDER BY p.created_at DESC LIMIT ?",
            (user_id, limit))
        return [dict(r) for r in await cursor.fetchall()]

async def get_pesanan(status=None, limit=50):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            cursor = await db.execute(
                "SELECT p.*, pr.nama as nama_produk FROM pesanan p JOIN produk pr ON p.produk_id=pr.id WHERE p.status=? ORDER BY p.created_at DESC LIMIT ?",
                (status, limit))
        else:
            cursor = await db.execute(
                "SELECT p.*, pr.nama as nama_produk FROM pesanan p JOIN produk pr ON p.produk_id=pr.id ORDER BY p.created_at DESC LIMIT ?",
                (limit,))
        return [dict(r) for r in await cursor.fetchall()]

async def update_status_pesanan(pid, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE pesanan SET status=? WHERE id=?", (status, pid))
        await db.commit()

# ===== DEPOSIT & SALDO =====
async def buat_deposit(user_id, nominal):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("INSERT INTO deposit (user_id, nominal) VALUES (?,?)", (user_id, nominal))
        await db.commit()
        return cursor.lastrowid

async def get_deposit_by_id(did):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM deposit WHERE id=?", (did,))
        r = await cursor.fetchone()
        return dict(r) if r else None

async def get_deposit(status=None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            cursor = await db.execute("SELECT * FROM deposit WHERE status=? ORDER BY created_at DESC", (status,))
        else:
            cursor = await db.execute("SELECT * FROM deposit ORDER BY created_at DESC LIMIT 50")
        return [dict(r) for r in await cursor.fetchall()]

async def update_deposit_status(did, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE deposit SET status=? WHERE id=?", (status, did))
        await db.commit()

async def get_saldo(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT jumlah FROM saldo WHERE user_id=?", (user_id,))
        r = await cursor.fetchone()
        return r[0] if r else 0

async def tambah_saldo(user_id, nominal):
    async with aiosqlite.connect(DB_PATH) as db:
        existing = await db.execute("SELECT jumlah FROM saldo WHERE user_id=?", (user_id,))
        r = await existing.fetchone()
        if r:
            await db.execute("UPDATE saldo SET jumlah = jumlah + ? WHERE user_id=?", (nominal, user_id))
        else:
            await db.execute("INSERT INTO saldo (user_id, jumlah) VALUES (?,?)", (user_id, nominal))
        await db.commit()

async def kurangi_saldo(user_id, nominal):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE saldo SET jumlah = jumlah - ? WHERE user_id=?", (nominal, user_id))
        await db.commit()

# ===== STATS =====
async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        pesanan = (await (await db.execute("SELECT COUNT(*) FROM pesanan")).fetchone())[0]
        pendapatan = (await (await db.execute("SELECT COALESCE(SUM(total),0) FROM pesanan WHERE status='selesai'")).fetchone())[0]
        produk = (await (await db.execute("SELECT COUNT(*) FROM produk WHERE aktif=1")).fetchone())[0]
        menunggu = (await (await db.execute("SELECT COUNT(*) FROM pesanan WHERE status='menunggu'")).fetchone())[0]
        stok = (await (await db.execute("SELECT COALESCE(SUM(stok_awal-terjual),0) FROM produk")).fetchone())[0]
        deposit_baru = (await (await db.execute("SELECT COUNT(*) FROM deposit WHERE status='menunggu'")).fetchone())[0]
        return dict(total_pesanan=pesanan, total_pendapatan=pendapatan, total_produk=produk,
                    pesanan_baru=menunggu, total_stok=stok, deposit_baru=deposit_baru)
