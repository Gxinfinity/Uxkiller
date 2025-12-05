# tg_usdt_seller_bot.py
import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import sqlite3
import time

BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"

ADMINS = [7487670897, 6792736525]
ADMIN_GROUP_ID = -1003344654667
SUPPORT_USERNAME = "YourSupportUsername"  # example: CryptoHelpX

UPI_ID = "priyanshkumar@bpunity"
BANK_INFO = """
🏦 **BANK DETAILS**
👤 Name: *PRIYANSH KUMAR*
🏧 Bank: Fino Payment Bank
💳 A/C: `20322227398`
🔐 IFSC: `FINO0001157`
"""

QR_URL = "https://graph.org/file/bb11c1622ee16e8e7637e-a8b5bfa3bf9d1fcdcf.jpg"
LOGO_URL = "https://graph.org/file/3ccf692a7d8ef875255ad-c769ee91e0422550c2.jpg"

MIN_USDT = 10
MAX_USDT = 50000

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = sqlite3.connect("orders.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders(
 order_id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER,
 username TEXT,
 usdt REAL,
 network TEXT,
 wallet TEXT,
 amount INTEGER,
 status TEXT,
 timestamp INTEGER,
 screenshot TEXT
)
""")
db.commit()

def price_calculator(usdt):
    return int(usdt * 97) if usdt <= 100 else int(usdt * 96)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("💰 BUY USDT", callback_data="BUY")],
        [InlineKeyboardButton("🛟 Support", url=f"https://t.me/{SUPPORT_USERNAME}")]
    ]
    await update.message.reply_photo(
        LOGO_URL,
        caption=f"""
👋 **Welcome to USDT Seller Bot!**

📌 *Fast & Trusted Seller*

⭐ Price:
• 1-100 USDT = ₹97 / USDT  
• 101+ USDT = ₹96 / USDT

🔢 Limits:
Minimum **{MIN_USDT} USDT**
Maximum **{MAX_USDT} USDT**

Press BUY USDT or type amount directly 👇
""",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

async def callback_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["stage"] = "await_amount"
    await update.callback_query.message.reply_text("Kitna USDT chahiye? (Only number)")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    stage = context.user_data.get("stage")

    # Amount stage
    if (stage in (None, "await_amount")) and txt.replace('.', '', 1).isdigit():
        usdt = float(txt)

        if usdt < MIN_USDT:
            return await update.message.reply_text(f"Minimum {MIN_USDT} USDT order allowed ❌")
        if usdt > MAX_USDT:
            return await update.message.reply_text(f"Maximum {MAX_USDT} USDT allowed ❌")

        amount = price_calculator(usdt)

        context.user_data.update({
            "usdt": usdt,
            "amount": amount,
            "stage": "choose_network"
        })

        keyboard = [
            [
                InlineKeyboardButton("TRC20", callback_data="NET:TRC20"),
                InlineKeyboardButton("BEP20", callback_data="NET:BEP20")
            ],
            [InlineKeyboardButton("ERC20", callback_data="NET:ERC20")]
        ]

        await update.message.reply_text(
            f"USDT: {usdt}\nAmount: ₹{amount}\n\nChoose Network:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if stage == "await_wallet":
        wallet = txt
        usdt = context.user_data["usdt"]
        amount = context.user_data["amount"]
        network = context.user_data["network"]

        cursor.execute("""
        INSERT INTO orders(user_id, username, usdt, network, wallet, amount, status, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?)
        """, (update.effective_user.id, update.effective_user.username or "",
              usdt, network, wallet, amount, int(time.time())))
        db.commit()
        order_id = cursor.lastrowid
        context.user_data.clear()

        caption = f"""
📌 Order #{order_id}
👤 @{update.effective_user.username or update.effective_user.id}
💵 USDT: {usdt}
🔗 Network: {network}
📍 Wallet: `{wallet}`
💰 Amount: ₹{amount}

⏳ Pay within 30 minutes
📤 Screenshot bhejo payment ka
"""

        await update.message.reply_photo(
            QR_URL, caption=caption, parse_mode="Markdown"
        )
        return

async def cb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "BUY":
        return await callback_buy(update, context)

    if q.data.startswith("NET:"):
        net = q.data.split(":")[1]
        context.user_data["network"] = net
        context.user_data["stage"] = "await_wallet"
        return await q.message.reply_text("Wallet address bhejo:")

    if q.data.startswith("ADMIN:"):
        action, order_id = q.data.split(":")[1:]
        order_id = int(order_id)
        if q.from_user.id not in ADMINS:
            return await q.answer("Admin only ❌", show_alert=True)

        cursor.execute("SELECT user_id FROM orders WHERE order_id=?", (order_id,))
        row = cursor.fetchone()
        if not row: return

        uid = row[0]

        if action == "APPROVE":
            cursor.execute("UPDATE orders SET status='APPROVED' WHERE order_id=?", (order_id,))
            db.commit()
            await context.bot.send_message(uid, f"✅ Order #{order_id} Approved — USDT releasing soon!")
            await q.edit_message_caption(f"Order #{order_id} ✔ Approved")
        else:
            cursor.execute("UPDATE orders SET status='CANCELLED' WHERE order_id=?", (order_id,))
            db.commit()
            await context.bot.send_message(uid, f"❌ Order #{order_id} Cancelled")
            await q.edit_message_caption(f"Order #{order_id} ❌ Cancelled")

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    cursor.execute("""
    SELECT order_id, usdt, network, wallet, amount FROM orders
    WHERE user_id=? AND status='PENDING'
    ORDER BY order_id DESC LIMIT 1
    """, (user.id,))
    row = cursor.fetchone()
    if not row:
        return await update.message.reply_text("No pending order found.")

    order_id, usdt, network, wallet, amount = row
    file_id = update.message.photo[-1].file_id
    cursor.execute("UPDATE orders SET screenshot=? WHERE order_id=?", (file_id, order_id))
    db.commit()

    caption = (
        f"📌 Payment Proof — Order #{order_id}\n"
        f"👤 @{user.username or user.id}\n"
        f"USDT: {usdt}\n"
        f"Network: {network}\n"
        f"Wallet: `{wallet}`\n"
        f"Amount: ₹{amount}"
    )

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✔ Approve", callback_data=f"ADMIN:APPROVE:{order_id}"),
            InlineKeyboardButton("✖ Cancel", callback_data=f"ADMIN:CANCEL:{order_id}")
        ]
    ])

    await context.bot.send_photo(
        ADMIN_GROUP_ID, file_id,
        caption=caption, reply_markup=kb, parse_mode="Markdown"
    )
    await update.message.reply_text("📥 Submitted! Admin verify karega.")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(cb_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.run_polling()

if __name__ == "__main__":
    main()