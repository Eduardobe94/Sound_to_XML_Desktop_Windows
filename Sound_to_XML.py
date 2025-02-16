import os
import re
import json
import shutil
import logging
import asyncio
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv
from pydub import AudioSegment
from pydub.silence import split_on_silence
import whisper
from openai import OpenAI, AsyncOpenAI
from rapidfuzz import fuzz, process

# Configuración básica del logging (puedes ajustarlo según necesites)
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# ============================================================
# Clase de utilidades para conversiones y funciones comunes
# ============================================================
class Util:
    @staticmethod
    def segundos_a_srt(segundos: float) -> str:
        """Convierte segundos a formato SRT (HH:MM:SS,mmm)."""
        horas = int(segundos // 3600)
        minutos = int((segundos % 3600) // 60)
        segundos_rest = segundos % 60
        return f"{horas:02d}:{minutos:02d}:{segundos_rest:06.3f}".replace('.', ',')

    @staticmethod
    def segundos_a_frames(segundos: float, fps: int = 30) -> int:
        """Convierte segundos a frames (por defecto 30fps)."""
        return int(float(segundos) * fps)

# ============================================================
# Clases de datos
# ============================================================
class Segmento:
    def __init__(self):
        self.texto = ""
        self.tiempo_inicio = 0.0
        self.tiempo_fin = 0.0
        self.score_matching = 0.0
        self.descripcion_visual = ""
        self.storyboard = ""  # Ahora será una sola cadena con la guía visual
        self.tipo_visual = {
            "footage": [],
            "b_roll": [],
            "cgi_3d": [],
            "motion_graphics": [],
            "infografias": [],
            "textos": [],
            "lower_thirds": [],
            "efectos_vfx": [],
            "transiciones": []
        }
        self.palabras_clave = []

class ProyectoEdicion:
    def __init__(self):
        self.segmentos = []
        self.metadata = {
            "titulo": "",
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "duracion_total": 0,
            "num_segmentos": 0,
            "analisis_guion": {
                "tema_principal": "",
                "tono": "",
                "estructura": "",
                "mensaje_clave": "",
                "estilo_visual": "",
                "momentos_clave": [],
                "shot_list": [],
                "referencias_visuales": []
            },
            "prompts": {
                "analisis_guion": {},
                "segmentacion": {},
                "analisis_visual": {}
            }
        }
    
    def actualizar_metadata(self):
        self.metadata["num_segmentos"] = len(self.segmentos)
        if self.segmentos:
            self.metadata["duracion_total"] = max(seg.tiempo_fin for seg in self.segmentos)
    
    def guardar_prompt(self, fase, system_content, user_content, response_content):
        self.metadata["prompts"][fase] = {
            "system": system_content,
            "user": user_content,
            "response": response_content
        }

# ============================================================
# Clase principal de procesamiento
# ============================================================
class MoodboardSimple:
    # Compilamos la expresión regular una única vez para normalizar texto
    _patron_normalizar = re.compile(r'[^\w\s]')

    def __init__(self, audio_folder=None, whisper_model=None):
        self.CARPETA_AUDIOS = audio_folder or "audiosrt"
        self.project_folder = self._create_project_folder()
        self.ensure_folders_exist()
        self.proyecto = ProyectoEdicion()
        self.segmentos_procesados = []
        self.model = whisper_model if whisper_model else whisper.load_model("small")
        
        # Actualizar la inicialización del cliente OpenAI
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.async_client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
    
    def _create_project_folder(self):
        """Genera un nombre único para la carpeta del proyecto basado en la fecha."""
        fecha = datetime.now().strftime("%Y-%m-%d")
        i = 1
        while True:
            project_name = f"project_{i:03d}_{fecha}"
            project_path = os.path.join(self.CARPETA_AUDIOS, project_name)
            if not os.path.exists(project_path):
                return project_name
            i += 1
    
    def ensure_folders_exist(self):
        """Crea las carpetas necesarias para el proyecto."""
        os.makedirs(self.CARPETA_AUDIOS, exist_ok=True)
        project_path = os.path.join(self.CARPETA_AUDIOS, self.project_folder)
        os.makedirs(project_path, exist_ok=True)
        os.makedirs(os.path.join(project_path, "premiere", "assets"), exist_ok=True)
        os.makedirs(os.path.join(project_path, "analysis"), exist_ok=True)
        
        self.xml_path = os.path.join(project_path, "premiere", f"{self.project_folder}.xml")
        self.srt_path = os.path.join(project_path, "premiere", f"{self.project_folder}.srt")
        self.analysis_path = os.path.join(project_path, "analysis", "whisper_output.txt")
        self.gpt_analysis_path = os.path.join(project_path, "analysis", "gpt_analysis.txt")
        self.words_srt_path = os.path.join(project_path, "analysis", "words_timing.srt")
        self.assets_path = os.path.join(project_path, "premiere", "assets")
    
    def print_status(self, message, emoji="ℹ️"):
        """Muestra mensajes de estado (se puede reemplazar por logging)."""
        logger.info(f"{emoji} {message}")
    
    @staticmethod
    def normalizar_texto(texto: str) -> str:
        """Convierte el texto a minúsculas y elimina signos de puntuación."""
        return MoodboardSimple._patron_normalizar.sub('', texto.lower())
    
    def obtener_archivo_audio(self):
        """Busca en la carpeta un archivo de audio con extensiones válidas."""
        archivos = [f for f in os.listdir(self.CARPETA_AUDIOS)
                    if f.lower().endswith((".mp3", ".wav", ".m4a"))]
        if not archivos:
            raise FileNotFoundError("❌ No se encontraron archivos de audio.")
        return os.path.join(self.CARPETA_AUDIOS, archivos[0])
    
    def transcribir_audio(self, audio_path):
        """Transcribe el audio usando Whisper y guarda la transcripción con timestamps."""
        self.print_status("Transcribiendo audio con timestamps de palabras...", "🎙")
        self.transcripcion = self.model.transcribe(audio_path, word_timestamps=True)
        with open(self.analysis_path, 'w', encoding='utf-8') as f:
            json.dump(self.transcripcion, f, ensure_ascii=False, indent=2)
        self.generar_srt_palabras()
    
    def generar_srt_palabras(self):
        """Genera un SRT que detalla el tiempo exacto de cada palabra."""
        self.print_status("Generando SRT con tiempos por palabra...", "📝")
        with open(self.words_srt_path, 'w', encoding='utf-8') as f:
            word_count = 1
            for segment in self.transcripcion.get('segments', []):
                for word in segment.get('words', []):
                    f.write(f"{word_count}\n")
                    tiempo_inicio = Util.segundos_a_srt(word['start'])
                    tiempo_fin = Util.segundos_a_srt(word['end'])
                    f.write(f"{tiempo_inicio} --> {tiempo_fin}\n")
                    duracion = word['end'] - word['start']
                    f.write(f"{word['word']}\n")
                    f.write(f"[Duración: {duracion:.3f}s]\n\n")
                    word_count += 1
        self.print_status(f"SRT de palabras generado: {self.words_srt_path}", "✅")
    
    def copiar_audio(self, audio_path):
        """Copia el audio a la carpeta de assets con un nombre único."""
        self.print_status("Copiando archivo de audio a assets...", "📁")
        extension = os.path.splitext(audio_path)[1]
        self.audio_filename = f"audio_{self.project_folder}{extension}"
        self.audio_dest = os.path.join(self.assets_path, self.audio_filename)
        shutil.copy2(audio_path, self.audio_dest)
        return self.audio_dest
    
    def eliminar_silencios(self, audio_path):
        """Elimina silencios del audio usando pydub."""
        self.print_status("Eliminando silencios del audio...", "🔇")
        audio = AudioSegment.from_file(audio_path)
        min_silence_len = 500  # ms
        silence_thresh = -40   # dB
        keep_silence = 100     # ms a mantener
        chunks = split_on_silence(audio, min_silence_len=min_silence_len,
                                    silence_thresh=silence_thresh,
                                    keep_silence=keep_silence)
        audio_sin_silencios = sum(chunks)
        nombre_base, extension = os.path.splitext(audio_path)
        audio_procesado = f"{nombre_base}_sin_silencios{extension}"
        audio_sin_silencios.export(audio_procesado, format=extension.lstrip('.'))
        self.print_status(f"Audio procesado guardado en: {audio_procesado}", "✅")
        return audio_procesado
    
    def _contar_tokens(self, texto: str) -> int:
        """Estimación aproximada de tokens (4 caracteres = 1 token)."""
        return len(texto) // 4

    def _registrar_uso_tokens(self, f, messages, response):
        """Registra el uso de tokens para una llamada a GPT."""
        # Contar tokens en los mensajes
        tokens_prompt = sum(self._contar_tokens(m["content"]) for m in messages)
        tokens_respuesta = self._contar_tokens(response)
        tokens_total = tokens_prompt + tokens_respuesta

        f.write("\n=== USO DE TOKENS ===\n")
        f.write(f"Tokens en prompt: ~{tokens_prompt}\n")
        f.write(f"Tokens en respuesta: ~{tokens_respuesta}\n")
        f.write(f"Total tokens estimados: ~{tokens_total}\n")
        f.write("(Nota: Esta es una estimación aproximada)\n\n")

        return tokens_prompt, tokens_respuesta, tokens_total

    def _registrar_interaccion_gpt(self, f, fase, system_content, user_content, response_content):
        """Registra una interacción completa con GPT en el archivo de análisis."""
        f.write(f"\n{'='*100}\n")
        f.write(f"=== INTERACCIÓN GPT-4 ({fase}) ===\n")
        f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*100}\n\n")

        f.write("=== SYSTEM PROMPT ===\n")
        f.write(f"{system_content}\n\n")

        f.write("=== USER PROMPT ===\n")
        f.write(f"{user_content}\n\n")

        f.write("=== RESPUESTA DE GPT-4 ===\n")
        f.write(f"{response_content}\n\n")

        # Registrar uso de tokens
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]
        tokens_prompt, tokens_respuesta, tokens_total = self._registrar_uso_tokens(f, messages, response_content)

        f.write(f"\n{'='*100}\n")
        return tokens_total

    async def _procesar_grupo_async(self, grupo, grupo_num, total_grupos, json_template, contexto_completo):
        """Procesa un grupo de segmentos de manera asíncrona, utilizando el análisis previo del guion."""
        # Preparar el texto del grupo actual
        segmentos_grupo = "\n".join(
            [f"[GRUPO ACTUAL] Segmento {i+1}: \"{s['texto']}\" ({s['tiempo_inicio']:.2f}s -> {s['tiempo_fin']:.2f}s)"
             for i, s in enumerate(grupo, start=grupo_num * len(grupo))]
        )

        # Obtener el análisis previo del guion
        analisis_previo = self.proyecto.metadata["analisis_guion"]
        
        # Preparar información del estilo visual
        estilo_visual = analisis_previo.get("estilo_visual", {})
        if isinstance(estilo_visual, str):
            info_estilo = estilo_visual
        else:
            info_estilo = f"""
Estilo: {estilo_visual.get('descripcion', 'No especificado')}
Atmósfera: {estilo_visual.get('atmosfera', 'No especificada')}
Paleta de colores: {', '.join(estilo_visual.get('paleta_colores', ['No especificada']))}
"""

        # Preparar información de momentos clave
        momentos_clave = "\n".join([
            f"- {momento['descripcion']} (Impacto: {momento['impacto']})"
            for momento in analisis_previo.get("momentos_clave", [])
        ])

        # Preparar información de shot list
        shot_list = "\n".join([
            f"- Tipo: {shot['tipo_toma']}, Movimiento: {shot['movimiento']}, Propósito: {shot['proposito']}"
            for shot in analisis_previo.get("shot_list", [])
        ])

        # Preparar información de referencias visuales
        referencias = "\n".join([
            f"- {ref['tipo']}: {ref['referencia']} ({ref['aspecto']})"
            for ref in analisis_previo.get("referencias_visuales", [])
        ])

        prompt_analisis = f'''Analiza cada segmento y genera un plan visual detallado, considerando el análisis previo del guion y el contexto completo.

ANÁLISIS PREVIO DEL GUION:
Tema principal: {analisis_previo.get('tema_principal', 'No especificado')}
Tono: {analisis_previo.get('tono', 'No especificado')}
Mensaje clave: {analisis_previo.get('mensaje_clave', 'No especificado')}

ESTILO VISUAL DEFINIDO:
{info_estilo}

MOMENTOS CLAVE IDENTIFICADOS:
{momentos_clave}

SHOT LIST GENERAL:
{shot_list}

REFERENCIAS VISUALES:
{referencias}

ELEMENTOS TÉCNICOS REQUERIDOS:
Efectos visuales: {', '.join(analisis_previo.get('elementos_tecnicos', {}).get('efectos_visuales', ['No especificados']))}
Gráficos/Animaciones: {', '.join(analisis_previo.get('elementos_tecnicos', {}).get('graficos_animaciones', ['No especificados']))}
Post-producción: {', '.join(analisis_previo.get('elementos_tecnicos', {}).get('post_produccion', ['No especificados']))}

CONTEXTO COMPLETO DEL GUION:
{contexto_completo}

SEGMENTOS A PROCESAR EN ESTE GRUPO:
{segmentos_grupo}

INSTRUCCIONES:
1. Para cada segmento del GRUPO ACTUAL, especifica los elementos visuales necesarios.
2. Mantén consistencia con el estilo visual y tono definidos en el análisis previo.
3. Considera los momentos clave al proponer elementos visuales.
4. Utiliza las referencias visuales como guía para el tratamiento.
5. En el campo "tipo_visual", SOLO incluye las categorías que tengan contenido.
6. NO incluir categorías vacías o con listas vacías.
7. Las categorías disponibles son:
   - b_roll: Imágenes de apoyo que enriquecen la historia y mantienen la atención visual
   - cgi_3d: representacion visual de información que no puede ser filmada directamente y explica ideas complejas
   - motion_graphics: animaciones de elementos graficos que explican información de manera clara y dinámica
   - textos: Superposición de texto con fechas, y datos clave
   - infografias: elementos graficos que refuerzan la información presentada, hacen que la información compleja sea visualmente atractiva y fácil de entender
   - transiciones: Uso de técnicas avanzadas de edición, transiciones narrativas para conectar escenas
             
IMPORTANTE:
1. Sé específico con cada elemento visual
2. Asegúrate de que cada elemento visual apoye la narrativa general
3. Incluye solo los tipos de contenido que podrían mejorar la escena
4. Mantén el mismo orden de los segmentos proporcionados
5. Usa el contexto completo para crear transiciones coherentes
6. Evita repeticiones innecesarias de recursos visuales similares
7. SOLO procesa los segmentos marcados como [GRUPO ACTUAL]
8. Asegúrate de que las propuestas visuales sean consistentes con el análisis previo del guion

Devuelve solo JSON válido siguiendo esta plantilla:
{json_template}'''

        # Logging del grupo usando el nuevo método
        with open(self.gpt_analysis_path, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*100}\n")
            f.write(f"=== PROCESANDO GRUPO {grupo_num + 1}/{total_grupos} ===\n")
            f.write(f"Número de segmentos en este grupo: {len(grupo)}\n")
            f.write("Segmentos a procesar:\n")
            f.write(segmentos_grupo + "\n")

        try:
            system_content = "Eres un director de arte y experto en visuales con amplia experiencia en post-producción. Tu tarea es crear planes visuales extremadamente detallados para cada segmento, especificando exactamente qué tipos de contenido visual se necesitan. Considera el análisis previo del guion y el contexto completo para mantener coherencia visual y narrativa."
            
            # Llamada asíncrona a GPT-4
            response = await self.async_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": prompt_analisis}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )

            respuesta = response.choices[0].message.content

            # Logging de la interacción
            with open(self.gpt_analysis_path, 'a', encoding='utf-8') as f:
                self._registrar_interaccion_gpt(f, f"ANÁLISIS VISUAL - GRUPO {grupo_num + 1}", 
                                              system_content, prompt_analisis, respuesta)

            analisis = json.loads(respuesta)
            return grupo_num, analisis.get('analisis_segmentos', [])

        except Exception as e:
            error_msg = f"Error en grupo {grupo_num + 1}: {str(e)}"
            self.print_status(error_msg, "⚠️")
            with open(self.gpt_analysis_path, 'a', encoding='utf-8') as f:
                f.write(f"\n=== ERROR EN GRUPO {grupo_num + 1} ===\n")
                f.write(f"{error_msg}\n")
            return grupo_num, []

    async def analizar_segmentos_paralelo(self, json_template):
        """Analiza todos los segmentos en paralelo usando asyncio, manteniendo el contexto completo."""
        SEGMENTOS_POR_GRUPO = 12
        grupos = [
            self.segmentos_procesados[i:i + SEGMENTOS_POR_GRUPO]
            for i in range(0, len(self.segmentos_procesados), SEGMENTOS_POR_GRUPO)
        ]

        # Preparar el contexto completo como texto fluido
        contexto_completo = " ".join([s['texto'] for s in self.segmentos_procesados])

        self.print_status(f"Procesando {len(self.segmentos_procesados)} segmentos en {len(grupos)} grupos en paralelo", "🚀")

        # Crear tareas para cada grupo
        tareas = [
            self._procesar_grupo_async(grupo, i, len(grupos), json_template, contexto_completo)
            for i, grupo in enumerate(grupos)
        ]

        # Ejecutar todas las tareas en paralelo
        resultados = await asyncio.gather(*tareas)

        # Ordenar resultados por número de grupo
        resultados_ordenados = sorted(resultados, key=lambda x: x[0])
        
        # Extraer solo los análisis
        todos_analisis = []
        for _, analisis_grupo in resultados_ordenados:
            todos_analisis.extend(analisis_grupo)

        return todos_analisis

    async def segmentar_con_gpt(self):
        """Versión actualizada que usa el análisis previo del guion para mejorar la segmentación."""
        self.print_status("Analizando transcripción con GPT-4...", "🤖")
        
        # Obtener el texto completo sin tiempos
        palabras_completas = [
            word['word'].strip()
            for segment in self.transcripcion.get('segments', [])
            for word in segment.get('words', [])
            if word['word'].strip()
        ]
        texto_completo = " ".join(palabras_completas)
        
        # Preparar el contexto del análisis previo
        analisis_previo = self.proyecto.metadata["analisis_guion"]
        momentos_clave = "\n".join([
            f"- {momento['descripcion']} (Impacto: {momento['impacto']})"
            for momento in analisis_previo.get("momentos_clave", [])
        ])
        
        estilo_visual = analisis_previo.get("estilo_visual", {})
        if isinstance(estilo_visual, str):
            info_estilo = estilo_visual
        else:
            info_estilo = f"""
Estilo: {estilo_visual.get('descripcion', 'No especificado')}
Atmósfera: {estilo_visual.get('atmosfera', 'No especificada')}
Paleta de colores: {', '.join(estilo_visual.get('paleta_colores', ['No especificada']))}
"""
        
        # Preparar prompts para GPT-4
        system_prompt = (
            """Eres un experto en análisis narrativo, dirección de arte y edición de video.
Tu tarea es segmentar voice-overs en unidades coherentes siguiendo reglas específicas y el análisis previo del guion.
Mantén los tiempos exactos de cada palabra y genera descripciones visuales evocadoras que sean consistentes con el análisis general."""
        )
        
        prompt_segmentacion = f'''Analiza y segmenta este texto considerando el análisis previo del guion y estas reglas específicas:

ANÁLISIS PREVIO DEL GUION:
Tema principal: {analisis_previo.get('tema_principal', 'No especificado')}
Tono: {analisis_previo.get('tono', 'No especificado')}
Mensaje clave: {analisis_previo.get('mensaje_clave', 'No especificado')}
Estructura: {analisis_previo.get('estructura', 'No especificada')}

ESTILO VISUAL DEFINIDO:
{info_estilo}

MOMENTOS CLAVE IDENTIFICADOS:
{momentos_clave}

REGLAS DE SEGMENTACIÓN:
- Segmentos de 1-20 palabras basada en unidades narrativas
- Separar en nuevo segmento por:
  * Puntuación: (. ! ? , ; :)
  * Inicio/fin de oraciones
  * Conectores: y, o, pero, porque, sin embargo, además, también, luego, entonces
- Mantener coherencia y ritmo natural
- Cada segmento debe representar una idea o momento narrativo completo
- Respetar pausas naturales del discurso
- Considerar:
  * Inicio y fin de ideas
  * Puntos de énfasis identificados en el análisis
  * Transiciones narrativas
  * Momentos clave del análisis previo

OBJETIVOS DE LA SEGMENTACIÓN:
1. Crear unidades visuales potentes que respeten los momentos clave identificados
2. Tengan ritmo natural para edición
3. Enfatizar los puntos de mayor impacto
4. Facilitar las transiciones entre ideas principales
5. Mantener el ritmo narrativo establecido en el análisis

- Devuelve solo JSON válido con el siguiente formato:
{{
    "segmentos": [
        {{"texto": "texto exacto del segmento"}}
    ]
}}

Texto a procesar:
{texto_completo}
'''
        # Guardar el prompt en el archivo de análisis
        with open(self.gpt_analysis_path, 'a', encoding='utf-8') as f:
            f.write("\n=== MENSAJES ENVIADOS A GPT-4 (SEGMENTACIÓN) ===\n")
            f.write("System message:\n")
            f.write(system_prompt + "\n\n")
            f.write("User message:\n")
            f.write(prompt_segmentacion + "\n\n")

        # Llamada a GPT-4
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt_segmentacion}
        ]
        response_segmentacion = self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=messages,
            temperature=0.5,
            response_format={"type": "json_object"}
        )
        respuesta_seg = response_segmentacion.choices[0].message.content

        with open(self.gpt_analysis_path, 'a', encoding='utf-8') as f:
            f.write("=== RESPUESTA DE GPT-4 (SEGMENTACIÓN) ===\n")
            f.write(respuesta_seg + "\n")
            self._registrar_uso_tokens(f, messages, respuesta_seg)
        
        self.proyecto.guardar_prompt("segmentacion", system_prompt, prompt_segmentacion, respuesta_seg)

        try:
            segmentacion = json.loads(respuesta_seg)
            segmentos_narrativos = segmentacion.get('segmentos', [])
            self.print_status("Asociando tiempos a segmentos...", "⏱️")

            # Preprocesar palabras de Whisper
            palabras_whisper = []
            for segment in self.transcripcion.get('segments', []):
                for word in segment.get('words', []):
                    if word['word'].strip():
                        palabras_whisper.append({
                            'texto': word['word'].strip(),
                            'inicio': float(word['start']),
                            'fin': float(word['end']),
                            'indice': len(palabras_whisper)
                        })

            # Crear un índice invertido: palabra normalizada -> lista de ocurrencias
            indice_palabras = defaultdict(list)
            for palabra in palabras_whisper:
                texto_norm = self.normalizar_texto(palabra['texto'])
                indice_palabras[texto_norm].append(palabra)

            ultima_posicion = 0
            for segmento in segmentos_narrativos:
                texto_segmento = segmento['texto']
                inicio, fin, score = self.encontrar_mejor_secuencia(texto_segmento, ultima_posicion, palabras_whisper, indice_palabras)
                if inicio is not None and score > 70:
                    self.segmentos_procesados.append({
                        'texto': texto_segmento,
                        'tiempo_inicio': inicio,
                        'tiempo_fin': fin,
                        'score_matching': score
                    })
                    ultima_posicion = next(
                        (i for i, p in enumerate(palabras_whisper) if p['fin'] > fin),
                        ultima_posicion + 1
                    )
                    self.print_status(f"✓ Segmento matcheado (score: {score:.1f}%): {texto_segmento}", "🎯")
                else:
                    self.print_status(f"⚠️ No se encontró coincidencia confiable para: {texto_segmento}", "⚠️")

            # Realizar el análisis visual de los segmentos
            json_template = '''{
    "analisis_segmentos": [
        {
            "texto": "texto exacto del segmento",
            "descripcion_visual": "representación visual cinematográfica que captura la atmósfera, esencia y tono de la escena",
            "storyboard": "guía visual detallada que define la composición, encuadre, movimientos de cámara y elementos clave de la toma (max 10 palabras)",
            "tipo_visual": {
                "b_roll": [],
                "cgi_3d": [],
                "motion_graphics": [],
                "textos": [],
                "infografias": [],
                "transiciones": []
            },
            "palabras_clave": ["1 a 3 palabras clave para búsqueda de material visual"]
        }
    ]
}'''
            # Analizar los segmentos en paralelo
            todos_analisis = await self.analizar_segmentos_paralelo(json_template)
            
            # Actualizar los segmentos procesados con el análisis visual
            for i, analisis in enumerate(todos_analisis):
                if i < len(self.segmentos_procesados):
                    self.segmentos_procesados[i].update({
                        'descripcion_visual': analisis.get('descripcion_visual', ''),
                        'storyboard': analisis.get('storyboard', ''),
                        'tipo_visual': json.dumps(analisis.get('tipo_visual', {}), ensure_ascii=False),
                        'palabras_clave': analisis.get('palabras_clave', [])
                    })

        except Exception as e:
            error_msg = f"Error en la segmentación: {str(e)}"
            self.print_status(error_msg, "❌")
            with open(self.gpt_analysis_path, 'a', encoding='utf-8') as f:
                f.write("\n=== ERROR EN SEGMENTACIÓN ===\n")
                f.write(error_msg + "\n")
            raise

    def encontrar_mejor_secuencia(self, texto_segmento, ultima_pos, palabras_whisper, indice_palabras):
        """Busca la mejor coincidencia de la secuencia en la transcripción."""
        palabras_segmento = [self.normalizar_texto(p) for p in texto_segmento.split()]
        mejor_inicio, mejor_fin, mejor_score = None, None, 0
        primera_palabra = palabras_segmento[0]
        candidatos_inicio = []
        if primera_palabra in indice_palabras:
            candidatos_inicio.extend(p['indice'] for p in indice_palabras[primera_palabra] if p['indice'] >= ultima_pos)
        if not candidatos_inicio:
            matches = process.extract(
                primera_palabra,
                [p['texto'] for p in palabras_whisper[ultima_pos:]],
                scorer=fuzz.ratio,
                limit=3
            )
            candidatos_inicio.extend(i + ultima_pos for i, (_, score) in enumerate(matches) if score > 80)
        for pos_inicio in candidatos_inicio:
            if pos_inicio + len(palabras_segmento) > len(palabras_whisper):
                continue
            secuencia_whisper = [
                self.normalizar_texto(palabras_whisper[i]['texto'])
                for i in range(pos_inicio, pos_inicio + len(palabras_segmento))
            ]
            score_total = sum(
                fuzz.ratio(w1, w2) for w1, w2 in zip(palabras_segmento, secuencia_whisper)
            ) / len(palabras_segmento)
            if score_total > mejor_score:
                mejor_score = score_total
                mejor_inicio = pos_inicio
                mejor_fin = pos_inicio + len(palabras_segmento) - 1
            if score_total > 95:
                break
        if mejor_inicio is not None:
            return palabras_whisper[mejor_inicio]['inicio'], palabras_whisper[mejor_fin]['fin'], mejor_score
        return None, None, 0

    def generar_srt_nuevo(self):
        """Genera el archivo SRT final usando los datos estructurados del proyecto."""
        self.print_status("Generando archivo SRT final...", "📝")
        with open(self.srt_path, 'w', encoding='utf-8') as f:
            for i, segmento in enumerate(self.proyecto.segmentos, 1):
                f.write(f"{i}\n")
                tiempo_inicio = Util.segundos_a_srt(segmento.tiempo_inicio)
                tiempo_fin = Util.segundos_a_srt(segmento.tiempo_fin)
                f.write(f"{tiempo_inicio} --> {tiempo_fin}\n")

                # Procesar tipo_visual para mostrar solo los elementos con contenido
                tipo_visual_dict = segmento.tipo_visual
                if isinstance(tipo_visual_dict, str):
                    try:
                        tipo_visual_dict = json.loads(tipo_visual_dict)
                    except json.JSONDecodeError:
                        tipo_visual_dict = {}
                
                tipo_visual_formateado = []
                if isinstance(tipo_visual_dict, dict):
                    for key, value in tipo_visual_dict.items():
                        if value and len(value) > 0:
                            elementos = value if isinstance(value, list) else [value]
                            for elemento in elementos:
                                tipo_visual_formateado.append(f"{key}: {elemento}")
                
                tipo_visual_str = "\n".join(tipo_visual_formateado) if tipo_visual_formateado else "Sin elementos visuales"
                
                palabras_clave = (
                    ', '.join(segmento.palabras_clave)
                    if isinstance(segmento.palabras_clave, list)
                    else segmento.palabras_clave if segmento.palabras_clave
                    else "Sin palabras clave"
                )

                # Formatear el subtítulo con el formato exacto deseado
                subtitulo = f'''DESCRIPCIÓN VISUAL:
{segmento.descripcion_visual or "Sin descripción visual"}

STORYBOARD:
{segmento.storyboard or "Sin storyboard"}

TIPO VISUAL:
{tipo_visual_str}

PALABRAS CLAVE:
{palabras_clave}

TEXTO:
{segmento.texto}
'''
                f.write(f"{subtitulo}\n")
    
    def generar_xml_nuevo(self, audio_path):
        """Genera el archivo XML final para Premiere, con los marcadores correspondientes."""
        self.print_status("Generando archivo XML final...", "🎬")
        xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xmeml>
