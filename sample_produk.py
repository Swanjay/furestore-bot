#!/usr/bin/env python3
"""Sample produk digital — FureStore v2"""
import sys; sys.path.insert(0, '/home/ubuntu/toko-bot')
import asyncio, database as db

PRODUK = [
    {"kode": "chatgpt_001", "nama": "ChatGPT Plus", "harga": 35000, "kategori": "Akun Premium", "deskripsi": "ChatGPT Plus. GPT-4, DALL-E. Durasi: 30 hari.", "populer": 1},
    {"kode": "gemini_001", "nama": "Gemini AI", "harga": 20000, "kategori": "Akun Premium", "deskripsi": "Google Gemini Advanced. AI terbaru dari Google.", "populer": 1},
    {"kode": "vidio_plat_001", "nama": "Vidio Platinum TV", "harga": 15000, "kategori": "Akun Premium", "deskripsi": "Vidio Platinum untuk Smart TV. Nonton Liga 1 & series."},
    {"kode": "viu_prem_001", "nama": "Viu Premium", "harga": 10000, "kategori": "Langganan", "deskripsi": "Viu Premium 30 hari. Drama Korea & Asia.", "populer": 1},
    {"kode": "netflix_001", "nama": "Netflix Premium", "harga": 25000, "kategori": "Akun Premium", "deskripsi": "Netflix Premium 1 bulan. 4K Ultra HD."},
    {"kode": "spotify_001", "nama": "Spotify Premium", "harga": 15000, "kategori": "Akun Premium", "deskripsi": "Spotify Premium 1 bulan. Musik tanpa iklan."},
    {"kode": "canva_001", "nama": "Canva Pro", "harga": 18000, "kategori": "Akun Premium", "deskripsi": "Canva Pro 1 bulan. Semua fitur premium."},
    {"kode": "capcut_001", "nama": "CapCut Pro", "harga": 12000, "kategori": "Akun Premium", "deskripsi": "CapCut Pro 30 hari. Tanpa watermark."},
    {"kode": "youtube_001", "nama": "YouTube Premium", "harga": 20000, "kategori": "Langganan", "deskripsi": "YouTube Premium 30 hari. Tanpa iklan + YT Music."},
    {"kode": "wetv_001", "nama": "WeTV VIP", "harga": 12000, "kategori": "Langganan", "deskripsi": "WeTV VIP 30 hari. Drama China & anime."},
    {"kode": "token_pln", "nama": "Token PLN", "harga": 20000, "kategori": "Token & Voucher", "deskripsi": "Token listrik PLN Rp20.000."},
    {"kode": "gopay_50k", "nama": "Voucher GoPay", "harga": 50000, "kategori": "Token & Voucher", "deskripsi": "Voucher GoPay Rp50.000."},
]

STOK = {
    "chatgpt_001": ["chatgpt1@gmail.com:gpt2024!", "chatgpt2@gmail.com:gpt2024!", "chatgpt3@gmail.com:gpt2024!"],
    "gemini_001": ["gemini1@gmail.com:gem123", "gemini2@gmail.com:gem123"],
    "vidio_plat_001": ["vidio1@gmail.com:platinum1", "vidio2@gmail.com:platinum2"] + [f"vidio{i}@email.com:plat{i}" for i in range(3, 23)],
    "viu_prem_001": [f"viu{i}@gmail.com:viu{i}" for i in range(1, 101)],
    "netflix_001": ["nf1@gmail.com:nf2024!", "nf2@gmail.com:nf2024!"],
    "spotify_001": ["sp1@gmail.com:spotify1", "sp2@gmail.com:spotify2", "sp3@gmail.com:spotify3"],
    "canva_001": ["canva1@gmail.com:canva123"],
    "capcut_001": ["capcut1@gmail.com:cap123", "capcut2@gmail.com:cap123"],
    "youtube_001": ["yt1@gmail.com:yt123", "yt2@gmail.com:yt123"],
    "wetv_001": ["wetv1@gmail.com:wetv789"],
    "token_pln": ["5678901234567890", "5678901234567891", "5678901234567892"],
    "gopay_50k": ["GOV-ABCD-1234-EFGH"],
}

async def main():
    await db.init_db()
    total_stok = 0
    for p in PRODUK:
        ok = await db.tambah_produk(p['kode'], p['nama'], p['harga'], p['deskripsi'], p['kategori'], p.get('populer', 0))
        if ok and p['kode'] in STOK:
            semua = await db.get_produk()
            produk = next((x for x in semua if x['kode'] == p['kode']), None)
            if produk:
                n = await db.tambah_stok(produk['id'], STOK[p['kode']])
                total_stok += n
        print(f"{'🔥' if p.get('populer') else '✅'} {p['nama']} — Rp{p['harga']:,}")
    
    print(f"\n🎉 {len(PRODUK)} produk + {total_stok} stok!")

if __name__ == "__main__":
    asyncio.run(main())
