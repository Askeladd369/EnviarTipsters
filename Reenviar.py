import os
import logging
import pandas as pd
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, InputMediaPhoto

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Configurar parámetros del bot
api_id = "22823293"
api_hash = "c110fb4d3ba8473643b8e33e1c81be1d"
bot_token = "7165468466:AAFPgIY2H89jbdK8kx_VW5KJVAz1xvkzm68" #"7472327662:AAEo_XSXk8s_BrDfhvlc51HBR0epE767h7E"
canal_privado_id =  "-1002471002368"#"-1002431937420" #
canal_privado_id = int(canal_privado_id)
# Lista de administradores autorizados (IDs de usuario)
admins_autorizados = [1142604997, 1209577470, 1762748618]  # Reemplazar con los IDs de los administradores

app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Ruta donde se guardará el archivo Excel
excel_file_path = "C:\\Users\\Administrator\\EnviarTipsters\\excel.xlsx" #"C:\\Users\\saidd\\OneDrive\\Escritorio\\Bot de Telegram pruebas\\Bot Reventas\\excel.xlsx"#
def es_admin(usr_id):
    return usr_id in admins_autorizados

# Función para leer y procesar los datos del archivo Excel
def leer_datos_excel():
    try:
        # Leer las hojas de Tipsters, Grupos y Canales
        df_tipsters = pd.read_excel(excel_file_path, sheet_name='Tipsters')
        df_grupos = pd.read_excel(excel_file_path, sheet_name='Grupos')
        df_canales = pd.read_excel(excel_file_path, sheet_name='Canales')

        # Verificar que el archivo tenga las columnas esperadas en Tipsters
        required_columns = ['Tipster', 'Bank Inicial', 'Bank Actual', 'Victorias', 'Derrotas', 'Efectividad', 'Racha']
        for column in required_columns:
            if column not in df_tipsters.columns:
                raise ValueError(f"La columna '{column}' falta en la hoja 'Tipsters'.")

        # Procesar los tipsters y sus estadísticas
        tipsters_data = {}
        for _, row in df_tipsters.iterrows():
            tipster = row['Tipster']
            tipsters_data[tipster] = {
                'bank_inicial': row['Bank Inicial'],
                'bank_actual': row['Bank Actual'],
                'victorias': row['Victorias'],
                'derrotas': row['Derrotas'],
                'efectividad': row['Efectividad'],
                'racha': row['Racha'],
                'grupos': []  # Inicialmente vacío, se llenará con la información de la hoja 'Grupos'
            }

        # Procesar los grupos (hoja 'Grupos')
        for _, row in df_grupos.iterrows():
            tipster = row['Tipster']
            # Normalizar los nombres de los grupos (convertir a minúsculas y eliminar espacios en blanco)
            grupos = [row[grupo].strip().lower() for grupo in df_grupos.columns[:-1] if pd.notna(row[grupo])]
            if tipster in tipsters_data:
                tipsters_data[tipster]['grupos'] = grupos  # Actualizar los grupos de cada tipster

        # Procesar los canales (hoja 'Canales')
        grupos_canales = {}
        for _, row in df_canales.iterrows():
            grupo = row['Grupo'].strip().lower() if pd.notna(row['Grupo']) else None  # Normalizar los nombres
            canal = str(int(row['Canal'])) if pd.notna(row['Canal']) else None
            marca_agua = row['Marca de Agua'] if pd.notna(row['Marca de Agua']) else None

            # Aquí es importante asegurarnos de que el grupo y su marca de agua se asignen correctamente
            if grupo and canal:
                if grupo not in grupos_canales:
                    grupos_canales[grupo] = {
                        'canal': canal,
                        'marca_agua': marca_agua
                    }
                else:
                    # Si un grupo tiene varias filas, asegurarse de que no se sobreescriban los valores
                    logging.warning(f"El grupo '{grupo}' ya tiene un canal y marca de agua asignado.")
        
        # Retornar los datos procesados
        return tipsters_data, grupos_canales

    except FileNotFoundError as e:
        print(f"Error: No se encontró el archivo Excel. Asegúrate de que el archivo esté en la ruta correcta.")
        raise e
    except Exception as e:
        print(f"Error al leer los datos del archivo Excel: {str(e)}")
        raise e


