#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright FunASR (https://github.com/FunAudioLLM/SenseVoice). All Rights Reserved.
#  MIT License  (https://opensource.org/licenses/MIT)

from pathlib import Path
from funasr_onnx import SenseVoiceSmall
from funasr_onnx.utils.postprocess_utils import rich_transcription_postprocess
import warnings
warnings.filterwarnings("ignore", message="pkg_resources is deprecated")

model_dir = "iic/SenseVoiceSmall"

model = SenseVoiceSmall(model_dir, batch_size=10, quantize=True)

# inference
wav_or_scp = ["/Users/yangdongju/Downloads/录音记录_20250928_0006.wav"]

res = model(wav_or_scp, language="auto", textnorm="withitn")
print([rich_transcription_postprocess(i) for i in res])