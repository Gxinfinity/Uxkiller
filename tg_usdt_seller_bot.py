import sqlite3, time, threading
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext

TOKEN = "YOUR_BOT_TOKEN"

ADMIN_IDS = [7487670897, 6792736525]
LOG_GROUP_ID = -1003344654667

UPI_ID = "priyanshkumar@bpunity"
QR_URL = "https://graph.org/file/bb11c1622ee16e8e7637e-a8b5bfa3bf9d1fcdcf.jpg"

BANK_DETAILS = """
🏦 BANK DETAILS
Account Holder: PRIYANSH KUMAR
Bank: FINO PAYMENT BANK
A/C Number: 20322227398
IFSC: FINO0001157
""".strip()

db = sqlite3.connect("orders.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY, user_id INTEGER, username TEXT, amount REAL, status TEXT, created INT)")
db.commit()

def start(update, _):
    update.message.reply_text("💳 Payment Bot\n\n/order — create payment request")

def order(update, context):
    update.message.reply_text("Kitna amount pay karna hai? Example: 1000\nReply: `/amt 1000`", parse_mode="Markdown")

def amt(update, context):
    try:
        amt = float(update.message.text.split()[1])
    except:
        update.message.reply_text("Format: /amt 1000")
        return

    user = update.message.from_user
    cursor.execute("INSERT INTO orders(user_id, username, amount, status, created) VALUES(?,?,?,?,?)",
                   (user.id, user.username, amt, "AWAITING_PAYMENT", int(time.time())))
    db.commit()
    order_id = cursor.lastrowid

    caption = f"""
🧾 Payment Request #{order_id}
👤 User: @{user.username}
💰 Amount: ₹{amt}

⏳ 30 minutes ke andar payment karein

📍 Scan QR👇
UPI: `{UPI_ID}`

{BANK_DETAILS}

📸 Payment screenshot bheje!
""".strip()

    update.message.reply_photo(photo=QR_URL, caption=caption, parse_mode="Markdown")
    threading.Thread(target=timer_cancel, args=(order_id, update, context)).start()

def timer_cancel(order_id, update, context):
    time.sleep(1800)
    cursor.execute("SELECT status FROM orders WHERE id=?", (order_id,))
    st = cursor.fetchone()
    if st and st[0] == "AWAITING_PAYMENT":
        cursor.execute("UPDATE orders SET status='EXPIRED' WHERE id=?", (order_id,))
        db.commit()
        update.message.reply_text(f"⚠️ Payment #{order_id} Auto-Cancelled ❌")

def photo(update: Update, context: CallbackContext):
    user = update.message.from_user
    cursor.execute("SELECT id FROM orders WHERE user_id=? AND status='AWAITING_PAYMENT' ORDER BY id DESC LIMIT 1", (user.id,))
    row = cursor.fetchone()
    if not row:
        update.message.reply_text("⚠️ No active pending payment!")
        return

    order_id = row[0]
    cursor.execute("UPDATE orders SET status='AWAITING_VERIFY' WHERE id=?", (order_id,))
    db.commit()

    keyboard = [
        [
            InlineKeyboardButton("✔ Accept", callback_data=f"ok_{order_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"rej_{order_id}")
        ]
    ]

    update.message.forward(LOG_GROUP_ID)
    context.bot.send_message(LOG_GROUP_ID,
        f"📌 Verify Payment #{order_id}\nUser: @{user.username}",
        reply_markup=InlineKeyboardMarkup(keyboard))

    update.message.reply_text("🕵️ Payment Screenshot forwarded for verification…")

def admin_action(update: Update, context: CallbackContext):
    q = update.callback_query
    if q.from_user.id not in ADMIN_IDS:
        q.answer("Admin only", show_alert=True)
        return

    action, order_id = q.data.split("_")
    order_id = int(order_id)

    if action == "ok":
        cursor.execute("UPDATE orders SET status='PAID' WHERE id=?", (order_id,))
        msg = f"Payment #{order_id} ✔ Verified"
    else:
        cursor.execute("UPDATE orders SET status='REJECTED' WHERE id=?", (order_id,))
        msg = f"Payment #{order_id} ❌ Rejected"

    db.commit()
    q.answer("Updated")
    q.message.edit_text(msg)

upd = Updater(TOKEN)
dp = upd.dispatcher

dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("order", order))
dp.add_handler(CommandHandler("amt", amt))
dp.add_handler(MessageHandler(Filters.photo, photo))
dp.add_handler(CallbackQueryHandler(admin_action))
upd.start_polling()
upd.idle()