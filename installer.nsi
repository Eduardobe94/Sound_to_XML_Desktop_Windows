!include "MUI2.nsh"
!include "FileFunc.nsh"

; Definir variables
Name "Sound to XML Converter"
OutFile "Sound to XML Installer.exe"
InstallDir "$PROGRAMFILES64\Sound to XML"
RequestExecutionLevel admin

; Interfaz moderna
!define MUI_ICON "icon.ico"
!define MUI_UNICON "icon.ico"
!define MUI_WELCOMEFINISHPAGE_BITMAP "installer_welcome.bmp"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "installer_header.bmp"
!define MUI_ABORTWARNING

; Páginas del instalador
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Páginas de desinstalación
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Idiomas
!insertmacro MUI_LANGUAGE "Spanish"

Section "Instalar"
    SetOutPath "$INSTDIR"
    
    ; Copiar archivos
    File /r "dist\Sound to XML Converter\*.*"
    
    ; Crear acceso directo en el menú de inicio
    CreateDirectory "$SMPROGRAMS\Sound to XML"
    CreateShortcut "$SMPROGRAMS\Sound to XML\Sound to XML Converter.lnk" "$INSTDIR\Sound to XML Converter.exe"
    CreateShortcut "$DESKTOP\Sound to XML Converter.lnk" "$INSTDIR\Sound to XML Converter.exe"
    
    ; Escribir información de desinstalación
    WriteUninstaller "$INSTDIR\uninstall.exe"
    
    ; Registrar desinstalador en Panel de Control
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\SoundToXML" \
                     "DisplayName" "Sound to XML Converter"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\SoundToXML" \
                     "UninstallString" "$\"$INSTDIR\uninstall.exe$\""
SectionEnd

Section "Uninstall"
    ; Eliminar archivos y carpetas
    RMDir /r "$INSTDIR"
    
    ; Eliminar accesos directos
    Delete "$SMPROGRAMS\Sound to XML\Sound to XML Converter.lnk"
    RMDir "$SMPROGRAMS\Sound to XML"
    Delete "$DESKTOP\Sound to XML Converter.lnk"
    
    ; Eliminar registro
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\SoundToXML"
SectionEnd 