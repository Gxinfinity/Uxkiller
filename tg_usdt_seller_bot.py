import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import sqlite3
import time

BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"

ADMINS = [7487670897, 6792736525]
LOG_GROUP = -1003344654667

UPI_ID = "priyanshkumar@bpunity"

BANK_INFO = """
🏦 BANK DETAILS:
Account Holder: PRIYANSH KUMAR
Account Number: 20322227398
IFSC Code: FINO0001157
Bank: Fino Payment Bank
"""

QR_URL = "https://graph.org/file/bb11c1622ee16e8e7637e-a8b5bfa3bf9d1fcdcf.jpg"

logging.basicConfig(level=logging.INFO)

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
    if usdt <= 100:
        return int(usdt * 97)
    else:
        return int(usdt * 96)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome to the USDT Selling Bot!\n\n➡ Use /sell to order USDT")

async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Kitna USDT chahiye? (Only Number)")

    return

async def text_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if not text.isdigit():
        return
    
    usdt = float(text)
    amount = price_calculator(usdt)

    keyboard = [
        [
            InlineKeyboardButton("BEP20", callback_data=f"net:BEP20:{usdt}:{amount}"),
            InlineKeyboardButton("TRC20", callback_data=f"net:TRC20:{usdt}:{amount}"),
        ],
        [
            InlineKeyboardButton("ERC20", callback_data=f"net:ERC20:{usdt}:{amount}")
        ]
    ]

    await update.message.reply_text(
        f"USDT: {usdt}\nAmount: ₹{amount}\n\nChoose Network:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split(":")

    if data[0] == "net":
        network, usdt, amount = data[1], float(data[2]), int(data[3])
        await query.message.reply_text("Apna crypto wallet address bhejo:")

        context.user_data["order"] = (network, usdt, amount)

    elif data[0] == "admin":
        action, order_id = data[1], int(data[2])

        cursor.execute(f"SELECT user_id FROM orders WHERE order_id={order_id}")
        row = cursor.fetchone()
        if not row:
            return
        
        user_id = row[0]

        if action == "approve":
            msg = "🎉 USDT Released Successfully!"
            cursor.execute(f"UPDATE orders SET status='APPROVED' WHERE order_id={order_id}")

        if action == "cancel":
            msg = "❌ Order Cancelled"
            cursor.execute(f"UPDATE orders SET status='CANCELLED' WHERE order_id={order_id}")

        db.commit()
        await context.bot.send_message(user_id, msg)
        await query.edit_message_text(f"Admin: {msg}")

async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "order" not in context.user_data:
        return

    wallet = update.message.text
    network, usdt, amount = context.user_data["order"]

    cursor.execute("""
    INSERT INTO orders(user_id, username, usdt, network, wallet, amount, status, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?)
    """, (update.message.from_user.id, update.message.from_user.username, usdt, network, wallet, amount, int(time.time())))
    db.commit()

    order_id = cursor.lastrowid

    msg = f"""
📌 Order #{order_id}
USDT: {usdt}
Network: {network}
Wallet: `{wallet}`
Amount: ₹{amount}

🧾 Pay below:
🥷 UPI: {UPI_ID}
{BANK_INFO}

⏳ Pay within 30 minutes
📤 Payment Screenshot bhejo
    """

    await update.message.reply_photo(photo=QR_URL, caption=msg, parse_mode="Markdown")

async def screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        return
    
    photo_file_id = update.message.photo[-1].file_id
    user = update.message.from_user

    cursor.execute("""
    SELECT order_id FROM orders 
    WHERE user_id=? AND status='PENDING'
    ORDER BY order_id DESC LIMIT 1
    """, (user.id,))
    
    row = cursor.fetchone()
    if not row:
        return
    
    order_id = row[0]

    cursor.execute(f"UPDATE orders SET screenshot='{photo_file_id}' WHERE order_id={order_id}")
    db.commit()

    keyboard = [
        [
            InlineKeyboardButton("Approve", callback_data=f"admin:approve:{order_id}"),
            InlineKeyboardButton("Cancel", callback_data=f"admin:cancel:{order_id}"),
        ]
    ]

    await update.bot.send_photo(
        LOG_GROUP, photo_file_id,
        caption=f"📌 Payment Proof\nOrder #{order_id}\nUser @{user.username}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await update.message.reply_text("📥 Payment Submitted. Admin Verify Karega.")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sell", sell))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_msg))
    app.add_handler(MessageHandler(filters.TEXT, wallet))
    app.add_handler(MessageHandler(filters.PHOTO, screenshot))
    app.add_handler(CallbackQueryHandler(callback))

    asyncio.run(main())

if __name__ == "__main__":
    import asyncio
    asyncio.get_event_loop().run_until_complete(main())