import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from to_notion import fetch_book, get_preview, add_to_notion
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("telegram_bot_token")
#for temporary storage
PENDING_BOOK = "pending_book"
PENDING_PREVIEW = "pending_preview"

def _build_preview_message(book: dict, preview: str) -> str:
    title = book.get("title", "Unknown title")
    authors = book.get("authors", "")
    pages = book.get("pages", 0)
    year = book.get("year", "")

    lines = [
        f"📖 *{title}*",
        f"✍️ {authors}" if authors else "",
        f"📄 Pages: {pages}" if pages else "",
        f"📅 Year: {year}" if year else "",
        "",
        "🤖 *AI Preview (no spoilers):*",
        preview.strip()[:3500],
    ]
    return "\n".join([x for x in lines if x])


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    book_name = update.message.text.strip()

    await update.message.reply_text("📚 Searching for the book...")

    book = fetch_book(book_name)
    if not book:
        await update.message.reply_text("❌ Book not found.")
        return

    await update.message.reply_text("🤖 Generating AI preview...")
    try:
        preview_text = get_preview(book["title"], book.get("authors", ""))
    except Exception:
        await update.message.reply_text("❌ AI preview failed. Try again.")
        return

    context.user_data[PENDING_BOOK] = book
    context.user_data[PENDING_PREVIEW] = preview_text

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Add to Notion", callback_data="add_confirm")],
        [InlineKeyboardButton("❌ Cancel", callback_data="add_cancel")],
    ])

    msg = _build_preview_message(book, preview_text)
    await update.message.reply_text(msg, reply_markup=keyboard, parse_mode="Markdown")

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "add_cancel":
        context.user_data.pop(PENDING_BOOK, None)
        context.user_data.pop(PENDING_PREVIEW, None)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("cancelled. Send another book title anytime.")
        return

    if query.data == "add_confirm":
        book = context.user_data.get(PENDING_BOOK)
        preview_text = context.user_data.get(PENDING_PREVIEW)

        if not book or not preview_text:
            await query.message.reply_text("⚠️ Nothing pending. Send a book title first.")
            return

        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("📝 Adding to Notion...")

        try:
            add_to_notion(book, preview_text)
        except Exception as e:
            await query.message.reply_text(f"❌ Failed to add to Notion:\n{e}")
            return
        finally:
            context.user_data.pop(PENDING_BOOK, None)
            context.user_data.pop(PENDING_PREVIEW, None)

        await query.message.reply_text("✅ Added to Notion!")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.run_polling()

if __name__ == "__main__":
    main()
