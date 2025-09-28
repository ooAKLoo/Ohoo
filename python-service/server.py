# server.py
import os
import gc
import sys
import time
import asyncio
import tempfile
import logging
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

# 强制刷新输出缓冲区
sys.stdout.reconfigure(line_buffering=True)

import torch
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="SenseVoice Streaming API")

# 添加CORS支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局模型变量和信号量
model = None
# 限制并发请求数量
SEMAPHORE = asyncio.Semaphore(3)  # 最多同时处理3个请求


def init_model():
    """初始化模型"""
    global model
    try:
        print("=" * 70, flush=True)
        print("🚀 开始初始化 SenseVoice 语音识别模型", flush=True)
        print("⚠️  首次运行需要下载模型文件（约1GB），请耐心等待...", flush=True)
        print("=" * 70, flush=True)
        
        # 检测设备
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        print(f"📱 使用设备: {device}", flush=True)

        # 设置缓存目录
        cache_dir = Path.home() / ".cache" / "modelscope"
        print(f"📂 模型缓存目录: {cache_dir}", flush=True)
        
        # 检查模型是否已下载
        model_path = cache_dir / "hub" / "iic" / "SenseVoiceSmall"
        if model_path.exists():
            print("✅ 检测到已下载的模型文件", flush=True)
        else:
            print("⬇️  开始下载模型文件，请保持网络连接...", flush=True)

        # 设置PyTorch性能优化
        if torch.cuda.is_available():
            torch.backends.cudnn.benchmark = True
            torch.cuda.empty_cache()

        # 初始化模型
        print("⏳ 正在加载模型到内存，请稍候...", flush=True)
        start_time = time.time()
        
        model = AutoModel(
            model="iic/SenseVoiceSmall",
            trust_remote_code=True,
            vad_model="fsmn-vad",
            vad_kwargs={
                "max_single_segment_time": 20000,  # 降低到20秒提高分段精度
                "max_single_segment_time_s": 20,   # 添加秒为单位的参数
                "speech_noise_threshold": 0.8,     # 添加语音噪声阈值
            },
            device=device,
            disable_update=True,
            ban_emo_unk=True,  # 保持情感识别能力
        )
        
        load_time = time.time() - start_time
        print(f"⏱️  模型加载完成！耗时: {load_time:.2f} 秒", flush=True)

        # 模型推理优化
        if hasattr(model.model, 'eval'):
            model.model.eval()
        
        print("=" * 70, flush=True)
        print("✅ 模型初始化成功！服务准备就绪", flush=True)
        print("🌐 API地址: http://localhost:8001", flush=True)
        print("=" * 70, flush=True)
        return True
    except Exception as e:
        print(f"❌ 模型初始化失败: {e}", flush=True)
        logger.error(f"Failed to initialize model: {e}")
        return False


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化模型"""
    if not init_model():
        logger.error("Failed to initialize model")


@app.get("/")
async def root():
    """健康检查"""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "device": "cuda" if torch.cuda.is_available() else "cpu"
    }


async def cleanup_temp_file(file_path: str):
    """异步清理临时文件"""
    await asyncio.sleep(1)  # 短暂延迟确保文件使用完毕
    try:
        os.unlink(file_path)
    except:
        pass

@app.post("/transcribe/normal")
async def transcribe_normal(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        language: Optional[str] = Form("auto"),
        use_itn: Optional[bool] = Form(True)
):
    """
    转录接口
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    # 文件大小限制
    file_size = 0
    contents = b""
    chunk_size = 8192
    max_size = 100 * 1024 * 1024  # 100MB
    
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        file_size += len(chunk)
        if file_size > max_size:
            raise HTTPException(status_code=413, detail="File too large")
        contents += chunk

    # 信号量限制并发
    async with SEMAPHORE:
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        # 添加后台任务清理文件
        background_tasks.add_task(cleanup_temp_file, tmp_path)

        try:
            # 使用torch.no_grad()减少内存占用
            with torch.no_grad():
                res = model.generate(
                    input=tmp_path,
                    cache={},
                    language=language,  # 使用原始语言参数
                    use_itn=use_itn,
                    batch_size_s=40,      # 保持优化的批处理大小
                    merge_vad=True,
                    merge_length_s=10,    # 保持优化的合并策略
                    ban_emo_unk=True,     # 保持情感标签优化
                )

            if res and len(res) > 0:
                text = rich_transcription_postprocess(res[0]["text"])
                
                # 主动清理GPU内存
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    
                return {
                    "text": text,
                    "filename": file.filename,
                    "language": language
                }
            else:
                raise HTTPException(status_code=500, detail="No transcription result")

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    print("\n" + "🎤" * 35 + "\n", flush=True)
    print("🚀 启动 Ohoo SenseVoice 语音识别服务...", flush=True)
    print(f"📅 启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("\n" + "🎤" * 35 + "\n", flush=True)
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8001,
        log_level="info",
        access_log=True
    )