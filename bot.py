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
WAITING_FOR_NAME = 1

# Menyimpan sementara file gambar dan chat_id pengguna
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Halo! Kirimkan gambar yang ingin Anda konversi ke PDF."
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    # Simpan foto di user_data sementara
    user_data[update.effective_chat.id] = {
        "photo": photo_bytes
    }
    
    await update.message.reply_text("Masukkan nama file output PDF (tanpa ekstensi):")
    return WAITING_FOR_NAME

async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_name = update.message.text.strip()
    if not file_name:
        await update.message.reply_text("Nama file tidak valid. Masukkan nama file yang benar:")
        return WAITING_FOR_NAME
    
    # Ambil foto yang disimpan sebelumnya
    data = user_data.get(update.effective_chat.id)
    if not data:
        await update.message.reply_text("Terjadi kesalahan. Silakan kirim gambar lagi.")
        return ConversationHandler.END
    
    photo_bytes = data["photo"]
    
    # Konversi gambar ke PDF
    image = Image.open(io.BytesIO(photo_bytes)).convert("RGB")
    pdf_stream = io.BytesIO()
    image.save(pdf_stream, format="PDF")
    pdf_stream.seek(0)
    
    # Kirim file PDF ke pengguna
    await update.message.reply_document(
        document=InputFile(pdf_stream, filename=f"{file_name}.pdf"),
        caption="Berikut PDF yang telah dibuat!"
    )
    
    # Bersihkan data sementara
    user_data.pop(update.effective_chat.id, None)
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Dibatalkan.")
    return ConversationHandler.END

def main():
    # Ganti dengan token bot Anda
    BOT_TOKEN = "7676918385:AAEnyECKBbQ9fnJk6h1TvWsGm6yiaj7h8As"
    
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # ConversationHandler untuk menangani percakapan
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.PHOTO, handle_photo)],
        states={
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
