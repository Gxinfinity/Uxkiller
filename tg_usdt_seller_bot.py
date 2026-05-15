# tg_usdt_seller_bot.py

import logging
import sqlite3
import threading
import time

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"

ADMINS = [7487670897, 6792736525]
ADMIN_GROUP_ID = -1003344654667
SUPPORT_USERNAME = "pxiSupport"

MIN_USDT = 30
MAX_USDT = 50000

# =========================
# PAYMENT DETAILS UPDATED
# =========================

UPI_ID = "nareshsinghchauhan1@oksbi"

BANK_INFO_TEXT = (
    "👤 Name: NARESH SINGH CHAUHAN\n"
)

QR_URL = "https://graph.org/file/a02ca4f82476e234e4465-1fa60e811bf5854014.jpg"

LOGO_URL = "https://graph.org/file/4fc1ecca4629e98f0423c-b8af9f9d9c3f9ac655.jpg"

FOOTER_TAG = "💎 Lᴇɢɪᴛ ᴜꜱᴅᴛ ᴅᴇᴀʟꜱ ᴄᴏɴɴᴇᴄᴛ"

# =========================

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
    screenshot TEXT,
    escrow INTEGER DEFAULT 0
)
""")

db.commit()


# =========================
# AUTO EXPIRE
# =========================

def start_auto_expire(order_id: int):
    def worker():
        time.sleep(1800)

        cursor.execute(
            "SELECT user_id,status FROM orders WHERE order_id=?",
            (order_id,)
        )

        row = cursor.fetchone()

        if row and row[1] == "PENDING":
            cursor.execute(
                "UPDATE orders SET status='EXPIRED' WHERE order_id=?",
                (order_id,)
            )
            db.commit()

    threading.Thread(target=worker, daemon=True).start()


# =========================
# PRICE
# =========================

def price_calculator(usdt: float) -> int:
    if usdt <= 100:
        return int(usdt * 97)
    return int(usdt * 96)


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [InlineKeyboardButton("💰 BUY USDT", callback_data="BUY")],
        [InlineKeyboardButton("🛡 ESCROW DEAL", callback_data="ESCROW")],
        [InlineKeyboardButton("🛠 SUPPORT", url=f"https://t.me/{SUPPORT_USERNAME}")]
    ]

    caption = f"""
<blockquote>👋 Welcome To <b>USDT SELLER BOT</b></blockquote>

<blockquote>⚡ Trusted • Fast • Secure</blockquote>

<blockquote>💵 PRICE:</blockquote>

<blockquote>
• 1 - 100 USDT = ₹97
• 101+ USDT = ₹96
</blockquote>

<blockquote>
🔢 LIMITS:
Min {MIN_USDT} — Max {MAX_USDT} USDT
</blockquote>

<blockquote>
🛡 Escrow Available
👇 Buy Button Press Kijiye
</blockquote>

{FOOTER_TAG}
"""

    await update.message.reply_photo(
        photo=LOGO_URL,
        caption=caption,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# BUY CALLBACK
# =========================

async def callback_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["stage"] = "await_amount"
    context.user_data["escrow"] = 0

    await update.callback_query.message.reply_text(
        "Kitna USDT chahiye? (Only Number)"
    )


# =========================
# ESCROW CALLBACK
# =========================

async def callback_escrow(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["stage"] = "await_amount"
    context.user_data["escrow"] = 1

    await update.callback_query.message.reply_text(
        "🛡 ESCROW MODE ENABLED\n\nKitna USDT chahiye?"
    )


# =========================
# TEXT HANDLER
# =========================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    txt = update.message.text.strip()
    stage = context.user_data.get("stage")

    # =====================
    # AMOUNT
    # =====================

    if stage != "await_wallet" and txt.replace('.', '', 1).isdigit():

        usdt = float(txt)

        if usdt < MIN_USDT:
            return await update.message.reply_text(
                f"❌ Minimum {MIN_USDT} USDT"
            )

        if usdt > MAX_USDT:
            return await update.message.reply_text(
                f"❌ Maximum {MAX_USDT} USDT"
            )

        amount = price_calculator(usdt)

        context.user_data["usdt"] = usdt
        context.user_data["amount"] = amount
        context.user_data["stage"] = "choose_network"

        keyboard = [
            [
                InlineKeyboardButton(
                    "TRC20",
                    callback_data="NET:TRC20"
                ),

                InlineKeyboardButton(
                    "BEP20",
                    callback_data="NET:BEP20"
                )
            ],

            [
                InlineKeyboardButton(
                    "ERC20",
                    callback_data="NET:ERC20"
                )
            ]
        ]

        escrow_text = "Enabled ✅" if context.user_data.get("escrow") else "Disabled ❌"

        return await update.message.reply_text(
            f"""
💰 USDT: {usdt}

💵 Amount: ₹{amount}

🛡 Escrow: {escrow_text}

👇 Network Select Karo
""",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # =====================
    # WALLET
    # =====================

    if stage == "await_wallet":

        wallet = txt

        usdt = context.user_data["usdt"]
        amount = context.user_data["amount"]
        network = context.user_data["network"]
        escrow = context.user_data.get("escrow", 0)

        cursor.execute("""
        INSERT INTO orders(
            user_id,
            username,
            usdt,
            network,
            wallet,
            amount,
            status,
            timestamp,
            escrow
        )

        VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?, ?)
        """, (
            update.effective_user.id,
            update.effective_user.username or "",
            usdt,
            network,
            wallet,
            amount,
            int(time.time()),
            escrow
        ))

        db.commit()

        order_id = cursor.lastrowid

        start_auto_expire(order_id)

        context.user_data.clear()

        escrow_line = "🛡 ESCROW DEAL ENABLED\n" if escrow else ""

        caption = f"""