# Cargar los datos del Excel al iniciar el bot
tipsters_data, grupos_canales = leer_datos_excel()

# Crear los botones paginados
def crear_botones_tipsters(tipsters, page=1, botones_por_pagina=10):
    total_pages = (len(tipsters) + botones_por_pagina - 1) // botones_por_pagina
    start_index = (page - 1) * botones_por_pagina
    end_index = start_index + botones_por_pagina

    botones = [
        [InlineKeyboardButton(tipster, callback_data=f"tipster:{tipster}")]
        for tipster in tipsters[start_index:end_index]
    ]
    
    navigation_buttons = []
    if page > 1:
        navigation_buttons.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"page:{page - 1}"))
    if page < total_pages:
        navigation_buttons.append(InlineKeyboardButton("Siguiente ➡️", callback_data=f"page:{page + 1}"))

    if navigation_buttons:
        botones.append(navigation_buttons)

    return InlineKeyboardMarkup(botones)

# Comando para mostrar el menú de tipsters
@app.on_message(filters.command("menu"))
async def mostrar_menu(client, message: Message):

    if not es_admin(message.from_user.id):
        await message.reply("No tienes permiso para usar este bot.")
        return
    
    try:
        # Verificamos si los datos de tipsters están disponibles
        if not tipsters_data:
            await message.reply("No se encontraron tipsters en los datos cargados.")
            return

        # La lista de tipsters es la clave del diccionario tipsters_data
        tipsters = list(tipsters_data.keys())  # Extraer los nombres de los tipsters desde las claves

        # Mostrar los primeros botones con los nombres de los tipsters
        botones = crear_botones_tipsters(tipsters, page=1)
        await message.reply("Selecciona un tipster:", reply_markup=botones)

    except Exception as e:
        logging.error(f"Error al mostrar el menú: {str(e)}")
        await message.reply(f"Hubo un error al mostrar el menú: {str(e)}")

# Diccionario global para almacenar el tipster seleccionado por cada usuario
sesion_tipsters = {}


# Manejar la selección del tipster desde los botones
@app.on_callback_query(filters.regex(r"^tipster:"))
async def seleccionar_tipster(client, callback_query):
    if not es_admin(callback_query.from_user.id):
        await callback_query.answer("No tienes permiso para usar este bot.", show_alert=True)
        return

    # Extraer el nombre del tipster del callback data
    tipster_seleccionado = callback_query.data.split(":")[1]

    # Guardar el tipster seleccionado en la sesión del usuario
    sesion_tipsters[callback_query.from_user.id] = tipster_seleccionado

    # Confirmar la selección del tipster
    await callback_query.message.edit_text(
        f"Has seleccionado a {tipster_seleccionado}. Ahora puedes enviar las imágenes correspondientes."
    )

# Manejar el cambio de página
@app.on_callback_query(filters.regex(r"^page:"))
async def cambiar_pagina(client, callback_query):

    if not es_admin(callback_query.from_user.id):
        await callback_query.answer("No tienes permiso para usar este bot.", show_alert=True)
        return
    
    page = int(callback_query.data.split(":")[1])

    try:
        # Verificamos si los datos de tipsters están disponibles
        if not tipsters_data:
            await callback_query.message.edit_text("No se encontraron tipsters en los datos cargados.")
            return

        # La lista de tipsters es la clave del diccionario tipsters_data
        tipsters = list(tipsters_data.keys())  # Extraer los nombres de los tipsters desde las claves

        # Crear nuevos botones con la página seleccionada
        botones = crear_botones_tipsters(tipsters, page=page)
        await callback_query.message.edit_reply_markup(reply_markup=botones)

    except Exception as e:
        logging.error(f"Error al cambiar de página: {str(e)}")
        await callback_query.message.edit_text(f"Hubo un error al cambiar de página: {str(e)}")

