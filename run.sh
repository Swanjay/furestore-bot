#!/bin/bash
# Jalankan bot dengan auto-restart jika crash
echo "🚀 Toko Bot — Starting..."
echo "━━━━━━━━━━━━━━━━━━"

# Stop instance lama
pkill -f "python3 bot.py" 2>/dev/null

# Install dependencies
pip3 install -r requirements.txt -q 2>/dev/null

# Inisialisasi sample produk (tambahin kalau db baru)
python3 -c "import sqlite3; conn=sqlite3.connect('toko.db'); c=conn.execute('SELECT COUNT(*) FROM produk'); count=c.fetchone()[0]; print(f'Produk di DB: {count}'); exit(0 if count>0 else 1)" 2>/dev/null || echo "Menambahkan sample..." && python3 sample_produk.py 2>/dev/null

# Start bot
echo "✅ Bot siap! Jalanin dengan: nohup python3 bot.py > bot.log 2>&1 &"
echo ""
echo "Atau langsung: python3 bot.py"