<xmeml version="5">
    <sequence>
        <name>MoodboardXZ_{self.project_folder}</name>
        <duration>7200</duration>
        <rate>
            <timebase>30</timebase>
            <ntsc>TRUE</ntsc>
        </rate>
        <timecode>
            <rate>
                <timebase>30</timebase>
                <ntsc>TRUE</ntsc>
            </rate>
            <string>00:00:00:00</string>
            <frame>0</frame>
            <source>source</source>
            <displayformat>NDF</displayformat>
        </timecode>
        <media>
            <audio>
                <track>
                    <enabled>TRUE</enabled>
                    <locked>FALSE</locked>
                    <clipitem id="audio_1">
                        <name>{os.path.basename(audio_path)}</name>
                        <duration>7200</duration>
                        <rate>
                            <timebase>30</timebase>
                            <ntsc>TRUE</ntsc>
                        </rate>
                        <file id="file_1">
                            <name>{os.path.basename(audio_path)}</name>
                            <pathurl>file://{os.path.abspath(audio_path)}</pathurl>
                            <rate>
                                <timebase>30</timebase>
                                <ntsc>TRUE</ntsc>
                            </rate>
                            <duration>7200</duration>
                            <media>
                                <audio>
                                    <samplecharacteristics>
                                        <depth>16</depth>
                                        <samplerate>48000</samplerate>
                                    </samplecharacteristics>
                                    <channelcount>2</channelcount>
                                </audio>
                            </media>
                        </file>
                        <sourcetrack>
                            <mediatype>audio</mediatype>
                        </sourcetrack>
                        <in>0</in>
                        <out>7200</out>
                        <start>0</start>
                        <end>7200</end>
                    </clipitem>
                </track>
            </audio>
        </media>
        <markers>'''
        for i, segmento in enumerate(self.proyecto.segmentos, 1):
            start_frame = Util.segundos_a_frames(segmento.tiempo_inicio)
            end_frame = Util.segundos_a_frames(segmento.tiempo_fin)
            if start_frame >= end_frame:
                end_frame = start_frame + 1
            texto = segmento.texto.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            idea = segmento.descripcion_visual.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            # Procesar tipo_visual para mostrar solo los elementos con contenido
            tipo_visual_dict = segmento.tipo_visual
            if isinstance(tipo_visual_dict, str):
                try:
                    tipo_visual_dict = json.loads(tipo_visual_dict)
                except json.JSONDecodeError:
                    tipo_visual_dict = {}
            
            tipo_visual_formateado = []
            if isinstance(tipo_visual_dict, dict):
                for key, value in tipo_visual_dict.items():
                    if value and len(value) > 0:
                        elementos = value if isinstance(value, list) else [value]
                        for elemento in elementos:
                            # Escapar caracteres especiales que podrían causar problemas en XML
                            elemento_escapado = elemento.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
                            tipo_visual_formateado.append(f"{key}: {elemento_escapado}")
            
            tipo_visual_str = "\n".join(tipo_visual_formateado)
            
            palabras_clave = (
                ', '.join(segmento.palabras_clave)
                if isinstance(segmento.palabras_clave, list)
                else segmento.palabras_clave
            )
            palabras_clave = palabras_clave.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            # Formatear el título del marcador para incluir la idea principal
            marker_title = f"[{i}] {idea[:100]}"  # Limitar a 100 caracteres para evitar títulos muy largos
            
            # Formatear la descripción del marcador
            comment = f"""DESCRIPCIÓN VISUAL:
{idea}

STORYBOARD:
{segmento.storyboard}

TIPO VISUAL:
{tipo_visual_str}

PALABRAS CLAVE:
{palabras_clave}

TEXTO:
{texto}""".replace('\n', '&#xA;')  # Convertir saltos de línea a entidad XML
            
            xml += f'''
            <marker>
                <name>{marker_title}</name>
                <comment>{comment}</comment>
                <in>{start_frame}</in>
                <out>{end_frame}</out>
            </marker>'''
        xml += '''
        </markers>
    </sequence>
