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
    print("Error: pyzbar is not installed. Run 'pip install pyzbar' and ensure libzbar is installed (e.g., 'apt-get install libzbar0' on Debian-based systems).")
    exit(1)
try:
    import qrcode
except ImportError:
    print("Error: qrcode is not installed. Run 'pip install qrcode' to resolve.")
    exit(1)
try:
    from telegram.ext import Application, CommandHandler, MessageHandler, filters
except ImportError:
    print("Error: python-telegram-bot is not installed. Run 'pip install python-telegram-bot>=21.0' to resolve.")
    exit(1)

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Use environment variable for token (recommended for Zeabur)
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8433651914:AAFbaeXrXP17WURqLpzY9p5lLYQap37VzaM')  # Updated with provided token
OWNER_IDS = {6563471310, 8058901135, 7599661912}
is_on = False
allowed_users = set()
allowed_groups = set()

def parse_emv(data: str) -> dict:
    i = 0
    result = {}
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
            logger.error(f"Invalid length in EMV data: {len_str}")
            break
        value = data[i:i+length]
        i += length
        result[tag] = value
    return result

async def start(update, context):
    user = update.message.from_user
    user_id = user.id
    user_name = user.full_name or user.username or "Usuario"
    user_link = f"tg://user?id={user_id}"
    chat_id = update.message.chat_id
    is_group = update.message.chat.type in ['group', 'supergroup']
    base_welcome = (
        f"👋 ¡Bienvenido/a, [{user_name}]({user_link})! 🎉\n"
        f"🆔 Tu ID de Telegram es: `{user_id}`\n"
        "📷 Envía una imagen de un código QR de Nequi, Bancolombia, Davivienda o Daviplata, "
        "y obtendrás la plataforma, número, nombre, ubicación y DNI asociados. 🚀\n"
        "🔄 Para generar un código QR, usa /qrgen <datos>.\n"
        "Bot creado por [@Teampaz2](https://t.me/Teampaz2) y [@ninja_ofici4l](https://t.me/ninja_ofici4l)"
    )
    if is_group:
        if chat_id in allowed_groups or is_on or user_id in OWNER_IDS:
            welcome_message = base_welcome.replace("¡Bienvenido/a, ", "¡Bienvenido/a al grupo, ")
            await update.message.reply_text(welcome_message, parse_mode='Markdown')
        else:
            await update.message.reply_text(
                '🚫 Este grupo no está autorizado para usar el bot. Contacta a [@Teampaz2](https://t.me/Teampaz2) o [@ninja_ofici4l](https://t.me/ninja_ofici4l) para más información. 📩',
                parse_mode='Markdown'
            )
    else:
        if is_on or user_id in OWNER_IDS or user_id in allowed_users:
            on_message = (
                "\n\n✅ **Sistemas activos para todos de [𝐍𝐄𝐐𝐔𝐈 𝐙𝐗](https://t.me/Nequizx)** 🌐\n"
                "Presiona /qrgen para generar el comprobante."
            )
            welcome_message = base_welcome + on_message
            await update.message.reply_text(welcome_message, parse_mode='Markdown')
        else:
            off_message = (
                "\n\n🔴 **Atención: Sistemas apagados** 🔴\n"
                "Para activar los sistemas y disfrutar de todas las funciones, adquiere tu V.I.P contactando a [@Teampaz2](https://t.me/Teampaz2) o [@ninja_ofici4l](https://t.me/ninja_ofici4l), "
                "o comparte el grupo [𝐍𝐄𝐐𝐔𝐈 𝐙𝐗 🔥😎](https://t.me/Nequizx) con 20 personas que se unan para obtenerlo gratis."
            )
            welcome_message = base_welcome + off_message
            await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def group_added(update, context):
    if update.message.chat.type in ['group', 'supergroup']:
        chat_id = update.message.chat_id
        chat_title = update.message.chat.title or "Grupo"
        allowed_groups.add(chat_id)  # Automatically allow the group
        welcome_message = (
            f"👋 ¡Hola, {chat_title}! 🎉\n"
            f"🆔 ID del grupo: `{chat_id}`\n"
            "📷 He sido agregado a este grupo. Envía un código QR de Nequi, "
            "Bancolombia, Davivienda o Daviplata, y obtendrás la información asociada. 🚀\n"
            "🔄 Para generar un código QR, usa /qrgen <datos>.\n"
            "Bot creado por [@Teampaz2](https://t.me/Teampaz2) y [@ninja_ofici4l](https://t.me/ninja_ofici4l)"
        )
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
        logger.info(f"Bot added to group {chat_id} ({chat_title})")

