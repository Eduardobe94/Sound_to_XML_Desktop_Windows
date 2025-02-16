import sys
import os
import asyncio
import logging
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                            QWidget, QLabel, QProgressBar, QTextEdit, QFileDialog,
                            QHBoxLayout, QFrame, QSplitter, QMenuBar, QMenu, QStatusBar,
                            QDialog, QLineEdit)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QAction, QPalette, QColor, QFontDatabase
from Sound_to_XML import MoodboardSimple
import whisper
from openai import OpenAI, AsyncOpenAI
import subprocess
import platform

# Configuración del logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

class WhisperModelLoader:
    _instance = None
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            cls._model = whisper.load_model("small")
        return cls._model

class AsyncProcessor(QThread):
    """Clase para manejar el procesamiento asíncrono en un hilo separado."""
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(tuple)
    error_signal = pyqtSignal(str)

    def __init__(self, audio_path):
        super().__init__()
        self.audio_path = audio_path
        self.model = WhisperModelLoader.get_model()  # Usar el modelo ya cargado

    async def process_audio(self):
        try:
            moodboard = MoodboardSimple(whisper_model=self.model)  # Pasar el modelo
            moodboard.print_status = lambda msg, emoji="ℹ️": self.progress_signal.emit(f"{emoji} {msg}")
            xml_path, srt_path = await moodboard.procesar_audio(self.audio_path)
            return xml_path, srt_path
        except Exception as e:
            raise Exception(f"Error durante el procesamiento: {str(e)}")

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.process_audio())
            loop.close()
            self.finished_signal.emit(result)
        except Exception as e:
            self.error_signal.emit(str(e))

class DarkPalette(QPalette):
    def __init__(self):
        super().__init__()
        # Colores principales
        self.setColor(QPalette.ColorRole.Window, QColor("#1a1a1a"))
        self.setColor(QPalette.ColorRole.WindowText, QColor("#ffffff"))
        self.setColor(QPalette.ColorRole.Base, QColor("#232323"))
        self.setColor(QPalette.ColorRole.AlternateBase, QColor("#2b2b2b"))
        self.setColor(QPalette.ColorRole.ToolTipBase, QColor("#1a1a1a"))
        self.setColor(QPalette.ColorRole.ToolTipText, QColor("#ffffff"))
        self.setColor(QPalette.ColorRole.Text, QColor("#ffffff"))
        self.setColor(QPalette.ColorRole.Button, QColor("#232323"))
        self.setColor(QPalette.ColorRole.ButtonText, QColor("#ffffff"))
        self.setColor(QPalette.ColorRole.Link, QColor("#0086b6"))
        self.setColor(QPalette.ColorRole.Highlight, QColor("#2979ff"))
        self.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))

class OutputFolderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar carpeta de salida")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        
        # Campo de carpeta
        folder_frame = QFrame()
        folder_layout = QHBoxLayout(folder_frame)
        
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("Selecciona la carpeta de salida")
        self.folder_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
            }
        """)
        
        browse_button = QPushButton("Examinar")
        browse_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #2979ff;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
        """)
        browse_button.clicked.connect(self.browse_folder)
        
        folder_layout.addWidget(self.folder_input)
        folder_layout.addWidget(browse_button)
        
        # Botones de aceptar/cancelar
        button_frame = QFrame()
        button_layout = QHBoxLayout(button_frame)
        
        ok_button = QPushButton("Aceptar")
        ok_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #2979ff;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
        """)
        ok_button.clicked.connect(self.accept)
        
        cancel_button = QPushButton("Cancelar")
        cancel_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #424242;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #323232;
            }
        """)
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(ok_button)
        
        layout.addWidget(folder_frame)
        layout.addWidget(button_frame)
        
        # Establecer carpeta por defecto
        default_folder = os.path.expanduser("~/Documents/Sound to XML Output")
        self.folder_input.setText(default_folder)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta de salida",
            self.folder_input.text()
        )
        if folder:
            self.folder_input.setText(folder)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sound to XML")
        self.setMinimumSize(1200, 800)
        
        # Crear barra de estado
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #1e1e1e;
                color: #9e9e9e;
                padding: 5px;
                font-size: 12px;
            }
        """)
        self.setStatusBar(self.status_bar)
        
        # Widget principal
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Header minimalista
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-bottom: 1px solid #333333;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        # Título
        title = QLabel("Sound to XML")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: 500;
            color: #ffffff;
            font-family: -apple-system, system-ui, BlinkMacSystemFont, "Segoe UI", Roboto;
        """)
        header_layout.addWidget(title)
        
        # Botón de selección de archivo en el header
        self.select_button = QPushButton("Seleccionar Audio")
        self.select_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 14px;
                background-color: #2979ff;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
            QPushButton:disabled {
                background-color: #424242;
                color: #757575;
            }
        """)
        header_layout.addWidget(self.select_button, alignment=Qt.AlignmentFlag.AlignRight)
        
        main_layout.addWidget(header)

        # Contenedor principal
        content = QFrame()
        content.setStyleSheet("""
            QFrame {
                background-color: #121212;
            }
        """)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)

        # Panel de estado
        status_panel = QFrame()
        status_panel.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 6px;
                padding: 15px;
            }
        """)
        status_layout = QVBoxLayout(status_panel)
        
        # Información del archivo
        self.file_label = QLabel("Ningún archivo seleccionado")
        self.file_label.setStyleSheet("""
            color: #9e9e9e;
            font-size: 14px;
            padding: 5px 0;
        """)
        status_layout.addWidget(self.file_label)

        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 3px;
                background-color: #2b2b2b;
                height: 6px;
                margin-top: 10px;
            }
            QProgressBar::chunk {
                background-color: #2979ff;
                border-radius: 3px;
            }
        """)
        status_layout.addWidget(self.progress_bar)
        
        content_layout.addWidget(status_panel)

        # Panel de resultados (inicialmente oculto)
        self.results_panel = QFrame()
        self.results_panel.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 6px;
                padding: 15px;
            }
        """)
        self.results_panel.hide()
        results_layout = QHBoxLayout(self.results_panel)
        results_layout.setSpacing(10)
        
        # Botones de acción
        self.xml_button = self.create_action_button("Abrir XML", "📄")
        self.srt_button = self.create_action_button("Abrir SRT", "📝")
        self.audio_button = self.create_action_button("Abrir Audio", "🎵")
        self.folder_button = self.create_action_button("Abrir Carpeta", "📁")
        
        results_layout.addWidget(self.xml_button)
        results_layout.addWidget(self.srt_button)
        results_layout.addWidget(self.audio_button)
        results_layout.addWidget(self.folder_button)
        
        content_layout.addWidget(self.results_panel)

        # Panel de log
        log_panel = QFrame()
        log_panel.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 6px;
            }
        """)
        log_layout = QVBoxLayout(log_panel)
        
        # Título del log
        log_title = QLabel("Registro de Actividad")
        log_title.setStyleSheet("""
            font-size: 14px;
            font-weight: 500;
            color: #ffffff;
            padding: 10px;
        """)
        log_layout.addWidget(log_title)

        # Área de log
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("""
            QTextEdit {
                border: none;
                background-color: #1a1a1a;
                color: #e0e0e0;
                padding: 15px;
                font-family: 'SF Mono', 'Consolas', monospace;
                font-size: 13px;
                line-height: 1.5;
            }
        """)
        log_layout.addWidget(self.log_area)
        
        content_layout.addWidget(log_panel)
        main_layout.addWidget(content)

        # Estado inicial
        self.progress_bar.hide()
        self.audio_path = None
        self.processor = None

        # Conectar señales
        self.select_button.clicked.connect(self.select_file)

    def select_file(self):
        try:
            file_dialog = QFileDialog()
            file_path, _ = file_dialog.getOpenFileName(
                self,
                "Seleccionar archivo de audio",
                "",
                "Archivos de audio (*.mp3 *.wav *.m4a)"
            )
            
            if file_path:
                # Mostrar diálogo de carpeta de salida
                dialog = OutputFolderDialog(self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    output_folder = dialog.folder_input.text()
                    os.makedirs(output_folder, exist_ok=True)
                    
                    self.audio_path = file_path
                    self.output_folder = output_folder
                    self.file_label.setText(f"Archivo: {os.path.basename(file_path)}")
                    self.start_processing()
        except Exception as e:
            self.add_log(f"\n❌ Error: {str(e)}")

    def start_processing(self):
        self.select_button.setEnabled(False)
        self.progress_bar.show()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 3px;
                background-color: #2b2b2b;
                height: 6px;
                margin-top: 10px;
            }
            QProgressBar::chunk {
                background-color: #2979ff;
                border-radius: 3px;
            }
        """)
        self.log_area.clear()
        self.add_log("Iniciando procesamiento...")
        self.status_bar.showMessage("Procesando archivo...")

        self.processor = AsyncProcessor(self.audio_path)
        self.processor.progress_signal.connect(self.update_progress)
        self.processor.finished_signal.connect(self.processing_finished)
        self.processor.error_signal.connect(self.processing_error)
        self.processor.start()

    def update_progress(self, message):
        self.add_log(message)

    def processing_finished(self, result):
        xml_path, srt_path = result
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_bar.hide()
        self.select_button.setEnabled(True)
        
        # Guardar rutas de archivos
        self.xml_path = xml_path
        self.srt_path = srt_path
        
        # Actualizar log
        self.add_log("\n✅ ¡Procesamiento completado!")
        self.add_log(f"📄 XML generado en: {xml_path}")
        self.add_log(f"📄 SRT generado en: {srt_path}")
        
        # Mostrar panel de resultados y conectar botones
        self.results_panel.show()
        self.xml_button.clicked.connect(lambda: self.open_file(xml_path))
        self.srt_button.clicked.connect(lambda: self.open_file(srt_path))
        self.audio_button.clicked.connect(lambda: self.open_file(self.audio_path))
        self.folder_button.clicked.connect(lambda: self.open_folder(os.path.dirname(xml_path)))
        
        self.status_bar.showMessage("Procesamiento completado")

    def processing_error(self, error_message):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        self.select_button.setEnabled(True)
        self.add_log(f"\n❌ Error: {error_message}")
        self.status_bar.showMessage("Error en el procesamiento")

    def add_log(self, message):
        self.log_area.append(f"{message}")
        self.log_area.verticalScrollBar().setValue(
            self.log_area.verticalScrollBar().maximum()
        )

    def load_whisper_model(self):
        """Carga el modelo Whisper en un hilo separado."""
        WhisperModelLoader.get_model()

    def on_model_loaded(self):
        """Se llama cuando el modelo ha terminado de cargar."""
        self.status_message.setText("")
        self.select_button.setEnabled(True)
        self.status_bar.showMessage("Listo para procesar")

    def create_action_button(self, text, icon):
        button = QPushButton(f"{icon} {text}")
        button.setStyleSheet("""
            QPushButton {
                padding: 10px 20px;
                background-color: #2b2b2b;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #3b3b3b;
            }
            QPushButton:disabled {
                background-color: #1e1e1e;
                color: #666666;
            }
        """)
        return button

    def open_file(self, path):
        if platform.system() == 'Darwin':  # macOS
            subprocess.run(['open', path])
        elif platform.system() == 'Windows':  # Windows
            os.startfile(path)
        else:  # Linux
            subprocess.run(['xdg-open', path])

    def open_folder(self, path):
        if platform.system() == 'Darwin':  # macOS
            subprocess.run(['open', path])
        elif platform.system() == 'Windows':  # Windows
            os.startfile(path)
        else:  # Linux
            subprocess.run(['xdg-open', path])

def main():
    app = QApplication(sys.argv)
    
    # Aplicar paleta oscura
    app.setPalette(DarkPalette())
    
    # Establecer el estilo global de la aplicación
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 