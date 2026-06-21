#!/usr/bin/env python3
"""
FureStore Bot v2 — Digital Store Telegram
Style: Reply Keyboard + Inline Buttons, QRIS auto-nominal
"""

import logging, asyncio
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, BotCommand, InputFile
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

import config, database as db, qris_helper

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== STATES =====
(BELI_KODE, BELI_JUMLAH, BELI_METODE, DEPOSIT_JUMLAH, DEPOSIT_BUKTI,
 ADMIN_TAMBAH_KODE, ADMIN_TAMBAH_NAMA, ADMIN_TAMBAH_HARGA, ADMIN_TAMBAH_KAT, ADMIN_TAMBAH_DESK,
 ADMIN_STOK_KODE, ADMIN_STOK_ISI) = range(12)

def rp(a):
    return f"Rp{a:,.0f}".replace(",", ".")

def is_admin(uid):
    return uid in config.ADMIN_IDS

# ===== CUSTOM KEYBOARD =====
def main_kb():
    return ReplyKeyboardMarkup([
        [KeyboardButton("≡ List Produk"), KeyboardButton("≡ Voucher")],
        [KeyboardButton("≡ Laporan Stok"), KeyboardButton("≡ Produk Populer")],
        [KeyboardButton("≡ Deposit"), KeyboardButton("≡ Cara Order")],
        [KeyboardButton("≡ Information"), KeyboardButton("≡ Pesanan Saya")],
    ], resize_keyboard=True)

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ *Data berhasil dimuat!*\n\n"
        f"Selamat datang di *{config.TOKO_NAMA}*! 🌟\n"
        "Klik tombol di bawah untuk mulai belanja.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_kb()
    )

# ===== LIST PRODUK =====
async def list_produk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    semua = await db.get_produk()
    if not semua:
        await update.message.reply_text("≡ Belum ada produk.", reply_markup=main_kb())
        return
    
    context.user_data['produk_list'] = semua
    context.user_data['produk_page'] = 0
    await tampil_produk_page(update.message, context)

async def tampil_produk_page(msg, context):
    items = context.user_data.get('produk_list', [])
    page = context.user_data.get('produk_page', 0)
    per_page = 10
    total_page = max(1, (len(items) + per_page - 1) // per_page)
    
    start = page * per_page
    page_items = items[start:start+per_page]
    
    teks = "━━━━━━━━━━━━━━━━━━\n"
    teks += "≡ *LIST PRODUCT*\n"
    teks += "━━━━━━━━━━━━━━━━━━\n\n"
    
    buttons = []
    for i, p in enumerate(page_items):
        num = start + i + 1
        stok = p['stok']
        status = f"{stok}" if stok > 0 else "HABIS"
        teks += f"  [{num}]. {p['nama'].upper()} ( {status} )\n"
        buttons.append(InlineKeyboardButton(f"{num}", callback_data=f"prod_{p['id']}"))
    
    teks += f"\n📅 Halaman {page+1} / {total_page}\n"
    
    # Number buttons in rows of 4
    rows = [buttons[i:i+4] for i in range(0, len(buttons), 4)]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data="page_prev"))
    if page < total_page - 1:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data="page_next"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("🔥 PRODUK POPULER", callback_data="populer_produk")])
    
    await msg.reply_text(teks, reply_markup=InlineKeyboardMarkup(rows))

async def page_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    page = context.user_data.get('produk_page', 0)
    if q.data == "page_prev":
        context.user_data['produk_page'] = max(0, page - 1)
    else:
        items = context.user_data.get('produk_list', [])
        max_page = max(0, (len(items) - 1) // 10)
        context.user_data['produk_page'] = min(max_page, page + 1)
    
    await tampil_produk_page_callback(q, context)

async def tampil_produk_page_callback(q, context):
    items = context.user_data.get('produk_list', [])
    page = context.user_data.get('produk_page', 0)
    per_page = 10
    total_page = max(1, (len(items) + per_page - 1) // per_page)
    
    start = page * per_page
    page_items = items[start:start+per_page]
    
    teks = "━━━━━━━━━━━━━━━━━━\n"
    teks += "≡ *LIST PRODUCT*\n"
    teks += "━━━━━━━━━━━━━━━━━━\n\n"
    
    buttons = []
    for i, p in enumerate(page_items):
        num = start + i + 1
        stok = p['stok']
        status = f"{stok}" if stok > 0 else "HABIS"
        teks += f"  [{num}]. {p['nama'].upper()} ( {status} )\n"
        buttons.append(InlineKeyboardButton(f"{num}", callback_data=f"prod_{p['id']}"))
    
    teks += f"\n📅 Halaman {page+1} / {total_page}\n"
    
    rows = [buttons[i:i+4] for i in range(0, len(buttons), 4)]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data="page_prev"))
    if page < total_page - 1:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data="page_next"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("🔥 PRODUK POPULER", callback_data="populer_produk")])
    
    await q.edit_message_text(teks, reply_markup=InlineKeyboardMarkup(rows))

