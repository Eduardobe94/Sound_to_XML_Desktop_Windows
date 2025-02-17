# -*- mode: python ; coding: utf-8 -*-
import os
import platform
import whisper

block_cipher = None

# Obtener la ruta del paquete whisper
whisper_path = os.path.dirname(whisper.__file__)

# Determinar los archivos de assets de Whisper
whisper_assets = [
    (os.path.join(whisper_path, 'assets', 'mel_filters.npz'), 'whisper/assets'),
    (os.path.join(whisper_path, 'assets', 'multilingual.tiktoken'), 'whisper/assets')
]

# Agregar información de dependencias del sistema
if platform.system() == 'Darwin':
    info_plist = {
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSHighResolutionCapable': 'True',
        'CFBundleIconFile': 'icon.icns',
        'CFBundleDisplayName': 'Sound to XML',
        'LSMinimumSystemVersion': '10.15',
        'LSEnvironment': {
            'PATH': '/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin'
        }
    }
else:
    info_plist = {}

a = Analysis(
    ['main_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('.env', '.'),
        *whisper_assets  # Incluir assets de Whisper
    ],
    hiddenimports=[
        'PyQt6.sip',
        'dotenv',
        'pydub',
        'whisper',
        'numpy',
        'torch'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Sound to XML Converter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Sound to XML Converter'
)

# Para macOS
app = BUNDLE(
    coll,
    name='Sound to XML Converter.app',
    icon='icon.icns',
    bundle_identifier='com.kubrickai.soundtoxml',
    info_plist=info_plist,
) 