# Comando para subir un nuevo archivo Excel y actualizar tanto la hoja 'Tipsters' como 'Grupos'
@app.on_message(filters.command("subir_excel") & filters.document)
async def upload_excel(client, message: Message):
    if not es_admin(message.from_user.id):
        await message.reply("No tienes permiso para usar este bot.")
        return
    global tipsters_data, grupos_canales  # Actualizar variables globales
    if message.document.mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        try:
            # Descargar el archivo de manera asíncrona
            file_path = await message.download(file_name=excel_file_path)

            # Cargar las hojas actualizadas
            df_tipsters_actualizado = pd.read_excel(excel_file_path, sheet_name='Tipsters')  # Cargar hoja Tipsters
            df_grupos_actualizado = pd.read_excel(excel_file_path, sheet_name='Grupos')      # Cargar hoja Grupos

            # Actualizar la información de los tipsters (hoja 'Tipsters')
            tipsters_data = {}  # Reinicializamos la data de tipsters
            for _, row in df_tipsters_actualizado.iterrows():
                tipster = row['Tipster']
                tipsters_data[tipster] = {
                    'bank_inicial': row['Bank Inicial'],
                    'bank_actual': row['Bank Actual'],
                    'victorias': row['Victorias'],
                    'derrotas': row['Derrotas'],
                    'efectividad': row['Efectividad'],
                    'racha': row['Racha'],
                    'grupos': []  # Inicialmente vacío, se llenará con la información de la hoja 'Grupos'
                }

            # Procesar los grupos (hoja 'Grupos')
            columnas_grupos = df_grupos_actualizado.columns[:-1]  # Todas las columnas menos la última
            tipster_grupos = df_grupos_actualizado['Tipster']     # Última columna que contiene los tipsters

            # Actualizar los grupos en tipsters_data
            for _, row in df_grupos_actualizado.iterrows():
                tipster = row['Tipster']
                grupos = [row[grupo] for grupo in columnas_grupos if pd.notna(row[grupo])]  # Grupos no vacíos
                if tipster in tipsters_data:
                    tipsters_data[tipster]['grupos'] = grupos  # Actualizar los grupos de cada tipster

            await message.reply("Las hojas 'Tipsters' y 'Grupos' han sido actualizadas correctamente.")
            logging.info(f"Archivo Excel descargado y hojas 'Tipsters' y 'Grupos' actualizadas en: {file_path}")

        except Exception as e:
            await message.reply(f"Hubo un error al subir el archivo Excel: {str(e)}")
            logging.error(f"Error al subir el archivo Excel: {str(e)}")
    else:
        await message.reply("Por favor, sube un archivo Excel válido (.xlsx).")

# Función auxiliar para verificar si un valor es NaN
def is_nan(value):
    return value != value