# ===== PRODUK DETAIL =====
async def produk_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    produk_id = int(q.data.split("_")[1])
    p = await db.get_produk_by_id(produk_id)
    
    if not p:
        await q.edit_message_text("❌ Produk tidak ditemukan.")
        return
    
    teks = (
        f"━━━━━━━━━━━━━━━━━━\n"
        f"*{p['nama'].upper()}*\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📝 {p['deskripsi'] or '-'}\n\n"
        f"≡ Harga: *{rp(p['harga'])}*\n"
        f"≡ Stok: *{p['stok']} unit*\n"
        f"≡ Kategori: {p['kategori']}\n"
        f"\n*Kode: `{p['kode']}`*"
    )
    
    buttons = []
    if p['stok'] > 0:
        buttons.append([InlineKeyboardButton("🛒 Beli Sekarang", callback_data=f"beli_{p['id']}")])
    buttons.append([InlineKeyboardButton("← Kembali", callback_data="back_produk")])
    
    await q.edit_message_text(teks, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

async def back_produk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    items = context.user_data.get('produk_list', [])
    if items:
        await tampil_produk_page_callback(q, context)
    else:
        await q.edit_message_text("Ketik /start")

# ===== PRODUK POPULER =====
async def populer_produk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    semua = await db.get_produk()
    populer = [p for p in semua if p['populer']]
    
    if not populer:
        populer = semua[:5] if semua else []
    
    if not populer:
        await q.edit_message_text("Belum ada produk.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Kembali", callback_data="back_produk")]]))
        return
    
    teks = "🔥 *PRODUK POPULER*\n\n"
    buttons = []
    for i, p in enumerate(populer):
        teks += f"[{i+1}] *{p['nama']}* — {rp(p['harga'])} (stok: {p['stok']})\n"
        buttons.append(InlineKeyboardButton(f"{i+1}", callback_data=f"prod_{p['id']}"))
    
    rows = [buttons[i:i+4] for i in range(0, len(buttons), 4)]
    rows.append([InlineKeyboardButton("≡ Semua Produk", callback_data="back_produk")])
    
    await q.edit_message_text(teks, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(rows))

# ===== LARAPAN STOK (public) =====
async def laporan_stok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    semua = await db.get_produk()
    if not semua:
        await update.message.reply_text("Belum ada produk.", reply_markup=main_kb())
        return
    
    teks = "━━━━━━━━━━━━━━━━━━\n📦 *LAPORAN STOK*\n━━━━━━━━━━━━━━━━━━\n\n"
    for p in semua:
        s = p['stok']
        teks += f"• {p['nama']} — {s} unit {'✅' if s > 0 else '❌ HABIS'}\n"
    
    await update.message.reply_text(teks, parse_mode=ParseMode.MARKDOWN, reply_markup=main_kb())

# ===== PRODUK POPULER (dari keyboard) =====
async def populer_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    semua = await db.get_produk()
    populer = [p for p in semua if p['populer']]
    if not populer:
        populer = semua[:5]
    
    if not populer:
        await update.message.reply_text("Belum ada produk.", reply_markup=main_kb())
        return
    
    teks = "🔥 *PRODUK POPULER*\n\n"
    buttons = []
    for i, p in enumerate(populer):
        teks += f"[{i+1}] *{p['nama']}* — {rp(p['harga'])} (stok: {p['stok']})\n"
        buttons.append(InlineKeyboardButton(f"{i+1}", callback_data=f"prod_{p['id']}"))
    
    rows = [buttons[i:i+4] for i in range(0, len(buttons), 4)]
    await update.message.reply_text(teks, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(rows))

