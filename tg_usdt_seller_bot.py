import sqlite3, time, threading
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext

TOKEN = "YOUR_BOT_TOKEN"

ADMIN_IDS = [123456789]  # <-- CHANGE
LOG_GROUP_ID = -100123456789  # <-- CHANGE

UPI_ID = "yourupi@bank"  # <-- CHANGE
BANK_DETAILS = "Account: 0000000000 | IFSC: XXXX0123456"  # <-- OPTIONAL CHANGE

RATES = {
    "BEP20": 96,
    "TRC20": 96,
    "ERC20": 97
}

db = sqlite3.connect("orders.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY, user_id INTEGER, username TEXT, usdt REAL, m_network TEXT, wallet TEXT, amount REAL, status TEXT, created INT)")
db.commit()

def start(update, _):
    update.message.reply_text("USDT SELLING BOT 🌐\n\n/order — place order\nOnly Seller payment via UPI/Bank.")

def order(update, context):
    update.message.reply_text("Kitna USDT chahiye? Example: 100\nReply: `/usdt 100`", parse_mode="Markdown")

def usdt_amount(update, context):
    try:
        qty = float(update.message.text.split()[1])
    except:
        update.message.reply_text("Format: /usdt 100")
        return

    keyboard = [
        [InlineKeyboardButton("BEP20", callback_data=f"net_BEP20_{qty}")],
        [InlineKeyboardButton("TRC20", callback_data=f"net_TRC20_{qty}")],
        [InlineKeyboardButton("ERC20", callback_data=f"net_ERC20_{qty}")],
    ]
    update.message.reply_text("Network select kare:", reply_markup=InlineKeyboardMarkup(keyboard))

def net_selected(update: Update, context: CallbackContext):
    q = update.callback_query
    _, net, qty = q.data.split("_")
    qty = float(qty)
    context.user_data["usdt"] = qty
    context.user_data["net"] = net
    q.message.reply_text(f"Wallet address bhejo TRC/BEP/ERC ke hisab se:")
    q.answer()

def wallet(update, context):
    if "usdt" not in context.user_data:
        return
    wallet_addr = update.message.text
    qty = context.user_data["usdt"]
    net = context.user_data["net"]
    rate = RATES[net]
    amount = qty * rate
    user = update.message.from_user

    cursor.execute("INSERT INTO orders(user_id, username, usdt, m_network, wallet, amount, status, created) VALUES(?,?,?,?,?,?,?,?)",
                   (user.id, user.username, qty, net, wallet_addr, amount, "AWAITING_PAYMENT", int(time.time())))
    db.commit()
    order_id = cursor.lastrowid

    msg = f"""
🧾 Order #{order_id}
User: @{user.username}
USDT: {qty}
Network: {net}
Wallet: `{wallet_addr}`
Amount: ₹{amount}

Pay karo 30 min me:
UPI: {UPI_ID}
{BANK_DETAILS}

Payment ka screenshot bhejo!
"""
    update.message.reply_text(msg, parse_mode="Markdown")

    threading.Thread(target=timer_cancel, args=(order_id, update, context)).start()

def timer_cancel(order_id, update, context):
    time.sleep(1800)
    cursor.execute("SELECT status FROM orders WHERE id=?", (order_id,))
    st = cursor.fetchone()
    if st and st[0] == "AWAITING_PAYMENT":
        cursor.execute("UPDATE orders SET status='EXPIRED' WHERE id=?", (order_id,))
        db.commit()
        try:
            update.message.reply_text(f"⏳ Order #{order_id} expired auto-cancelled ❌")
        except:
            pass

def photo(update: Update, context: CallbackContext):
    user = update.message.from_user
    cursor.execute("SELECT id FROM orders WHERE user_id=? AND status='AWAITING_PAYMENT' ORDER BY id DESC LIMIT 1", (user.id,))
    row = cursor.fetchone()
    if not row:
        update.message.reply_text("Koi active order nahi!")
        return

    order_id = row[0]
    cursor.execute("UPDATE orders SET status='AWAITING_VERIFY' WHERE id=?", (order_id,))
    db.commit()

    keyboard = [
        [
            InlineKeyboardButton("✔ Approve", callback_data=f"approve_{order_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{order_id}")
        ],
        [
            InlineKeyboardButton("↩ Refund", callback_data=f"refund_{order_id}")
        ]
    ]

    update.message.forward(LOG_GROUP_ID)
    context.bot.send_message(LOG_GROUP_ID,
        f"🧾 Proof for Order #{order_id}\nUser: @{user.username}\nAdmin Action Required!",
        reply_markup=InlineKeyboardMarkup(keyboard))

    update.message.reply_text("Payment screenshot received! Verification pending 🔍")

def admin_action(update: Update, context: CallbackContext):
    q = update.callback_query
    if q.from_user.id not in ADMIN_IDS:
        q.answer("Admin only", show_alert=True)
        return

    action, order_id = q.data.split("_")
    order_id = int(order_id)

    if action == "approve":
        cursor.execute("UPDATE orders SET status='PAID' WHERE id=?", (order_id,))
        msg = f"Order #{order_id} Approved ✔\nCrypto send karo manually!"
    elif action == "cancel":
        cursor.execute("UPDATE orders SET status='CANCELLED' WHERE id=?", (order_id,))
        msg = f"Order #{order_id} Cancelled ❌"
    else:
        cursor.execute("UPDATE orders SET status='REFUNDING' WHERE id=?", (order_id,))
        msg = f"Order #{order_id} Refund Processing ↩"

    db.commit()
    q.answer("Done")
    q.message.edit_text(msg)

upd = Updater(TOKEN)
d = upd.dispatcher
d.add_handler(CommandHandler("start", start))
d.add_handler(CommandHandler("order", order))
d.add_handler(CommandHandler("usdt", usdt_amount))
d.add_handler(MessageHandler(Filters.text & ~Filters.command, wallet))
d.add_handler(MessageHandler(Filters.photo, photo))
d.add_handler(CallbackQueryHandler(admin_action))
d.add_handler(CallbackQueryHandler(net_selected, pattern="^net_"))

upd.start_polling()
upd.idle()