async def qrbin(update, context):
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    if not (is_on or user_id in OWNER_IDS or user_id in allowed_users or chat_id in allowed_groups):
        await update.message.reply_text(
            '🚫 No estás autorizado para usar este bot. Contacta a [@Teampaz2](https://t.me/Teampaz2) o [@ninja_ofici4l](https://t.me/ninja_ofici4l) para más información. 📩',
            parse_mode='Markdown'
        )
        return
    await update.message.reply_text("📷 Por favor, envía la imagen del código QR como respuesta a este mensaje.")

async def qrgen(update, context):
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    if not (is_on or user_id in OWNER_IDS or user_id in allowed_users or chat_id in allowed_groups):
        await update.message.reply_text(
            '🚫 No estás autorizado para usar este bot. Contacta a [@Teampaz2](https://t.me/Teampaz2) o [@ninja_ofici4l](https://t.me/ninja_ofici4l) para más información. 📩',
            parse_mode='Markdown'
        )
        return
    if context.args:
        data = ' '.join(context.args)
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color='black', back_color='white')
            bio = BytesIO()
            bio.name = 'qr.png'
            img.save(bio, 'PNG')
            bio.seek(0)
            await update.message.reply_photo(photo=bio)
            logger.info(f"QR generated for data: {data} by user {user_id}")
        except Exception as e:
            logger.error(f"Error generating QR: {e}")
            await update.message.reply_text('❌ Error al generar el QR. Intenta de nuevo.')
    else:
        await update.message.reply_text('📝 Uso: /qrgen <datos para el QR>')

async def on_command(update, context):
    if update.message.from_user.id in OWNER_IDS:
        global is_on
        is_on = True
        await update.message.reply_text('✅ Bot activado para todos. 🌐')
        logger.info("Bot turned ON by owner")
    else:
        await update.message.reply_text(
            '🚫 Solo los propietarios pueden usar este comando. Contacta a [@Teampaz2](https://t.me/Teampaz2) o [@ninja_ofici4l](https://t.me/ninja_ofici4l) para más información. 📩',
            parse_mode='Markdown'
        )

async def off_command(update, context):
    if update.message.from_user.id in OWNER_IDS:
        global is_on
        is_on = False
        await update.message.reply_text('⛔ Bot desactivado. 🔒')
        logger.info("Bot turned OFF by owner")
    else:
        await update.message.reply_text(
            '🚫 Solo los propietarios pueden usar este comando. Contacta a [@Teampaz2](https://t.me/Teampaz2) o [@ninja_ofici4l](https://t.me/ninja_ofici4l) para más información. 📩',
            parse_mode='Markdown'
        )

async def agregar(update, context):
    if update.message.from_user.id in OWNER_IDS:
        if context.args:
            try:
                user_id = int(context.args[0])
                allowed_users.add(user_id)
                await update.message.reply_text(f'✅ Usuario {user_id} agregado. 👍')
                logger.info(f"User {user_id} added to allowed_users")
            except ValueError:
                await update.message.reply_text('❌ ID de usuario inválido. 🔢')
        else:
            await update.message.reply_text('📝 Uso: /agregar <user_id>')
    else:
        await update.message.reply_text(
            '🚫 Solo los propietarios pueden usar este comando. Contacta a [@Teampaz2](https://t.me/Teampaz2) o [@ninja_ofici4l](https://t.me/ninja_ofici4l) para más información. 📩',
            parse_mode='Markdown'
        )

