import os
import io
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

# Menyimpan sementara file gambar dan chat_id pengguna
user_data = {}
active_users = {}  # Menyimpan siapa yang sedang aktif di bot

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Halo! Untuk mulai, ketik /vins dan kirim gambar yang ingin Anda konversi ke PDF. Kirim /cancel untuk membatalkan."
    )

async def vins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Cek apakah ada pengguna yang sedang berinteraksi
    if user_id in active_users:
        await update.message.reply_text("Anda sudah dalam proses. Kirim lebih banyak gambar atau gunakan /cancel.")
        return

    active_users[user_id] = chat_id
    await update.message.reply_text(
        "Silakan kirimkan gambar yang ingin Anda konversi ke PDF. Kirim /done jika sudah selesai."
    )

    return WAITING_FOR_PHOTOS

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Cek apakah pengguna sedang dalam percakapan
    if user_id not in active_users or active_users[user_id] != chat_id:
        await update.message.reply_text("Ketik /vins untuk memulai proses konversi PDF.")
        return

    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()

    # Simpan foto di user_data sementara
    if chat_id not in user_data:
        user_data[chat_id] = {
            "photos": []
        }
    
    user_data[chat_id]["photos"].append(photo_bytes)
    
    await update.message.reply_text(f"Gambar diterima. Kirim lebih banyak atau gunakan /done untuk menyelesaikan.")

    return WAITING_FOR_PHOTOS

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Cek jika pengguna dalam percakapan
    if user_id not in active_users or active_users[user_id] != chat_id:
        await update.message.reply_text("Ketik /vins untuk memulai proses konversi PDF.")
        return

    if chat_id not in user_data or not user_data[chat_id]["photos"]:
        await update.message.reply_text("Belum ada gambar yang diterima. Silakan kirim gambar terlebih dahulu.")
        return WAITING_FOR_PHOTOS

    # Minta nama file
    await update.message.reply_text("Masukkan nama file output PDF (tanpa ekstensi):")
    return WAITING_FOR_NAME

async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Cek jika pengguna dalam percakapan
    if user_id not in active_users or active_users[user_id] != chat_id:
        await update.message.reply_text("Ketik /vins untuk memulai proses konversi PDF.")
        return

    file_name = update.message.text.strip()
    if not file_name:
        await update.message.reply_text("Nama file tidak valid. Masukkan nama file yang benar:")
        return WAITING_FOR_NAME
    
    data = user_data.get(chat_id)
    if not data or not data["photos"]:
        await update.message.reply_text("Terjadi kesalahan. Silakan kirim gambar lagi.")
        return ConversationHandler.END

    photos_bytes = data["photos"]

    # Konversi gambar-gambar ke PDF
    images = []
    for photo_bytes in photos_bytes:
        image = Image.open(io.BytesIO(photo_bytes)).convert("RGB")
        images.append(image)

    pdf_stream = io.BytesIO()
    images[0].save(pdf_stream, save_all=True, append_images=images[1:], format="PDF")
    pdf_stream.seek(0)

    # Kirim file PDF ke pengguna
    await update.message.reply_document(
        document=InputFile(pdf_stream, filename=f"{file_name}.pdf"),
        caption="Berikut PDF yang telah dibuat!"
    )
    
    # Bersihkan data sementara
    del user_data[chat_id]
    del active_users[user_id]  # Hapus pengguna dari daftar aktif

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    if user_id in active_users:
        del active_users[user_id]

    if chat_id in user_data:
        del user_data[chat_id]

    await update.message.reply_text("Dibatalkan.")
    return ConversationHandler.END

def main():
    # Ganti dengan token bot Anda
    BOT_TOKEN = "7676918385:AAEnyECKBbQ9fnJk6h1TvWsGm6yiaj7h8As"  # Ganti dengan token bot Anda
    
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # ConversationHandler untuk menangani percakapan
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("vins", vins)],
        states={
            WAITING_FOR_PHOTOS: [MessageHandler(filters.PHOTO, handle_photo), CommandHandler("done", done)],
            WAITING_FOR_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    
    print("Bot sedang berjalan...")
    application.run_polling()

if __name__ == "__main__":
    main()
