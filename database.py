"""
Database FureStore — Digital Store
Produk digital: Akun, Token, Langganan
Auto-delivery stok: admin tambah stok (akun/token), otomatis kirim ke pembeli
"""

import aiosqlite
import datetime

DB_PATH = "toko.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Tabel produk
        await db.execute("""
            CREATE TABLE IF NOT EXISTS produk (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kode TEXT UNIQUE NOT NULL,
                nama TEXT NOT NULL,
                harga INTEGER NOT NULL,
                deskripsi TEXT DEFAULT '',
                kategori TEXT DEFAULT 'Lainnya',
                aktif INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabel stok (akun/token/kode — satu per baris, auto-kirim ke pembeli)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS stok (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produk_id INTEGER NOT NULL,
                isi TEXT NOT NULL,
                terjual INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (produk_id) REFERENCES produk(id)
            )
        """)

        # Tabel pesanan
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pesanan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT DEFAULT '',
                produk_id INTEGER NOT NULL,
                jumlah INTEGER DEFAULT 1,
                total INTEGER NOT NULL,
                metode_bayar TEXT DEFAULT '',
                status TEXT DEFAULT 'menunggu',
                bukti_bayar TEXT DEFAULT '',
                catatan TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (produk_id) REFERENCES produk(id)
            )
        """)

        await db.commit()

# ===== PRODUK =====

async def tambah_produk(kode, nama, harga, deskripsi='', kategori='Lainnya'):
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO produk (kode, nama, harga, deskripsi, kategori) VALUES (?, ?, ?, ?, ?)",
                (kode, nama, harga, deskripsi, kategori)
            )
            await db.commit()
            return True
        except:
            return False

async def get_produk(kategori=None, aktif_only=True):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if aktif_only:
            if kategori:
                cursor = await db.execute("SELECT * FROM produk WHERE kategori = ? AND aktif = 1", (kategori,))
            else:
                cursor = await db.execute("SELECT * FROM produk WHERE aktif = 1")
        else:
            if kategori:
                cursor = await db.execute("SELECT * FROM produk WHERE kategori = ?", (kategori,))
            else:
                cursor = await db.execute("SELECT * FROM produk")
        rows = await cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            # Hitung stok tersedia (belum terjual)
            stok_cursor = await db.execute(
                "SELECT COUNT(*) FROM stok WHERE produk_id = ? AND terjual = 0", (d['id'],)
            )
            stok_row = await stok_cursor.fetchone()
            d['stok'] = stok_row[0]
            result.append(d)
        return result

async def get_produk_by_id(produk_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM produk WHERE id = ?", (produk_id,))
        r = await cursor.fetchone()
        if r:
            d = dict(r)
            stok_cursor = await db.execute(
                "SELECT COUNT(*) FROM stok WHERE produk_id = ? AND terjual = 0", (d['id'],)
            )
            stok_row = await stok_cursor.fetchone()
            d['stok'] = stok_row[0]
            return d
        return None

async def get_kategori():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT DISTINCT kategori FROM produk WHERE aktif = 1")
        rows = await cursor.fetchall()
        return [r[0] for r in rows]

# ===== STOK (akun/token/kode) =====

async def tambah_stok(produk_id, items: list):
    """Tambah stok - items = list of string (akun:pass, token, kode, dll)"""
    async with aiosqlite.connect(DB_PATH) as db:
        for item in items:
            await db.execute(
                "INSERT INTO stok (produk_id, isi) VALUES (?, ?)",
                (produk_id, item.strip())
            )
        await db.commit()
        return len(items)

async def ambil_stok(produk_id):
    """Ambil 1 stok yang belum terjual (untuk auto-delivery)"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, isi FROM stok WHERE produk_id = ? AND terjual = 0 LIMIT 1",
            (produk_id,)
        )
        row = await cursor.fetchone()
        if row:
            await db.execute("UPDATE stok SET terjual = 1 WHERE id = ?", (row[0],))
            await db.commit()
            return row[1]  # isi stok
        return None

# ===== PESANAN =====

async def buat_pesanan(user_id, username, produk_id, jumlah, total, metode_bayar, catatan=''):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO pesanan (user_id, username, produk_id, jumlah, total, metode_bayar, catatan) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, username, produk_id, jumlah, total, metode_bayar, catatan)
        )
        await db.commit()
        return cursor.lastrowid

async def get_pesanan_by_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT p.*, pr.nama as nama_produk 
               FROM pesanan p 
               JOIN produk pr ON p.produk_id = pr.id 
               WHERE p.user_id = ? ORDER BY p.created_at DESC""",
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_pesanan(status=None, limit=50):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            cursor = await db.execute(
                """SELECT p.*, pr.nama as nama_produk 
                   FROM pesanan p 
                   JOIN produk pr ON p.produk_id = pr.id 
                   WHERE p.status = ? ORDER BY p.created_at DESC LIMIT ?""",
                (status, limit)
            )
        else:
            cursor = await db.execute(
                """SELECT p.*, pr.nama as nama_produk 
                   FROM pesanan p 
                   JOIN produk pr ON p.produk_id = pr.id 
                   ORDER BY p.created_at DESC LIMIT ?""",
                (limit,)
            )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_pesanan_by_id(pesanan_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT p.*, pr.nama as nama_produk, pr.kode as kode_produk
               FROM pesanan p 
               JOIN produk pr ON p.produk_id = pr.id 
               WHERE p.id = ?""",
            (pesanan_id,)
        )
        r = await cursor.fetchone()
        return dict(r) if r else None

async def update_status_pesanan(pesanan_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE pesanan SET status = ? WHERE id = ?", (status, pesanan_id))
        await db.commit()

async def update_bukti_bayar(pesanan_id, bukti_bayar):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE pesanan SET bukti_bayar = ? WHERE id = ?", (bukti_bayar, pesanan_id))
        await db.commit()

# ===== STATISTIK =====

async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM pesanan")
        total_pesanan = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COALESCE(SUM(total), 0) FROM pesanan WHERE status != 'dibatalkan'")
        total_pendapatan = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM produk WHERE aktif = 1")
        total_produk = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM pesanan WHERE status = 'menunggu'")
        pesanan_baru = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM stok WHERE terjual = 0")
        total_stok = (await cursor.fetchone())[0]

        return {
            'total_pesanan': total_pesanan,
            'total_pendapatan': total_pendapatan,
            'total_produk': total_produk,
            'pesanan_baru': pesanan_baru,
            'total_stok': total_stok
        }
