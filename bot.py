import os
import logging
from io import BytesIO
from urllib.parse import quote

import qrcode
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Config (from Railway env vars) ────────────────────────────────────────────
BOT_TOKEN   = os.environ["BOT_TOKEN"]
SUPPORT     = os.environ.get("SUPPORT", "@yoursupport")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")        # e.g. https://mybot.up.railway.app
PORT        = int(os.environ.get("PORT", 8080))

# ── Images — pasted directly here instead of Railway variables ────────────────
# Telegram file_id (fastest) or a public HTTPS image URL. Leave "" for none.
CATALOGUE_PHOTO = "https://i.postimg.cc/JzNWCN6K/photo-2026-06-16-12-51-18.jpg"

# ── Paytm / UPI merchant details — QR codes are generated on the fly ──────────
UPI_ID        = os.environ.get("UPI_ID", "")          # e.g. merchant@paytm
MERCHANT_NAME = os.environ.get("MERCHANT_NAME", "Merchant")

# ── Conversation states ────────────────────────────────────────────────────────
CHOOSE_OPTION, = range(1)

# ── Option definitions ─────────────────────────────────────────────────────────
OPTION_KEYS = list("ABCDEFGHIJKLMN")

OPTION_NAMES = {
    "A": " 𝗦𝗡𝗔𝗣-𝗟𝗘𝗔𝗞𝗦💦",         
    "B": "𝐌𝐎𝐌-𝐒𝐎𝐍💦",        
    "C": "𝐂𝐇!𝐋𝐃-C0𝐑𝐍💦",
    "D": "𝐑@𝐏E-𝐏𝐑𝐍💦",
    "E": "🔰𝐍𝐞𝐩𝐚𝐥𝐢 𝐆𝐢𝐫𝐥𝐬",
    "F": "𝐓𝐄𝐄𝐍 𝐈𝐍𝐃𝐈𝐀 𝐆𝐈𝐑𝐋💦",
    "G": "𝗦𝗣𝗔 𝗟𝗘𝗔𝗞𝗦💦",
    "H": "𝐈𝐍𝐒𝐓𝐀 𝐋𝐄À𝐊𝐒👄",
    "I": "𝗔𝗡𝗜𝗠𝗔𝗟-𝗖0𝗥𝗡💦",
    "J": "𝙏e𝙡u𝙜𝙪 𝙇𝙚𝙖𝙠𝙨💦",
    "K": "SLEEPING PILLS😪",
    "L": "𝐂𝐇!𝐋𝐃-C0𝐑𝐍💦 8500+ 📷",
    "M": "𝑴𝒂𝒍𝒍𝒖 𝒈𝒊𝒓𝒍👄",
    "N": "𝐓𝐚𝐦𝐢𝐥 𝐠𝐢𝐫𝐥💦",
}


OPTION_PRICES = {
    "A": 49,               
    "B": 59,
    "C": 59,
    "D": 59,
    "E": 29,
    "F": 39,
    "G": 39,
    "H": 49,
    "I": 59,
    "J": 59,
    "K": 55,
    "L": 279,
    "M": 39,
    "N": 39,
}

