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

# ========== CONFIG - replace BOT_TOKEN ==========
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"

ADMINS = [7487670897, 6792736525]            # your admin IDs
ADMIN_GROUP_ID = -1003344654667              # your admin log group id

UPI_ID = "priyanshkumar@bpunity"
BANK_INFO = """
🏦 BANK DETAILS:
Account Holder: PRIYANSH KUMAR
Account Number: 20322227398
IFSC Code: FINO0001157
Bank: Fino Payment Bank
"""

QR_URL = "https://graph.org/file/bb11c1622ee16e8e7637e-a8b5bfa3bf9d1fcdcf.jpg"

LOGGING = True

# ========== logging ==========
if LOGGING:
    logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== DB ==========
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

# ========== Helper ==========
def price_calculator(usdt: float) -> int:
    # <=100 : 97 rs, >100 : 96 rs
    return int(usdt * 97) if usdt <= 100 else int(usdt * 96)

def start_auto_expire(order_id: int, ttl_seconds: int = 30*60):
    def worker():
        time.sleep(ttl_seconds)
        cursor.execute("SELECT status FROM orders WHERE order_id=?", (order_id,))
        r = cursor.fetchone()
        if r and r[0] == "PENDING":
            cursor.execute("UPDATE orders SET status='EXPIRED' WHERE order_id=?", (order_id,))
            db.commit()
            # notify buyer if still active
            cursor.execute("SELECT user_id FROM orders WHERE order_id=?", (order_id,))
            row = cursor.fetchone()
            if row:
                try:
                    app = ApplicationBuilder().token(BOT_TOKEN).build()
                    # can't reliably use app here (avoid building new instance). skip notifying to prevent extra complexity.
                except Exception:
                    pass
    t = threading.Thread(target=worker, daemon=True)
    t.start()

# ========== Handlers ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [["BUY USDT"]]
    reply = ReplyKeyboardMarkup(kb, resize_keyboard=True)
    await update.message.reply_text("👋 Welcome to USDT Seller Bot!\nPress BUY USDT or type amount (number).", reply_markup=reply)

