"""
Config FureStore Bot
Baca dari environment variables (untuk Railway/VPS)
"""
import os

# ===== BOT TELEGRAM =====
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# ===== ADMIN =====
admin_ids_str = os.getenv("ADMIN_IDS", "831794275")
ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",")]

# ===== INFO TOKO =====
TOKO_NAMA = os.getenv("TOKO_NAMA", "Furestore")
TOKO_DESC = os.getenv("TOKO_DESC", "Toko online terpercaya, murah meriah! 🛍️")
TOKO_SAPAAN = os.getenv("TOKO_SAPAAN", "Kak")

# ===== PENGIRIMAN =====
GRATIS_ONGKIR_MIN = int(os.getenv("GRATIS_ONGKIR_MIN", "80000"))
ONGKIR_DEFAULT = int(os.getenv("ONGKIR_DEFAULT", "12000"))

# ===== PEMBAYARAN =====
REKENING = {
    "DANA": os.getenv("REKENING_DANA", "085600650481 a/n Furestore"),
}