# ===== CARA ORDER =====
async def cara_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teks = (
        "━━━━━━━━━━━━━━━━━━\n"
        "≡ *CARA ORDER*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "1️⃣ Ketik *≡ List Produk*\n"
        "2️⃣ Pilih produk (klik nomor)\n"
        "3️⃣ Klik *🛒 Beli Sekarang*\n"
        "4️⃣ Masukkan jumlah\n"
        "5️⃣ Pilih metode bayar (QRIS/DANA/OVO)\n"
        "6️⃣ Transfer sesuai nominal\n"
        "7️⃣ Kirim bukti bayar\n"
        "8️⃣ Akun/token langsung dikirim otomatis! 🔥\n\n"
        f"💬 Admin: {config.ADMIN_USERNAME}\n"
        "⏰ Proses verifikasi: 1-60 menit"
    )
    await update.message.reply_text(teks, parse_mode=ParseMode.MARKDOWN, reply_markup=main_kb())

# ===== INFORMATION =====
async def information(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teks = (
        "━━━━━━━━━━━━━━━━━━\n"
        f"ℹ️ *{config.TOKO_NAMA}*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"{config.TOKO_DESC}\n\n"
        "≡ *Jaminan:*\n"
        "• Garansi 30 hari\n"
        "• Garansi ganti baru\n"
        "• Support 24/7\n\n"
        "≡ *Metode Pembayaran:*\n"
        "• QRIS (semua e-wallet)\n"
        "• DANA\n"
        "• OVO\n"
        "• GoPay\n\n"
        f"💬 Admin: {config.ADMIN_USERNAME}\n"
    )
    await update.message.reply_text(teks, parse_mode=ParseMode.MARKDOWN, reply_markup=main_kb())

# ===== VOUCHER =====
async def voucher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "━━━━━━━━━━━━━━━━━━\n"
        "≡ *VOUCHER*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Masukkan kode voucher untuk mendapatkan diskon!\n\n"
        "Ketik kode voucher kamu:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_kb()
    )

# ===== DEPOSIT =====
async def deposit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    saldo = await db.get_saldo(update.effective_user.id)
    await update.message.reply_text(
        "━━━━━━━━━━━━━━━━━━\n"
        "💰 *DEPOSIT*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"Saldo kamu: *{rp(saldo)}*\n\n"
        "Ketik nominal deposit (minimal Rp10.000):",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_kb()
    )
    return DEPOSIT_JUMLAH

async def deposit_jumlah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        nominal = int(update.message.text.replace("rp", "").replace("Rp", "").replace(".", "").replace(",", ""))
        if nominal < 10000:
            await update.message.reply_text("❌ Minimal Rp10.000!")
            return DEPOSIT_JUMLAH
    except:
        await update.message.reply_text("❌ Masukkan angka saja!")
        return DEPOSIT_JUMLAH
    
    context.user_data['deposit_nominal'] = nominal
    depo_id = await db.buat_deposit(update.effective_user.id, nominal)
    context.user_data['deposit_id'] = depo_id
    
    # Generate QRIS
    qr_path = qris_helper.generate_qris_simple(nominal, depo_id)
    qris_text = qris_helper.get_payment_summary(nominal, depo_id, "QRIS/DANA/OVO")
    
    await update.message.reply_photo(
        photo=open(qr_path, 'rb'),
        caption=f"✅ *Deposit #{depo_id} Dibuat!*\n\nNominal: *{rp(nominal)}*\n\n📸 Transfer ke *DANA*: `{config.PEMBAYARAN['DANA']}`\n📸 Atau scan QRIS di atas\n\nKirim *bukti bayar* (screenshot) setelah transfer.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_kb()
    )
    return DEPOSIT_BUKTI

async def deposit_bukti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    depo_id = context.user_data.get('deposit_id')
    nominal = context.user_data.get('deposit_nominal')
    
    await update.message.reply_text("✅ Bukti deposit diterima! Admin akan verifikasi sebentar.", reply_markup=main_kb())
    
    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id,
                f"💰 *DEPOSIT BARU #{depo_id}*\n\n"
                f"Dari: {update.effective_user.first_name}\n"
                f"Nominal: {rp(nominal)}",
                parse_mode=ParseMode.MARKDOWN)
            await context.bot.forward_message(admin_id, update.effective_user.id, update.message.message_id)
        except: pass
    
    return ConversationHandler.END