async def buy_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["stage"] = "await_amount"
    await update.message.reply_text("Kitna USDT chahiye? (Only number)")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    # If user clicked BUY USDT keyboard
    if txt.upper() == "BUY USDT":
        await buy_cmd(update, context)
        return

    stage = context.user_data.get("stage")

    # Stage: awaiting amount
    if stage in (None, "await_amount") and txt.replace('.', '', 1).isdigit():
        usdt = float(txt)
        amount = price_calculator(usdt)
        context.user_data["usdt"] = usdt
        context.user_data["amount"] = amount
        context.user_data["stage"] = "choose_network"

        keyboard = [
            [InlineKeyboardButton("TRC20", callback_data="NET:TRC20"),
             InlineKeyboardButton("BEP20", callback_data="NET:BEP20")],
            [InlineKeyboardButton("ERC20", callback_data="NET:ERC20")]
        ]
        await update.message.reply_text(f"USDT: {usdt}\nAmount: ₹{amount}\nChoose network:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Stage: waiting for wallet address
    if stage == "await_wallet":
        wallet = txt
        usdt = context.user_data.get("usdt")
        amount = context.user_data.get("amount")
        network = context.user_data.get("network")
        if not (usdt and amount and network):
            await update.message.reply_text("Session expired or invalid. Please /buy again.")
            context.user_data.clear()
            return

        # Insert order
        cursor.execute("""
        INSERT INTO orders(user_id, username, usdt, network, wallet, amount, status, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?)
        """, (update.effective_user.id, update.effective_user.username or "", usdt, network, wallet, amount, int(time.time())))
        db.commit()
        order_id = cursor.lastrowid

        # start expire timer
        start_auto_expire(order_id, ttl_seconds=30*60)

        context.user_data.clear()

        caption = f"""📌 Order #{order_id}
👤 User: @{update.effective_user.username or update.effective_user.id}
💵 USDT: {usdt}
🔗 Network: {network}
📍 Wallet: `{wallet}`
💰 Amount: ₹{amount}

⏳ Pay within 30 minutes.
📤 After payment upload screenshot here.
"""
        # send QR + details to user
        await update.message.reply_photo(photo=QR_URL, caption=caption, parse_mode="Markdown")
        return

    # Other messages ignored
    # (helps avoid double triggers)
    return

async def callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    # Network selection
    if data.startswith("NET:"):
        net = data.split(":",1)[1]
        context.user_data["network"] = net
        context.user_data["stage"] = "await_wallet"
        await q.message.reply_text(f"Network selected: {net}\nAb apna wallet address bhejo:")
        return

    # Admin actions: format ADMIN:ACTION:ORDERID
    if data.startswith("ADMIN:"):
        parts = data.split(":")
        if len(parts) != 3:
            await q.message.reply_text("Invalid admin callback")
            return
        action = parts[1]      # APPROVE or CANCEL
        order_id = int(parts[2])

        # Check admin
        if q.from_user.id not in ADMINS:
            await q.answer("Admin only", show_alert=True)
            return

        # Find buyer
        cursor.execute("SELECT user_id,status FROM orders WHERE order_id=?", (order_id,))
        row = cursor.fetchone()
        if not row:
            await q.message.reply_text("Order not found")
            return
        user_id, status = row

        if action == "APPROVE":
            cursor.execute("UPDATE orders SET status='APPROVED' WHERE order_id=?", (order_id,))
            db.commit()
            await context.bot.send_message(user_id, f"✅ Your payment for Order #{order_id} verified. Seller/Admin will send USDT shortly.")
            await q.edit_message_caption(f"✅ Order #{order_id} APPROVED by Admin @{q.from_user.username}")
        elif action == "CANCEL":
            cursor.execute("UPDATE orders SET status='CANCELLED' WHERE order_id=?", (order_id,))
            db.commit()
            await context.bot.send_message(user_id, f"❌ Your Order #{order_id} has been cancelled by Admin.")
            await q.edit_message_caption(f"❌ Order #{order_id} CANCELLED by Admin @{q.from_user.username}")
        else:
            await q.answer("Unknown action")
        return

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # User uploaded payment screenshot; find last pending order for this user
    if not update.message.photo:
        return
    user = update.effective_user
    cursor.execute("""
    SELECT order_id, usdt, network, wallet, amount FROM orders
    WHERE user_id=? AND status='PENDING'
    ORDER BY order_id DESC LIMIT 1
    """, (user.id,))
    row = cursor.fetchone()
    if not row:
        await update.message.reply_text("No pending order found. Create an order first via /buy or typing amount.")
        return
    order_id, usdt, network, wallet, amount = row

    # save screenshot file_id
    file_id = update.message.photo[-1].file_id
    cursor.execute("UPDATE orders SET screenshot=? WHERE order_id=?", (file_id, order_id))
    db.commit()

    # build admin caption with details and buttons
    caption = (f"📌 Payment Proof\nOrder #{order_id}\n👤 @{user.username or user.id}\n"
               f"💵 USDT: {usdt}\n🔗 Network: {network}\n📍 Wallet: `{wallet}`\n💰 Amount: ₹{amount}")

    keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"ADMIN:APPROVE:{order_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"ADMIN:CANCEL:{order_id}")
        ]
    ]
    # forward photo (send) to admin group with caption and admin buttons
    await context.bot.send_photo(chat_id=ADMIN_GROUP_ID, photo=file_id, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    # confirm to user
    await update.message.reply_text(f"📤 Payment proof received for Order #{order_id}. Admin will verify soon.")

# ========== Application startup ==========
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy_cmd))
    app.add_handler(CallbackQueryHandler(callback_query))
    # Order of text handlers: text_handler first (for amount/wallet flow)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    # Run (synchronous) — avoids asyncio.run conflicts on some VPS/envs
    app.run_polling()

if __name__ == "__main__":
    main()