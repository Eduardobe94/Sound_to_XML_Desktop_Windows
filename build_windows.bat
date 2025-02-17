@echo off
echo Limpiando builds anteriores...
rmdir /s /q build dist
del "Sound to XML Installer.exe" 2>nul

echo Asegurando permisos de FFmpeg...
copy /y ffmpeg\ffmpeg.exe dist\ 2>nul
copy /y ffmpeg\ffprobe.exe dist\ 2>nul

echo Construyendo la aplicación...
pyinstaller Sound_to_XML.spec

echo Comprimiendo archivos binarios...
for /r "dist\Sound to XML Converter" %%i in (*.dll *.pyd) do (
    upx --best "%%i"
)

echo Creando instalador...
"C:\Program Files (x86)\NSIS\makensis.exe" installer.nsi

echo Limpiando archivos temporales...
rmdir /s /q build 