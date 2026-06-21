"""
Database Toko — SQLite async, tabel produk, keranjang, pesanan.
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
                deskripsi TEXT DEFAULT '',
                harga INTEGER NOT NULL,
                stok INTEGER DEFAULT 0,
                foto TEXT DEFAULT '',
                kategori TEXT DEFAULT 'Umum',
                aktif INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Tabel keranjang (per user)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS keranjang (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                produk_id INTEGER NOT NULL,
                jumlah INTEGER DEFAULT 1,
                FOREIGN KEY (produk_id) REFERENCES produk(id)
            )
        """)
        # Tabel pesanan
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pesanan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT DEFAULT '',
                nama TEXT DEFAULT '',
                alamat TEXT DEFAULT '',
                nohp TEXT DEFAULT '',
                total INTEGER DEFAULT 0,
                ongkir INTEGER DEFAULT 0,
                status TEXT DEFAULT 'menunggu',
                bukti_bayar TEXT DEFAULT '',
                catatan TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Tabel item pesanan
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pesanan_item (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pesanan_id INTEGER NOT NULL,
                produk_id INTEGER NOT NULL,
                nama_produk TEXT NOT NULL,
                harga INTEGER NOT NULL,
                jumlah INTEGER DEFAULT 1,
                FOREIGN KEY (pesanan_id) REFERENCES pesanan(id)
            )
        """)
        await db.commit()

# ===== PRODUK =====

async def tambah_produk(kode, nama, harga, stok=0, deskripsi='', foto='', kategori='Umum'):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO produk (kode, nama, harga, stok, deskripsi, foto, kategori) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (kode, nama, harga, stok, deskripsi, foto, kategori)
        )
        await db.commit()

async def get_produk(kode=None, aktif_only=True):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if kode:
            cursor = await db.execute("SELECT * FROM produk WHERE kode = ?", (kode,))
        elif aktif_only:
            cursor = await db.execute("SELECT * FROM produk WHERE aktif = 1 AND stok > 0 ORDER BY kategori, nama")
        else:
            cursor = await db.execute("SELECT * FROM produk ORDER BY kategori, nama")
        return await cursor.fetchall()

async def get_produk_by_id(pid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM produk WHERE id = ?", (pid,))
        return await cursor.fetchone()

async def update_stok(produk_id, delta):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE produk SET stok = MAX(0, stok + ?) WHERE id = ?", (delta, produk_id))
        await db.commit()

async def hapus_produk(kode):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE produk SET aktif = 0 WHERE kode = ?", (kode,))
        await db.commit()

async def get_kategori():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT DISTINCT kategori FROM produk WHERE aktif = 1 AND stok > 0 ORDER BY kategori")
        return [r[0] for r in await cursor.fetchall()]

# ===== KERANJANG =====

async def tambah_keranjang(user_id, produk_id, jumlah=1):
    async with aiosqlite.connect(DB_PATH) as db:
        # Cek apakah sudah ada
        cursor = await db.execute("SELECT id, jumlah FROM keranjang WHERE user_id = ? AND produk_id = ?", (user_id, produk_id))
        existing = await cursor.fetchone()
        if existing:
            await db.execute("UPDATE keranjang SET jumlah = jumlah + ? WHERE id = ?", (jumlah, existing[0]))
        else:
            await db.execute("INSERT INTO keranjang (user_id, produk_id, jumlah) VALUES (?, ?, ?)", (user_id, produk_id, jumlah))
        await db.commit()

async def get_keranjang(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT k.id, k.jumlah, p.kode, p.nama, p.harga, p.stok, p.id as produk_id
            FROM keranjang k JOIN produk p ON k.produk_id = p.id
            WHERE k.user_id = ?
        """, (user_id,))
        return await cursor.fetchall()

async def hapus_keranjang_item(item_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM keranjang WHERE id = ?", (item_id,))
        await db.commit()

async def kosongkan_keranjang(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM keranjang WHERE user_id = ?", (user_id,))
        await db.commit()

async def hitung_total(user_id):
    items = await get_keranjang(user_id)
    return sum(item['harga'] * item['jumlah'] for item in items)

# ===== PESANAN =====

async def buat_pesanan(user_id, username, nama, alamat, nohp, total, ongkir, catatan=''):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO pesanan (user_id, username, nama, alamat, nohp, total, ongkir, catatan) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, username, nama, alamat, nohp, total, ongkir, catatan)
        )
        pesanan_id = cursor.lastrowid
        # Simpan item
        items = await get_keranjang(user_id)
        for item in items:
            await db.execute(
                "INSERT INTO pesanan_item (pesanan_id, produk_id, nama_produk, harga, jumlah) VALUES (?, ?, ?, ?, ?)",
                (pesanan_id, item['produk_id'], item['nama'], item['harga'], item['jumlah'])
            )
            await update_stok(item['produk_id'], -item['jumlah'])
        await kosongkan_keranjang(user_id)
        await db.commit()
        return pesanan_id

async def get_pesanan(status=None, limit=20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            cursor = await db.execute("SELECT * FROM pesanan WHERE status = ? ORDER BY created_at DESC LIMIT ?", (status, limit))
        else:
            cursor = await db.execute("SELECT * FROM pesanan ORDER BY created_at DESC LIMIT ?", (limit,))
        return await cursor.fetchall()

async def get_pesanan_by_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM pesanan WHERE user_id = ? ORDER BY created_at DESC LIMIT 10", (user_id,))
        return await cursor.fetchall()

async def update_status_pesanan(pesanan_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE pesanan SET status = ? WHERE id = ?", (status, pesanan_id))
        await db.commit()

async def get_detail_pesanan(pesanan_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM pesanan WHERE id = ?", (pesanan_id,))
        pesanan = await cursor.fetchone()
        cursor2 = await db.execute("SELECT * FROM pesanan_item WHERE pesanan_id = ?", (pesanan_id,))
        items = await cursor2.fetchall()
        return pesanan, items

async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        total_pesanan = (await (await db.execute("SELECT COUNT(*) FROM pesanan")).fetchone())[0]
        total_pendapatan = (await (await db.execute("SELECT COALESCE(SUM(total),0) FROM pesanan WHERE status != 'dibatalkan'")).fetchone())[0]
        total_produk = (await (await db.execute("SELECT COUNT(*) FROM produk WHERE aktif = 1")).fetchone())[0]
        pesanan_baru = (await (await db.execute("SELECT COUNT(*) FROM pesanan WHERE status = 'menunggu'")).fetchone())[0]
        return {
            "total_pesanan": total_pesanan,
            "total_pendapatan": total_pendapatan,
            "total_produk": total_produk,
            "pesanan_baru": pesanan_baru
        }
