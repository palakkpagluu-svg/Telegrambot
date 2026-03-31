import os, json, qrcode
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
ADMIN_USERNAME = "yourusername"

DATA_FILE = "data.json"

# ===== LOAD / SAVE =====
def load_data():
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()

# ===== USER =====
def get_user(uid):
    uid = str(uid)
    if uid not in data:
        data[uid] = {"balance": 0, "orders": []}
    return data[uid]

# ===== QR =====
def generate_qr(amount):
    file = f"qr_{amount}.png"
    link = f"upi://pay?pa=niteshextema@fam&am={amount}&cu=INR"
    img = qrcode.make(link)
    img.save(file)
    return file

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("💰 Wallet", callback_data="wallet")],
        [InlineKeyboardButton("📦 Buy Followers", callback_data="order")],
        [InlineKeyboardButton("👤 Account", callback_data="account")],
        [InlineKeyboardButton("📜 Orders", callback_data="history")],
        [InlineKeyboardButton("🎯 Promo", callback_data="promo")],
        [InlineKeyboardButton("📞 Contact", callback_data="contact")]
    ]

    await update.message.reply_text(
        "🔥 PRO BOT (NO ERROR VERSION)\n⏱ 0–24 Hours Delivery",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ===== BUTTON =====
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = str(q.from_user.id)
    user = get_user(uid)

    if q.data == "wallet":
        await q.message.reply_text("Enter amount:")
        context.user_data["step"] = "wallet"

    elif q.data == "account":
        await q.message.reply_text(f"💰 Balance: ₹{user['balance']}")

    elif q.data == "history":
        if not user["orders"]:
            await q.message.reply_text("No orders yet ❌")
        else:
            text = "📜 Last Orders:\n"
            for o in user["orders"][-5:]:
                text += f"{o}\n"
            await q.message.reply_text(text)

    elif q.data == "order":
        kb = [
            [InlineKeyboardButton("1K - ₹20", callback_data="buy_20")],
            [InlineKeyboardButton("2K - ₹40", callback_data="buy_40")],
            [InlineKeyboardButton("5K - ₹100", callback_data="buy_100")],
            [InlineKeyboardButton("10K - ₹200", callback_data="buy_200")],
            [InlineKeyboardButton("30K - ₹900", callback_data="buy_900")],
            [InlineKeyboardButton("50K - ₹1000", callback_data="buy_1000")]
        ]
        await q.message.reply_text("Choose package:", reply_markup=InlineKeyboardMarkup(kb))

    elif q.data.startswith("buy_"):
        amt = int(q.data.split("_")[1])

        if user["balance"] < amt:
            await q.message.reply_text("❌ Not enough balance")
            return

        context.user_data["amount"] = amt
        await q.message.reply_text("Send Instagram username:")
        context.user_data["step"] = "username"

    elif q.data == "promo":
        await q.message.reply_text("Send promo code:")
        context.user_data["step"] = "promo"

    elif q.data == "contact":
        await q.message.reply_text(f"https://t.me/{ADMIN_USERNAME}")

# ===== MESSAGE =====
async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    user = get_user(uid)
    txt = update.message.text

    if context.user_data.get("step") == "wallet":
        try:
            amt = int(txt)
            context.user_data["amt"] = amt

            qr = generate_qr(amt)
            await update.message.reply_photo(open(qr, "rb"), caption=f"Pay ₹{amt}")
            context.user_data["step"] = "pay"
        except:
            await update.message.reply_text("Enter valid amount ❌")

    elif context.user_data.get("step") == "username":
        username = txt
        amt = context.user_data["amount"]

        user["balance"] -= amt
        user["orders"].append(f"{username} - ₹{amt}")
        save_data(data)

        await context.bot.send_message(
            ADMIN_ID,
            f"📦 NEW ORDER\nUser: {uid}\nUsername: {username}\nAmount: ₹{amt}"
        )

        await update.message.reply_text(
            "✅ Order placed!\n⏱ 0–24 hours delivery\n❗ Contact admin if issue"
        )

        context.user_data["step"] = None

    elif context.user_data.get("step") == "promo":
        if txt.upper() == "NEW10":
            user["balance"] += 10
            save_data(data)
            await update.message.reply_text("Promo applied ✅")
        else:
            await update.message.reply_text("Invalid ❌")

# ===== PHOTO =====
async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    amt = context.user_data.get("amt", 0)

    file = await update.message.photo[-1].get_file()
    path = f"{uid}.jpg"
    await file.download_to_drive(path)

    kb = [[InlineKeyboardButton("Approve", callback_data=f"ok_{uid}_{amt}")]]

    await context.bot.send_photo(
        ADMIN_ID,
        open(path, "rb"),
        caption=f"Payment\nUser: {uid}\n₹{amt}",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ===== ADMIN =====
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    _, uid, amt = q.data.split("_")
    user = get_user(uid)

    user["balance"] += int(amt)
    save_data(data)

    await context.bot.send_message(uid, f"₹{amt} added ✅")

# ===== BROADCAST =====
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(ADMIN_ID):
        return

    msg = " ".join(context.args)
    for uid in data:
        try:
            await context.bot.send_message(uid, msg)
        except:
            pass

# ===== MAIN =====
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(admin, pattern="^ok_"))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))
    app.add_handler(MessageHandler(filters.PHOTO, photo))

    print("🔥 Bot Running Successfully...")
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
