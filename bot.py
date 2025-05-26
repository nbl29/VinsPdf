import os
import io
import asyncio
from PIL import Image
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)

# Tahapan percakapan
WAITING_FOR_PHOTOS = 1
WAITING_FOR_NAME = 2

# Menyimpan data pengguna dan status aktif
user_data = {}
active_users = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Halo! Untuk mulai, ketik /vins dan kirim gambar yang ingin Anda konversi ke PDF. "
        "Ketik /cancel untuk membatalkan."
    )

async def vins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_users:
        await update.message.reply_text(
            "Anda sudah dalam proses. Kirim lebih banyak gambar atau gunakan /cancel."
        )
        return

    active_users.add(user_id)
    user_data[user_id] = {"photos": [], "message_ids": []}

    message = await update.message.reply_text(
        "Silakan kirimkan gambar yang ingin Anda konversi ke PDF. "
        "Ketik /done jika sudah selesai."
    )
    user_data[user_id]["message_ids"].append(message.message_id)
    return WAITING_FOR_PHOTOS

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in active_users:
        await update.message.reply_text("Ketik /vins untuk memulai proses konversi PDF.")
        return

    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    user_data[user_id]["photos"].append(photo_bytes)

    # Catat pesan pengguna (gambar)
    user_data[user_id]["message_ids"].append(update.message.message_id)

    reply = await update.message.reply_text(
        "Gambar diterima. Kirim lebih banyak atau ketik /done untuk menyelesaikan."
    )
    user_data[user_id]["message_ids"].append(reply.message_id)
    return WAITING_FOR_PHOTOS

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in active_users:
        await update.message.reply_text("Ketik /vins untuk memulai proses konversi PDF.")
        return

    if not user_data[user_id]["photos"]:
        await update.message.reply_text("Belum ada gambar yang diterima. Silakan kirim gambar terlebih dahulu.")
        return WAITING_FOR_PHOTOS

    reply = await update.message.reply_text("Masukkan nama file output PDF (tanpa ekstensi):")
    user_data[user_id]["message_ids"].append(reply.message_id)
    user_data[user_id]["message_ids"].append(update.message.message_id)  # pesan /done
    return WAITING_FOR_NAME

async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in active_users:
        await update.message.reply_text("Ketik /vins untuk memulai proses konversi PDF.")
        return

    file_name = update.message.text.strip()
    if not file_name:
        reply = await update.message.reply_text("Nama file tidak valid. Masukkan nama file yang benar:")
        user_data[user_id]["message_ids"].append(reply.message_id)
        user_data[user_id]["message_ids"].append(update.message.message_id)
        return WAITING_FOR_NAME

    # Catat pesan nama file dari pengguna
    user_data[user_id]["message_ids"].append(update.message.message_id)

    # Hapus semua pesan pengguna & bot sebelumnya
    for message_id in user_data[user_id]["message_ids"]:
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message_id)
        except Exception as e:
            print(f"Error deleting message {message_id}: {e}")

    # Kirim pesan sementara "PDF sedang diproses..."
    process_message = await update.message.reply_text("PDF sedang diproses...")

    # Konversi gambar-gambar ke PDF
    images = [
        Image.open(io.BytesIO(photo_bytes)).convert("RGB")
        for photo_bytes in user_data[user_id]["photos"]
    ]

    pdf_stream = io.BytesIO()
    images[0].save(pdf_stream, save_all=True, append_images=images[1:], format="PDF")
    pdf_stream.seek(0)

    await asyncio.sleep(2)  # delay jika ingin lebih dramatis

    # Hapus pesan "PDF sedang diproses..."
    try:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=process_message.message_id)
    except Exception as e:
        print(f"Error deleting process message: {e}")

    # Kirim file PDF ke pengguna
    await update.message.reply_document(
        document=InputFile(pdf_stream, filename=f"{file_name}.pdf"),
        caption="Berikut PDF yang telah dibuat!"
    )

    # Bersihkan data pengguna
    del user_data[user_id]
    active_users.remove(user_id)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_users:
        active_users.remove(user_id)
    if user_id in user_data:
        del user_data[user_id]
    await update.message.reply_text("Dibatalkan.")
    return ConversationHandler.END

def main():
    BOT_TOKEN = "7676918385:AAEnyECKBbQ9fnJk6h1TvWsGm6yiaj7h8As"  # Ganti dengan token bot Anda
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("vins", vins)],
        states={
            WAITING_FOR_PHOTOS: [
                MessageHandler(filters.PHOTO, handle_photo),
                CommandHandler("done", done)
            ],
            WAITING_FOR_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)

    print("Bot sedang berjalan...")
    application.run_polling()

if __name__ == "__main__":
    main()
