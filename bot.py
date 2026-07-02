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
CATALOGUE_PHOTO = ""   # TODO: paste your catalogue image URL/file_id here

# ── Paytm / UPI merchant details — QR codes are generated on the fly ──────────
UPI_ID        = os.environ.get("UPI_ID", "")          # e.g. merchant@paytm
MERCHANT_NAME = os.environ.get("MERCHANT_NAME", "Merchant")

# ── Conversation states ────────────────────────────────────────────────────────
CHOOSE_OPTION, = range(1)

# ── Option definitions ─────────────────────────────────────────────────────────
OPTION_KEYS = list("ABCDEFGHIJKLMN")

OPTION_NAMES = {
    "A": " 𝗦𝗡𝗔𝗣-𝗟𝗘𝗔𝗞𝗦💦 -₹49 ",          # TODO: rename
    "B": "𝐌𝐎𝐌-𝐒𝐎𝐍💦 -₹59",          # TODO: rename
    "C": "𝐂𝐇!𝐋𝐃-C0𝐑𝐍💦 -₹59",
    "D": "𝐑@𝐏E-𝐏𝐑𝐍💦 -₹59",
    "E": "🔰𝐍𝐞𝐩𝐚𝐥𝐢 𝐆𝐢𝐫𝐥𝐬 -₹29",
    "F": "𝐓𝐄𝐄𝐍 𝐈𝐍𝐃𝐈𝐀 𝐆𝐈𝐑𝐋💦 -₹39",
    "G": "𝗦𝗣𝗔 𝗟𝗘𝗔𝗞𝗦💦 -₹39",
    "H": "𝐈𝐍𝐒𝐓𝐀 𝐋𝐄À𝐊𝐒👄 -₹49",
    "I": "𝗔𝗡𝗜𝗠𝗔𝗟_𝗖0𝗥𝗡💦 -₹59",
    "J": "𝙏e𝙡u𝙜𝙪 𝙇𝙚𝙖𝙠𝙨💦 -₹59",
    "K": "SLEEPING PILLS😪 -₹55",
    "L": "𝐂𝐇!𝐋𝐃-C0𝐑𝐍💦 8500+ 📷 -₹279",
    "M": "𝑴𝒂𝒍𝒍𝒖 𝒈𝒊𝒓𝒍👄 -₹39",
    "N": "𝐓𝐚𝐦𝐢𝐥 𝐠𝐢𝐫𝐥💦 -₹39",
}

OPTION_PRICES = {
    "A": 49,               # TODO: set real price
    "B": 59,               # TODO: set real price
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
    "A": ["blob:https://web.telegram.org/06100d7a-168e-4fbe-ac94-c278a597060f" , "blob:https://web.telegram.org/6acc63cd-3dea-4a18-a7f7-cefaf103d441" , "blob:https://web.telegram.org/49ae5aef-1aac-4e9a-9649-42819720bff2" ],   # TODO: e.g. ["https://example.com/a1.jpg"]
    "B": ["blob:https://web.telegram.org/38c64af1-c30e-4c71-9725-5e18d23ef3b9" , "blob:https://web.telegram.org/20b7dece-591b-46d3-8958-e2c4ffc8f706"],
    "C": ["blob:https://web.telegram.org/176bd91e-c98f-4ac0-ac6b-d5d99d21c41200" , "blob:https://web.telegram.org/b459781f-725b-40c7-b4ad-b4dc5b774cc6"],
    "D": ["blob:https://web.telegram.org/5b0ebb56-f009-4297-9ef8-c40cf6f8b9a2"],
    "E": ["blob:https://web.telegram.org/c98f9566-e69f-41d2-b712-87da49ee362b"],
    "F": ["blob:https://web.telegram.org/a84aac0d-6b17-4384-a2ad-014ef611b60a"],
    "G": ["blob:https://web.telegram.org/07bbe593-ebce-4f03-b67f-0e735df5dd1f" , "blob:https://web.telegram.org/2c11f78e-d431-4a8e-96ee-edaadd56a649"],
    "H": ["blob:https://web.telegram.org/ddea0376-35a3-4625-9537-5c82e6663ad8"],
    "I": ["blob:https://web.telegram.org/7d019ca3-3eae-4484-bb4f-2d00f9860f55"],
    "J": ["blob:https://web.telegram.org/47f48b4e-b109-4149-95b2-063f9ed9a097" , "blob:https://web.telegram.org/32c056d6-5c76-4c0e-92d5-9d85c52b4963"],
    "K": ["blob:https://web.telegram.org/1b57ac22-9334-48df-b0a8-bed4619e9fe3" , "blob:https://web.telegram.org/5dbab2e2-98c7-4ce2-882d-d404ac5f881f"],
    "L": ["blob:https://web.telegram.org/9595b4ce-f5ec-44f8-a2b6-a47459bcf8b0" , "blob:https://web.telegram.org/bb9aed2b-d207-4ec0-bb80-db1cc1f65372"],
    "M": ["blob:https://web.telegram.org/a7157449-5ba6-4b0e-8cfc-70167ebaf8db" , "blob:https://web.telegram.org/21cd1b0f-3561-432a-9b75-51f9b6b809dc" , "blob:https://web.telegram.org/66239956-2ee7-45af-8ca7-83118b199948"],
    "N": ["blob:https://web.telegram.org/381ab83d-15f7-4d09-8c70-47484384b684" , "blob:https://web.telegram.org/43a0d8ad-66a6-4ca1-899c-23b4e00bde09"],   # e.g. ["https://example.com/n1.jpg", "https://example.com/n2.jpg"]
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
    caption = "📋 Our Service Catalogue*\n\n𝘛𝘩𝘪𝘴 𝘪𝘴 𝘢 𝘱𝘳𝘦𝘮𝘪𝘶𝘮 𝘢𝘥𝘶𝘭𝘵 𝘦𝘯𝘵𝘦𝘳𝘵𝘢𝘪𝘯𝘮𝘦𝘯𝘵 𝘱𝘭𝘢𝘵𝘧𝘰𝘳𝘮 𝘰𝘧𝘧𝘦𝘳𝘪𝘯𝘨 𝘢 𝘥𝘪𝘷𝘦𝘳𝘴𝘦, 𝘤𝘶𝘳𝘢𝘵𝘦𝘥 𝘭𝘪𝘣𝘳𝘢𝘳𝘺 𝘰𝘧 𝘩𝘪𝘨𝘩-𝘲𝘶𝘢𝘭𝘪𝘵𝘺 𝘤𝘰𝘯𝘵𝘦𝘯𝘵\n\nPlease select an option:"

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
