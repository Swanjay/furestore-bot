#!/usr/bin/env python3
"""Sample produk digital untuk Furestore"""
import asyncio, sys
sys.path.insert(0, '/home/ubuntu/toko-bot')
import database as db

PRODUK = [
    # Akun Premium
    {"kode": "netflix_001", "nama": "Netflix Premium", "harga": 25000, "kategori": "Akun Premium", "deskripsi": "Akun Netflix Premium. Tonton semua series & film. Durasi: 30 hari."},
    {"kode": "spotify_001", "nama": "Spotify Premium", "harga": 15000, "kategori": "Akun Premium", "deskripsi": "Spotify Premium individual. Musik tanpa iklan. Durasi: 30 hari."},
    {"kode": "canva_001", "nama": "Canva Pro", "harga": 18000, "kategori": "Akun Premium", "deskripsi": "Canva Pro 1 bulan. Semua fitur premium + template pro."},
    {"kode": "chatgpt_001", "nama": "ChatGPT Plus", "harga": 35000, "kategori": "Akun Premium", "deskripsi": "ChatGPT Plus. GPT-4, DALL-E, browsing. 1 akun share."},
    {"kode": "capcut_001", "nama": "CapCut Pro", "harga": 12000, "kategori": "Akun Premium", "deskripsi": "CapCut Pro. Editing video tanpa watermark. 30 hari."},
    
    # Token & Voucher
    {"kode": "token_pln", "nama": "Token PLN", "harga": 20000, "kategori": "Token & Voucher", "deskripsi": "Token listrik PLN Rp20.000. Masukkan nomor meter setelah pembelian."},
    {"kode": "voucher_gopay", "nama": "Voucher GoPay", "harga": 50000, "kategori": "Token & Voucher", "deskripsi": "Voucher GoPay Rp50.000. Langsung masuk akun GoPay."},
    {"kode": "pulsa_telkomsel", "nama": "Pulsa Telkomsel 50k", "harga": 52000, "kategori": "Token & Voucher", "deskripsi": "Pulsa Telkomsel Rp50.000. Langsung masuk. Kirim nomor HP setelah beli."},
    
    # Langganan
    {"kode": "youtube_prem", "nama": "YouTube Premium", "harga": 20000, "kategori": "Langganan", "deskripsi": "YouTube Premium. Tanpa iklan + YouTube Music. 30 hari."},
    {"kode": "viu_prem", "nama": "Viu Premium", "harga": 10000, "kategori": "Langganan", "deskripsi": "Viu Premium. Drama Korea & konten Asia. 30 hari."},
    {"kode": "wetv_prem", "nama": "WeTV VIP", "harga": 12000, "kategori": "Langganan", "deskripsi": "WeTV VIP. Drama China & anime. 30 hari."},
]

STOK = [
    # Netflix
    ("netflix_001", "netflix1@gmail.com:nflx2024!"),
    ("netflix_001", "netflix2@gmail.com:nflx2024!"),
    ("netflix_001", "netflix3@gmail.com:nflx2024!"),
    # Spotify
    ("spotify_001", "spotify1@gmail.com:spot123"),
    ("spotify_001", "spotify2@gmail.com:spot123"),
    # Canva
    ("canva_001", "canva1@gmail.com:canva456"),
    ("canva_001", "canva2@gmail.com:canva456"),
    # ChatGPT
    ("chatgpt_001", "chatgpt1@gmail.com:gpt789"),
    # CapCut
    ("capcut_001", "capcut1@gmail.com:capcut321"),
    ("capcut_001", "capcut2@gmail.com:capcut321"),
    # Token
    ("token_pln", "5678901234567890"),
    ("token_pln", "5678901234567891"),
    ("token_pln", "5678901234567892"),
    # GoPay
    ("voucher_gopay", "GOV-ABCD-1234-EFGH"),
    ("voucher_gopay", "GOV-IJKL-5678-MNOP"),
    # Pulsa
    ("pulsa_telkomsel", "081234567890"),
    ("pulsa_telkomsel", "085678901234"),
    # YouTube
    ("youtube_prem", "yt1@gmail.com:yt123"),
    ("youtube_prem", "yt2@gmail.com:yt123"),
    # Viu
    ("viu_prem", "viu1@gmail.com:viu456"),
    # WeTV
    ("wetv_prem", "wetv1@gmail.com:wetv789"),
]

async def main():
    await db.init_db()
    for p in PRODUK:
        await db.tambah_produk(**p)
        print(f"✅ {p['nama']} — {rp(p['harga'])}")
    
    semua = await db.get_produk()
    stok_map = {}
    for s in STOK:
        kode, isi = s
        for p in semua:
            if p['kode'] == kode:
                if p['id'] not in stok_map:
                    stok_map[p['id']] = []
                stok_map[p['id']].append(isi)
                break
    
    total = 0
    for pid, items in stok_map.items():
        n = await db.tambah_stok(pid, items)
        total += n
    
    print(f"\n🎉 {len(PRODUK)} produk + {total} stok ditambahkan!")
    print("Jalankan: python3 bot.py")

def rp(angka):
    return f"Rp{angka:,.0f}".replace(",", ".")

if __name__ == "__main__":
    asyncio.run(main())
