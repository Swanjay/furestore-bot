#!/usr/bin/env python3
"""
Bot Jual Beli Telegram — Furestore
Features:
  - Katalog produk per kategori
  - Keranjang belanja
  - Checkout + upload bukti bayar
  - Admin panel (manage produk & pesanan)
  - AI customer service (via Groq)
  - Broadcast ke pelanggan
  - Statistik penjualan
"""

import asyncio
import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    BotCommand
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

import config
import database as db

# ===== LOGGING =====
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== CONVERSATION STATES =====
WAIT_NAMA, WAIT_ALAMAT, WAIT_NOHP, WAIT_CATATAN = range(4)
WAIT_PRODUK_KODE, WAIT_PRODUK_NAMA, WAIT_PRODUK_HARGA, WAIT_PRODUK_STOK, WAIT_PRODUK_KATEGORI = range(4, 9)
WAIT_PRODUK_DESK = 9

# ===== HELPERS =====

def is_admin(user_id):
    return user_id in config.ADMIN_IDS

def format_rupiah(angka):
    return f"Rp{angka:,.0f}".replace(",", ".")

def sapaan():
    return config.TOKO_SAPAAN

# ===== MENU UTAMA =====

def menu_utama_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("≡ Lihat Katalog", callback_data="katalog"),
         InlineKeyboardButton("🛒 Keranjang", callback_data="keranjang")],
        [InlineKeyboardButton("📋 Pesanan Saya", callback_data="pesanan_saya"),
         InlineKeyboardButton("💬 Chat Admin", callback_data="chat_admin")],
        [InlineKeyboardButton("ℹ️ Info Toko", callback_data="info_toko")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    nama = user.first_name
    text = (
        f"Assalamu'alaikum, {sapaan()} {nama}! 🌙\n\n"
        f"Selamat datang di *{config.TOKO_NAMA}*!\n"
        f"{config.TOKO_DESC}\n\n"
        f"Pilih menu di bawah untuk mulai belanja 👇"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=menu_utama_keyboard())
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=menu_utama_keyboard())

# ===== KATALOG =====

async def katalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    kategoris = await db.get_kategori()
    if not kategoris:
        await query.edit_message_text(
            "≡ Katalog kosong.\nAdmin belum menambahkan produk.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Menu", callback_data="menu")]])
        )
        return

    buttons = []
    for kat in kategoris:
        buttons.append([InlineKeyboardButton(f"≡ {kat}", callback_data=f"kat_{kat}")])
    buttons.append([InlineKeyboardButton("≡ Semua Produk", callback_data="kat_semua")])
    buttons.append([InlineKeyboardButton("← Menu", callback_data="menu")])

    await query.edit_message_text(
        "≡ *Katalog Produk*\n\nPilih kategori:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def lihat_kategori(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    kat = query.data.split("_", 1)[1]
    if kat == "semua":
        produk_list = await db.get_produk()
    else:
        semua = await db.get_produk()
        produk_list = [p for p in semua if p['kategori'] == kat]

    if not produk_list:
        await query.edit_message_text(
            f"≡ Kategori *{kat}* belum ada produk.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Katalog", callback_data="katalog")]])
        )
        return

    context.user_data['produk_list'] = [dict(p) for p in produk_list]
    context.user_data['produk_idx'] = 0

    await tampilkan_produk(query, context)

async def tampilkan_produk(query, context):
    items = context.user_data.get('produk_list', [])
    idx = context.user_data.get('produk_idx', 0)

    if not items:
        return

    p = items[idx]
    stok_text = f"✅ Stok: {p['stok']}" if p['stok'] > 0 else "❌ Habis"
    text = (
        f"*{p['nama']}*\n\n"
        f"{p['deskripsi'] or 'Tidak ada deskripsi.'}\n\n"
        f"≡ Harga: *{format_rupiah(p['harga'])}*\n"
        f"📦 {stok_text}\n"
        f"≡ Kategori: {p['kategori']}\n"
        f"\n≡ {idx+1} / {len(items)}"
    )

    buttons = []
    if p['stok'] > 0:
        buttons.append([InlineKeyboardButton("🛒 Tambah ke Keranjang", callback_data=f"add_{p['id']}")])

    nav = []
    if idx > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data="produk_prev"))
    if idx < len(items) - 1:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data="produk_next"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton("← Katalog", callback_data="katalog")])

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