deposit_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^≡ Deposit$"), deposit_start)],
    states={
        DEPOSIT_JUMLAH: [MessageHandler(filters.TEXT & ~filters.COMMAND, deposit_jumlah)],
        DEPOSIT_BUKTI: [MessageHandler(filters.PHOTO, deposit_bukti)],
    },
    fallbacks=[]
)

# ===== PESANAN SAYA =====
async def pesanan_saya(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pesanan = await db.get_pesanan_by_user(update.effective_user.id)
    if not pesanan:
        await update.message.reply_text("≡ Belum ada pesanan.", reply_markup=main_kb())
        return
    
    teks = "📋 *Pesanan Saya*\n\n"
    emoji = {"menunggu": "🟡", "selesai": "✅", "dibatalkan": "❌"}
    for p in pesanan:
        e = emoji.get(p['status'], "⚪")
        teks += f"{e} #{p['id']} — {p['nama_produk']} x{p['jumlah']} — {rp(p['total'])} — {p['status']}\n"
    
    await update.message.reply_text(teks, parse_mode=ParseMode.MARKDOWN, reply_markup=main_kb())

# ===== BELI PRODUK =====
async def beli_produk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    produk_id = int(q.data.split("_")[1])
    p = await db.get_produk_by_id(produk_id)
    
    if not p or p['stok'] <= 0:
        await q.edit_message_text("❌ Stok habis.")
        return ConversationHandler.END
    
    context.user_data['beli_produk'] = dict(p)
    
    await q.edit_message_text(
        f"🛒 *Beli {p['nama']}*\n\n"
        f"Harga: {rp(p['harga'])} /pc\n"
        f"Stok: {p['stok']}\n\n"
        f"Berapa jumlah yang mau dibeli?",
        parse_mode=ParseMode.MARKDOWN
    )
    return BELI_JUMLAH

async def beli_jumlah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        jumlah = int(update.message.text)
        p = context.user_data.get('beli_produk', {})
        if jumlah < 1:
            await update.message.reply_text("❌ Minimal 1!")
            return BELI_JUMLAH
        if jumlah > p.get('stok', 0):
            await update.message.reply_text(f"❌ Stok cuma {p['stok']}!")
            return BELI_JUMLAH
        
        context.user_data['beli_jumlah'] = jumlah
        total = p['harga'] * jumlah
        context.user_data['beli_total'] = total
        
        buttons = [
            [InlineKeyboardButton("≡ QRIS (Semua E-wallet)", callback_data="pay_QRIS")],
            [InlineKeyboardButton("≡ DANA", callback_data="pay_DANA"), InlineKeyboardButton("≡ OVO", callback_data="pay_OVO")],
            [InlineKeyboardButton("≡ GoPay", callback_data="pay_GOPAY")],
        ]
        
        await update.message.reply_text(
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🛒 *PILIH PEMBAYARAN*\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"Produk: {p['nama']}\n"
            f"Jumlah: {jumlah}pc\n"
            f"Total: *{rp(total)}*\n\n"
            f"Pilih metode pembayaran:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return BELI_METODE
        
    except ValueError:
        await update.message.reply_text("❌ Angka saja!")
        return BELI_JUMLAH

async def beli_metode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    metode = q.data.split("_")[1]
    user = q.from_user
    p = context.user_data.get('beli_produk', {})
    jumlah = context.user_data.get('beli_jumlah', 1)
    total = context.user_data.get('beli_total', p['harga'])
    
    # Ambil stok
    stok_isi = await db.ambil_stok(p['id'])
    if not stok_isi:
        await q.edit_message_text("❌ Stok habis!")
        return ConversationHandler.END
    
    # Buat pesanan (langsung selesai karena stok sudah diambil)
    pesanan_id = await db.buat_pesanan(
        user_id=user.id, username=user.username or '', produk_id=p['id'],
        jumlah=jumlah, total=total, metode_bayar=metode
    )
    
    # Generate QRIS
    qr_path = qris_helper.generate_qris_simple(total, pesanan_id)
    
    # Kirim QR + info pembayaran
    no_rek = config.PEMBAYARAN.get(metode, "-")
    
    if metode == "QRIS":
        teks_bayar = f"📸 *Scan QRIS di atas* atau transfer ke:\n`{config.PEMBAYARAN['DANA']}`"
    else:
        teks_bayar = f"📸 Transfer ke *{metode}*: `{no_rek}`"
    
    await q.edit_message_text(
        f"✅ *Pesanan #{pesanan_id} Dibuat!*\n\n"
        f"Produk: {p['nama']}\n"
        f"Jumlah: {jumlah}pc\n"
        f"Total: *{rp(total)}*\n\n"
        f"{teks_bayar}\n\n"
        f"⚠️ *Transfer sesuai nominal ya!*\n"
        f"📸 Kirim *bukti bayar* setelah transfer.\n"
        f"⚡ Akun/token langsung dikirim otomatis setelah verifikasi!",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Simpan stok di context untuk kirim nanti
    context.user_data['stok_isi'] = stok_isi
    context.user_data['pesanan_id'] = pesanan_id
    
    # Notif admin
    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id,
                f"🔔 *PESANAN #{pesanan_id}*\n\n"
                f"Dari: {user.first_name} (@{user.username or '-'})\n"
                f"Produk: {p['nama']} x{jumlah}\n"
                f"Total: {rp(total)}\n"
                f"Metode: {metode}\n\n"
                f"Klik /admin → Verifikasi",
                parse_mode=ParseMode.MARKDOWN)
        except: pass
    
    return ConversationHandler.END

beli_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(beli_produk, pattern="^beli_")],
    states={
        BELI_JUMLAH: [MessageHandler(filters.TEXT & ~filters.COMMAND, beli_jumlah)],
        BELI_METODE: [CallbackQueryHandler(beli_metode, pattern="^pay_")],
    },
    fallbacks=[]
)

