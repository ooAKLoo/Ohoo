"""
打包Python服务为独立exe
运行: python build.py
"""
import PyInstaller.__main__
import sys

PyInstaller.__main__.run([
    'server.py',
    '--onefile',
    '--name=sense_voice_server',
    '--add-data=.;.',
    '--hidden-import=funasr',
    '--hidden-import=torch',
    '--distpath=../src-tauri/binaries',
    '--clean',
    '--noconfirm'
])