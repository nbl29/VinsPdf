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

# Menyimpan data pengguna dan status aktif
user_data = {}  # Menyimpan data berdasarkan user_id
active_users = set()  # Menggunakan set untuk menyimpan ID pengguna yang sedang aktif

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Halo! Untuk mulai, ketik /vins dan kirim gambar yang ingin Anda konversi ke PDF. Kirim /cancel untuk membatalkan."
    )

async def vins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_users:
        await update.message.reply_text("Anda sudah dalam proses. Kirim lebih banyak gambar atau gunakan /cancel.")
        return

    active_users.add(user_id)
    user_data[user_id] = {"photos": []}  # Simpan data berdasarkan user_id
    await update.message.reply_text(
        "Silakan kirimkan gambar yang ingin Anda konversi ke PDF. Kirim /done jika sudah selesai."
    )

    return WAITING_FOR_PHOTOS

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in active_users:
        await update.message.reply_text("Ketik /vins untuk memulai proses konversi PDF.")
        return

    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()

    user_data[user_id]["photos"].append(photo_bytes)
    await update.message.reply_text(f"Gambar diterima. Kirim lebih banyak atau gunakan /done untuk menyelesaikan.")

    return WAITING_FOR_PHOTOS

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in active_users:
        await update.message.reply_text("Ketik /vins untuk memulai proses konversi PDF.")
        return

    if user_id not in user_data or not user_data[user_id]["photos"]:
        await update.message.reply_text("Belum ada gambar yang diterima. Silakan kirim gambar terlebih dahulu.")
        return WAITING_FOR_PHOTOS

    # Minta nama file
    await update.message.reply_text("Masukkan nama file output PDF (tanpa ekstensi):")
    return WAITING_FOR_NAME

async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in active_users:
        await update.message.reply_text("Ketik /vins untuk memulai proses konversi PDF.")
        return

    file_name = update.message.text.strip()
    if not file_name:
        await update.message.reply_text("Nama file tidak valid. Masukkan nama file yang benar:")
        return WAITING_FOR_NAME
    
    photos_bytes = user_data[user_id]["photos"]

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
    
    # Bersihkan data pengguna
    del user_data[user_id]
    active_users.remove(user_id)  # Hapus pengguna dari daftar aktif

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