# ===== ADMIN =====
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Bukan admin.")
        return
    
    stats = await db.get_stats()
    teks = (
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔧 *ADMIN — {config.TOKO_NAMA}*\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"≡ Pesanan: {stats['total_pesanan']}\n"
        f"💰 Pendapatan: {rp(stats['total_pendapatan'])}\n"
        f"≡ Produk: {stats['total_produk']} | Stok: {stats['total_stok']}\n"
        f"🔔 Pesanan Baru: {stats['pesanan_baru']}\n"
        f"💰 Deposit Baru: {stats['deposit_baru']}\n"
    )
    buttons = [
        [InlineKeyboardButton("≡ Kelola Produk", callback_data="adm_produk")],
        [InlineKeyboardButton("🔔 Pesanan Baru", callback_data="adm_pesanan_baru"),
         InlineKeyboardButton("≡ Semua", callback_data="adm_semua_pesanan")],
        [InlineKeyboardButton("➕ Tambah Produk", callback_data="adm_tambah_produk"),
         InlineKeyboardButton("📦 Tambah Stok", callback_data="adm_tambah_stok")],
        [InlineKeyboardButton("≡ Statistik", callback_data="adm_stats")]
    ]
    await update.message.reply_text(teks, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

async def adm_produk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    semua = await db.get_produk()
    if not semua:
        await q.edit_message_text("Belum ada produk.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Admin", callback_data="adm_back")]]))
        return
    teks = "≡ *DAFTAR PRODUK*\n\n"
    for p in semua:
        status = "✅" if p['stok'] > 0 else "❌"
        teks += f"{status} `{p['kode']}` — {p['nama']} — {rp(p['harga'])} (stok: {p['stok']})\n"
    await q.edit_message_text(teks, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Tambah", callback_data="adm_tambah_produk"), InlineKeyboardButton("📦 Stok", callback_data="adm_tambah_stok")],
        [InlineKeyboardButton("← Admin", callback_data="adm_back")]]))

