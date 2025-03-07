@echo off
echo Limpiando builds anteriores...
rmdir /s /q build dist
del "Sound to XML Installer.exe" 2>nul

echo Creando directorios necesarios...
mkdir dist 2>nul
mkdir dist\assets 2>nul
mkdir dist\ffmpeg 2>nul

echo Instalando dependencias...
pip install --upgrade pip
pip install PyQt6==6.4.0
pip install PyQt6-sip==13.4.0
pip install PyQt6-Qt6==6.4.0
pip install openai-whisper==1.0.0

echo Localizando archivos de Whisper...
for /f "tokens=*" %%i in ('python -c "import whisper; import os; print(os.path.dirname(whisper.__file__))"') do set WHISPER_PATH=%%i
echo Whisper path: %WHISPER_PATH%

echo Verificando archivos necesarios...
if not exist "assets\icon.ico" (
    echo Error: Falta icon.ico
    exit /b 1
)
if not exist "ffmpeg\ffmpeg.exe" (
    echo Error: Falta ffmpeg.exe
    exit /b 1
)
if not exist "main_gui.py" (
    echo Error: No se encuentra main_gui.py
    exit /b 1
)

echo Copiando recursos...
xcopy /y /e /i assets dist\assets
xcopy /y /e /i ffmpeg dist\ffmpeg
xcopy /y /e /i "%WHISPER_PATH%\assets" "dist\whisper_assets"

echo Construyendo la aplicación...
python -m PyInstaller --clean ^
    --noconsole ^
    --icon="assets\icon.ico" ^
    --add-data="assets;assets" ^
    --add-data="ffmpeg;ffmpeg" ^
    --add-data="%WHISPER_PATH%\assets;whisper\assets" ^
    --hidden-import=PyQt6 ^
    --hidden-import=PyQt6.QtCore ^
    --hidden-import=PyQt6.QtGui ^
    --hidden-import=PyQt6.QtWidgets ^
    --hidden-import=PyQt6.sip ^
    --hidden-import=pydub ^
    --hidden-import=openai-whisper ^
    --hidden-import=numpy ^
    --hidden-import=soundfile ^
    --collect-all whisper ^
    --collect-all PyQt6 ^
    --name="Sound to XML Converter" ^
    main_gui.py

if errorlevel 1 (
    echo Error al construir el ejecutable
    exit /b 1
)

echo Verificando archivos generados...
if not exist "dist\Sound to XML Converter\Sound to XML Converter.exe" (
    echo Error: No se generó el ejecutable correctamente
    exit /b 1
)

echo Creando instalador...
"C:\Program Files (x86)\NSIS\makensis.exe" installer.nsi

if exist "Sound to XML Installer.exe" (
    echo Instalador creado exitosamente: "Sound to XML Installer.exe"
) else (
    echo Error: No se pudo crear el instalador
    exit /b 1
) 