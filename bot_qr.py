import logging
import re
from io import BytesIO
import os

try:
    from PIL import Image
except ImportError:
    print("Error: PIL (Pillow) is not installed. Run 'pip install Pillow' to resolve.")
    exit(1)

try:
    from pyzbar.pyzbar import decode
except ImportError:
    print("Error: pyzbar is not installed. Run 'pip install pyzbar' and install libzbar.")
    exit(1)

try:
    import qrcode
except ImportError:
    print("Error: qrcode is not installed. Run 'pip install qrcode' to resolve.")
    exit(1)

try:
    from telegram.ext import Application, CommandHandler, MessageHandler, filters
except ImportError:
    print("Error: python-telegram-bot is not installed. Run 'pip install python-telegram-bot>=21.0'.")
    exit(1)

# Configuración básica
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8433651914:AAFbaeXrXP17WURqLpzY9p5lLYQap37VzaM')
OWNER_IDS = {6563471310, 8058901135, 7599661912}
is_on = False
allowed_users = set()
allowed_groups = set()

# Lógica EMV (igual que tenías)
def parse_emv(data: str) -> dict:
    i, result = 0, {}
    while i < len(data):
        tag = data[i:i+2]
        i += 2
        if i >= len(data):
            break
        len_str = data[i:i+2]
        i += 2
        if i >= len(data):
            break
        try:
            length = int(len_str)
        except ValueError:
            break
        value = data[i:i+length]
        i += length
        result[tag] = value
    return result

# Handlers / comandos
async def start(update, context):
    user = update.message.from_user
    user_id = user.id
    user_name = user.full_name or user.username or "Usuario"
    chat_id = update.message.chat_id
    is_group = update.message.chat.type in ['group', 'supergroup']
    base_welcome = (
        f"🎉 ¡Hola *{user_name}*! 👋\n"
        f"🆔 Tu ID de Telegram es: `{user_id}`\n"
        "📷 Envía una imagen de un código QR de Nequi / Bancolombia / Davivienda / Daviplata.\n"
        "🔄 O usa /qrgen <datos> para generar un QR."
    )
    if is_group:
        if chat_id in allowed_groups or is_on or user_id in OWNER_IDS:
            await update.message.reply_text(base_welcome.replace("¡Hola", "¡Hola al grupo"), parse_mode='Markdown')
        else:
            await update.message.reply_text(
                '🚫 Grupo no autorizado. Contacta a [@Teampaz2](https://t.me/Teampaz2) o [@ninja_ofici4l](https://t.me/ninja_ofici4l).',
                parse_mode='Markdown'
            )
    else:
        if is_on or user_id in OWNER_IDS or user_id in allowed_users:
            await update.message.reply_text(base_welcome + "\n\n✅ Sistemas activos.", parse_mode='Markdown')
        else:
            await update.message.reply_text(
                base_welcome + "\n\n🔴 Sistemas apagados. Adquiere VIP o comparte [𝐍𝐄𝐐𝐔𝐈 𝐙𝐗](https://t.me/Nequizx).",
                parse_mode='Markdown'
            )

async def qrbin(update, context):
    await update.message.reply_text("📷 Envía la imagen del QR.")

async def qrgen(update, context):
    if not context.args:
        await update.message.reply_text("📝 Uso: /qrgen <datos>")
        return
    data = ' '.join(context.args)
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    bio = BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    await update.message.reply_photo(photo=bio)

async def handle_photo(update, context):
    await update.message.reply_text("📦 Escaneando QR...")
    photo = update.message.photo[-1]
    photo_file = await photo.get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    image = Image.open(BytesIO(photo_bytes))
    decoded = decode(image)
    if not decoded:
        await update.message.reply_text("❌ No detecté QR.")
        return
    data = decoded[0].data.decode('utf-8', errors='ignore')
    await update.message.reply_text(f"✅ Datos leídos:\n```{data}```")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('qrbin', qrbin))
    app.add_handler(CommandHandler('qrgen', qrgen))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    logger.info("Starting bot...")
    app.run_polling(allowed_updates=['message'])

if __name__ == '__main__':
    main()