async def adm_pesanan_baru(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    pesanan = await db.get_pesanan(status='menunggu')
    if not pesanan:
        await q.edit_message_text("✅ Tidak ada pesanan menunggu.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Admin", callback_data="adm_back")]]))
        return
    teks = "🔔 *PESANAN MENUNGGU*\n\n"
    buttons = []
    for p in pesanan:
        teks += f"#{p['id']} — {p['nama_produk']} x{p['jumlah']} — {rp(p['total'])} — @{p['username']}\n"
        buttons.append([InlineKeyboardButton(f"✅ Verif #{p['id']}", callback_data=f"adm_verif_{p['id']}"),
                        InlineKeyboardButton(f"❌ Tolak", callback_data=f"adm_tolak_{p['id']}")])
    buttons.append([InlineKeyboardButton("← Admin", callback_data="adm_back")])
    await q.edit_message_text(teks, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

async def adm_verif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    pesanan_id = int(q.data.split("_")[2])
    p = await db.get_pesanan_by_id(pesanan_id)
    if not p:
        await q.answer("❌")
        return
    
    stok_isi = await db.ambil_stok(p['produk_id'])
    if not stok_isi:
        await q.answer("❌ Stok habis!", show_alert=True)
        return
    
    await db.update_status_pesanan(pesanan_id, 'selesai')
    await q.answer("✅ Terverifikasi!")
    
    # Kirim akun ke pembeli
    if ":" in stok_isi:
        a, pw = stok_isi.split(":", 1)
        teks = f"✅ *Pesanan #{pesanan_id} — Terverifikasi!*\n\n🔑 *Akun:*\nEmail: `{a}`\nPassword: `{pw}`\n\n⚠️ Segera ganti password setelah login!"
    elif stok_isi.startswith("http"):
        teks = f"✅ *Pesanan #{pesanan_id} — Terverifikasi!*\n\n🔗 *Link:* {stok_isi}"
    else:
        teks = f"✅ *Pesanan #{pesanan_id} — Terverifikasi!*\n\n🔑 *Kode/Token:*\n`{stok_isi}`"
    
    try:
        await context.bot.send_message(p['user_id'], teks, parse_mode=ParseMode.MARKDOWN)
    except:
        pass
    
    await q.edit_message_text(f"✅ Pesanan #{pesanan_id} diverifikasi & barang dikirim!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Admin", callback_data="adm_back")]]))

async def adm_tolak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    pesanan_id = int(q.data.split("_")[2])
    p = await db.get_pesanan_by_id(pesanan_id)
    await db.update_status_pesanan(pesanan_id, 'dibatalkan')
    await q.answer("❌ Dibatalkan.")
    
    if p:
        try:
            await context.bot.send_message(p['user_id'], f"❌ *Pesanan #{pesanan_id} Dibatalkan*", parse_mode=ParseMode.MARKDOWN)
        except: pass
    
    await q.edit_message_text(f"❌ Pesanan #{pesanan_id} dibatalkan.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Admin", callback_data="adm_back")]]))