</xmeml>'''
        with open(self.xml_path, "w", encoding='utf-8') as f:
            f.write(xml)
        self.print_status(f"XML generado con {len(self.proyecto.segmentos)} marcadores", "✅")
        self.print_status("Marcadores generados:", "📍")
        for i, segmento in enumerate(self.proyecto.segmentos, 1):
            inicio = Util.segundos_a_frames(segmento.tiempo_inicio)
            fin = Util.segundos_a_frames(segmento.tiempo_fin)
            self.print_status(
                f"Marcador {i}: Frame {inicio} -> {fin} ({segmento.tiempo_inicio:.2f}s -> {segmento.tiempo_fin:.2f}s)",
                "🔖"
            )
    
    async def analizar_texto_completo(self):
        """Realiza un análisis profundo del texto completo antes de la segmentación."""
        self.print_status("Analizando el guion completo...", "📚")
        
        # Obtener el texto completo sin tiempos
        palabras_completas = [
            word['word'].strip()
            for segment in self.transcripcion.get('segments', [])
            for word in segment.get('words', [])
            if word['word'].strip()
        ]
        texto_completo = " ".join(palabras_completas)
        
        # Preparar prompts para el análisis del guion
        system_prompt = """Eres un experto guionista y director de arte con amplia experiencia en análisis de guiones y dirección visual.
Tu tarea es realizar un análisis profundo del texto proporcionado, identificando elementos clave que guiarán la dirección visual y la narrativa."""

        prompt_analisis = f'''Analiza este texto y proporciona un desglose detallado del guion (script breakdown).