@app.on_message(filters.photo)
async def manejar_imagen(client, message: Message):
    if not es_admin(message.from_user.id):
        await message.reply("No tienes permiso para enviar imágenes.")
        return

    # Obtener el tipster seleccionado desde la sesión del usuario
    tipster_seleccionado = sesion_tipsters.get(message.from_user.id)
    if not tipster_seleccionado:
        await message.reply("No has seleccionado un tipster. Usa /menu para seleccionar uno.")
        return

    tipster_info = tipsters_data.get(tipster_seleccionado)  # Obtener los datos del tipster seleccionado
    if not tipster_info:
        await message.reply(f"No se encontraron datos para el tipster '{tipster_seleccionado}'.")
        return

    media_paths = []  # Guardar los caminos de las imágenes originales para eliminarlas luego
    watermarked_paths = {}  # Guardar los caminos de las imágenes con marca de agua para cada canal

    try:
        # Obtener los grupos asociados al tipster
        grupos_tipster = [grupo.lower().strip() for grupo in tipster_info['grupos']]  # Normalizar los grupos

        # Generar el mensaje con las estadísticas del tipster
        mensaje = generar_mensaje_con_estadisticas(tipster_seleccionado, tipster_info)

        # Si es un grupo de medios (varias imágenes enviadas juntas), procesarlo una sola vez
        media_group_msgs = []
        if message.media_group_id:
            media_group_msgs = await client.get_media_group(message.chat.id, message.id)
            logging.info(f"Procesando grupo de medios con ID: {message.media_group_id}")
        else:
            media_group_msgs.append(message)

        # Procesar cada imagen enviada
        media_group_privado = []
        media_group_canales = {}

        # El primer mensaje del grupo de medios es el que llevará el caption (nombre del tipster)
        is_first_image = True

        for media_msg in media_group_msgs:
            try:
                # Descargar la imagen original
                imagen_path = await client.download_media(media_msg.photo.file_id)
                media_paths.append(imagen_path)  # Guardar la imagen original para eliminarla más tarde
                logging.info(f"Imagen original descargada: {imagen_path}")

                # Añadir la imagen sin marca de agua para el canal privado
                caption = mensaje if is_first_image else ""
                media_group_privado.append(InputMediaPhoto(imagen_path, caption=caption))
                is_first_image = False  # Solo el primer mensaje tiene el caption

                # Aplicar la marca de agua correspondiente para cada canal y grupo
                for grupo in grupos_tipster:
                    if grupo not in grupos_canales:
                        logging.error(f"No se encontró información de canal y marca de agua para el grupo '{grupo}'.")
                        continue

                    canal_info = grupos_canales[grupo]
                    canal = canal_info['canal']
                    marca_agua = canal_info['marca_agua']

                    logging.info(f"Aplicando marca de agua para el grupo '{grupo}' con la ruta '{marca_agua}' en el canal '{canal}'")

                    # Hacer una copia de la imagen original para cada grupo antes de aplicar la marca de agua
                    imagen_copia_path = imagen_path.replace(".jpg", f"_{grupo}.jpg")
                    os.system(f'copy "{imagen_path}" "{imagen_copia_path}"')  # Crear una copia de la imagen original

                    # Asegúrate de que la copia de la imagen se agregue a media_paths para eliminarla más tarde
                    media_paths.append(imagen_copia_path)

                    imagen_con_marca = agregar_marca_agua(imagen_copia_path, marca_agua)

                    # Guardar la imagen con marca de agua para eliminarla más tarde
                    if canal not in watermarked_paths:
                        watermarked_paths[canal] = []
                    watermarked_paths[canal].append(imagen_con_marca)

                    # Crear el grupo de medios para cada canal
                    if canal not in media_group_canales:
                        media_group_canales[canal] = []

                    # Solo el primer mensaje tendrá el mensaje de estadísticas
                    caption = mensaje if len(media_group_canales[canal]) == 0 else ""
                    media_group_canales[canal].append(
                        InputMediaPhoto(imagen_con_marca, caption=caption)
                    )

            except Exception as e:
                logging.error(f"Error al manejar la imagen: {str(e)}")
                if message.chat.type == "private":
                    await message.reply(f"Error al manejar la imagen: {str(e)}")

        # Enviar todas las imágenes al canal privado
        await enviar_imagen_a_canal_privado(client, message, tipster_seleccionado, media_group_privado)

        # Enviar las imágenes a los canales correspondientes
        for canal, media_group in media_group_canales.items():
            try:
                logging.info(f"Enviando grupo de imágenes al canal: {canal}")
                await client.send_media_group(chat_id=canal, media=media_group)
            except Exception as e:
                logging.error(f"Error al enviar el grupo de imágenes al canal {canal}: {str(e)}")
                if message.chat.type == "private":
                    await message.reply(f"Error al enviar el grupo de imágenes al canal {canal}: {str(e)}")

    except Exception as e:
        logging.error(f"Error al manejar las imágenes: {str(e)}")
        if message.chat.type == "private":
            await message.reply(f"Error al manejar las imágenes: {str(e)}")

    finally:
        # Asegurarse de que las imágenes originales y con marca de agua sean eliminadas después de ser enviadas
        for imagen_path in media_paths:
            if imagen_path and os.path.exists(imagen_path):
                try:
                    os.remove(imagen_path)
                    logging.info(f"Imagen original eliminada: {imagen_path}")
                except Exception as e:
                    logging.error(f"Error al eliminar la imagen original: {imagen_path}, Error: {str(e)}")

        # Eliminar también las imágenes con marca de agua
        for canal, imagenes_con_marca in watermarked_paths.items():
            for imagen_con_marca in imagenes_con_marca:
                if imagen_con_marca and os.path.exists(imagen_con_marca):
                    try:
                        os.remove(imagen_con_marca)
                        logging.info(f"Imagen con marca de agua eliminada: {imagen_con_marca}")
                    except Exception as e:
                        logging.error(f"Error al eliminar la imagen con marca de agua: {imagen_con_marca}, Error: {str(e)}")