async def produk_prev(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['produk_idx'] = max(0, context.user_data.get('produk_idx', 0) - 1)
    await tampilkan_produk(query, context)

async def produk_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    items = context.user_data.get('produk_list', [])
    context.user_data['produk_idx'] = min(len(items) - 1, context.user_data.get('produk_idx', 0) + 1)
    await tampilkan_produk(query, context)

# ===== KERANJANG =====

async def tambah_ke_keranjang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    produk_id = int(query.data.split("_")[1])
    user_id = query.from_user.id

    await db.tambah_keranjang(user_id, produk_id)
    await query.answer("✅ Ditambahkan ke keranjang!", show_alert=True)

async def lihat_keranjang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    items = await db.get_keranjang(user_id)
    if not items:
        await query.edit_message_text(
            "🛒 *Keranjang Kosong*\n\nYuk mulai belanja!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("≡ Belanja Sekarang", callback_data="katalog")],
                [InlineKeyboardButton("← Menu", callback_data="menu")]
            ])
        )
        return

    total = 0
    text = "🛒 *Keranjang Belanja*\n\n"
    buttons = []

    for item in items:
        subtotal = item['harga'] * item['jumlah']
        total += subtotal
        text += f"• {item['nama']}\n  {item['jumlah']}x {format_rupiah(item['harga'])} = *{format_rupiah(subtotal)}*\n"
        buttons.append([
            InlineKeyboardButton("➖", callback_data=f"qty_minus_{item['id']}"),
            InlineKeyboardButton(f"{item['jumlah']}", callback_data="noop"),
            InlineKeyboardButton("➕", callback_data=f"qty_plus_{item['id']}"),
            InlineKeyboardButton("❌", callback_data=f"del_{item['id']}")
        ])

    ongkir = 0 if total >= config.GRATIS_ONGKIR_MIN else config.ONGKIR_DEFAULT
    text += f"\n≡ Subtotal: *{format_rupiah(total)}*\n"
    text += f"≡ Ongkir: {'GRATIS ✅' if ongkir == 0 else format_rupiah(ongkir)}\n"
    text += f"\n💰 *Total: {format_rupiah(total + ongkir)}*"

    buttons.append([InlineKeyboardButton("✅ Checkout", callback_data="checkout")])
    buttons.append([InlineKeyboardButton("🗑️ Kosongkan", callback_data="kosong_keranjang")])
    buttons.append([InlineKeyboardButton("≡ Lanjut Belanja", callback_data="katalog")])
    buttons.append([InlineKeyboardButton("← Menu", callback_data="menu")])

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

async def qty_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split("_")
    action = parts[1]
    item_id = int(parts[2])
    user_id = query.from_user.id

    items = await db.get_keranjang(user_id)
    item = next((i for i in items if i['id'] == item_id), None)

    if item:
        if action == "plus" and item['jumlah'] < item['stok']:
            await db.tambah_keranjang(user_id, item['produk_id'], 1)
        elif action == "minus":
            if item['jumlah'] <= 1:
                await db.hapus_keranjang_item(item_id)
            else:
                import aiosqlite
                async with aiosqlite.connect("toko.db") as adb:
                    await adb.execute("UPDATE keranjang SET jumlah = jumlah - 1 WHERE id = ?", (item_id,))
                    await adb.commit()

    await query.answer()
    context.callback_query = query
    await lihat_keranjang(update, context)

async def hapus_item_keranjang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    item_id = int(query.data.split("_")[1])
    await db.hapus_keranjang_item(item_id)
    await query.answer("❌ Item dihapus")
    context.callback_query = query
    await lihat_keranjang(update, context)

async def kosong_keranjang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await db.kosongkan_keranjang(query.from_user.id)
    await query.answer("🗑️ Keranjang dikosongkan")
    context.callback_query = query
    await lihat_keranjang(update, context)

# ===== CHECKOUT =====

async def checkout_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    items = await db.get_keranjang(user_id)
    if not items:
        await query.edit_message_text("Keranjang kosong!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Menu", callback_data="menu")]]))
        return ConversationHandler.END

    await query.edit_message_text(
        f"{sapaan()}, mulai checkout ya!\n\n"
        "≡ *Nama lengkap* untuk pengiriman?\n_(Ketik nama lengkap kamu)_",
        parse_mode=ParseMode.MARKDOWN
    )
    return WAIT_NAMA