# ── Per-option product photos ──────────────────────────────────────────────────
# Each value can be a Telegram file_id or a public HTTPS image URL.
# Put one or more images per option — options with 2+ images are sent as an album.
# Leave the list empty ([]) to fall back to a text-only message for that option.
OPTION_IMAGES = {
    "A": [
        "https://i.postimg.cc/BbBGdhyV/6195183861843562642.jpg",
        "https://i.postimg.cc/CMGYB11F/6195183861843562643.jpg",
        "https://i.postimg.cc/sfYyQXX3/6195183861843562644.jpg",
    ],
    "B": [
        "https://i.postimg.cc/j2KpQH5j/6197136079098416672.jpg",
        "https://i.postimg.cc/Vv1xBq6v/6197136079098416673.jpg",
    ],
    "C": [
        "https://i.postimg.cc/PJ2RW09m/6194864509550268113.jpg",
        "https://i.postimg.cc/MHdF7gN1/6194864509550268114.jpg",
    ],
    "D": [
        "https://i.postimg.cc/L6Wymkpy/6194839624509755003.jpg",
    ],
    "E": [
        "https://i.postimg.cc/QxFbYBTd/6194838550767931046.jpg",
    ],
    "F": [
        "https://i.postimg.cc/SsZ6DqQG/6194838550767931045.jpg",
    ],
    "G": [
        "https://i.postimg.cc/MTrB1DtL/6194839624509755001.jpg",
        "https://i.postimg.cc/nzwmqkT3/6194839624509755002.jpg",
    ],
    "H": [
        "https://i.postimg.cc/mrm1GwvJ/6194839624509755000.jpg",
    ],
    "I": [
        "https://i.postimg.cc/cJxFsdHd/6194994548275089265.jpg",
    ],
    "J": [
        "https://i.postimg.cc/sgycc356/6195091794924606466.jpg",
        "https://i.postimg.cc/zG5jjqT2/6195091794924606467.jpg",
    ],
    "K": [
        "https://i.postimg.cc/x8MvvZ8f/6194994548275089267.jpg",
        "https://i.postimg.cc/wMLXXrM6/6194994548275089268.jpg",
    ],
    "L": [
        "https://i.postimg.cc/Y06FGmD0/6194887302941707888.jpg",
        "https://i.postimg.cc/90d9Rqgr/6194887302941707889.jpg",
    ],
    "M": [
        "https://i.postimg.cc/h4LQ0TMf/6201777302362854382.jpg",
        "https://i.postimg.cc/G3FTjGz4/6201777302362854383.jpg",
        "https://i.postimg.cc/v8rxvfX1/6201777302362854384.jpg",
    ],
    "N": [
        "https://i.postimg.cc/pTDrqMfG/6201741606889656404.jpg",
        "https://i.postimg.cc/NM1Fpv6b/6201741606889656405.jpg",
    ],
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def option_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(f"{OPTION_NAMES.get(k, k)} — ₹{OPTION_PRICES[k]}", callback_data=f"opt:{k}")]
        for k in OPTION_KEYS
    ]
    return InlineKeyboardMarkup(rows)


def buy_keyboard(option: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💳 Buy Now", callback_data=f"buy:{option}")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back")],
        ]
    )


def generate_upi_qr(amount: int, note: str) -> BytesIO:
    """Build a Paytm/UPI payment QR on the fly from the merchant UPI ID."""
    upi_uri = (
        f"upi://pay?pa={quote(UPI_ID)}&pn={quote(MERCHANT_NAME)}"
        f"&am={amount}&cu=INR&tn={quote(note)}"
    )
    img = qrcode.make(upi_uri)
    buf = BytesIO()
    buf.name = "qr.png"
    img.save(buf, "PNG")
    buf.seek(0)
    return buf


