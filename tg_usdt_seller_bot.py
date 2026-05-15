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

# =========================================================
# 🌞 SUN CRYPTO ESCROW
# =========================================================

BOT_TOKEN = ""

ADMINS = [8564072723, 6792736525, 8179168001,]

# NEW LOGGER / ADMIN GROUP
ADMIN_GROUP_ID = -1003933002377

SUPPORT_USERNAME = "SunCryptoEscrow"

BOT_NAME = "🌞 Sun Crypto Escrow"

# =========================================================
# LIMITS
# =========================================================

MIN_USDT = 50
MAX_USDT = 10000

# =========================================================
# FIXED PRICE
# =========================================================

USDT_PRICE = 98

# =========================================================
# PAYMENT DETAILS
# =========================================================

UPI_ID = "nareshsinghchauhan1@oksbi"

ACCOUNT_NAME = "NARESH SINGH CHAUHAN"

# =========================================================
# IMAGES
# =========================================================

QR_URL = "https://graph.org/file/a02ca4f82476e234e4465-1fa60e811bf5854014.jpg"

LOGO_URL = "https://graph.org/file/52009de412b6fa6f88902-0aaa3a3dd322da5d94.jpg"

# =========================================================
# FOOTER
# =========================================================

FOOTER_TAG = "💎 Trusted • Secure • Fastest USDT Deals"

# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================================================
# DATABASE
# =========================================================

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
    escrow INTEGER,
    escrow_charge INTEGER,
    billing TEXT,
    status TEXT,
    timestamp INTEGER,
    screenshot TEXT
)
""")

db.commit()

# =========================================================
# AUTO EXPIRE
# =========================================================

def start_auto_expire(order_id: int):

    def worker():

        time.sleep(1800)

        cursor.execute(
            "SELECT status FROM orders WHERE order_id=?",
            (order_id,)
        )

        row = cursor.fetchone()

        if row and row[0] == "PENDING":

            cursor.execute(
                "UPDATE orders SET status='EXPIRED' WHERE order_id=?",
                (order_id,)
            )

            db.commit()

    threading.Thread(target=worker, daemon=True).start()

# =========================================================
# PRICE CALCULATOR
# =========================================================

def price_calculator(usdt: float):

    return int(usdt * USDT_PRICE)

# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [

        [
            InlineKeyboardButton(
                "💰 Buy USDT",
                callback_data="BUY"
            )
        ],

        [
            InlineKeyboardButton(
                "🛡 Escrow Deal",
                callback_data="ESCROW"
            )
        ],

        [
            InlineKeyboardButton(
                "📞 Support",
                url=f"https://t.me/{SUPPORT_USERNAME}"
            )
        ]

    ]

    caption = f"""
<blockquote>
🌞 <b>WELCOME TO SUN CRYPTO ESCROW</b>
</blockquote>

<blockquote>
🚀 INDIA'S TRUSTED USDT MARKETPLACE
</blockquote>

<blockquote>
⚡ Instant Deals  
🔒 Safe Transactions  
🛡 Secure Escrow  
💸 Fast Payments  
</blockquote>

<blockquote>
💰 LIVE RATE : ₹{USDT_PRICE} / USDT
</blockquote>

<blockquote>
📦 LIMITS
➜ Minimum : {MIN_USDT} USDT
➜ Maximum : {MAX_USDT} USDT
</blockquote>

<blockquote>
🛡 ESCROW CHARGE : ₹0
</blockquote>

<blockquote>
🔥 100% Trusted Crypto Service
🔥 Instant Approval
🔥 Fastest Support
🔥 Manual Scam-Free Verification
</blockquote>

<blockquote>
👇 CLICK BUTTON BELOW TO START
</blockquote>

{FOOTER_TAG}
"""

    await update.message.reply_photo(
        photo=LOGO_URL,
        caption=caption,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =========================================================
# BUY
# =========================================================

async def callback_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["stage"] = "await_amount"
    context.user_data["escrow"] = 0

    await update.callback_query.message.reply_text(
        f"""
💰 Enter USDT Amount

📌 Minimum : {MIN_USDT}
📌 Maximum : {MAX_USDT}
"""
    )

# =========================================================
# ESCROW
# =========================================================

async def callback_escrow(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["stage"] = "await_amount"
    context.user_data["escrow"] = 1

    await update.callback_query.message.reply_text(
        f"""
🛡 ESCROW MODE ENABLED

💰 Enter USDT Amount

📌 Minimum : {MIN_USDT}
📌 Maximum : {MAX_USDT}

💸 Escrow Charges : ₹0
"""
    )

# =========================================================
# TEXT HANDLER
# =========================================================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    txt = update.message.text.strip()

    stage = context.user_data.get("stage")

    # =====================================================
    # AMOUNT
    # =====================================================

    if stage != "await_wallet" and txt.replace('.', '', 1).isdigit():

        usdt = float(txt)

        if usdt < MIN_USDT:

            return await update.message.reply_text(
                f"❌ Minimum Buy Limit Is {MIN_USDT} USDT"
            )

        if usdt > MAX_USDT:

            return await update.message.reply_text(
                f"❌ Maximum Buy Limit Is {MAX_USDT} USDT"
            )

        amount = price_calculator(usdt)

        escrow = context.user_data.get("escrow", 0)

        escrow_charge = 0

        total = amount + escrow_charge

        billing = f"""
🧾 BILLING DETAILS

💰 USDT : {usdt}

💵 Rate : ₹{USDT_PRICE}

💸 Amount : ₹{amount}

🛡 Escrow Charge : ₹0

━━━━━━━━━━━━━━━

