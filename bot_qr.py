import logging
import re
import json
import os
import asyncio
from io import BytesIO

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
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    from telegram import Update
except ImportError:
    print("Error: python-telegram-bot is not installed. Run 'pip install python-telegram-bot>=21.0'.")
    exit(1)

# ------------------------------------------------------------------
# CONFIG
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8433651914:AAFbaeXrXP17WURqLpzY9p5lLYQap37VzaM')
OWNER_IDS = [7994105703, 8058901135, 7599661912]

is_on = False
allowed_users = set()
allowed_groups = set()
pending_qr = {}

# ------------------------------------------------------------------
# JSON HELPERS
def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return default or set()

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(list(data), f, indent=2)

USERS_FILE  = "allowed_users.json"
GROUPS_FILE = "allowed_groups.json"
ADMINS_FILE = "admins.json"

USERS  = load_json(USERS_FILE)
GROUPS = load_json(GROUPS_FILE)
ADMINS = load_json(ADMINS_FILE, default=set(OWNER_IDS))

# ------------------------------------------------------------------
# UTILS
def parse_emv(data: str) -> dict:
    i, result = 0, {}
    while i < len(data):
        tag = data[i:i+2]
        i += 2
        len_str = data[i:i+2]
        i += 2
        try:
            length = int(len_str)
        except ValueError:
            break
        value = data[i:i+length]
        i += length
        result[tag] = value
    return result

# ------------------------------------------------------------------
# HANDLERS
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 ¡Hola *{user.full_name or user.username or 'Amig@'}*!\n"
        f"📷 Envía una imagen de QR y obtén la info completa.",
        parse_mode="Markdown"
    )

# ------------------------------------------------------------------
# COMANDOS ADMIN
async def help_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    await update.message.reply_text(
        "🛠 *Comandos admin*\n\n"
        "• /on  → activar bot\n"
        "• /off → desactivar bot\n"
        "• /agregar <id> → autorizar usuario\n"
        "• /eliminar <id> → quitar usuario\n"
        "• /verusuarios → listar usuarios\n"
        "• /agregargrupo <id> → autorizar grupo\n"
        "• /eliminargrupo <id> → quitar grupo\n"
        "• /vergrupos → listar grupos\n"
        "• /help → este menú",
        parse_mode="Markdown"
    )

async def on_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    global is_on
    is_on = True
    await update.message.reply_text("✅ Bot activado globalmente.")

async def off_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    global is_on
    is_on = False
    await update.message.reply_text("⛔ Bot desactivado globalmente.")

# Usuarios
async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    if not context.args:
        await update.message.reply_text("Uso: /agregar <user_id>")
        return
    try:
        uid = int(context.args[0])
        USERS.add(uid)
        save_json(USERS_FILE, USERS)
        await update.message.reply_text(f"✅ Usuario {uid} agregado.")
    except ValueError:
        await update.message.reply_text("❌ ID inválido.")

async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    if not context.args:
        await update.message.reply_text("Uso: /eliminar <user_id>")
        return
    try:
        uid = int(context.args[0])
        USERS.discard(uid)
        save_json(USERS_FILE, USERS)
        await update.message.reply_text(f"🗑️ Usuario {uid} eliminado.")
    except ValueError:
        await update.message.reply_text("❌ ID inválido.")

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    txt = "\n".join(map(str, sorted(USERS))) if USERS else "Sin usuarios."
    await update.message.reply_text(f"👥 Usuarios:\n{txt}")

# Grupos
async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    if not context.args:
        await update.message.reply_text("Uso: /agregargrupo <group_id>")
        return
    try:
        gid = int(context.args[0])
        GROUPS.add(gid)
        save_json(GROUPS_FILE, GROUPS)
        await update.message.reply_text(f"✅ Grupo {gid} agregado.")
    except ValueError:
        await update.message.reply_text("❌ ID inválido.")

async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    if not context.args:
        await update.message.reply_text("Uso: /eliminargrupo <group_id>")
        return
    try:
        gid = int(context.args[0])
        GROUPS.discard(gid)
        save_json(GROUPS_FILE, GROUPS)
        await update.message.reply_text(f"🗑️ Grupo {gid} eliminado.")
    except ValueError:
        await update.message.reply_text("❌ ID inválido.")

async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    txt = "\n".join(map(str, sorted(GROUPS))) if GROUPS else "Sin grupos."
    await update.message.reply_text(f"🗂 Grupos:\n{txt}")