async def checkout_nama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['checkout_nama'] = update.message.text
    await update.message.reply_text(
        "📍 *Alamat lengkap* pengiriman?\n_(Jalan, No Rumah, RT/RW, Kel, Kec, Kota, Kodepos)_",
        parse_mode=ParseMode.MARKDOWN
    )
    return WAIT_ALAMAT

async def checkout_alamat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['checkout_alamat'] = update.message.text
    await update.message.reply_text("≡ *No. HP* yang bisa dihubungi?", parse_mode=ParseMode.MARKDOWN)
    return WAIT_NOHP

async def checkout_nohp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['checkout_nohp'] = update.message.text
    await update.message.reply_text(
        "📝 *Catatan* untuk pesanan? (ketik - jika tidak ada)",
        parse_mode=ParseMode.MARKDOWN
    )
    return WAIT_CATATAN

async def checkout_catatan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    catatan = update.message.text if update.message.text != '-' else ''

    total = await db.hitung_total(user_id)
    ongkir = 0 if total >= config.GRATIS_ONGKIR_MIN else config.ONGKIR_DEFAULT
    grand_total = total + ongkir

    context.user_data['checkout_total'] = grand_total
    context.user_data['checkout_ongkir'] = ongkir
    context.user_data['checkout_catatan'] = catatan

    pesanan_id = await db.buat_pesanan(
        user_id=user_id,
        username=user.username or '',
        nama=context.user_data['checkout_nama'],
        alamat=context.user_data['checkout_alamat'],
        nohp=context.user_data['checkout_nohp'],
        total=grand_total,
        ongkir=ongkir,
        catatan=catatan
    )

    rekening_text = "\n".join([f"  • {bank}: {rek}" for bank, rek in config.REKENING.items()])

    text = (
        f"✅ *Pesanan #{pesanan_id} Berhasil Dibuat!*\n\n"
        f"≡ Total: *{format_rupiah(grand_total)}*\n"
        f"≡ Ongkir: {'GRATIS' if ongkir == 0 else format_rupiah(ongkir)}\n\n"
        f"≡ *Transfer ke:*\n{rekening_text}\n\n"
        f"📸 Setelah transfer, *kirim bukti bayar* (foto/struk) ke chat ini.\n"
        f"Admin akan memproses pesanan setelah verifikasi pembayaran."
    )

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"🔔 *PESANAN BARU #{pesanan_id}*\n\n"
                f"Dari: {user.first_name} (@{user.username or '-'})\n"
                f"Nama: {context.user_data['checkout_nama']}\n"
                f"Total: *{format_rupiah(grand_total)}*\n"
                f"Catatan: {catatan or '-'}\n\n"
                f"/detail_{pesanan_id} untuk lihat detail",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass

    return ConversationHandler.END

async def checkout_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Checkout dibatalkan.", reply_markup=menu_utama_keyboard())
    return ConversationHandler.END

# ===== PESANAN =====

async def pesanan_saya(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    pesanan_list = await db.get_pesanan_by_user(user_id)
    if not pesanan_list:
        await query.edit_message_text(
            "📋 *Belum ada pesanan.*\n\nYuk belanja dulu!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("≡ Belanja", callback_data="katalog")],
                [InlineKeyboardButton("← Menu", callback_data="menu")]
            ])
        )
        return

    text = "📋 *Pesanan Saya*\n\n"
    status_emoji = {
        "menunggu": "🟡", "diproses": "🔵", "dikirim": "🟣",
        "selesai": "✅", "dibatalkan": "❌"
    }

    for p in pesanan_list:
        emoji = status_emoji.get(p['status'], "⚪")
        text += f"{emoji} *#{p['id']}* — {format_rupiah(p['total'])} — {p['status'].upper()}\n"
        text += f"   {p['created_at'][:16]}\n\n"

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("← Menu", callback_data="menu")]
    ]))

# ===== INFO TOKO =====