async def adm_semua_pesanan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    pesanan = await db.get_pesanan(limit=20)
    if not pesanan:
        await q.edit_message_text("Belum ada pesanan.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Admin", callback_data="adm_back")]]))
        return
    emoji = {"menunggu": "🟡", "selesai": "✅", "dibatalkan": "❌"}
    teks = "≡ *SEMUA PESANAN*\n\n"
    for p in pesanan:
        e = emoji.get(p['status'], "⚪")
        teks += f"{e} #{p['id']} — {p['nama_produk']} — {rp(p['total'])} — {p['status']}\n"
    await q.edit_message_text(teks, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Admin", callback_data="adm_back")]]))

async def adm_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    stats = await db.get_stats()
    teks = (
        f"🔧 *Admin — {config.TOKO_NAMA}*\n\n"
        f"≡ Pesanan: {stats['total_pesanan']} | 💰 {rp(stats['total_pendapatan'])}\n"
        f"≡ Produk: {stats['total_produk']} | Stok: {stats['total_stok']}\n"
        f"🔔 Menunggu: {stats['pesanan_baru']}\n"
    )
    buttons = [
        [InlineKeyboardButton("≡ Kelola Produk", callback_data="adm_produk")],
        [InlineKeyboardButton("🔔 Pesanan Baru", callback_data="adm_pesanan_baru"),
         InlineKeyboardButton("≡ Semua", callback_data="adm_semua_pesanan")],
        [InlineKeyboardButton("➕ Tambah Produk", callback_data="adm_tambah_produk"),
         InlineKeyboardButton("📦 Tambah Stok", callback_data="adm_tambah_stok")],
        [InlineKeyboardButton("≡ Statistik", callback_data="adm_stats")]
    ]
    await q.edit_message_text(teks, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

async def adm_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    stats = await db.get_stats()
    teks = f"≡ *Statistik*\n\nPesanan: {stats['total_pesanan']}\nPendapatan: *{rp(stats['total_pendapatan'])}*\nProduk: {stats['total_produk']}\nStok: {stats['total_stok']}"
    await q.edit_message_text(teks, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Admin", callback_data="adm_back")]]))

# ===== ADMIN: TAMBAH PRODUK =====
async def adm_tambah_produk_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("➕ *Tambah Produk*\n\nKetik *kode produk* (tanpa spasi, contoh: `netflix_001`)", parse_mode=ParseMode.MARKDOWN)
    return ADMIN_TAMBAH_KODE

async def adm_tambah_kode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_kode'] = update.message.text.strip().replace(" ", "_")
    await update.message.reply_text("≡ *Nama produk?*", parse_mode=ParseMode.MARKDOWN)
    return ADMIN_TAMBAH_NAMA

async def adm_tambah_nama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_nama'] = update.message.text
    await update.message.reply_text("💰 *Harga?* (angka)", parse_mode=ParseMode.MARKDOWN)
    return ADMIN_TAMBAH_HARGA

async def adm_tambah_harga(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['new_harga'] = int(update.message.text.replace("rp","").replace("Rp","").replace(".",""))
    except:
        await update.message.reply_text("❌ Angka!")
        return ADMIN_TAMBAH_HARGA
    await update.message.reply_text("≡ *Kategori?* (Akun Premium | Token & Voucher | Langganan)", parse_mode=ParseMode.MARKDOWN)
    return ADMIN_TAMBAH_KAT

async def adm_tambah_kategori(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_kat'] = update.message.text.title()
    await update.message.reply_text("📝 *Deskripsi?* (- jika tidak)", parse_mode=ParseMode.MARKDOWN)
    return ADMIN_TAMBAH_DESK

async def adm_tambah_desk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desk = update.message.text if update.message.text != '-' else ''
    await db.tambah_produk(context.user_data['new_kode'], context.user_data['new_nama'], context.user_data['new_harga'], desk, context.user_data['new_kat'])
    await update.message.reply_text(f"✅ *{context.user_data['new_nama']}* ditambahkan!", parse_mode=ParseMode.MARKDOWN, reply_markup=main_kb())
    return ConversationHandler.END

tambah_produk_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(adm_tambah_produk_start, pattern="^adm_tambah_produk$")],
    states={
        ADMIN_TAMBAH_KODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_tambah_kode)],
        ADMIN_TAMBAH_NAMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_tambah_nama)],
        ADMIN_TAMBAH_HARGA: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_tambah_harga)],
        ADMIN_TAMBAH_KAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_tambah_kategori)],
        ADMIN_TAMBAH_DESK: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_tambah_desk)],
    }, fallbacks=[])

# ===== ADMIN: TAMBAH STOK =====
async def adm_stok_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    semua = await db.get_produk()
    buttons = [[InlineKeyboardButton(f"{p['nama']} (stok:{p['stok']})", callback_data=f"adm_stok_{p['id']}")] for p in semua]
    buttons.append([InlineKeyboardButton("← Admin", callback_data="adm_back")])
    await q.edit_message_text("📦 *Tambah Stok*\n\nPilih produk:", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
    return ADMIN_STOK_ISI

async def adm_stok_pilih(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    produk_id = int(q.data.split("_")[2])
    p = await db.get_produk_by_id(produk_id)
    if not p:
        await q.edit_message_text("❌ Tidak ditemukan.")
        return ConversationHandler.END
    context.user_data['stok_produk_id'] = produk_id
    context.user_data['stok_produk_nama'] = p['nama']
    await q.edit_message_text(
        f"📦 *Tambah Stok: {p['nama']}*\n\n"
        "Kirim isi akun/token (satu per baris):\n"
        "• `email:password` — untuk akun\n"
        "• `token_xy...` — untuk token\n"
        "• `https://link...` — untuk link\n\n"
        "Contoh:\n```\nuser1@gmail.com:pass1\nuser2@gmail.com:pass2\n```",
        parse_mode=ParseMode.MARKDOWN
    )
    return ADMIN_STOK_ISI

async def adm_stok_isi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    items = [t.strip() for t in update.message.text.split("\n") if t.strip()]
    pid = context.user_data.get('stok_produk_id')
    nama = context.user_data.get('stok_produk_nama', '')
    n = await db.tambah_stok(pid, items)
    await update.message.reply_text(f"✅ *{n} stok ditambahkan!*\n\nProduk: {nama}", parse_mode=ParseMode.MARKDOWN, reply_markup=main_kb())
    return ConversationHandler.END

tambah_stok_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(adm_stok_pilih, pattern="^adm_stok_")],
    states={ADMIN_STOK_ISI: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_stok_isi)]},
    fallbacks=[])

