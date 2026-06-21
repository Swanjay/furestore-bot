# FureStore Bot — Digital Store Telegram 🤖

Bot Telegram buat jual **akun premium, token, & langganan aplikasi**. Auto-delivery setelah bayar!

## Fitur

### Pembeli:
- 🛍️ Katalog digital (Akun, Token, Langganan)
- 🛒 Beli via katalog atau kode produk
- 💳 Pilih metode bayar (DANA, OVO, GoPay, QRIS)
- 📸 Upload bukti bayar
- 📋 Cek status pesanan
- 🔑 Auto-delivery akun/token setelah verifikasi

### Admin:
- 🔧 Panel admin lengkap
- ➕ Tambah produk (kode, nama, harga, kategori)
- 📦 Tambah stok akun/token (email:pass per baris)
- ✅ Verifikasi pembayaran → otomatis kirim barang
- 📊 Statistik penjualan
- 🔔 Notif pesanan baru

## Setup

1. Buat bot di @BotFather
2. Edit `.env` dengan token & data toko
3. `python3 sample_produk.py` (opsional, untuk test)
4. `python3 bot.py`

## Deploy ke Railway

1. Fork/push repo ini ke GitHub
2. Login railway.app → Deploy from GitHub
3. Set env variables di Railway:
   - `BOT_TOKEN`
   - `ADMIN_IDS`
   - dll (lihat `.env`)
4. Done! Bot jalan 24/7
