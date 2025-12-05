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
import threading

BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"

ADMINS = [7487670897, 6792736525]
ADMIN_GROUP_ID = -1003344654667
SUPPORT_USERNAME = "pxiSupport"

MIN_USDT = 10
MAX_USDT = 50000

UPI_ID = "priyanshkumar@bpunity"
BANK_INFO = """
🏦 BANK DETAILS:
Name: PRIYANSH KUMAR
A/C: 20322227398
IFSC: FINO0001157
Bank: Fino Payment Bank
"""

QR_URL = "https://graph.org/file/bb11c1622ee16e8e7637e-a8b5bfa3bf9d1fcdcf.jpg"
LOGO_URL = "https://graph.org/file/3ccf692a7d8ef875255ad-c769ee91e0422550c2.jpg"

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

def start_auto_expire(order_id: int):
    """Expire order after 30 minutes"""
    def worker():
        time.sleep(1800)
        cursor.execute("SELECT user_id,status FROM orders WHERE order_id=?", (order_id,))
        row = cursor.fetchone()
        if row and row[1] == "PENDING":
            cursor.execute("UPDATE orders SET status='EXPIRED' WHERE order_id=?", (order_id,))
            db.commit()
    threading.Thread(target=worker, daemon=True).start()


def price_calculator(usdt: float) -> int:
    return int(usdt * 97) if usdt <= 100 else int(usdt * 96)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("💰 BUY USDT", callback_data="BUY")],
        [InlineKeyboardButton("🛠 Support", url=f"https://t.me/{SUPPORT_USERNAME}")]
    ]
    await update.message.reply_photo(
        LOGO_URL,
        caption=f"""
👋 Welcome to **USDT Seller Bot**  

⚡ Trusted | Fast | Secure

💵 Price:
• 1-100 USDT = ₹97
• 101+ USDT = ₹96

🔢 Limits:
Min {MIN_USDT} — Max {MAX_USDT} USDT

👇 BUY button press kijiye ya amount type kariye 
""",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

async def callback_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["stage"] = "await_amount"
    await update.callback_query.message.reply_text("Kitna USDT chahiye? (Only number)")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    stage = context.user_data.get("stage")

    if stage != "await_wallet" and txt.replace('.', '', 1).isdigit():
        usdt = float(txt)

        if usdt < MIN_USDT:
            return await update.message.reply_text(f"Minimum {MIN_USDT} USDT ❌")
        if usdt > MAX_USDT:
            return await update.message.reply_text(f"Maximum {MAX_USDT} USDT ❌")

        amount = price_calculator(usdt)

        context.user_data.update({
            "usdt": usdt,
            "amount": amount,
            "stage": "choose_network"
        })

        keyboard = [
            [InlineKeyboardButton("TRC20", callback_data="NET:TRC20"),
             InlineKeyboardButton("BEP20", callback_data="NET:BEP20")],
            [InlineKeyboardButton("ERC20", callback_data="NET:ERC20")]
        ]

        return await update.message.reply_text(
            f"USDT: {usdt}\nAmount: ₹{amount}\nNetwork choose keriye 👇",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    if stage == "await_wallet":
        wallet = txt
        usdt = context.user_data["usdt"]
        amount = context.user_data["amount"]
        network = context.user_data["network"]

        cursor.execute(
            "INSERT INTO orders(user_id, username, usdt, network, wallet, amount, status, timestamp) VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?)",
            (update.effective_user.id, update.effective_user.username or "",
             usdt, network, wallet, amount, int(time.time()))
        )
        db.commit()
        order_id = cursor.lastrowid
        start_auto_expire(order_id)
        context.user_data.clear()

        caption = f"""
📌 Order #{order_id}
USDT: {usdt}
Network: {network}
Wallet: `{wallet}`
Amount: ₹{amount}

⏳ 30 minutes me payment karo..
📤 Payment screenshot yahi bhejo...
"""
        return await update.message.reply_photo(QR_URL, caption=caption, parse_mode="Markdown")


async def cb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "BUY":
        return await callback_buy(update, context)

    if q.data.startswith("NET:"):
        context.user_data["network"] = q.data.split(":")[1]
        context.user_data["stage"] = "await_wallet"
        return await q.message.reply_text("Apna wallet address bhejein:")

    if q.data.startswith("ADMIN:"):
        action, order_id = q.data.split(":")[1:]
        order_id = int(order_id)

        if q.from_user.id not in ADMINS:
            return await q.answer("Admin only ❌", show_alert=True)

        cursor.execute("SELECT user_id FROM orders WHERE order_id=?", (order_id,))
        row = cursor.fetchone()
        if not row:
            return
        uid = row[0]

        if action == "APPROVE":
            cursor.execute("UPDATE orders SET status='APPROVED' WHERE order_id=?", (order_id,))
            db.commit()
            await context.bot.send_message(uid, f"🎯 Order #{order_id} Approved — USDT releasing…")
            await q.message.edit_caption(
                caption=f"Order #{order_id} ✔ Approved\nBy Admin @{q.from_user.username}"
            )
        else:
            cursor.execute("UPDATE orders SET status='CANCELLED' WHERE order_id=?", (order_id,))
            db.commit()
            await context.bot.send_message(uid, f"❌ Order #{order_id} Cancelled")
            await q.message.edit_caption(
                caption=f"Order #{order_id} ❌ Cancelled\nBy Admin @{q.from_user.username}"
            )

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cursor.execute(
        "SELECT order_id, usdt, network, wallet, amount FROM orders WHERE user_id=? AND status='PENDING' ORDER BY order_id DESC LIMIT 1",
        (user.id,))
    row = cursor.fetchone()

    if not row:
        return await update.message.reply_text("❌ No active order")

    order_id, usdt, network, wallet, amount = row
    file_id = update.message.photo[-1].file_id

    cursor.execute("UPDATE orders SET screenshot=? WHERE order_id=?", (file_id, order_id))
    db.commit()

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Approve", callback_data=f"ADMIN:APPROVE:{order_id}"),
         InlineKeyboardButton("Cancel", callback_data=f"ADMIN:CANCEL:{order_id}")]
    ])

    await context.bot.send_photo(
        ADMIN_GROUP_ID, file_id,
        caption=f"Payment Proof #{order_id}\nUser @{user.username or user.id}\nUSDT: {usdt}\nNetwork: {network}\nWallet: `{wallet}`\n₹{amount}",
        parse_mode="Markdown",
        reply_markup=kb
    )
    await update.message.reply_text("📥 Screenshot Received — Admin verify karega")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(cb_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.run_polling()

if __name__ == "__main__":
    main()