# ------------------------------------------------------------------
# QR PROCESSOR
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat = update.effective_chat
    chat_type = chat.type

    is_authorized = (
        user_id in ADMINS or
        user_id in USERS or
        chat.id in GROUPS
    )

    if not is_on and not is_authorized:
        await update.message.reply_text(
            '🚫 El bot está apagado. Contacta a @sangre_binerojs, @Teampaz2 o @ninja_ofici4l.',
            parse_mode='Markdown'
        )
        return

    if chat_type == "private" and is_on and not is_authorized:
        # Guardar foto para después
        photo = update.message.photo[-1]
        pending_qr[user_id] = photo
        await update.message.reply_text(
            "📬 Para recibir la información, **comparte el grupo [𝐍𝐄𝐐𝐔𝐈 𝐙𝐗](https://t.me/Nequizx)** con al menos 1 persona.\n"
            "🧑‍💻 Contacto: @sangre_binerojs | @Teampaz2 | @ninja_ofici4l",
            parse_mode='Markdown'
        )
        return

    await process_qr(update, context)

# ------------------------------------------------------------------
# PROCESAR QR
async def process_qr(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id=None):
    if user_id is None:
        user_id = update.effective_user.id

    try:
        if update.message and update.message.photo:
            photo = update.message.photo[-1]
        elif user_id in pending_qr:
            photo = pending_qr.pop(user_id)
        else:
            return

        photo_file = await photo.get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        image = Image.open(BytesIO(photo_bytes))
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        decoded = decode(image)
        if not decoded:
            await context.bot.send_message(chat_id=user_id, text='❌ No se detectó código QR.')
            return

        data = decoded[0].data.decode('utf-8', errors='ignore')

        platform = 'Desconocida'
        number   = 'N/A'
        name     = 'N/A'
        location = 'Bogotá'
        dni      = 'N/A'

        phone_regex  = r'(?:(?:\+57|57)|0)?3[0-9]{9}\b'
        account_regex = r'\b\d{10,16}\b'

        lower_data = data.lower()
        if 'nequi' in lower_data:
            platform = 'Nequi'
        elif 'bancolombia' in lower_data:
            platform = 'Bancolombia'
        elif 'davivienda' in lower_data:
            platform = 'Davivienda'
        elif 'daviplata' in lower_data:
            platform = 'Daviplata'

        emv = parse_emv(data)
        if '59' in emv:
            name = emv['59']
        if '60' in emv and emv['60']:
            location = emv['60']
        if '62' in emv:
            sub = parse_emv(emv['62'])
            dni = sub.get('01', dni)
            number = sub.get('02', number)

        if platform in ['Bancolombia', 'Davivienda']:
            m = re.search(account_regex, data)
            if m:
                number = m.group(0)
        if platform in ['Nequi', 'Daviplata']:
            m = re.search(phone_regex, data)
            if m:
                number = m.group(0)

        reply = (
            f"🏦 **Plataforma**: {platform}\n"
            f"📱 **Número**: {number}\n"
            f"👤 **Nombre**: {name}\n"
            f"📍 **Ubicación**: {location}\n"
            f"🪪 **DNI**: {dni}"
        )
        await context.bot.send_message(chat_id=user_id, text=reply, parse_mode='Markdown')

    except Exception as e:
        logger.error(e)
        await context.bot.send_message(chat_id=user_id, text='❌ Error procesando imagen.')

# ------------------------------------------------------------------
# DETECTAR MENSAJES EN GRUPO NEQUIZX
async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if chat.username and chat.username.lower() == "nequizx":
        if user.id not in USERS and user.id not in ADMINS:
            USERS.add(user.id)
            save_json(USERS_FILE, USERS)
            await asyncio.sleep(2)  # Pequeña pausa para simular "verificación"
            if user.id in pending_qr:
                await process_qr(update, context, user_id=user.id)

# ------------------------------------------------------------------
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_admin))
    app.add_handler(CommandHandler('ayuda', help_admin))
    app.add_handler(CommandHandler('on', on_cmd))
    app.add_handler(CommandHandler('off', off_cmd))
    app.add_handler(CommandHandler('agregar', add_user))
    app.add_handler(CommandHandler('eliminarusuario', remove_user))
    app.add_handler(CommandHandler('verusuario', list_users))
    app.add_handler(CommandHandler('agregargrupo', add_group))
    app.add_handler(CommandHandler('eliminargrupo', remove_group))
    app.add_handler(CommandHandler('vergrupos', list_groups))
    app.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & filters.Chat(username='@Nequizx'), handle_group_message))
    logger.info("Bot iniciado")
    app.run_polling(allowed_updates=['message'])

if __name__ == '__main__':
    main()
