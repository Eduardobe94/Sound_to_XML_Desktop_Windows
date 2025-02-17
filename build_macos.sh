#!/bin/bash

# Limpiar builds anteriores
rm -rf build dist
rm -f "Sound to XML Converter.dmg"

# Asegurar que FFmpeg está disponible
which ffmpeg || brew install ffmpeg

# Construir la aplicación
pyinstaller Sound_to_XML.spec

# Crear el icono para macOS si no existe
if [ ! -f "icon.icns" ]; then
    # Convertir .ico a .icns si es necesario
    sips -s format png assets/icon.ico --out icon.png
    mkdir icon.iconset
    sips -z 16 16   icon.png --out icon.iconset/icon_16x16.png
    sips -z 32 32   icon.png --out icon.iconset/icon_16x16@2x.png
    sips -z 32 32   icon.png --out icon.iconset/icon_32x32.png
    sips -z 64 64   icon.png --out icon.iconset/icon_32x32@2x.png
    sips -z 128 128 icon.png --out icon.iconset/icon_128x128.png
    sips -z 256 256 icon.png --out icon.iconset/icon_128x128@2x.png
    sips -z 256 256 icon.png --out icon.iconset/icon_256x256.png
    sips -z 512 512 icon.png --out icon.iconset/icon_256x256@2x.png
    sips -z 512 512 icon.png --out icon.iconset/icon_512x512.png
    sips -z 1024 1024 icon.png --out icon.iconset/icon_512x512@2x.png
    iconutil -c icns icon.iconset
    rm -rf icon.iconset icon.png
fi

# Limpiar archivos temporales
rm -rf build

# Crear el DMG
create-dmg \
  --volname "Sound to XML Installer" \
  --volicon "icon.icns" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "Sound to XML Converter.app" 175 190 \
  --hide-extension "Sound to XML Converter.app" \
  --app-drop-link 425 190 \
  "Sound to XML Installer.dmg" \
  "dist/Sound to XML Converter.app" || true

# Limpiar archivos temporales
rm -f "rw.*.Sound to XML Installer.dmg" 