📌 Order #{order_id}

💰 USDT: {usdt}

🌐 Network: {network}

🏦 Wallet:
`{wallet}`

💵 Amount: ₹{amount}

{escrow_line}

━━━━━━━━━━━━━━━

💳 PAYMENT DETAILS

👤 Name:
NARESH SINGH CHAUHAN

🏧 UPI:
`{UPI_ID}`

━━━━━━━━━━━━━━━

⏳ Payment Within 30 Minutes

📤 Payment Screenshot Yahi Send Kare

{FOOTER_TAG}
"""

        return await update.message.reply_photo(
            photo=QR_URL,
            caption=caption,
            parse_mode="Markdown"
        )


# =========================
# CALLBACK HANDLER
# =========================

async def cb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query

    await q.answer()

    # BUY
    if q.data == "BUY":
        return await callback_buy(update, context)

    # ESCROW
    if q.data == "ESCROW":
        return await callback_escrow(update, context)

    # NETWORK
    if q.data.startswith("NET:"):

        network = q.data.split(":")[1]

        context.user_data["network"] = network
        context.user_data["stage"] = "await_wallet"

        return await q.message.reply_text(
            "📥 Apna Wallet Address Send Karo:"
        )

    # =====================
    # ADMIN ACTIONS
    # =====================

    if q.data.startswith("ADMIN:"):

        action, order_id = q.data.split(":")[1:]
        order_id = int(order_id)

        if q.from_user.id not in ADMINS:
            return await q.answer(
                "Admin Only ❌",
                show_alert=True
            )

        cursor.execute(
            "SELECT user_id FROM orders WHERE order_id=?",
            (order_id,)
        )

        row = cursor.fetchone()

        if not row:
            return

        uid = row[0]

        # APPROVE
        if action == "APPROVE":

            cursor.execute(
                "UPDATE orders SET status='APPROVED' WHERE order_id=?",
                (order_id,)
            )

            db.commit()

            await context.bot.send_message(
                uid,
                f"""
✅ Order #{order_id} Approved

💸 USDT Releasing Soon

{FOOTER_TAG}
"""
            )

            try:
                await q.message.edit_caption(
                    caption=f"""
✅ ORDER APPROVED

📌 Order #{order_id}

👤 Approved By:
@{q.from_user.username}

{FOOTER_TAG}
"""
                )

            except:
                pass

        # CANCEL
        else:

            cursor.execute(
                "UPDATE orders SET status='CANCELLED' WHERE order_id=?",
                (order_id,)
            )

            db.commit()

            await context.bot.send_message(
                uid,
                f"""
❌ Order #{order_id} Cancelled

Contact Support:
@{SUPPORT_USERNAME}
"""
            )

            try:
                await q.message.edit_caption(
                    caption=f"""
❌ ORDER CANCELLED

📌 Order #{order_id}

👤 Cancelled By:
@{q.from_user.username}

{FOOTER_TAG}
"""
                )

            except:
                pass


# =========================
# PHOTO HANDLER
# =========================

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    cursor.execute("""
    SELECT
        order_id,
        usdt,
        network,
        wallet,
        amount,
        escrow

    FROM orders

    WHERE user_id=?
    AND status='PENDING'

    ORDER BY order_id DESC
    LIMIT 1
    """, (user.id,))

    row = cursor.fetchone()

    if not row:
        return await update.message.reply_text(
            "❌ No Active Order"
        )

    (
        order_id,
        usdt,
        network,
        wallet,
        amount,
        escrow
    ) = row

    file_id = update.message.photo[-1].file_id

    cursor.execute(
        "UPDATE orders SET screenshot=? WHERE order_id=?",
        (file_id, order_id)
    )

    db.commit()

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ APPROVE",
                callback_data=f"ADMIN:APPROVE:{order_id}"
            ),

            InlineKeyboardButton(
                "❌ CANCEL",
                callback_data=f"ADMIN:CANCEL:{order_id}"
            )
        ]
    ])

    escrow_text = "YES ✅" if escrow else "NO ❌"

    admin_caption = f"""
📥 PAYMENT PROOF RECEIVED

📌 Order ID: #{order_id}

👤 User:
@{user.username or user.id}

💰 USDT: {usdt}

🌐 Network: {network}

🏦 Wallet:
`{wallet}`

💵 Amount: ₹{amount}

🛡 Escrow: {escrow_text}

━━━━━━━━━━━━━━━

💳 PAYMENT DETAILS

👤 NARESH SINGH CHAUHAN

🏧 {UPI_ID}

━━━━━━━━━━━━━━━

{FOOTER_TAG}
"""

    await context.bot.send_photo(
        chat_id=ADMIN_GROUP_ID,
        photo=file_id,
        caption=admin_caption,
        parse_mode="Markdown",
        reply_markup=kb
    )

    await update.message.reply_text(
        "✅ Screenshot Received\n\nAdmin Verify Karega."
    )


# =========================
# MAIN
# =========================

def main():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        CallbackQueryHandler(cb_handler)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler
        )
    )

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            photo_handler
        )
    )

    print("BOT STARTED ✅")

    app.run_polling()


if __name__ == "__main__":
    main()