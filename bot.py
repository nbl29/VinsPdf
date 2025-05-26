import os
import io
from PIL import Image
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio

# Mengambil Token Telegram Bot dari variabel lingkungan
TOKEN = '7676918385:AAHreNwpLsnekkPd7QLe8buTflXrbHE0yzk'  # Pastikan untuk mengatur ini secara aman

# Direktori untuk menyimpan gambar sementara
IMAGES_FOLDER = 'images'
os.makedirs(IMAGES_FOLDER, exist_ok=True)

# List untuk menyimpan gambar
images_list = []

# Fungsi untuk menangani perintah /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Kirim gambar yang ingin Anda konversi menjadi PDF.')

# Fungsi untuk menangani gambar yang dikirim
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]  # Ambil foto dengan kualitas tertinggi
    file = photo.get_file()
    file_path = os.path.join(IMAGES_FOLDER, f'{photo.file_id}.jpg')
    
    await file.download(file_path)  # Simpan gambar ke direktori sementara
    images_list.append(file_path)  # Tambahkan gambar ke daftar
    await update.message.reply_text('Gambar diterima! Kirim gambar lain atau ketik /done untuk selesai.')

# Fungsi untuk menangani perintah /done
async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not images_list:
        await update.message.reply_text('Belum ada gambar yang diunggah. Kirim gambar terlebih dahulu.')
        return

    await update.message.reply_text('Masukkan nama file PDF (tanpa ekstensi):')
    return 'GET_PDF_NAME'  # Menandakan bahwa bot menunggu nama file PDF

# Fungsi untuk menangani nama file PDF
async def get_pdf_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pdf_name = update.message.text.strip()
    if not pdf_name:
        await update.message.reply_text('Nama file tidak boleh kosong. Masukkan nama file PDF (tanpa ekstensi):')
        return

    pdf_file_path = os.path.join(IMAGES_FOLDER, f'{pdf_name}.pdf')
    
    # Mengonversi gambar ke dalam PDF
    images = [Image.open(img_path) for img_path in images_list]
    for i in range(len(images)):
        images[i] = images[i].convert('RGB')

    images[0].save(pdf_file_path, save_all=True, append_images=images[1:])

    # Mengirim file PDF ke pengguna
    with open(pdf_file_path, 'rb') as pdf_file:
        await update.message.reply_document(document=InputFile(pdf_file), filename=f'{pdf_name}.pdf')

    # Hapus gambar sementara setelah konversi
    for img in images_list:
        os.remove(img)
    images_list.clear()  # Kosongkan daftar gambar

    await update.message.reply_text('PDF telah dibuat! Kirim lebih banyak gambar atau ketik /start untuk memulai kembali.')

# Fungsi utama untuk menjalankan bot
async def main():
    application = ApplicationBuilder().token(TOKEN).build()  # Ganti Updater dengan ApplicationBuilder
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))  # Menggunakan filters
    application.add_handler(CommandHandler("done", done))

    # Handler untuk menangani input nama file PDF
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_pdf_name))  # Menggunakan filters

    await application.run_polling()  # Menggunakan run_polling untuk menjalankan bot

if __name__ == '__main__':
    loop = asyncio.get_event_loop()  # Ambil loop yang sudah ada
    loop.run_until_complete(main())  # Menjalankan main