El análisis debe ser exhaustivo y considerar todos los aspectos narrativos y visuales.

TEXTO A ANALIZAR:
{texto_completo}

INSTRUCCIONES:
Realiza un análisis completo que incluya:

1. ANÁLISIS NARRATIVO:
   - Tema principal y subtemas
   - Tono y estilo narrativo
   - Estructura del contenido
   - Mensaje clave y objetivos
   - Público objetivo

2. ANÁLISIS VISUAL:
   - Estilo visual recomendado
   - Paleta de colores sugerida
   - Referencias visuales específicas
   - Atmósfera y mood general

3. MOMENTOS CLAVE:
   - Identificar puntos de mayor impacto
   - Momentos de transición importantes
   - Elementos que requieren énfasis visual

4. SHOT LIST PRELIMINAR:
   - Tipos de tomas recomendadas
   - Movimientos de cámara sugeridos
   - Composiciones específicas
   - Transiciones clave

5. ELEMENTOS TÉCNICOS:
   - Efectos visuales necesarios
   - Gráficos o animaciones requeridas
   - Necesidades específicas de post-producción

Devuelve solo JSON válido con el siguiente formato:
{{
    "analisis_guion": {{
        "tema_principal": "descripción del tema central",
        "tono": "descripción del tono y estilo",
        "estructura": "análisis de la estructura narrativa",
        "mensaje_clave": "mensaje principal que se quiere transmitir",
        "publico_objetivo": "descripción del público al que va dirigido",
        "estilo_visual": {{
            "descripcion": "descripción del estilo visual general",
            "paleta_colores": ["color1", "color2", "etc"],
            "atmosfera": "descripción de la atmósfera deseada"
        }},
        "momentos_clave": [
            {{
                "descripcion": "descripción del momento clave",
                "impacto": "alto/medio/bajo",
                "tratamiento_visual": "cómo debe tratarse visualmente"
            }}
        ],
        "shot_list": [
            {{
                "tipo_toma": "descripción del tipo de toma",
                "movimiento": "descripción del movimiento de cámara",
                "composicion": "descripción de la composición",
                "proposito": "objetivo de esta toma"
            }}
        ],
        "referencias_visuales": [
            {{
                "tipo": "película/serie/comercial/etc",
                "referencia": "nombre o descripción de la referencia",
                "aspecto": "qué aspecto específico se debe tomar como referencia"
            }}
        ],
        "elementos_tecnicos": {{
            "efectos_visuales": ["lista de efectos necesarios"],
            "graficos_animaciones": ["lista de gráficos/animaciones"],
            "post_produccion": ["necesidades específicas de post"]
        }}
    }}
}}'''

        try:
            # Llamada a GPT-4 para el análisis del guion
            response_analisis = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt_analisis}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            respuesta = response_analisis.choices[0].message.content
            
            # Registrar la interacción en el archivo de análisis
            with open(self.gpt_analysis_path, 'a', encoding='utf-8') as f:
                self._registrar_interaccion_gpt(f, "ANÁLISIS DEL GUION", system_prompt, prompt_analisis, respuesta)
            
            # Actualizar la metadata del proyecto con el análisis
            analisis = json.loads(respuesta)
            self.proyecto.metadata["analisis_guion"] = analisis["analisis_guion"]
            self.proyecto.guardar_prompt("analisis_guion", system_prompt, prompt_analisis, respuesta)
            
            self.print_status("Análisis del guion completado", "✨")
            return analisis["analisis_guion"]
            
        except Exception as e:
            error_msg = f"Error en el análisis del guion: {str(e)}"
            self.print_status(error_msg, "❌")
            with open(self.gpt_analysis_path, 'a', encoding='utf-8') as f:
                f.write("\n=== ERROR EN ANÁLISIS DEL GUION ===\n")
                f.write(error_msg + "\n")
            raise

    async def procesar_audio(self, archivo_audio=None):
        """Proceso completo: desde la preparación del audio hasta la generación de SRT y XML."""
        self.print_status("Iniciando procesamiento...", "🚀")
        with open(self.gpt_analysis_path, 'w', encoding='utf-8') as f:
            f.write("=== CONFIGURACIÓN ===\n")
            f.write(f"Modelo: gpt-4-turbo-preview\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        try:
            audio_path = archivo_audio or self.obtener_archivo_audio()
            self.print_status(f"Procesando archivo: {os.path.basename(audio_path)}", "🎙")
            audio_sin_silencios = self.eliminar_silencios(audio_path)
            audio_dest = self.copiar_audio(audio_sin_silencios)
            self.transcribir_audio(audio_dest)
            
            # Primero realizamos el análisis completo del guion
            analisis_guion = await self.analizar_texto_completo()
            
            # Luego continuamos con la segmentación y el resto del proceso
            await self.segmentar_con_gpt()
            
            # Convertir los segmentos procesados en objetos Segmento y agregarlos al proyecto
            for seg_dict in self.segmentos_procesados:
                seg = Segmento()
                seg.texto = seg_dict.get('texto', '')
                seg.tiempo_inicio = seg_dict.get('tiempo_inicio', 0.0)
                seg.tiempo_fin = seg_dict.get('tiempo_fin', 0.0)
                seg.score_matching = seg_dict.get('score_matching', 0.0)
                seg.descripcion_visual = seg_dict.get('descripcion_visual', '')
                seg.storyboard = seg_dict.get('storyboard', "")
                seg.tipo_visual = seg_dict.get('tipo_visual', {})
                seg.palabras_clave = seg_dict.get('palabras_clave', [])
                self.proyecto.segmentos.append(seg)
            
            self.proyecto.actualizar_metadata()
            self.generar_srt_nuevo()
            self.generar_xml_nuevo(audio_dest)
            self.print_status("¡Proceso completado exitosamente!", "🎉")
        except Exception as e:
            self.print_status(f"Error en el procesamiento: {str(e)}", "❌")
            with open(self.gpt_analysis_path, 'a', encoding='utf-8') as f:
                f.write("\n=== ERROR EN EL PROCESAMIENTO ===\n")
                f.write(f"Error: {str(e)}\n")
            raise
        finally:
            # Limpieza: eliminar el archivo de audio sin silencios
            if 'audio_sin_silencios' in locals() and os.path.exists(audio_sin_silencios):
                os.remove(audio_sin_silencios)
        return self.xml_path, self.srt_path

# ============================================================
# Ejemplo de uso
# ============================================================
if __name__ == "__main__":
    async def main():
        moodboard = MoodboardSimple()
        xml_path, srt_path = await moodboard.procesar_audio()
        logger.info(f"XML generado en: {xml_path}")
        logger.info(f"SRT generado en: {srt_path}")

    # Ejecutar el bucle de eventos de asyncio
    asyncio.run(main())
