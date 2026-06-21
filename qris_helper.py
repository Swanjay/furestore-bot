"""
QRIS Helper — Generate QR Code untuk pembayaran
"""
import qrcode
from io import BytesIO
import os, datetime

MERCHANT_ID = os.getenv("QRIS_MERCHANT", "00000012345678901234")
MERCHANT_NAME = "FURESTORE"

def generate_qris(amount, order_id):
    """Generate QR code sebagai gambar untuk pembayaran dengan nominal tetap"""
    # Format QRIS Indonesia (simplified EMVCo QRIS string)
    # Merchant Info + Amount
    merchant_info = f"ID153.M{MERCHANT_ID}"
    amount_str = f"{amount}"
    
    # Build EMVCo-compatible payload (simplified)
    payload_parts = [
        "00020101",          # Payload Format Indicator
        "010212",            # Point of Initiation Method (dynamic)
        f"30{len(merchant_info):02d}{merchant_info}",  # Merchant Account Info
        f"5303360",          # Transaction Currency (IDR)
        f"54{len(amount_str):02d}{amount_str}",        # Transaction Amount
        "5802ID",            # Country Code
    ]
    
    # Add timestamp for unique QR
    now = datetime.datetime.now()
    tag62 = f"62{len(f'05{order_id}'):02d}05{order_id}"
    payload_parts.append(tag62)
    
    # Join all parts
    qr_data = "".join(payload_parts)
    
    # Generate QR code image
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save to file
    path = f"/tmp/qris_{order_id}.png"
    img.save(path)
    return path

def generate_qris_simple(amount, order_id):
    """Generate QR sederhana yang berisi info pembayaran"""
    # Simple QR code with payment info text
    payment_info = f"""
=== PEMBAYARAN FURESTORE ===
Nomor Pesanan: #{order_id}
Total: Rp{amount:,}
Merchant: {MERCHANT_NAME}

Kode ini berisi informasi pembayaran.
Silakan transfer sesuai nominal di atas.
============================
"""
    
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=8, border=4)
    qr.add_data(payment_info)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    path = f"/tmp/qris_{order_id}.png"
    img.save(path)
    return path

def get_payment_summary(amount, order_id, metode):
    """Generate teks ringkasan pembayaran"""
    teks = f"""
━━━━━━━━━━━━━━━━━━
≡ *PEMBAYARAN*
━━━━━━━━━━━━━━━━━━

Pesanan: *#{order_id}*
Nominal: *Rp{amount:,}*
Metode: *{metode}*

━━━━━━━━━━━━━━━━━━

⚠️ *PENTING:*
• Transfer sesuai nominal di atas
• Tanpa .00 atau bulat-bulat
• Contoh: Rp25.000 (bukan Rp25.000,00)

📸 Kirim *bukti bayar* (screenshot) setelah transfer.
Admin akan verifikasi & akun langsung dikirim otomatis!
━━━━━━━━━━━━━━━━━━
"""
    return teks