async def info_toko(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    onkir_text = f"Gratis ongkir belanja >= {format_rupiah(config.GRATIS_ONGKIR_MIN)}"
    rekening_text = "\n".join([f"  • {bank}: {rek}" for bank, rek in config.REKENING.items()])

    text = (
        f"ℹ️ *{config.TOKO_NAMA}*\n\n"
        f"{config.TOKO_DESC}\n\n"
        f"≡ *Pengiriman:*\n{onkir_text}\nOngkir default: {format_rupiah(config.ONGKIR_DEFAULT)}\n\n"
        f"≡ *Pembayaran:*\n{rekening_text}\n\n"
        f"≡ *Cara Belanja:*\n"
        f"1. Pilih produk di Katalog\n"
        f"2. Tambah ke Keranjang\n"
        f"3. Checkout & isi data diri\n"
        f"4. Transfer & kirim bukti bayar\n"
        f"5. Admin proses & kirim pesanan\n"
    )

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Chat Admin", url=f"tg://user?id={config.ADMIN_IDS[0]}")],
        [InlineKeyboardButton("← Menu", callback_data="menu")]
    ]))

# ===== CHAT ADMIN =====

async def chat_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        f"💬 *Chat Admin*\n\n"
        f"Klik tombol di bawah untuk langsung chat admin.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("≡ Chat Admin Langsung", url=f"tg://user?id={config.ADMIN_IDS[0]}")],
            [InlineKeyboardButton("← Menu", callback_data="menu")]
        ])
    )

# ===== ADMIN PANEL =====

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Kamu bukan admin.")
        return

    stats = await db.get_stats()
    text = (
        f"🔧 *Admin Panel — {config.TOKO_NAMA}*\n\n"
        f"≡ Total Pesanan: {stats['total_pesanan']}\n"
        f"💰 Total Pendapatan: {format_rupiah(stats['total_pendapatan'])}\n"
        f"≡ Total Produk: {stats['total_produk']}\n"
        f"🔔 Pesanan Baru: {stats['pesanan_baru']}\n"
    )

    buttons = [
        [InlineKeyboardButton("≡ Kelola Produk", callback_data="admin_produk")],
        [InlineKeyboardButton("≡ Pesanan Baru", callback_data="admin_pesanan_baru"),
         InlineKeyboardButton("≡ Semua Pesanan", callback_data="admin_semua_pesanan")],
        [InlineKeyboardButton("➕ Tambah Produk", callback_data="admin_tambah_produk")],
        [InlineKeyboardButton("≡ Statistik", callback_data="admin_stats")]
    ]

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

async def admin_produk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    semua = await db.get_produk(aktif_only=False)
    if not semua:
        await query.edit_message_text("Belum ada produk.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Tambah Produk", callback_data="admin_tambah_produk")],
            [InlineKeyboardButton("← Admin", callback_data="admin_back")]
        ]))
        return

    text = "≡ *Daftar Produk*\n\n"
    for p in semua:
        status = "✅" if p['aktif'] and p['stok'] > 0 else "❌"
        text += f"{status} `{p['kode']}` — {p['nama']}\n"
        text += f"   {format_rupiah(p['harga'])} | Stok: {p['stok']} | {p['kategori']}\n\n"

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Tambah Produk", callback_data="admin_tambah_produk")],
        [InlineKeyboardButton("← Admin", callback_data="admin_back")]
    ]))

async def admin_pesanan_baru(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    pesanan = await db.get_pesanan(status='menunggu')
    if not pesanan:
        await query.edit_message_text("✅ Tidak ada pesanan baru.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("← Admin", callback_data="admin_back")]
        ]))
        return

    text = "🔔 *Pesanan Baru*\n\n"
    buttons = []
    for p in pesanan:
        text += f"#{p['id']} — {p['nama']} — {format_rupiah(p['total'])}\n"
        buttons.append([
            InlineKeyboardButton(f"≡ #{p['id']}", callback_data=f"detail_{p['id']}"),
            InlineKeyboardButton("✅ Proses", callback_data=f"proses_{p['id']}"),
            InlineKeyboardButton("❌ Batal", callback_data=f"batalkan_{p['id']}")
        ])
    buttons.append([InlineKeyboardButton("← Admin", callback_data="admin_back")])

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

