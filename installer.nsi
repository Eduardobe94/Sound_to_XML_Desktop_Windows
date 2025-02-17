!define APPNAME "Sound to XML Converter"
!define COMPANYNAME "Sound to XML"
!define DESCRIPTION "Conversor de audio a XML y SRT"
!define VERSIONMAJOR 1
!define VERSIONMINOR 0
!define VERSIONBUILD 0

# Configuración básica
SetCompressor lzma
Name "${APPNAME}"
OutFile "Sound to XML Converter Setup.exe"
InstallDir "$PROGRAMFILES64\${COMPANYNAME}\${APPNAME}"
InstallDirRegKey HKCU "Software\${COMPANYNAME}\${APPNAME}" ""

# Solicitar privilegios de administrador
RequestExecutionLevel admin

# Páginas del instalador
!include "MUI2.nsh"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Spanish"

Section "Instalar"
    SetOutPath $INSTDIR
    
    # Archivos principales
    File /r "dist\Sound to XML Converter\*.*"
    
    # Crear acceso directo en el menú inicio
    CreateDirectory "$SMPROGRAMS\${COMPANYNAME}"
    CreateShortCut "$SMPROGRAMS\${COMPANYNAME}\${APPNAME}.lnk" "$INSTDIR\Sound to XML Converter.exe"
    CreateShortCut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\Sound to XML Converter.exe"
    
    # Registro de desinstalación
    WriteUninstaller "$INSTDIR\uninstall.exe"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${COMPANYNAME} ${APPNAME}" \
                     "DisplayName" "${APPNAME}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${COMPANYNAME} ${APPNAME}" \
                     "UninstallString" "$\"$INSTDIR\uninstall.exe$\""
SectionEnd

Section "Uninstall"
    # Eliminar archivos y carpetas
    RMDir /r "$INSTDIR"
    
    # Eliminar accesos directos
    Delete "$SMPROGRAMS\${COMPANYNAME}\${APPNAME}.lnk"
    RMDir "$SMPROGRAMS\${COMPANYNAME}"
    Delete "$DESKTOP\${APPNAME}.lnk"
    
    # Eliminar registro
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${COMPANYNAME} ${APPNAME}"
SectionEnd 