# server.py - Paraformer版本
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

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Paraformer Speech Recognition API")

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
SEMAPHORE = asyncio.Semaphore(3)


def init_model():
    """初始化Paraformer模型"""
    global model
    try:
        print("=" * 70, flush=True)
        print("🚀 开始初始化 Paraformer 语音识别模型", flush=True)
        print("📢 Paraformer特点：中文识别准确率高，支持热词功能", flush=True)
        print("⚠️  首次运行需要下载模型文件，请耐心等待...", flush=True)
        print("=" * 70, flush=True)
        
        # 检测设备
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        print(f"📱 使用设备: {device}", flush=True)

        # 设置缓存目录
        cache_dir = Path.home() / ".cache" / "modelscope"
        print(f"📂 模型缓存目录: {cache_dir}", flush=True)
        
        # 检查模型是否已下载
        model_path = cache_dir / "hub" / "damo" / "speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
        if model_path.exists():
            print("✅ 检测到已下载的Paraformer模型文件", flush=True)
        else:
            print("⬇️  开始下载Paraformer模型文件，请保持网络连接...", flush=True)

        # 设置PyTorch性能优化
        if torch.cuda.is_available():
            torch.backends.cudnn.benchmark = True
            torch.cuda.empty_cache()

        # 初始化Paraformer模型
        print("⏳ 正在加载Paraformer模型到内存，请稍候...", flush=True)
        start_time = time.time()
        
        # Paraformer模型配置
        model = AutoModel(
            model="paraformer-zh",  # 使用中文Paraformer模型
            vad_model="fsmn-vad",   # VAD模型用于长音频切割
            punc_model="ct-punc",    # 标点恢复模型（可选）
            # spk_model="cam++",     # 说话人分离模型（可选，根据需要开启）
            vad_kwargs={
                "max_single_segment_time": 30000,  # VAD最大切割时长30秒
                "speech_noise_threshold": 0.8,     # 语音噪声阈值
            },
            device=device,
            disable_update=True,
            ncpu=4,  # CPU线程数
        )
        
        load_time = time.time() - start_time
        print(f"⏱️  Paraformer模型加载完成！耗时: {load_time:.2f} 秒", flush=True)

        # 模型推理优化
        if hasattr(model, 'model') and hasattr(model.model, 'eval'):
            model.model.eval()
        
        print("=" * 70, flush=True)
        print("✅ Paraformer模型初始化成功！服务准备就绪", flush=True)
        print("🌐 API地址: http://localhost:8001", flush=True)
        print("💡 提示：Paraformer对中文识别效果最佳", flush=True)
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
        logger.error("Failed to initialize Paraformer model")


@app.get("/")
async def root():
    """健康检查"""
    return {
        "status": "healthy",
        "model": "Paraformer-zh",
        "model_loaded": model is not None,
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "features": ["热词支持", "中文优化", "标点恢复", "VAD切割"]
    }


async def cleanup_temp_file(file_path: str):
    """异步清理临时文件"""
    await asyncio.sleep(1)
    try:
        os.unlink(file_path)
    except:
        pass


# 常用热词配置
DEFAULT_HOTWORDS = {
    "tech": "微信 支付宝 淘宝 ChatGPT OpenAI API Python JavaScript",
    "general": "的 了 吗 啊 呢 吧",  # 常用语气词
    "business": "会议 报告 项目 客户 产品 市场",
}


def post_process_text(text):
    """后处理：修正常见错误"""
    # 定义常见错误映射
    corrections = {
        # 品牌/产品名
        'we chat': 'WeChat',
        '微 信': '微信',
        'chat gpt': 'ChatGPT',
        'chat GPT': 'ChatGPT',
        
        # 常见中英混合
        'APP': 'App',
        'iphone': 'iPhone',
        'ipad': 'iPad',
        
        # 语音识别常见错误
        '的话': '的话',  # 防止被分开
        '那么': '那么',
    }
    
    for wrong, correct in corrections.items():
        text = text.replace(wrong, correct)
    
    # 清理多余空格
    text = ' '.join(text.split())
    
    return text


@app.post("/transcribe/normal")
async def transcribe_normal(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        language: Optional[str] = Form("auto"),
        use_itn: Optional[bool] = Form(True),
        scenario: Optional[str] = Form("mixed"),  # 场景参数
        hotwords: Optional[str] = Form("")  # 热词参数
):
    """
    转录接口 - Paraformer版本
    支持热词功能，中文识别效果更好
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
            # 准备热词
            final_hotwords = hotwords
            if not final_hotwords and scenario in ["mixed", "chinese"]:
                # 如果没有自定义热词，使用默认热词
                final_hotwords = DEFAULT_HOTWORDS.get("tech", "")
            
            print(f"🔥 使用热词: {final_hotwords[:50]}..." if final_hotwords else "未使用热词", flush=True)
            
            # 使用torch.no_grad()减少内存占用
            with torch.no_grad():
                res = model.generate(
                    input=tmp_path,
                    batch_size_s=300,  # Paraformer可以处理更长的批次
                    batch_size_threshold_s=60,  # 超过60秒的音频单独处理
                    hotword=final_hotwords,  # 应用热词
                    # Paraformer特有的参数
                    decoding_ctc_weight=0.0,  # CTC权重，0表示只用attention
                    beam_size=10,  # beam search大小
                )

            if res and len(res) > 0:
                # 提取文本结果
                text = res[0].get('text', '') if isinstance(res[0], dict) else str(res[0])
                
                # 后处理优化
                text = post_process_text(text)
                
                # 主动清理GPU内存
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                # 日志记录识别结果长度
                logger.info(f"识别完成，文本长度: {len(text)} 字符")
                    
                return {
                    "text": text,
                    "filename": file.filename,
                    "model": "Paraformer",
                    "hotwords_used": bool(final_hotwords),
                    "language": "zh"  # Paraformer主要用于中文
                }
            else:
                raise HTTPException(status_code=500, detail="No transcription result")

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


# 新增：流式识别接口（可选）
@app.post("/transcribe/streaming")
async def transcribe_streaming(
        file: UploadFile = File(...),
        chunk_size: str = Form("0,10,5"),  # 流式配置
        hotwords: Optional[str] = Form("")
):
    """
    流式识别接口（实验性功能）
    使用paraformer-zh-streaming模型
    """
    # 这里可以添加流式识别的实现
    # 需要使用 paraformer-zh-streaming 模型
    return {"message": "Streaming API is experimental", "status": "not_implemented"}


if __name__ == "__main__":
    import uvicorn
    print("\n" + "🎤" * 35 + "\n", flush=True)
    print("🚀 启动 Ohoo Paraformer 语音识别服务...", flush=True)
    print("📝 Paraformer版本：专注中文识别，支持热词功能", flush=True)
    print(f"📅 启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("\n" + "🎤" * 35 + "\n", flush=True)
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8001,
        log_level="info",
        access_log=True
    )