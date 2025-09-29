# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

# 收集 funasr 的所有组件
funasr_datas = []
funasr_binaries = []
funasr_hiddenimports = []

# 收集 funasr 的所有内容
tmp_ret = collect_all('funasr')
funasr_datas += tmp_ret[0]
funasr_binaries += tmp_ret[1]
funasr_hiddenimports += tmp_ret[2]

# 收集 modelscope 相关内容（funasr 依赖）
tmp_ret = collect_all('modelscope')
funasr_datas += tmp_ret[0]
funasr_binaries += tmp_ret[1]
funasr_hiddenimports += tmp_ret[2]

# 手动添加可能遗漏的模块
additional_hiddenimports = [
    'funasr.models',
    'funasr.models.sense_voice',
    'funasr.models.sense_voice.model',
    'funasr.models.emotion2vec',
    'funasr.models.campplus',
    'funasr.models.fsmn_vad',
    'funasr.models.fsmn_vad_streaming',
    'funasr.models.ct_transformer',
    'funasr.models.ct_transformer_streaming',
    'funasr.models.paraformer',
    'funasr.auto',
    'funasr.auto.auto_model',
    'funasr.utils',
    'funasr.utils.postprocess_utils',
    'funasr.train_utils',
    'funasr.metrics',
    'funasr.frontends',
    'funasr.layers',
    'torch._inductor.codecache',
    'torchaudio',
    'soundfile',
    'librosa',
    'numba',
    'llvmlite',
]

a = Analysis(
    ['server.py'],
    pathex=[],
    binaries=funasr_binaries,
    datas=funasr_datas,
    hiddenimports=funasr_hiddenimports + additional_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['sklearn', 'matplotlib', 'PIL'],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='sense_voice_server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)