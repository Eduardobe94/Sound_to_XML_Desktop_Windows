@echo off
echo Limpiando builds anteriores...
rmdir /s /q build dist
del "Sound to XML Installer.exe" 2>nul

echo Creando directorios necesarios...
mkdir dist 2>nul

echo Copiando recursos...
copy /y ffmpeg\ffmpeg.exe dist\ 2>nul
copy /y ffmpeg\ffprobe.exe dist\ 2>nul
copy /y assets\icon.ico dist\ 2>nul

echo Construyendo la aplicación...
pyinstaller --noconsole ^
    --icon=assets\icon.ico ^
    --add-data "assets;assets" ^
    --name "Sound to XML Converter" ^
    Sound_to_XML.spec

echo Comprimiendo archivos binarios...
for /r "dist\Sound to XML Converter" %%i in (*.dll *.pyd) do (
    upx --best "%%i"
)

echo Creando instalador...
"C:\Program Files (x86)\NSIS\makensis.exe" installer.nsi

echo Limpiando archivos temporales...
rmdir /s /q build 