💳 TOTAL PAYABLE : ₹{total}
"""

        context.user_data["usdt"] = usdt
        context.user_data["amount"] = amount
        context.user_data["billing"] = billing
        context.user_data["escrow_charge"] = escrow_charge

        context.user_data["stage"] = "choose_network"

        keyboard = [

            [
                InlineKeyboardButton(
                    "🌐 TRC20",
                    callback_data="NET:TRC20"
                ),

                InlineKeyboardButton(
                    "🟡 BEP20",
                    callback_data="NET:BEP20"
                )
            ],

            [
                InlineKeyboardButton(
                    "🔵 ERC20",
                    callback_data="NET:ERC20"
                )
            ]
        ]

        escrow_text = "Enabled ✅" if escrow else "Disabled ❌"

        return await update.message.reply_text(
            f"""
💎 ORDER SUMMARY

💰 USDT : {usdt}

💵 Amount : ₹{amount}

🛡 Escrow : {escrow_text}

💸 Escrow Charges : ₹0

━━━━━━━━━━━━━━━

👇 SELECT NETWORK
""",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # =====================================================
    # WALLET
    # =====================================================

    if stage == "await_wallet":

        wallet = txt

        usdt = context.user_data["usdt"]
        amount = context.user_data["amount"]
        network = context.user_data["network"]
        billing = context.user_data["billing"]

        escrow = context.user_data.get("escrow", 0)

        escrow_charge = context.user_data.get(
            "escrow_charge",
            0
        )

        cursor.execute("""
        INSERT INTO orders(
            user_id,
            username,
            usdt,
            network,
            wallet,
            amount,
            escrow,
            escrow_charge,
            billing,
            status,
            timestamp
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)
        """, (

            update.effective_user.id,
            update.effective_user.username or "",
            usdt,
            network,
            wallet,
            amount,
            escrow,
            escrow_charge,
            billing,
            int(time.time())
        ))

        db.commit()

        order_id = cursor.lastrowid

        start_auto_expire(order_id)

        context.user_data.clear()

        escrow_text = (
            "🛡 ESCROW ENABLED ✅"
            if escrow else
            "🛡 NORMAL DEAL"
        )

        caption = f"""
🌞 SUN CRYPTO ESCROW

━━━━━━━━━━━━━━━

📌 ORDER ID : #{order_id}

{escrow_text}

💰 USDT : {usdt}

🌐 Network : {network}

🏦 Wallet :
`{wallet}`

━━━━━━━━━━━━━━━

🧾 BILLING

💵 Rate : ₹{USDT_PRICE}

💸 Amount : ₹{amount}

🛡 Escrow Charge : ₹0

━━━━━━━━━━━━━━━

💳 TOTAL PAYABLE :
₹{amount}

━━━━━━━━━━━━━━━

💳 PAYMENT DETAILS

👤 {ACCOUNT_NAME}

🏧 UPI :
`{UPI_ID}`

━━━━━━━━━━━━━━━

⏳ Complete Payment Within 30 Minutes

📤 Send Payment Screenshot Here

🔥 Fast Approval Available

{FOOTER_TAG}
"""

        return await update.message.reply_photo(
            photo=QR_URL,
            caption=caption,
            parse_mode="Markdown"
        )

# =========================================================
# CALLBACKS
# =========================================================

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
            """
🏦 SEND YOUR WALLET ADDRESS

⚠️ Wrong Address = Fund Loss
"""
        )

    # =====================================================
    # ADMIN
    # =====================================================

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
✅ PAYMENT APPROVED

📌 Order #{order_id}

💸 USDT Will Be Sent Shortly

🌞 Thank You For Choosing
Sun Crypto Escrow
"""
            )

            try:

                await q.message.edit_caption(
                    caption=f"""
✅ ORDER APPROVED

📌 Order #{order_id}

👤 Approved By :
@{q.from_user.username}

🌞 Sun Crypto Escrow
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
❌ ORDER CANCELLED

📌 Order #{order_id}

📞 Contact Support :
@{SUPPORT_USERNAME}
"""
            )

            try:

                await q.message.edit_caption(
                    caption=f"""
❌ ORDER CANCELLED

📌 Order #{order_id}

👤 Cancelled By :
@{q.from_user.username}

🌞 Sun Crypto Escrow
"""
                )

            except:
                pass

# =========================================================
# PHOTO HANDLER
# =========================================================

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
            "❌ No Active Order Found"
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

    keyboard = InlineKeyboardMarkup([

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

    escrow_text = "Enabled ✅" if escrow else "Disabled ❌"

    admin_caption = f"""
📥 NEW PAYMENT PROOF

━━━━━━━━━━━━━━━

📌 Order ID : #{order_id}

👤 User :
@{user.username or user.id}

💰 USDT : {usdt}

🌐 Network : {network}

🏦 Wallet :
`{wallet}`

💵 Amount : ₹{amount}

🛡 Escrow : {escrow_text}

━━━━━━━━━━━━━━━

💳 Payment Receiver

👤 {ACCOUNT_NAME}

🏧 {UPI_ID}

━━━━━━━━━━━━━━━

🌞 SUN CRYPTO ESCROW
"""

    await context.bot.send_photo(
        chat_id=ADMIN_GROUP_ID,
        photo=file_id,
        caption=admin_caption,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

    await update.message.reply_text(
        """
✅ SCREENSHOT RECEIVED

⏳ Admin Verification Pending

🔥 Usually Takes 1-5 Minutes
"""
    )

# =========================================================
# MAIN
# =========================================================

def main():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

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

    print("🌞 SUN CRYPTO ESCROW STARTED")

    app.run_polling()

# =========================================================

if __name__ == "__main__":
    main()