async def admin_semua_pesanan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    pesanan = await db.get_pesanan(limit=20)
    if not pesanan:
        await query.edit_message_text("Belum ada pesanan.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("← Admin", callback_data="admin_back")]
        ]))
        return

    status_emoji = {"menunggu": "🟡", "diproses": "🔵", "dikirim": "🟣", "selesai": "✅", "dibatalkan": "❌"}
    text = "≡ *Semua Pesanan*\n\n"
    buttons = []
    for p in pesanan:
        emoji = status_emoji.get(p['status'], "⚪")
        text += f"{emoji} #{p['id']} — {p['nama']} — {format_rupiah(p['total'])} — {p['status']}\n"
        buttons.append([InlineKeyboardButton(f"≡ Detail #{p['id']}", callback_data=f"detail_{p['id']}")])
    buttons.append([InlineKeyboardButton("← Admin", callback_data="admin_back")])

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

async def detail_pesanan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    pesanan_id = int(query.data.split("_")[1])
    pesanan, items = await db.get_detail_pesanan(pesanan_id)

    if not pesanan:
        await query.edit_message_text("Pesanan tidak ditemukan.")
        return

    items_text = "\n".join([f"• {i['nama_produk']} x{i['jumlah']} = {format_rupiah(i['harga'] * i['jumlah'])}" for i in items])
    text = (
        f"≡ *Pesanan #{pesanan['id']}*\n\n"
        f"Status: *{pesanan['status'].upper()}*\n"
        f"Pemesan: {pesanan['nama']} (@{pesanan['username'] or '-'})\n"
        f"No HP: {pesanan['nohp']}\n"
        f"Alamat: {pesanan['alamat']}\n\n"
        f"≡ *Item:*\n{items_text}\n\n"
        f"Ongkir: {format_rupiah(pesanan['ongkir'])}\n"
        f"💰 *Total: {format_rupiah(pesanan['total'])}*\n"
        f"Catatan: {pesanan['catatan'] or '-'}\n"
        f"Waktu: {pesanan['created_at'][:16]}"
    )

    buttons = []
    if is_admin(query.from_user.id):
        if pesanan['status'] == 'menunggu':
            buttons.append([
                InlineKeyboardButton("✅ Proses", callback_data=f"proses_{pesanan['id']}"),
                InlineKeyboardButton("❌ Batal", callback_data=f"batalkan_{pesanan['id']}")
            ])
        elif pesanan['status'] == 'diproses':
            buttons.append([
                InlineKeyboardButton("≡ Kirim", callback_data=f"kirim_{pesanan['id']}")
            ])
        elif pesanan['status'] == 'dikirim':
            buttons.append([
                InlineKeyboardButton("✅ Selesai", callback_data=f"selesai_{pesanan['id']}")
            ])

    buttons.append([InlineKeyboardButton("← Kembali", callback_data="admin_back")])
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

