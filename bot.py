import os
import logging
from pathlib import Path
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import img2pdf

# Logging
logging.basicConfig(level=logging.INFO)

# Folder sementara
TMP_DIR = "tmp"
Path(TMP_DIR).mkdir(exist_ok=True)

# Dictionary user -> list file image
user_photos = {}

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Selamat datang! Kirim beberapa gambar, lalu kirim /done untuk mendapatkan file PDF.\n"
        "Gunakan /reset untuk menghapus gambar sebelumnya."
    )

# /reset
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_photos:
        for path in user_photos[user_id]:
            if os.path.exists(path):
                os.remove(path)
        user_photos[user_id] = []
    await update.message.reply_text("Semua gambar telah dihapus. Silakan kirim ulang.")

# Menerima gambar
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_photos:
        user_photos[user_id] = []

    photo = update.message.photo[-1]  # Resolusi tertinggi
    file = await photo.get_file()
    index = len(user_photos[user_id])
    filename = str(Path(TMP_DIR) / f"{user_id}_{index}.jpg")
    filename = os.path.abspath(filename)

    await file.download_to_drive(custom_path=filename)

    # Validasi penyimpanan
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        user_photos[user_id].append(filename)
        await update.message.reply_text(f"Gambar {index + 1} diterima.")
        print(f"[DEBUG] Disimpan: {filename}")
    else:
        await update.message.reply_text("⚠️ Gagal menyimpan gambar.")

# /done: konversi ke PDF dan kirim ke user
async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photos = user_photos.get(user_id, [])

    if not photos:
        await update.message.reply_text("Belum ada gambar yang dikirim.")
        return

    valid_photos = []
    for path in photos:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            valid_photos.append(path)

    if not valid_photos:
        await update.message.reply_text("Semua file gagal dikonversi.")
        return

    output_pdf = str(Path(TMP_DIR) / f"{user_id}_output.pdf")

    try:
        with open(output_pdf, "wb") as f:
            f.write(img2pdf.convert(valid_photos))

        await update.message.reply_document(
            InputFile(output_pdf),
            caption="✅ Berikut hasil konversi PDF-mu!"
        )
    except Exception as e:
        await update.message.reply_text(f"Gagal membuat PDF: {e}")
        print(f"[ERROR] {e}")
    finally:
        # Menghapus file gambar yang valid
        for path in valid_photos:
            if os.path.exists(path):
                os.remove(path)
        # Menghapus pdf output
        if os.path.exists(output_pdf):
            os.remove(output_pdf)
        user_photos[user_id] = []

# Main
if __name__ == "__main__":
    TOKEN = "7676918385:AAHreNwpLsnekkPd7QLe8buTflXrbHE0yzk"  # Ganti token sesuai bot kamu
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot aktif...")
    app.run_polling()