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
    return int(usdt * 97) if usdt <= 100 else int(usdt * 96)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[ "BUY USDT" ]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "👋 Welcome to USDT Seller Bot!\nPress BUY button👇",
        reply_markup=reply_markup
    )

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Kitna USDT chahiye? (Only Number)")
    context.user_data["stage"] = "usdt"

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text

    if txt == "BUY USDT":
        await buy(update, context)
        return

    if context.user_data.get("stage") == "usdt" and txt.isdigit():
        usdt = float(txt)
        amount = price_calculator(usdt)
        context.user_data["usdt"] = usdt
        context.user_data["amount"] = amount

        keyboard = [
            [
                InlineKeyboardButton("BEP20", callback_data="BEP20"),
                InlineKeyboardButton("TRC20", callback_data="TRC20"),
            ],
            [
                InlineKeyboardButton("ERC20", callback_data="ERC20"),
            ]
        ]

        context.user_data["stage"] = "network"

        await update.message.reply_text(
            f"USDT: {usdt}\nAmount: ₹{amount}\n\nChoose network:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if context.user_data.get("stage") == "wallet":
        wallet = txt
        usdt = context.user_data["usdt"]
        amount = context.user_data["amount"]
        network = context.user_data["network"]

        cursor.execute("""
        INSERT INTO orders(user_id, username, usdt, network, wallet, amount, status, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?)
        """, (update.message.from_user.id, update.message.from_user.username,
              usdt, network, wallet, amount, int(time.time())))
        db.commit()

        order_id = cursor.lastrowid

        context.user_data.clear()

        await update.message.reply_photo(
            QR_URL,
            caption=f"""
📌 Order #{order_id}
USDT: {usdt}
Network: {network}
Wallet: `{wallet}`
Amount: ₹{amount}

🚨 Payment within 30 minutes

💸 PAY VIA:
UPI: {UPI_ID}
{BANK_INFO}

📤 Send Screenshot after payment!
""",
            parse_mode="Markdown"
        )
        return

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    user = query.from_user.id

    if data in ["BEP20", "TRC20", "ERC20"]:
        context.user_data["network"] = data
        context.user_data["stage"] = "wallet"

        await query.message.reply_text("Apna wallet address bhejo:")
        return

    if data.startswith("admin_"):
        split = data.split("_")
        action = split[1]
        order_id = int(split[2])

        cursor.execute("SELECT user_id FROM orders WHERE order_id=?", (order_id,))
        row = cursor.fetchone()
        if not row:
            return

        user_id = row[0]
        msg = "🎉 USDT Released!" if action == "approve" else "❌ Order Cancelled!"

        cursor.execute("UPDATE orders SET status=? WHERE order_id=?", (msg.split()[1], order_id))
        db.commit()

        await context.bot.send_message(user_id, msg)
        await query.edit_message_text(f"Admin Action: {msg}")

async def screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        return

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

    photo_id = update.message.photo[-1].file_id
    cursor.execute("UPDATE orders SET screenshot=? WHERE order_id=?", (photo_id, order_id))
    db.commit()

    keyboard = [
        [
            InlineKeyboardButton("Approve", callback_data=f"admin_approve_{order_id}"),
            InlineKeyboardButton("Cancel", callback_data=f"admin_cancel_{order_id}"),
        ]
    ]

    await context.bot.send_photo(
        LOG_GROUP,
        photo_id,
        caption=f"📌 Payment Proof\nOrder #{order_id}\n👤 @{user.username}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await update.message.reply_text("📥 Payment Submitted. Admin verify karega!")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.PHOTO, screenshot))
    app.add_handler(CallbackQueryHandler(callback))

    await app.run_polling(close_loop=False)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())