async def update_pesanan_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split("_")
    action = parts[0]
    pesanan_id = int(parts[1])

    if not is_admin(query.from_user.id):
        await query.answer("⛔ Bukan admin!")
        return

    status_map = {
        "proses": "diproses",
        "kirim": "dikirim",
        "selesai": "selesai",
        "batalkan": "dibatalkan"
    }

    new_status = status_map.get(action)
    if new_status:
        await db.update_status_pesanan(pesanan_id, new_status)
        pesanan, _ = await db.get_detail_pesanan(pesanan_id)

        emoji_map = {"diproses": "🔵", "dikirim": "🟣", "selesai": "✅", "dibatalkan": "❌"}
        await query.answer(f"Status diubah ke {new_status.upper()}")

        if pesanan:
            try:
                msg_map = {
                    "diproses": "Pesanan sedang diproses admin. Mohon ditunggu ya!",
                    "dikirim": "Pesanan sudah dikirim! Cek resi di chat admin.",
                    "selesai": "Pesanan selesai. Terima kasih sudah belanja!",
                    "dibatalkan": "Pesanan dibatalkan. Hubungi admin untuk info."
                }
                await context.bot.send_message(
                    pesanan['user_id'],
                    f"{emoji_map.get(new_status, '⚪')} *Pesanan #{pesanan_id}*\n\n"
                    f"Status: *{new_status.upper()}*\n\n{msg_map.get(new_status, '')}",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass

    context.callback_query = query
    await detail_pesanan(update, context)

# ===== ADMIN: TAMBAH PRODUK =====

async def admin_tambah_produk_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "➕ *Tambah Produk Baru*\n\n"
        "Ketik *kode produk* (unik, tanpa spasi, contoh: `kaos_003`)",
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
        harga = int(update.message.text.replace(".", "").replace(",", "").replace("rp", "").replace("Rp", ""))
        context.user_data['new_harga'] = harga
    except:
        await update.message.reply_text("❌ Harga harus angka! Coba lagi:")
        return WAIT_PRODUK_HARGA
    await update.message.reply_text("📦 *Stok berapa?*", parse_mode=ParseMode.MARKDOWN)
    return WAIT_PRODUK_STOK

async def admin_tambah_stok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['new_stok'] = int(update.message.text)
    except:
        await update.message.reply_text("❌ Stok harus angka!")
        return WAIT_PRODUK_STOK
    await update.message.reply_text("≡ *Kategori?* (contoh: Baju, Aksesoris, Elektronik)", parse_mode=ParseMode.MARKDOWN)
    return WAIT_PRODUK_KATEGORI

async def admin_tambah_kategori(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_kategori'] = update.message.text.title()
    await update.message.reply_text("📝 *Deskripsi?* (ketik - jika tidak ada)", parse_mode=ParseMode.MARKDOWN)
    return WAIT_PRODUK_DESK

async def admin_tambah_desk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    deskripsi = update.message.text if update.message.text != '-' else ''

    await db.tambah_produk(
        kode=context.user_data['new_kode'],
        nama=context.user_data['new_nama'],
        harga=context.user_data['new_harga'],
        stok=context.user_data['new_stok'],
        deskripsi=deskripsi,
        kategori=context.user_data['new_kategori']
    )

    text = (
        f"✅ *Produk Ditambahkan!*\n\n"
        f"Kode: `{context.user_data['new_kode']}`\n"
        f"Nama: {context.user_data['new_nama']}\n"
        f"Harga: {format_rupiah(context.user_data['new_harga'])}\n"
        f"Stok: {context.user_data['new_stok']}\n"
        f"Kategori: {context.user_data['new_kategori']}"
    )

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Tambah Lagi", callback_data="admin_tambah_produk")],
        [InlineKeyboardButton("≡ Lihat Produk", callback_data="admin_produk")],
        [InlineKeyboardButton("← Admin", callback_data="admin_back")]
    ]))
    return ConversationHandler.END

async def admin_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    stats = await db.get_stats()
    text = (
        f"🔧 *Admin Panel — {config.TOKO_NAMA}*\n\n"
        f"≡ Total Pesanan: {stats['total_pesanan']}\n"
        f"💰 Total Pendapatan: {format_rupiah(stats['total_pendapatan'])}\n"
        f"≡ Total Produk: {stats['total_produk']}\n"
        f"🔔 Pesanan Baru: {stats['pesanan_baru']}\n"
    )
    buttons = [
        [InlineKeyboardButton("≡ Kelola Produk", callback_data="admin_produk")],
        [InlineKeyboardButton("≡ Pesanan Baru", callback_data="admin_pesanan_baru"),
         InlineKeyboardButton("≡ Semua Pesanan", callback_data="admin_semua_pesanan")],
        [InlineKeyboardButton("➕ Tambah Produk", callback_data="admin_tambah_produk")],
    ]
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

# ===== STATISTIK =====

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    stats = await db.get_stats()
    semua_pesanan = await db.get_pesanan(limit=1000)

    by_status = {}
    for p in semua_pesanan:
        s = p['status']
        by_status[s] = by_status.get(s, 0) + 1

    text = (
        f"≡ *Statistik Detail*\n\n"
        f"Total Pesanan: {stats['total_pesanan']}\n"
        f"Total Pendapatan: *{format_rupiah(stats['total_pendapatan'])}*\n"
        f"Total Produk Aktif: {stats['total_produk']}\n\n"
        f"≡ *Per Status:*\n"
    )
    for s, count in by_status.items():
        text += f"  • {s}: {count}\n"

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("← Admin", callback_data="admin_back")]
    ]))

# ===== BUKTI BAYAR =====

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"📸 *Bukti Bayar dari {user.first_name} (@{user.username or '-'})*\n"
                f"User ID: `{user.id}`",
                parse_mode=ParseMode.MARKDOWN
            )
            await context.bot.forward_message(
                admin_id,
                user.id,
                update.message.message_id
            )
        except:
            pass
    await update.message.reply_text(
        "✅ Bukti bayar diterima! Admin akan verifikasi sebentar lagi.\n"
        "Terima kasih! 💕"
    )

