# Toko Bot 🛍️ — Bot Jual Beli Telegram

Bot Telegram untuk jual beli online, lengkap dengan katalog, keranjang, checkout, dan admin panel.

## Fitur

### Untuk Pembeli:
- 🛍️ Katalog produk per kategori
- 🔍 Detail produk (harga, stok, deskripsi)
- 🛒 Keranjang belanja (tambah/kurangi/hapus)
- ✅ Checkout otomatis (nama, alamat, HP, catatan)
- 📸 Upload bukti bayar
- 📋 Riwayat pesanan
- 💬 Chat admin langsung
- 🚚 Info ongkir otomatis

### Untuk Admin:
- 🔧 Panel admin lengkap
- ➕ Tambah/hapus produk via chat
- 📦 Kelola pesanan (proses → kirim → selesai)
- 🔔 Notifikasi pesanan baru
- 📊 Statistik penjualan
- 💬 Forward bukti bayar dari pembeli

## Setup

### 1. Buat Bot Telegram
1. Buka Telegram, cari @BotFather
2. Ketik `/newbot`
3. Ikuti instruksi, dapatkan TOKEN

### 2. Edit config.py
```python
BOT_TOKEN = "TOKEN_DARI_BOTFATHER"
ADMIN_IDS = [ID_TELEGRAM_KAMU]  # Dapat dari @userinfobot
TOKO_NAMA = "Toko Kamu"
TOKO_DESC = "Deskripsi tokomu"
```

### 3. Install & Jalankan
```bash
pip install -r requirements.txt
python bot.py
```

### 4. Hosting 24 Jam
- **Railway.app** — gratis, auto-deploy dari GitHub
- **Render.com** — gratis, mudah setup
- **VPS** — mulai Rp50rb/bulan

## Commands

### Pembeli:
- `/start` — Menu utama

### Admin:
- `/admin` — Panel admin

## Struktur File
```
toko-bot/
├── bot.py           # Bot utama
├── config.py        # Konfigurasi
├── database.py      # Database SQLite
├── requirements.txt # Dependencies
└── README.md        # Dokumentasi
```

## Database

SQLite otomatis dibuat saat pertama kali jalan. Tabel:
- `produk` — daftar produk
- `keranjang` — keranjang per user
- `pesanan` — data pesanan
- `pesanan_item` — detail item pesanan

## Cara Kerja

1. Pembeli buka bot → /start
2. Pilih produk → tambah ke keranjang
3. Checkout → isi data diri
4. Transfer → kirim bukti bayar
5. Admin dapat notif → proses pesanan
6. Admin kirim barang → update status
7. Pembeli dapat notif status pesanan

## Tips

- **Produk**: Tambah via /admin → Tambah Produk
- **Kategori**: Otomatis dari input produk
- **Ongkir**: Atur GRATIS_ONGKIR_MIN di config.py
- **Multi Admin**: Tambah ID di ADMIN_IDS list
- **Broadcast**: Fitur broadcast ke semua pelanggan