async def show_product(chat_id: int, option: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the product photo(s) — single photo or album — with Buy Now / Back."""
    name    = OPTION_NAMES.get(option, f"Option {option}")
    price   = OPTION_PRICES.get(option, 0)
    images  = OPTION_IMAGES.get(option, [])
    caption = f"🛍️ *{name}*\n\nPrice: *₹{price}*"
    markup  = buy_keyboard(option)

    msg_ids = []
    if len(images) == 1:
        sent = await context.bot.send_photo(
            chat_id, photo=images[0], caption=caption, reply_markup=markup, parse_mode="Markdown"
        )
        msg_ids.append(sent.message_id)
    elif len(images) >= 2:
        album = await context.bot.send_media_group(
            chat_id, media=[InputMediaPhoto(url) for url in images]
        )
        msg_ids.extend(m.message_id for m in album)
        btn_msg = await context.bot.send_message(chat_id, caption, reply_markup=markup, parse_mode="Markdown")
        msg_ids.append(btn_msg.message_id)
    else:
        sent = await context.bot.send_message(chat_id, caption, reply_markup=markup, parse_mode="Markdown")
        msg_ids.append(sent.message_id)

    context.user_data["product_msgs"] = msg_ids


async def clear_product_msgs(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete whatever show_product() sent (single photo, or an album + button message)."""
    for msg_id in context.user_data.pop("product_msgs", []):
        try:
            await context.bot.delete_message(chat_id, msg_id)
        except Exception:
            pass


async def send_catalogue(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send catalogue photo (or text fallback) with option buttons."""
    markup  = option_keyboard()
    caption = "📋 *Our Service Catalogue*\n\n𝘛𝘩𝘪𝘴 𝘪𝘴 𝘢 𝘱𝘳𝘦𝘮𝘪𝘶𝘮 𝘢𝘥𝘶𝘭𝘵 𝘦𝘯𝘵𝘦𝘳𝘵𝘢𝘪𝘯𝘮𝘦𝘯𝘵 𝘱𝘭𝘢𝘵𝘧𝘰𝘳𝘮 𝘰𝘧𝘧𝘦𝘳𝘪𝘯𝘨 𝘢 𝘥𝘪𝘷𝘦𝘳𝘴𝘦, 𝘤𝘶𝘳𝘢𝘵𝘦𝘥 𝘭𝘪𝘣𝘳𝘢𝘳𝘺 𝘰𝘧 𝘩𝘪𝘨𝘩-𝘲𝘶𝘢𝘭𝘪𝘵𝘺 𝘤𝘰𝘯𝘵𝘦𝘯𝘵\n\nPlease select an option:"

    if CATALOGUE_PHOTO:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=CATALOGUE_PHOTO,
            caption=caption,
            reply_markup=markup,
            parse_mode="Markdown",
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=caption,
            reply_markup=markup,
            parse_mode="Markdown",
        )


# ── Handlers ───────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point — show catalogue immediately, no age gate."""
    await send_catalogue(update.effective_chat.id, context)
    return CHOOSE_OPTION


async def cb_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle option selection — show product photo(s) + Buy Now / Back."""
    q = update.callback_query
    await q.answer()
    option  = q.data.split(":", 1)[1]
    chat_id = q.from_user.id

    try:
        await q.delete_message()
    except Exception:
        pass

    await show_product(chat_id, option, context)
    return CHOOSE_OPTION


async def cb_buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle Buy Now — generate a UPI QR for this option's amount."""
    q = update.callback_query
    await q.answer()
    option  = q.data.split(":", 1)[1]
    chat_id = q.from_user.id

    name  = OPTION_NAMES.get(option, f"Option {option}")
    price = OPTION_PRICES.get(option, 0)

    payment_text = (
        f"💳 *Payment — {name}*\n\n"
        f"Amount: *₹{price}*\n\n"
        f"Please scan the QR code below to pay via *Paytm / UPI*.\n\n"
        f"⏳ Once you've paid, please wait — your payment will be "
        f"reviewed and approved manually. You'll be notified once it's confirmed. ✅"
    )

    await clear_product_msgs(chat_id, context)

    if UPI_ID:
        qr = generate_upi_qr(price, f"{name} payment")
        await context.bot.send_photo(chat_id, photo=qr, caption=payment_text, parse_mode="Markdown")
    else:
        await context.bot.send_message(
            chat_id,
            payment_text + f"\n\n_QR unavailable — contact {SUPPORT} to pay._",
            parse_mode="Markdown",
        )

    return ConversationHandler.END


async def cb_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle Back — return to the catalogue."""
    q = update.callback_query
    await q.answer()
    chat_id = q.from_user.id

    await clear_product_msgs(chat_id, context)
    await send_catalogue(chat_id, context)
    return CHOOSE_OPTION


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Session cancelled. Type /start to begin again.")
    return ConversationHandler.END


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Dev helper — send/forward any photo to the bot to get its file_id for OPTION_IMAGES."""
    file_id = update.message.photo[-1].file_id
    await update.message.reply_text(f"file_id:\n`{file_id}`", parse_mode="Markdown")


# ── App entry point ────────────────────────────────────────────────────────────

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            CHOOSE_OPTION: [
                CallbackQueryHandler(cb_option, pattern=r"^opt:"),
                CallbackQueryHandler(cb_buy, pattern=r"^buy:"),
                CallbackQueryHandler(cb_back, pattern=r"^back$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
        per_user=True,
        per_chat=True,
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))

    # ── Webhook (Railway) vs polling (local dev) ───────────────────────────────
    if WEBHOOK_URL:
        logger.info("Starting webhook on port %s …", PORT)
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
        )
    else:
        logger.info("WEBHOOK_URL not set — using long polling (local dev mode)")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
