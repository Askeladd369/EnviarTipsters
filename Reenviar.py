import os
import logging
import pandas as pd
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Configurar parámetros del bot
api_id = "22823293"
api_hash = "c110fb4d3ba8473643b8e33e1c81be1d"
bot_token = "7165468466:AAFPgIY2H89jbdK8kx_VW5KJVAz1xvkzm68"
canal_privado_id = "-1002431937420"  # ID del canal privado donde se envían las imágenes originales
canal_privado_id = int(canal_privado_id)

app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Ruta donde se guardará el archivo Excel
excel_file_path = "C:\\Users\\Administrator\\EnviarTIpsters\\excel.xlsx"

# Función para leer los datos desde las tres hojas del archivo Excel
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
        columnas_grupos = df_grupos.columns[:-1]  # Todas las columnas menos la última (que es Tipster)
        for _, row in df_grupos.iterrows():
            tipster = row['Tipster']
            grupos = [row[grupo] for grupo in columnas_grupos if pd.notna(row[grupo])]  # Grupos no vacíos
            if tipster in tipsters_data:
                tipsters_data[tipster]['grupos'] = grupos  # Actualizar los grupos de cada tipster

        # Procesar los canales (hoja 'Canales')
        grupos_canales = {}
        for _, row in df_canales.iterrows():
            grupo = row['Grupo']
            canal = str(int(row['Canal'])) if pd.notna(row['Canal']) else None
            marca_agua = row['Marca de Agua'] if pd.notna(row['Marca de Agua']) else None

            if grupo and canal:
                if grupo not in grupos_canales:
                    grupos_canales[grupo] = []
                grupos_canales[grupo].append({
                    'canal': canal,
                    'marca_agua': marca_agua
                })

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

# Manejar la selección del tipster
@app.on_callback_query(filters.regex(r"^tipster:"))
async def seleccionar_tipster(client, callback_query):
    global tipster_seleccionado
    tipster_seleccionado = callback_query.data.split(":")[1]

    # Confirmar la selección del tipster
    await callback_query.message.edit_text(
        f"Has seleccionado a {tipster_seleccionado}. Ahora puedes enviar las imágenes correspondientes."
    )

# Manejar el cambio de página
@app.on_callback_query(filters.regex(r"^page:"))
async def cambiar_pagina(client, callback_query):
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

# Manejar el envío de imágenes
@app.on_message(filters.photo)
async def manejar_imagen(client, message: Message):
    global tipster_seleccionado

    if tipster_seleccionado is None:
        if message.chat.type == "private":
            await message.reply("Por favor, selecciona primero un tipster usando el menú de botones.")
        return

    try:
        # Buscar el tipster seleccionado en la lista de datos cargados
        tipster_info = tipsters_data.get(tipster_seleccionado)

        if tipster_info is None:
            if message.chat.type == "private":
                await message.reply(f"No se encontró el tipster '{tipster_seleccionado}' en el Excel.")
            return

        # Obtener los grupos asociados al tipster
        grupos = tipster_info.get('grupos', [])

        if not grupos:
            logging.error(f"No se encontraron grupos para el tipster '{tipster_seleccionado}'.")
            if message.chat.type == "private":
                await message.reply(f"No se encontraron grupos para el tipster '{tipster_seleccionado}'.")
            return

        # Generar el mensaje con las estadísticas del tipster
        mensaje = generar_mensaje_con_estadisticas(tipster_seleccionado, tipster_info)

        # Descargar la imagen original
        imagen_path = await client.download_media(message.photo.file_id)
        logging.info(f"Imagen original descargada: {imagen_path}")

        # Enviar la imagen original al canal privado con el nombre del tipster
        await enviar_imagen_a_canal_privado(client, message, tipster_seleccionado, imagen_path)

        # Procesar los grupos y canales
        for grupo in grupos:
            canal_info = grupos_canales.get(grupo, [])

            if not canal_info:
                logging.error(f"No se encontraron canales para el grupo '{grupo}'.")
                if message.chat.type == "private":
                    await message.reply(f"No se encontraron canales para el grupo '{grupo}'.")
                continue

            for canal in canal_info:
                try:
                    marca_agua = canal['marca_agua']
                    imagen_con_marca = agregar_marca_agua(imagen_path, marca_agua)
                    
                    logging.info(f"Enviando imagen al canal: {canal['canal']}")
                    await client.send_photo(chat_id=canal['canal'], photo=imagen_con_marca, caption=mensaje)
                
                except Exception as e:
                    logging.error(f"Error al enviar la imagen al canal {canal['canal']}: {str(e)}")
                    if message.chat.type == "private":
                        await message.reply(f"Error al enviar la imagen al canal {canal['canal']}: {str(e)}")
                
                finally:
                    # Eliminar la imagen con marca de agua
                    if os.path.exists(imagen_con_marca):
                        os.remove(imagen_con_marca)

        # Eliminar la imagen original
        if os.path.exists(imagen_path):
            os.remove(imagen_path)
        logging.info(f"Imagen original eliminada: {imagen_path}")

    except Exception as e:
        logging.error(f"Error al manejar la imagen: {str(e)}")
        if message.chat.type == "private":
            await message.reply(f"Error al manejar la imagen: {str(e)}")



# Función para generar el mensaje de estadísticas
def generar_mensaje_con_estadisticas(tipster, datos_tipster):
    mensaje = f"{tipster}\nEstadísticas:\n"
    
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

# Función para enviar imágenes al canal privado
async def enviar_imagen_a_canal_privado(client, message, tipster, imagen_path):
    try:
        # Envía la imagen al canal privado con solo el nombre del tipster en la descripción
        await client.send_photo(
            chat_id=canal_privado_id,
            photo=imagen_path,
            caption=tipster
        )
        logging.info(f"Imagen enviada al canal privado: {tipster}")
    except Exception as e:
        logging.error(f"Error al enviar la imagen al canal privado: {str(e)}")
        if message.chat.type == "private":
            await message.reply(f"Error al enviar la imagen al canal privado: {str(e)}")

# Función auxiliar para verificar si un valor es NaN
def is_nan(value):
    return value != value

# Iniciar el bot
app.run()