# ===== FOTO =====
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text("✅ Bukti bayar diterima! Admin akan verifikasi sebentar.", reply_markup=main_kb())
    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id,
                f"📸 *Bukti Bayar*\nDari: {user.first_name} (@{user.username or '-'})\n\nCek /admin → Pesanan Baru",
                parse_mode=ParseMode.MARKDOWN)
            await context.bot.forward_message(admin_id, user.id, update.message.message_id)
        except: pass

# ===== HANDLER UNTUK KOSONG =====
async def noop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

# ===== MAIN =====
async def post_init(app):
    await db.init_db()
    await app.bot.set_my_commands([BotCommand("start", "Beranda"), BotCommand("admin", "Panel admin")])
    produk = await db.get_produk()
    print(f"✅ {config.TOKO_NAMA} berjalan! {len(produk)} produk loaded.")

def main():
    app = Application.builder().token(config.BOT_TOKEN).post_init(post_init).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    
    # Conversations
    app.add_handler(beli_conv)
    app.add_handler(deposit_conv)
    app.add_handler(tambah_produk_conv)
    app.add_handler(tambah_stok_conv)
    
    # Reply Keyboard handlers
    app.add_handler(MessageHandler(filters.Regex("^≡ List Produk$"), list_produk))
    app.add_handler(MessageHandler(filters.Regex("^≡ Voucher$"), voucher))
    app.add_handler(MessageHandler(filters.Regex("^≡ Laporan Stok$"), laporan_stok))
    app.add_handler(MessageHandler(filters.Regex("^≡ Produk Populer$"), populer_keyboard))
    app.add_handler(MessageHandler(filters.Regex("^≡ Cara Order$"), cara_order))
    app.add_handler(MessageHandler(filters.Regex("^≡ Information$"), information))
    app.add_handler(MessageHandler(filters.Regex("^≡ Pesanan Saya$"), pesanan_saya))
    
    # Callback handlers
    app.add_handler(CallbackQueryHandler(page_nav, pattern="^page_(prev|next)$"))
    app.add_handler(CallbackQueryHandler(produk_detail, pattern="^prod_"))
    app.add_handler(CallbackQueryHandler(populer_produk, pattern="^populer_produk$"))
    app.add_handler(CallbackQueryHandler(back_produk, pattern="^back_produk$"))
    app.add_handler(CallbackQueryHandler(noop, pattern="^noop$"))
    
    # Admin callbacks
    app.add_handler(CallbackQueryHandler(adm_back, pattern="^adm_back$"))
    app.add_handler(CallbackQueryHandler(adm_produk, pattern="^adm_produk$"))
    app.add_handler(CallbackQueryHandler(adm_pesanan_baru, pattern="^adm_pesanan_baru$"))
    app.add_handler(CallbackQueryHandler(adm_semua_pesanan, pattern="^adm_semua_pesanan$"))
    app.add_handler(CallbackQueryHandler(adm_stats, pattern="^adm_stats$"))
    app.add_handler(CallbackQueryHandler(adm_verif, pattern="^adm_verif_"))
    app.add_handler(CallbackQueryHandler(adm_tolak, pattern="^adm_tolak_"))
    
    # Photo handler
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print(f"🚀 {config.TOKO_NAMA} starting...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