async def agregargrupo(update, context):
    if update.message.from_user.id in OWNER_IDS:
        if context.args:
            try:
                group_id = int(context.args[0])
                allowed_groups.add(group_id)
                await update.message.reply_text(
                    f'✅ Grupo {group_id} agregado. 👍\n'
                    'Este grupo ahora puede usar el bot incluso si los sistemas están apagados.'
                )
                logger.info(f"Group {group_id} added to allowed_groups")
            except ValueError:
                await update.message.reply_text('❌ ID de grupo inválido. 🔢')
        else:
            await update.message.reply_text('📝 Uso: /agregargrupo <group_id>')
    else:
        await update.message.reply_text(
            '🚫 Solo los propietarios pueden usar este comando. Contacta a [@Teampaz2](https://t.me/Teampaz2) o [@ninja_ofici4l](https://t.me/ninja_ofici4l) para más información. 📩',
            parse_mode='Markdown'
        )

async def eliminargrupo(update, context):
    if update.message.from_user.id in OWNER_IDS:
        if context.args:
            try:
                group_id = int(context.args[0])
                if group_id in allowed_groups:
                    allowed_groups.remove(group_id)
                    await update.message.reply_text(
                        f'✅ Grupo {group_id} eliminado de los grupos autorizados. 🚫\n'
                        'Este grupo ya no puede usar el bot si los sistemas están apagados.'
                    )
                    logger.info(f"Group {group_id} removed from allowed_groups")
                else:
                    await update.message.reply_text(f'❌ El grupo {group_id} no está en la lista de grupos autorizados. 🔍')
            except ValueError:
                await update.message.reply_text('❌ ID de grupo inválido. 🔢')
        else:
            await update.message.reply_text('📝 Uso: /eliminargrupo <group_id>')
    else:
        await update.message.reply_text(
            '🚫 Solo los propietarios pueden usar este comando. Contacta a [@Teampaz2](https://t.me/Teampaz2) o [@ninja_ofici4l](https://t.me/ninja_ofici4l) para más información. 📩',
            parse_mode='Markdown'
        )