# ===== DEFAULT HANDLER =====

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Ketik /start untuk memulai atau pilih menu di bawah 👇",
        reply_markup=menu_utama_keyboard()
    )

# ===== MAIN =====

async def post_init(app: Application):
    await db.init_db()
    await app.bot.set_my_commands([
        BotCommand("start", "Mulai bot"),
        BotCommand("admin", "Admin panel (khusus admin)"),
    ])
    produk = await db.get_produk()
    print(f"✅ Bot {config.TOKO_NAMA} berhasil jalan!")
    print(f"   Admin ID: {config.ADMIN_IDS}")
    print(f"   Total produk: {len(produk)}")

def main():
    app = Application.builder().token(config.BOT_TOKEN).post_init(post_init).build()

    # Checkout conversation
    checkout_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(checkout_start, pattern="^checkout$")],
        states={
            WAIT_NAMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, checkout_nama)],
            WAIT_ALAMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, checkout_alamat)],
            WAIT_NOHP: [MessageHandler(filters.TEXT & ~filters.COMMAND, checkout_nohp)],
            WAIT_CATATAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, checkout_catatan)],
        },
        fallbacks=[CommandHandler("cancel", checkout_cancel)],
    )

    # Tambah produk conversation
    tambah_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_tambah_produk_callback, pattern="^admin_tambah_produk$")],
        states={
            WAIT_PRODUK_KODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_tambah_kode)],
            WAIT_PRODUK_NAMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_tambah_nama)],
            WAIT_PRODUK_HARGA: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_tambah_harga)],
            WAIT_PRODUK_STOK: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_tambah_stok)],
            WAIT_PRODUK_KATEGORI: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_tambah_kategori)],
            WAIT_PRODUK_DESK: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_tambah_desk)],
        },
        fallbacks=[CommandHandler("cancel", checkout_cancel)],
    )

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))

    # Conversation handlers
    app.add_handler(checkout_conv)
    app.add_handler(tambah_conv)

    # Callback handlers
    app.add_handler(CallbackQueryHandler(start, pattern="^menu$"))
    app.add_handler(CallbackQueryHandler(katalog, pattern="^katalog$"))
    app.add_handler(CallbackQueryHandler(lihat_kategori, pattern="^kat_"))
    app.add_handler(CallbackQueryHandler(produk_prev, pattern="^produk_prev$"))
    app.add_handler(CallbackQueryHandler(produk_next, pattern="^produk_next$"))
    app.add_handler(CallbackQueryHandler(tambah_ke_keranjang, pattern="^add_"))
    app.add_handler(CallbackQueryHandler(lihat_keranjang, pattern="^keranjang$"))
    app.add_handler(CallbackQueryHandler(qty_update, pattern="^qty_"))
    app.add_handler(CallbackQueryHandler(hapus_item_keranjang, pattern="^del_"))
    app.add_handler(CallbackQueryHandler(kosong_keranjang, pattern="^kosong_keranjang$"))
    app.add_handler(CallbackQueryHandler(pesanan_saya, pattern="^pesanan_saya$"))
    app.add_handler(CallbackQueryHandler(info_toko, pattern="^info_toko$"))
    app.add_handler(CallbackQueryHandler(chat_admin, pattern="^chat_admin$"))

    # Admin callbacks
    app.add_handler(CallbackQueryHandler(admin_back, pattern="^admin_back$"))
    app.add_handler(CallbackQueryHandler(admin_produk, pattern="^admin_produk$"))
    app.add_handler(CallbackQueryHandler(admin_pesanan_baru, pattern="^admin_pesanan_baru$"))
    app.add_handler(CallbackQueryHandler(admin_semua_pesanan, pattern="^admin_semua_pesanan$"))
    app.add_handler(CallbackQueryHandler(admin_stats, pattern="^admin_stats$"))
    app.add_handler(CallbackQueryHandler(detail_pesanan, pattern="^detail_"))
    app.add_handler(CallbackQueryHandler(update_pesanan_status, pattern="^(proses|kirim|selesai|batalkan)_"))

    # Photo handler
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Default text handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print(f"🚀 Bot {config.TOKO_NAMA} starting...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
