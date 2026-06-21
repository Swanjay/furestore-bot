#!/usr/bin/env python3
"""
FureStore Bot — Digital Store Telegram
Jual: Akun Premium, Token, Langganan
Auto-delivery: admin konfirmasi bayar → otomatis kirim akun/token ke pembeli
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

import config
import database as db

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== STATES =====
WAIT_KODE_VOUCHER, WAIT_JUMLAH, WAIT_METODE = range(3)
WAIT_ITEM_STOK = 10
WAIT_PRODUK_KODE, WAIT_PRODUK_NAMA, WAIT_PRODUK_HARGA, WAIT_PRODUK_KATEGORI, WAIT_PRODUK_DESK = range(5)
WAIT_VOUCHER_ISI = 11

# ===== HELPERS =====
def is_admin(user_id):
    return user_id in config.ADMIN_IDS

def rp(angka):
    return f"Rp{angka:,.0f}".replace(",", ".")

# ===== MENU UTAMA =====
def menu_utama():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("≡ Katalog", callback_data="katalog"),
         InlineKeyboardButton("🛒 Beli Via Kode", callback_data="beli_via_kode")],
        [InlineKeyboardButton("📋 Pesanan Saya", callback_data="pesanan_saya"),
         InlineKeyboardButton("💬 Bantuan", callback_data="bantuan")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"Halo {config.TOKO_SAPAAN} {user.first_name}! 🌟\n\n"
        f"Selamat datang di *{config.TOKO_NAMA}*\n"
        f"{config.TOKO_DESC}\n\n"
        f"≡ *Produk Digital:*\n"
        f"• Akun Premium (Netflix, Spotify, Canva, dll)\n"
        f"• Token & Voucher\n"
        f"• Langganan Aplikasi\n\n"
        f"👇 Pilih menu di bawah:"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=menu_utama())
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=menu_utama())

# ===== KATALOG =====
async def katalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    kategoris = await db.get_kategori()
    if not kategoris:
        await q.edit_message_text("≡ Katalog kosong.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Menu", callback_data="menu")]]))
        return
    
    buttons = [[InlineKeyboardButton(f"≡ {k}", callback_data=f"kat_{k}")] for k in kategoris]
    buttons.append([InlineKeyboardButton("≡ Semua", callback_data="kat_Semua")])
    buttons.append([InlineKeyboardButton("← Menu", callback_data="menu")])
    await q.edit_message_text("≡ *Katalog Produk Digital*\nPilih kategori:", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

async def lihat_kategori(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    kat = q.data.split("_", 1)[1]
    
    if kat == "Semua":
        produk = await db.get_produk()
    else:
        produk = await db.get_produk(kategori=kat)
    
    if not produk:
        await q.edit_message_text(f"Belum ada produk di kategori *{kat}*", parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Katalog", callback_data="katalog")]]))
        return
    
    context.user_data['produk_list'] = [dict(p) for p in produk]
    context.user_data['produk_idx'] = 0
    await tampil_produk(q, context)

async def tampil_produk(q, context):
    items = context.user_data.get('produk_list', [])
    idx = context.user_data.get('produk_idx', 0)
    p = items[idx]
    
    stok_hidden = p['stok']  # Simpan di callback data biar gak ribet
    
    text = (
        f"*{p['nama']}*\n\n"
        f"{p['deskripsi'] or '-'}\n\n"
        f"≡ Harga: *{rp(p['harga'])}* /pc\n"
        f"📦 Stok: {p['stok']} unit\n"
        f"≡ Kategori: {p['kategori']}\n"
        f"\n{idx+1}/{len(items)}"
    )
    
    buttons = []
    if p['stok'] > 0:
        buttons.append([InlineKeyboardButton("🛒 Beli", callback_data=f"beli_{p['id']}")])
    
    nav = []
    if idx > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data="produk_prev"))
    if idx < len(items) - 1:
        nav.append(InlineKeyboardButton("➡️", callback_data="produk_next"))
    if nav:
        buttons.append(nav)
    
    buttons.append([InlineKeyboardButton("← Katalog", callback_data="katalog")])
    await q.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

async def produk_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    items = context.user_data.get('produk_list', [])
    idx = context.user_data.get('produk_idx', 0)
    if q.data == "produk_prev":
        context.user_data['produk_idx'] = max(0, idx - 1)
    else:
        context.user_data['produk_idx'] = min(len(items) - 1, idx + 1)
    await tampil_produk(q, context)

# ===== BELI VIA KODE PRODUK =====
async def beli_via_kode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "🛒 *Beli Via Kode*\n\n"
        "Ketik kode produk yang mau dibeli.\n"
        "Contoh: `netflix_001`\n\n"
        "Kode bisa lihat di /admin → Produk",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Menu", callback_data="menu")]])
    )
    return WAIT_KODE_VOUCHER

async def beli_kode_diterima(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kode = update.message.text.strip()
    semua = await db.get_produk()
    produk = next((p for p in semua if p['kode'] == kode), None)
    
    if not produk:
        await update.message.reply_text("❌ Kode tidak ditemukan. Coba lagi atau /start")
        return WAIT_KODE_VOUCHER
    
    if produk['stok'] <= 0:
        await update.message.reply_text("❌ Stok habis. /start untuk lihat produk lain.")
        return ConversationHandler.END
    
    context.user_data['beli_produk'] = dict(produk)
    
    text = (
        f"≡ *{produk['nama']}*\n"
        f"Harga: {rp(produk['harga'])} /pc\n"
        f"Stok: {produk['stok']}\n\n"
        f"Berapa *jumlah* yang mau dibeli?"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    return WAIT_JUMLAH

async def beli_jumlah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        jumlah = int(update.message.text)
        produk = context.user_data.get('beli_produk', {})
        if jumlah > produk.get('stok', 0):
            await update.message.reply_text(f"❌ Stok cuma {produk['stok']}. Masukkan jumlah yang lebih kecil:")
            return WAIT_JUMLAH
        if jumlah < 1:
            await update.message.reply_text("❌ Minimal 1.")
            return WAIT_JUMLAH
        
        context.user_data['beli_jumlah'] = jumlah
        total = produk['harga'] * jumlah
        
        # Pilih metode bayar
        buttons = []
        for metode in config.PEMBAYARAN.keys():
            buttons.append([InlineKeyboardButton(f"≡ {metode}", callback_data=f"metode_{metode}")])
        
        text = (
            f"🛒 *Ringkasan Pesanan*\n\n"
            f"Produk: {produk['nama']}\n"
            f"Jumlah: {jumlah}pc x {rp(produk['harga'])} = *{rp(total)}*\n\n"
            f"Pilih metode pembayaran:"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
        return WAIT_METODE
        
    except ValueError:
        await update.message.reply_text("❌ Masukkan angka saja.")
        return WAIT_JUMLAH

async def beli_pilih_metode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    metode = q.data.split("_")[1]
    user = q.from_user
    produk = context.user_data.get('beli_produk', {})
    jumlah = context.user_data.get('beli_jumlah', 1)
    total = produk['harga'] * jumlah
    
    # Buat pesanan
    pesanan_id = await db.buat_pesanan(
        user_id=user.id,
        username=user.username or '',
        produk_id=produk['id'],
        jumlah=jumlah,
        total=total,
        metode_bayar=metode,
        catatan=''
    )
    
    no_rek = config.PEMBAYARAN.get(metode, "-")
    
    text = (
        f"✅ *Pesanan #{pesanan_id} Dibuat!*\n\n"
        f"Produk: {produk['nama']}\n"
        f"Jumlah: {jumlah}pc\n"
        f"Total: *{rp(total)}*\n\n"
        f"≡ *Transfer ke {metode}:*\n`{no_rek}`\n\n"
        f"📸 *Setelah transfer, kirim FOTO BUKTI BAYAR ke chat ini.*\n"
        f"Nanti akun/token akan langsung dikirim otomatis setelah admin verifikasi!"
    )
    
    await q.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # Notif admin
    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"🔔 *PESANAN BARU #{pesanan_id}*\n\n"
                f"Dari: {user.first_name} (@{user.username or '-'})\n"
                f"Produk: {produk['nama']}\n"
                f"Jumlah: {jumlah}pc\n"
                f"Total: {rp(total)}\n"
                f"Metode: {metode}",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
    
    return ConversationHandler.END

# ===== BELI DARI KATALOG =====
async def beli_dari_katalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    produk_id = int(q.data.split("_")[1])
    produk = await db.get_produk_by_id(produk_id)
    
    if not produk or produk['stok'] <= 0:
        await q.edit_message_text("❌ Stok habis.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Katalog", callback_data="katalog")]]))
        return ConversationHandler.END
    
    context.user_data['beli_produk'] = dict(produk)
    
    text = (
        f"≡ *{produk['nama']}*\n"
        f"Harga: {rp(produk['harga'])} /pc\n"
        f"Stok: {produk['stok']}\n\n"
        f"Berapa *jumlah* yang mau dibeli?"
    )
    await q.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
    return WAIT_JUMLAH

# ===== BELI JUDUL =====
beli_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(beli_via_kode, pattern="^beli_via_kode$"),
        CallbackQueryHandler(beli_dari_katalog, pattern="^beli_"),
    ],
    states={
        WAIT_KODE_VOUCHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, beli_kode_diterima)],
        WAIT_JUMLAH: [MessageHandler(filters.TEXT & ~filters.COMMAND, beli_jumlah)],
        WAIT_METODE: [CallbackQueryHandler(beli_pilih_metode, pattern="^metode_")],
    },
    fallbacks=[CommandHandler("cancel", lambda u,c: (u.message.reply_text("❌ Dibatalkan.", reply_markup=menu_utama()), ConversationHandler.END))],
)

# ===== PESANAN SAYA =====
async def pesanan_saya(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    pesanan = await db.get_pesanan_by_user(q.from_user.id)
    if not pesanan:
        await q.edit_message_text("📋 *Belum ada pesanan.*\nYuk belanja!", parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("≡ Katalog", callback_data="katalog"), InlineKeyboardButton("← Menu", callback_data="menu")]]))
        return
    
    teks = "📋 *Pesanan Saya*\n\n"
    emoji = {"menunggu": "🟡", "diproses": "🔵", "selesai": "✅", "dibatalkan": "❌"}
    
    for p in pesanan:
        e = emoji.get(p['status'], "⚪")
        teks += f"{e} *#{p['id']}* — {p['nama_produk']} x{p['jumlah']}\n"
        teks += f"   {rp(p['total'])} — {p['status'].upper()}\n   {p['created_at'][:16]}\n\n"
    
    await q.edit_message_text(teks, parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Menu", callback_data="menu")]]))

# ===== BANTUAN =====
async def bantuan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    teks = (
        f"💬 *Bantuan {config.TOKO_NAMA}*\n\n"
        f"1. Pilih produk di Katalog\n"
        f"2. Tentukan jumlah\n"
        f"3. Pilih metode bayar\n"
        f"4. Transfer ke no. rekening\n"
        f"5. Kirim bukti bayar (foto)\n"
        f"6. Admin verifikasi → akun/token dikirim otomatis!\n\n"
        f"⏳ Proses verifikasi max 1x24 jam\n"
        f"💬 Admin: {config.ADMIN_USERNAME}"
    )
    await q.edit_message_text(teks, parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Menu", callback_data="menu")]]))

# ===== FOTO (BUKTI BAYAR) =====
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Kasih tahu user
    await update.message.reply_text("✅ Bukti bayar diterima! Admin akan verifikasi sebentar lagi.")
    
    # Forward ke admin + info user
    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"📸 *Bukti Bayar Baru*\nDari: {user.first_name} (@{user.username or '-'}) | ID: `{user.id}`\n\nCek /admin untuk verifikasi",
                parse_mode=ParseMode.MARKDOWN
            )
            await context.bot.forward_message(admin_id, user.id, update.message.message_id)
        except:
            pass

# ===== ADMIN PANEL =====
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Bukan admin.")
        return
    
    stats = await db.get_stats()
    teks = (
        f"🔧 *Admin — {config.TOKO_NAMA}*\n\n"
        f"≡ Total Pesanan: {stats['total_pesanan']}\n"
        f"💰 Pendapatan: {rp(stats['total_pendapatan'])}\n"
        f"≡ Produk: {stats['total_produk']} | Stok: {stats['total_stok']} unit\n"
        f"🔔 Menunggu: {stats['pesanan_baru']}\n"
    )
    buttons = [
        [InlineKeyboardButton("≡ Kelola Produk", callback_data="admin_produk")],
        [InlineKeyboardButton("🔔 Pesanan Baru", callback_data="admin_pesanan_baru"),
         InlineKeyboardButton("≡ Semua Pesanan", callback_data="admin_semua_pesanan")],
        [InlineKeyboardButton("➕ Tambah Produk", callback_data="admin_tambah_produk")],
        [InlineKeyboardButton("📦 Tambah Stok", callback_data="admin_tambah_stok")],
        [InlineKeyboardButton("≡ Statistik", callback_data="admin_stats")]
    ]
    await update.message.reply_text(teks, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

async def admin_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    stats = await db.get_stats()
    teks = (
        f"🔧 *Admin — {config.TOKO_NAMA}*\n\n"
        f"≡ Pesanan: {stats['total_pesanan']} | 💰 {rp(stats['total_pendapatan'])}\n"
        f"≡ Produk: {stats['total_produk']} | Stok: {stats['total_stok']} unit\n"
        f"🔔 Menunggu: {stats['pesanan_baru']}\n"
    )
    buttons = [
        [InlineKeyboardButton("≡ Kelola Produk", callback_data="admin_produk")],
        [InlineKeyboardButton("🔔 Pesanan Baru", callback_data="admin_pesanan_baru"),
         InlineKeyboardButton("≡ Semua Pesanan", callback_data="admin_semua_pesanan")],
        [InlineKeyboardButton("➕ Tambah Produk", callback_data="admin_tambah_produk")],
        [InlineKeyboardButton("📦 Tambah Stok", callback_data="admin_tambah_stok")],
        [InlineKeyboardButton("≡ Statistik", callback_data="admin_stats")]
    ]
    await q.edit_message_text(teks, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

async def admin_produk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    semua = await db.get_produk(aktif_only=False)
    if not semua:
        await q.edit_message_text("Belum ada produk.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Tambah Produk", callback_data="admin_tambah_produk")],
            [InlineKeyboardButton("← Admin", callback_data="admin_back")]]))
        return
    
    teks = "≡ *Daftar Produk*\n\n"
    for p in semua:
        status = "✅" if p['aktif'] and p['stok'] > 0 else "❌"
        teks += f"{status} `{p['kode']}` — *{p['nama']}*\n   {rp(p['harga'])} | Stok: {p['stok']} | {p['kategori']}\n\n"
    
    await q.edit_message_text(teks, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Tambah Produk", callback_data="admin_tambah_produk")],
        [InlineKeyboardButton("📦 Tambah Stok", callback_data="admin_tambah_stok")],
        [InlineKeyboardButton("← Admin", callback_data="admin_back")]]))

async def admin_pesanan_baru(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    pesanan = await db.get_pesanan(status='menunggu')
    if not pesanan:
        await q.edit_message_text("✅ Semua pesanan sudah diproses.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Admin", callback_data="admin_back")]]))
        return
    
    teks = "🔔 *Pesanan Menunggu Verifikasi*\n\n"
    buttons = []
    for p in pesanan:
        teks += f"#{p['id']} — {p['nama_produk']} x{p['jumlah']} — {rp(p['total'])} — {p['username']}\n"
        buttons.append([
            InlineKeyboardButton(f"≡ #{p['id']}", callback_data=f"detail_{p['id']}"),
            InlineKeyboardButton("✅ Verif", callback_data=f"verif_{p['id']}"),
            InlineKeyboardButton("❌ Tolak", callback_data=f"tolak_{p['id']}")
        ])
    buttons.append([InlineKeyboardButton("← Admin", callback_data="admin_back")])
    
    await q.edit_message_text(teks, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

async def admin_semua_pesanan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    pesanan = await db.get_pesanan(limit=20)
    if not pesanan:
        await q.edit_message_text("Belum ada pesanan.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Admin", callback_data="admin_back")]]))
        return
    
    emoji = {"menunggu": "🟡", "diproses": "🔵", "selesai": "✅", "dibatalkan": "❌"}
    teks = "≡ *Semua Pesanan*\n\n"
    buttons = []
    for p in pesanan:
        e = emoji.get(p['status'], "⚪")
        teks += f"{e} #{p['id']} — {p['nama_produk']} x{p['jumlah']} — {rp(p['total'])} — {p['status']}\n"
        buttons.append([InlineKeyboardButton(f"≡ Detail #{p['id']}", callback_data=f"detail_{p['id']}")])
    buttons.append([InlineKeyboardButton("← Admin", callback_data="admin_back")])
    
    await q.edit_message_text(teks, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

async def detail_pesanan_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    pesanan_id = int(q.data.split("_")[1])
    p = await db.get_pesanan_by_id(pesanan_id)
    if not p:
        await q.edit_message_text("Pesanan tidak ditemukan.")
        return
    
    emoji = {"menunggu": "🟡", "diproses": "🔵", "selesai": "✅", "dibatalkan": "❌"}
    teks = (
        f"≡ *Pesanan #{p['id']}*\n\n"
        f"Status: {emoji.get(p['status'])} *{p['status'].upper()}*\n"
        f"Pemesan: {p['username'] or '?'} (ID: `{p['user_id']}`)\n"
        f"Produk: {p['nama_produk']}\n"
        f"Jumlah: {p['jumlah']}pc\n"
        f"Total: {rp(p['total'])}\n"
        f"Metode: {p['metode_bayar']}\n"
        f"Catatan: {p['catatan'] or '-'}\n"
        f"Waktu: {p['created_at'][:16]}"
    )
    
    buttons = []
    if is_admin(q.from_user.id):
        if p['status'] == 'menunggu':
            buttons.append([InlineKeyboardButton("✅ Verif & Kirim", callback_data=f"verif_{p['id']}"),
                           InlineKeyboardButton("❌ Tolak", callback_data=f"tolak_{p['id']}")])
        elif p['status'] == 'selesai':
            buttons.append([InlineKeyboardButton("≡ Kirim Ulang", callback_data=f"kirim_ulang_{p['id']}")])
    buttons.append([InlineKeyboardButton("← Kembali", callback_data="admin_back")])
    
    await q.edit_message_text(teks, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

async def verif_pesanan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    pesanan_id = int(q.data.split("_")[1])
    
    if not is_admin(q.from_user.id):
        await q.answer("⛔", show_alert=True)
        return
    
    p = await db.get_pesanan_by_id(pesanan_id)
    if not p:
        await q.answer("❌ Tidak ditemukan")
        return
    
    # Ambil stok
    item_dikirim = await db.ambil_stok(p['produk_id'])
    
    if not item_dikirim:
        # Stok habis, kirim manual nanti
        await q.answer("❌ Stok habis! Tambah stok dulu.")
        return
    
    # Update status
    await db.update_status_pesanan(pesanan_id, 'selesai')
    await q.answer("✅ Terverifikasi! Akun dikirim ke pembeli.", show_alert=True)
    
    # Kirim barang ke pembeli
    try:
        # Format isi stok (bisa akun:pass, token, atau kode)
        if ":" in item_dikirim:
            akun, pw = item_dikirim.split(":", 1)
            teks_kirim = (
                f"✅ *Pesanan #{pesanan_id} — Terverifikasi!*\n\n"
                f"Produk: {p['nama_produk']}\n"
                f"Jumlah: {p['jumlah']}pc\n\n"
                f"🔑 *Akun Kamu:*\n"
                f"Email/User: `{akun}`\n"
                f"Password: `{pw}`\n\n"
                f"📝 *Cara Login:*\n"
                f"1. Buka website/aplikasi\n"
                f"2. Login pakai data di atas\n"
                f"3. Nikmati layanan premium!\n\n"
                f"💬 Admin: {config.ADMIN_USERNAME}"
            )
        elif item_dikirim.startswith("http"):
            teks_kirim = (
                f"✅ *Pesanan #{pesanan_id} — Terverifikasi!*\n\n"
                f"Produk: {p['nama_produk']}\n"
                f"Jumlah: {p['jumlah']}pc\n\n"
                f"🔗 *Link:* {item_dikirim}\n\n"
                f"💬 Admin: {config.ADMIN_USERNAME}"
            )
        else:
            teks_kirim = (
                f"✅ *Pesanan #{pesanan_id} — Terverifikasi!*\n\n"
                f"Produk: {p['nama_produk']}\n"
                f"Jumlah: {p['jumlah']}pc\n\n"
                f"🔑 *Kode/Token Kamu:*\n`{item_dikirim}`\n\n"
                f"💬 Admin: {config.ADMIN_USERNAME}"
            )
        
        await context.bot.send_message(p['user_id'], teks_kirim, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Gagal kirim barang: {e}")
    
    # Refresh detail
    context.callback_query = q
    await detail_pesanan_admin(update, context)

async def tolak_pesanan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    pesanan_id = int(q.data.split("_")[1])
    
    if not is_admin(q.from_user.id):
        await q.answer("⛔")
        return
    
    p = await db.get_pesanan_by_id(pesanan_id)
    if not p:
        await q.answer("❌")
        return
    
    await db.update_status_pesanan(pesanan_id, 'dibatalkan')
    await q.answer("❌ Pesanan dibatalkan.", show_alert=True)
    
    # Notif pembeli
    try:
        await context.bot.send_message(
            p['user_id'],
            f"❌ *Pesanan #{pesanan_id} Dibatalkan*\n\n"
            f"Produk: {p['nama_produk']}\n"
            f"Total: {rp(p['total'])}\n\n"
            f"Hubungi admin: {config.ADMIN_USERNAME} untuk info lebih lanjut.",
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        pass
    
    context.callback_query = q
    await detail_pesanan_admin(update, context)

# ===== TAMBAH PRODUK =====
async def admin_tambah_produk_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "➕ *Tambah Produk Baru*\n\nKetik *kode produk* (unik, tanpa spasi, contoh: `netflix_001`)",
        parse_mode=ParseMode.MARKDOWN
    )
    return WAIT_PRODUK_KODE

async def admin_tambah_kode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_kode'] = update.message.text.strip().replace(" ", "_")
    await update.message.reply_text("≡ *Nama produk?*", parse_mode=ParseMode.MARKDOWN)
    return WAIT_PRODUK_NAMA

async def admin_tambah_nama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_nama'] = update.message.text
    await update.message.reply_text("💰 *Harga?* (angka saja, contoh: `50000`)", parse_mode=ParseMode.MARKDOWN)
    return WAIT_PRODUK_HARGA

async def admin_tambah_harga(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        harga = int(update.message.text.replace(".", "").replace("Rp", "").replace("rp", ""))
        context.user_data['new_harga'] = harga
    except:
        await update.message.reply_text("❌ Harga harus angka!")
        return WAIT_PRODUK_HARGA
    await update.message.reply_text("≡ *Kategori?* (Akun | Token | Langganan | Lainnya)", parse_mode=ParseMode.MARKDOWN)
    return WAIT_PRODUK_KATEGORI

async def admin_tambah_kategori(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_kategori'] = update.message.text.title()
    await update.message.reply_text("📝 *Deskripsi?* (ketik - jika tidak)", parse_mode=ParseMode.MARKDOWN)
    return WAIT_PRODUK_DESK

async def admin_tambah_desk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    deskripsi = update.message.text if update.message.text != '-' else ''
    ok = await db.tambah_produk(
        kode=context.user_data['new_kode'],
        nama=context.user_data['new_nama'],
        harga=context.user_data['new_harga'],
        deskripsi=deskripsi,
        kategori=context.user_data['new_kategori']
    )
    if ok:
        teks = (
            f"✅ *Produk Ditambahkan!*\n\n"
            f"Kode: `{context.user_data['new_kode']}`\n"
            f"Nama: {context.user_data['new_nama']}\n"
            f"Harga: {rp(context.user_data['new_harga'])}\n"
            f"Kategori: {context.user_data['new_kategori']}"
        )
    else:
        teks = "❌ Gagal. Kode mungkin sudah ada."
    
    await update.message.reply_text(teks, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Tambah Lagi", callback_data="admin_tambah_produk")],
        [InlineKeyboardButton("← Admin", callback_data="admin_back")]]))
    return ConversationHandler.END

tambah_produk_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(admin_tambah_produk_start, pattern="^admin_tambah_produk$")],
    states={
        WAIT_PRODUK_KODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_tambah_kode)],
        WAIT_PRODUK_NAMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_tambah_nama)],
        WAIT_PRODUK_HARGA: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_tambah_harga)],
        WAIT_PRODUK_KATEGORI: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_tambah_kategori)],
        WAIT_PRODUK_DESK: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_tambah_desk)],
    },
    fallbacks=[CommandHandler("cancel", lambda u,c: (u.message.reply_text("❌"), ConversationHandler.END))],
)

# ===== TAMBAH STOK =====
async def admin_tambah_stok_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    semua = await db.get_produk()
    if not semua:
        await q.edit_message_text("Belum ada produk. Tambah produk dulu.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Tambah Produk", callback_data="admin_tambah_produk")],
            [InlineKeyboardButton("← Admin", callback_data="admin_back")]]))
        return ConversationHandler.END
    
    teks = "📦 *Tambah Stok*\n\nPilih produk:\n"
    buttons = []
    for p in semua:
        buttons.append([InlineKeyboardButton(f"{p['nama']} (stok: {p['stok']})", callback_data=f"stok_pilih_{p['id']}")])
    buttons.append([InlineKeyboardButton("← Admin", callback_data="admin_back")])
    
    await q.edit_message_text(teks, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
    return ConversationHandler.END  # Biar gak ngambang

async def admin_tambah_stok_pilih(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    produk_id = int(q.data.split("_")[2])
    produk = await db.get_produk_by_id(produk_id)
    if not produk:
        await q.edit_message_text("❌ Produk tidak ditemukan.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Admin", callback_data="admin_back")]]))
        return ConversationHandler.END
    
    context.user_data['stok_produk_id'] = produk_id
    context.user_data['stok_produk_nama'] = produk['nama']
    
    await q.edit_message_text(
        f"📦 *Tambah Stok: {produk['nama']}*\n\n"
        f"Kirim daftar akun/token (satu per baris).\n\n"
        f"*Format:*\n"
        f"• Akun: `email:password`\n"
        f"• Token: `token_xy...`\n"
        f"• Link: `https://...`\n\n"
        f"*Contoh:*\n"
        f"```\nuser1@gmail.com:pass123\nuser2@gmail.com:pass456\nABC123XYZ\nhttps://link.com/voucher\n```",
        parse_mode=ParseMode.MARKDOWN
    )
    return WAIT_ITEM_STOK

async def admin_stok_diterima(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teks = update.message.text.strip()
    items = [t.strip() for t in teks.split("\n") if t.strip()]
    produk_id = context.user_data.get('stok_produk_id')
    nama = context.user_data.get('stok_produk_nama', '')
    
    if not items:
        await update.message.reply_text("❌ Kirim minimal 1 item.")
        return WAIT_ITEM_STOK
    
    jumlah = await db.tambah_stok(produk_id, items)
    
    await update.message.reply_text(
        f"✅ *{jumlah} stok ditambahkan!*\n\nProduk: {nama}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 Tambah Lagi", callback_data="admin_tambah_stok")],
            [InlineKeyboardButton("← Admin", callback_data="admin_back")]]))
    return ConversationHandler.END

tambah_stok_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(admin_tambah_stok_pilih, pattern="^stok_pilih_")],
    states={
        WAIT_ITEM_STOK: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_stok_diterima)],
    },
    fallbacks=[CommandHandler("cancel", lambda u,c: (u.message.reply_text("❌"), ConversationHandler.END))],
)

# ===== STATS =====
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    stats = await db.get_stats()
    
    semua = await db.get_pesanan(limit=1000)
    by_status = {}
    for p in semua:
        by_status[p['status']] = by_status.get(p['status'], 0) + 1
    
    teks = f"≡ *Statistik*\n\nTotal Pesanan: {stats['total_pesanan']}\nPendapatan: *{rp(stats['total_pendapatan'])}*\nProduk: {stats['total_produk']}\nStok tersisa: {stats['total_stok']}\n\n"
    for s, c in by_status.items():
        teks += f"  • {s}: {c}\n"
    
    await q.edit_message_text(teks, parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Admin", callback_data="admin_back")]]))

# ===== MAIN =====
async def post_init(app: Application):
    await db.init_db()
    await app.bot.set_my_commands([BotCommand("start", "Beranda"), BotCommand("admin", "Panel admin")])
    produk = await db.get_produk()
    print(f"✅ {config.TOKO_NAMA} berjalan! Produk: {len(produk)}")

def main():
    app = Application.builder().token(config.BOT_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(beli_conv)
    app.add_handler(tambah_produk_conv)
    app.add_handler(tambah_stok_conv)
    
    app.add_handler(CallbackQueryHandler(start, pattern="^menu$"))
    app.add_handler(CallbackQueryHandler(katalog, pattern="^katalog$"))
    app.add_handler(CallbackQueryHandler(lihat_kategori, pattern="^kat_"))
    app.add_handler(CallbackQueryHandler(produk_nav, pattern="^produk_(prev|next)$"))
    app.add_handler(CallbackQueryHandler(pesanan_saya, pattern="^pesanan_saya$"))
    app.add_handler(CallbackQueryHandler(bantuan, pattern="^bantuan$"))
    
    app.add_handler(CallbackQueryHandler(admin_back, pattern="^admin_back$"))
    app.add_handler(CallbackQueryHandler(admin_produk, pattern="^admin_produk$"))
    app.add_handler(CallbackQueryHandler(admin_pesanan_baru, pattern="^admin_pesanan_baru$"))
    app.add_handler(CallbackQueryHandler(admin_semua_pesanan, pattern="^admin_semua_pesanan$"))
    app.add_handler(CallbackQueryHandler(admin_stats, pattern="^admin_stats$"))
    app.add_handler(CallbackQueryHandler(admin_tambah_stok_start, pattern="^admin_tambah_stok$"))
    app.add_handler(CallbackQueryHandler(detail_pesanan_admin, pattern="^detail_"))
    app.add_handler(CallbackQueryHandler(verif_pesanan, pattern="^verif_"))
    app.add_handler(CallbackQueryHandler(tolak_pesanan, pattern="^tolak_"))
    
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print(f"🚀 {config.TOKO_NAMA} starting...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