async def handle_photo(update, context):
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    is_authorized = is_on or user_id in OWNER_IDS or user_id in allowed_users or chat_id in allowed_groups
    if not is_authorized:
        await update.message.reply_text(
            '🚫 No estás autorizado para usar este bot. Contacta a [@Teampaz2](https://t.me/Teampaz2) o [@ninja_ofici4l](https://t.me/ninja_ofici4l) para más información. 📩',
            parse_mode='Markdown'
        )
        return
    await update.message.reply_text('📦 Escaneando la imagen...')
    logger.info(f"Processing photo from user {user_id} in chat {chat_id}")
    try:
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        # Ensure compatible image format
        try:
            image = Image.open(BytesIO(photo_bytes))
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")
        except Exception as e:
            logger.error(f"Failed to open image: {e}")
            await update.message.reply_text('❌ No pude abrir la imagen. Intenta con otra foto del QR. 📸')
            return
        decoded_objects = decode(image)
        if not decoded_objects:
            await update.message.reply_text('❌ No se detectó código QR en la imagen. 📸')
            return
        try:
            data = decoded_objects[0].data.decode('utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"Failed to decode QR data: {e}")
            await update.message.reply_text('❌ No pude decodificar el contenido del QR. 📄')
            return
        platform = 'Desconocida'
        number = 'N/A'
        name = 'N/A'
        location = 'Bogotá'  # Default to Bogotá if no location data
        dni = 'N/A'
        lower_data = data.lower()
        # Regex patterns
        phone_regex = r'(?:(?:\+57|57)|0)?3[0-9]{9}\b'
        account_regex = r'\b\d{10,16}\b'
        dni_regex = r'\b\d{7,10}\b'
        if 'nequi' in lower_data:
            platform = 'Nequi'
        elif 'bancolombia' in lower_data:
            platform = 'Bancolombia'
            account_match = re.search(account_regex, data)
            if account_match:
                number = account_match.group(0)
        elif 'davivienda' in lower_data:
            platform = 'Davivienda'
            if 'negocio' in lower_data or 'business' in lower_data:
                number = 'N/A (QR de negocio)'
            else:
                account_match = re.search(account_regex, data)
                if account_match:
                    number = account_match.group(0)
        elif 'daviplata' in lower_data:
            platform = 'Daviplata'
            phone_match = re.search(phone_regex, data)
            if phone_match:
                number = phone_match.group(0)
        # Enhanced EMV parsing
        try:
            emv_data = parse_emv(data)
            if '59' in emv_data:
                name = emv_data['59']
            if '60' in emv_data and emv_data['60']:
                location = emv_data['60']
            if '62' in emv_data:
                sub_data = parse_emv(emv_data['62'])
                if '01' in sub_data and re.match(dni_regex, sub_data['01']):
                    dni = sub_data['01']
                if '02' in sub_data:
                    number = sub_data['02']
                for sub_tag in ['03', '04', '05']:
                    if sub_tag in sub_data and re.match(dni_regex, sub_data[sub_tag]):
                        dni = sub_data[sub_tag]
            for t in range(26, 52):
                ts = f'{t:02d}'
                if ts in emv_data:
                    sub_data = parse_emv(emv_data[ts])
                    if '00' in sub_data:
                        guid = sub_data['00'].lower()
                        if 'nequi' in guid:
                            platform = 'Nequi'
                        elif 'bancolombia' in guid:
                            platform = 'Bancolombia'
                        elif 'davivienda' in guid:
                            platform = 'Davivienda'
                        elif 'daviplata' in guid:
                            platform = 'Daviplata'
                    if '01' in sub_data:
                        number = sub_data['01']
                        if platform in ['Nequi', 'Daviplata'] and not re.match(phone_regex, number):
                            number = 'N/A'
                    for sub_tag in ['02', '03']:
                        if sub_tag in sub_data and platform in ['Nequi', 'Daviplata']:
                            if re.match(phone_regex, sub_data[sub_tag]):
                                number = sub_data[sub_tag]
                    for sub_tag in ['04', '05']:
                        if sub_tag in sub_data and re.match(dni_regex, sub_data[sub_tag]):
                            dni = sub_data[sub_tag]
        except Exception as e:
            logger.error(f"Error parsing EMV data: {e}")
        response = (
            f'🏦 **Plataforma**: {platform}\n'
            f'📱 **Número**: {number}\n'
            f'👤 **Nombre**: {name}\n'
            f'📍 **Ubicación**: {location}\n'
            f'🪪 **DNI**: {dni}'
        )
        await update.message.reply_text(response, parse_mode='Markdown')
        logger.info against(f"QR processed successfully for user {user_id} in chat {chat_id}")
    except Exception as e:
        logger.error(f"Unexpected error in handle_photo: {e}")
        await update.message.reply_text('❌ Error inesperado al procesar la imagen. Intenta de nuevo. 📸')

def main():
    try:
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler('start', start))
        app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, group_added))
        app.add_handler(CommandHandler('qrbin', qrbin))
        app.add_handler(CommandHandler('qrgen', qrgen))
        app.add_handler(CommandHandler('on', on_command))
        app.add_handler(CommandHandler('off', off_command))
        app.add_handler(CommandHandler('agregar', agregar))
        app.add_handler(CommandHandler('agregargrupo', agregargrupo))
        app.add_handler(CommandHandler('eliminargrupo', eliminargrupo))
        app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        logger.info("Starting bot...")
        app.run_polling(allowed_updates=['message', 'chat_member'])
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        print(f"Error: Failed to start bot: {e}")

if __name__ == '__main__':
    main()
