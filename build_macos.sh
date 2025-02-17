#!/bin/bash

# Configuración
APP_NAME="Sound to XML Converter"
DMG_NAME="Sound to XML Converter Installer"
VERSION="1.0.0"

# Crear el ejecutable
pyinstaller Sound_to_XML.spec

# Crear el DMG
create-dmg \
  --volname "$DMG_NAME" \
  --volicon "icon.icns" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "$APP_NAME.app" 200 190 \
  --hide-extension "$APP_NAME.app" \
  --app-drop-link 600 185 \
  --no-internet-enable \
  "dist/$DMG_NAME.dmg" \
  "dist/$APP_NAME.app" 