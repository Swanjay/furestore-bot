#!/usr/bin/env python3
"""
Sample produk untuk Furestore.
Jalankan: python3 sample_produk.py
"""

import asyncio
import database as db

SAMPLE_PRODUK = [
    # Fashion
    {"kode": "kaos_001", "nama": "Kaos Polos Premium", "harga": 59900, "stok": 50, "kategori": "Fashion", "deskripsi": "Kaos polos bahan cotton combed 30s. Nyaman dipakai sehari-hari. Tersedia warna hitam & putih."},
    {"kode": "kaos_002", "nama": "Kaos Oversize Sablon", "harga": 79900, "stok": 35, "kategori": "Fashion", "deskripsi": "Kaos oversize dengan sablon design aesthetic. Bahan tebal, cocok buat OOTD harian."},
    {"kode": "hoodie_001", "nama": "Hoodie Non-Zipper", "harga": 149000, "stok": 20, "kategori": "Fashion", "deskripsi": "Hoodie non-zipper bahan fleece premium. Hangat, nyaman, cocok buat santai."},
    {"kode": "kemeja_001", "nama": "Kemeja Flanel Kotak", "harga": 99900, "stok": 25, "kategori": "Fashion", "deskripsi": "Kemeja flanel motif kotak-kotak. Bahan lembut, cocok buat gaya kasual."},

    # Aksesoris
    {"kode": "topi_001", "nama": "Topi Trucker Cap", "harga": 39900, "stok": 40, "kategori": "Aksesoris", "deskripsi": "Topi trucker dengan jaring di belakang. Model kekinian, adjustable."},
    {"kode": "tas_001", "nama": "Tas Selempang Kecil", "harga": 89900, "stok": 15, "kategori": "Aksesoris", "deskripsi": "Tas selempang kecil bahan kanvas. Muat HP, dompet, dan kunci. Cocok jalan-jalan."},
    {"kode": "dompet_001", "nama": "Dompet Kecil Minimalis", "harga": 49900, "stok": 30, "kategori": "Aksesoris", "deskripsi": "Dompet kecil dengan banyak slot kartu. Praktis dan elegan."},

    # Elektronik
    {"kode": "earphone_001", "nama": "TWS Bluetooth", "harga": 79000, "stok": 25, "kategori": "Elektronik", "deskripsi": "Earphone TWS dengan suara jernih. Tahan 4 jam pemakaian. Charging case included."},
    {"kode": "kabel_001", "nama": "Kabel Data USB-C", "harga": 25000, "stok": 60, "kategori": "Elektronik", "deskripsi": "Kabel data USB-C fast charging. Panjang 1 meter. Awet dan kuat."},
    {"kode": "charger_001", "nama": "Charger 18W Fast Charge", "harga": 55000, "stok": 30, "kategori": "Elektronik", "deskripsi": "Charger fast charging 18W. Cocok untuk semua HP Android & iPhone."},
]

async def main():
    await db.init_db()
    
    for p in SAMPLE_PRODUK:
        await db.tambah_produk(**p)
        print(f"✅ {p['nama']} — Rp{p['harga']:,}")
    
    print(f"\n🎉 {len(SAMPLE_PRODUK)} produk Furestore berhasil ditambahkan!")
    print("Jalankan bot: python3 bot.py")

if __name__ == "__main__":
    asyncio.run(main())
