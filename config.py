"""
Config FureStore Bot — Digital Store
"""
import os
from pathlib import Path

# Load .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

# ===== BOT =====
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# ===== ADMIN =====
ADMIN_IDS = [831794275]

# ===== TOKO =====
TOKO_NAMA = "Furestore"
TOKO_DESC = "Jual akun, token & langganan premium!"
TOKO_SAPAAN = "Kak"

# ===== PEMBAYARAN =====
PEMBAYARAN = {
    "DANA": "085600650481",
    "OVO": "085600650481",
    "GOPAY": "085600650481",
    "QRIS": "https://linkaja.example.com/qr/furestore",
}

ADMIN_USERNAME = "@furestore_admin"