# Función para enviar todas las imágenes al canal privado (solo el nombre del tipster como caption)
async def enviar_imagen_a_canal_privado(client, message, tipster, media_group):
    try:
        await client.send_media_group(chat_id=canal_privado_id, media=media_group)
        logging.info(f"Imágenes enviadas al canal privado con el nombre del tipster: {tipster}")
    except Exception as e:
        logging.error(f"Error al enviar las imágenes al canal privado: {str(e)}")
        if message.chat.type == "private":
            await message.reply(f"Error al enviar las imágenes al canal privado: {str(e)}")


# Función para generar el mensaje de estadísticas
def generar_mensaje_con_estadisticas(tipster, datos_tipster):
    mensaje = f"Tipster: {tipster}\nEstadísticas👇\n"
    
    if not is_nan(datos_tipster.get('bank_inicial')):
        mensaje += f"Bank Inicial 🏦: ${int(datos_tipster['bank_inicial']):,}\n"
    if not is_nan(datos_tipster.get('bank_actual')):
        mensaje += f"Bank Actual 🏦: ${int(datos_tipster['bank_actual']):,}\n"
    if not is_nan(datos_tipster.get('victorias')):
        mensaje += f"Victorias: {int(datos_tipster['victorias'])}✅\n"
    if not is_nan(datos_tipster.get('derrotas')):
        mensaje += f"Derrotas: {int(datos_tipster['derrotas'])}❌\n"
    if not is_nan(datos_tipster.get('efectividad')):
        mensaje += f"Efectividad: {int(datos_tipster['efectividad'])}% 📊\n"
    if not is_nan(datos_tipster.get('racha')):
        mensaje += f"Racha: {int(datos_tipster['racha'])} días\n"
    
    return mensaje.strip()

# Función para agregar la marca de agua a la imagen
def agregar_marca_agua(imagen_path, marca_agua_path):
    from PIL import Image

    base_image = Image.open(imagen_path).convert("RGBA")
    watermark = Image.open(marca_agua_path).convert("RGBA")

    # Calcular la escala y posicionar la marca de agua
    width_ratio = base_image.width / watermark.width
    height_ratio = base_image.height / watermark.height
    scale = min(width_ratio, height_ratio)

    new_size = (int(watermark.width * scale), int(watermark.height * scale))
    watermark = watermark.resize(new_size, Image.LANCZOS)

    position = ((base_image.width - watermark.width) // 2, (base_image.height - watermark.height) // 2)
    transparent = Image.new('RGBA', base_image.size, (0, 0, 0, 0))
    transparent.paste(base_image, (0, 0))  # Pegar la imagen base
    transparent.paste(watermark, position, mask=watermark)  # Pegar la marca de agua

    # Guardar la imagen con marca de agua
    output_path = imagen_path.replace(".jpg", "_watermarked.jpg")
    transparent.convert("RGB").save(output_path)

    return output_path

# Función auxiliar para verificar si un valor es NaN
def is_nan(value):
    return value != value

# Iniciar el bot
app.run()

