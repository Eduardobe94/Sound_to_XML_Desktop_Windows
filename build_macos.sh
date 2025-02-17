#!/bin/bash

# Limpiar builds anteriores
sudo rm -rf build dist

# Eliminar DMG anterior si existe
sudo rm -f "Sound to XML Installer.dmg"
sudo rm -f "rw.*.Sound to XML Installer.dmg"

# Asegurar permisos
chmod +x ffmpeg/*

# Construir la aplicación
pyinstaller Sound_to_XML.spec

# Comprimir archivos grandes
echo "Comprimiendo archivos binarios..."
find "dist/Sound to XML Converter.app" -type f \( -name "*.so" -o -name "*.dylib" \) -exec upx --best {} \;

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
sudo rm -f "rw.*.Sound to XML Installer.dmg" 