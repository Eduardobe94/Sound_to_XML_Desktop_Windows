# -*- mode: python ; coding: utf-8 -*-
import os
import platform
import whisper

block_cipher = None

# Obtener la ruta del paquete whisper
whisper_path = os.path.dirname(whisper.__file__)

# Solo incluir los assets necesarios de Whisper
whisper_assets = [
    (os.path.join(whisper_path, 'assets', 'mel_filters.npz'), 'whisper/assets'),
    (os.path.join(whisper_path, 'assets', 'multilingual.tiktoken'), 'whisper/assets')
]

# Excluir módulos innecesarios
excludes = [
    'matplotlib', 'tkinter', 'wx', 'PyQt4', 'PyQt5', 'IPython',
    'notebook', 'PIL', 'pandas', 'scipy', 'sklearn', 'cvxopt',
    'sympy', 'sphinx', 'flask', 'django', 'selenium', 'tensorflow',
    'keras', 'theano', 'opencv', 'qt5', 'PySide2', 'wx', 'gi'
]

# Incluir solo los hiddenimports necesarios
hiddenimports = [
    'PyQt6.sip',
    'dotenv',
    'pydub',
    'whisper',
    'numpy',
    'torch'
]

a = Analysis(
    ['main_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('.env', '.'),
        *whisper_assets
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Eliminar archivos innecesarios de torch
torch_excludes = [
    'torch/include',
    'torch/lib/cmake',
    'torch/lib/tmp_install',
    'torch/lib/*.a',
    'torch/lib/*.pdb',
    'torch/test',
    'torch/distributions',
    'torch/testing',
    'torch/legacy'
]

for exclude in torch_excludes:
    a.datas = [x for x in a.datas if not x[0].startswith(exclude)]

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
    info_plist={
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSHighResolutionCapable': 'True',
        'CFBundleIconFile': 'icon.icns',
        'CFBundleDisplayName': 'Sound to XML',
        'LSMinimumSystemVersion': '10.15',
        'LSEnvironment': {
            'PATH': '/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin'
        }
    },
) 