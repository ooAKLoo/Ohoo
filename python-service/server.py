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

# Nuitka/PyInstaller 补丁 - 必须放在 funasr 导入之前
if getattr(sys, 'frozen', False):
    # 创建缺失的 version.txt
    # 支持 Nuitka 和 PyInstaller 的不同路径
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 路径
        base_dir = sys._MEIPASS
    else:
        # Nuitka 路径（通常是可执行文件所在目录）
        base_dir = os.path.dirname(sys.executable)
    
    funasr_dir = os.path.join(base_dir, 'funasr')
    os.makedirs(funasr_dir, exist_ok=True)
    version_file = os.path.join(funasr_dir, 'version.txt')
    if not os.path.exists(version_file):
        with open(version_file, 'w') as f:
            f.write('1.2.7')
        print(f"✅ 创建 funasr version.txt: {version_file}", flush=True)

# 设置日志输出到文件（用于调试 Tauri sidecar）
def setup_logging():
    """设置日志输出到文件"""
    from datetime import datetime
    
    # 确定日志目录
    if getattr(sys, 'frozen', False):
        # 打包后的路径
        exe_dir = Path(sys.executable).parent
        if exe_dir.name == "MacOS":
            # macOS App 包结构，日志放在 App 同级目录
            log_dir = exe_dir.parent.parent.parent / "logs"
        else:
            log_dir = exe_dir / "logs"
    else:
        # 开发环境
        log_dir = Path(__file__).parent / "logs"
    
    # 创建日志目录
    log_dir.mkdir(exist_ok=True)
    
    # 日志文件名（带时间戳）
    log_file = log_dir / f"server_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # 重定向标准输出和错误
    class Logger:
        def __init__(self, filename):
            self.terminal = sys.stdout
            self.log = open(filename, "a", encoding='utf-8')
        
        def write(self, message):
            self.terminal.write(message)
            self.log.write(message)
            self.log.flush()  # 立即写入磁盘
        
        def flush(self):
            self.terminal.flush()
            self.log.flush()
        
        def isatty(self):
            return self.terminal.isatty()
        
        def fileno(self):
            return self.terminal.fileno()
    
    # 同时输出到控制台和文件
    sys.stdout = Logger(log_file)
    sys.stderr = Logger(log_file)
    
    print(f"📝 日志文件位置: {log_file}")
    print("=" * 70)
    
    return log_file

# 在打包环境下启用日志
if getattr(sys, 'frozen', False):
    setup_logging()

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from funasr_onnx import SenseVoiceSmall as ONNXSenseVoiceSmall
from funasr_onnx.utils.postprocess_utils import rich_transcription_postprocess

print("✅ ONNX 运行时加载成功", flush=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="SenseVoice ONNX API")

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

# ✅ 纯ONNX设备检测函数
def get_available_device():
    """检测可用设备（纯ONNX版本）"""
    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()
        
        if 'CUDAExecutionProvider' in providers:
            print("🚀 检测到CUDA支持", flush=True)
            return "cuda"
        elif 'CoreMLExecutionProvider' in providers:
            print("🍎 检测到CoreML支持", flush=True)
            return "coreml"
        else:
            print("💻 使用CPU", flush=True)
            return "cpu"
    except:
        print("💻 默认使用CPU", flush=True)
        return "cpu"


def get_model_path():
    """获取模型路径（支持PyInstaller打包和外部模型文件夹）"""
    
    # 1. 优先检查外部模型文件夹（与可执行文件同级）
    if getattr(sys, 'frozen', False):
        # 打包后的路径：可执行文件所在目录
        exe_dir = Path(sys.executable).parent
        # 对于macOS .app，需要向上找到Contents目录的父目录
        if exe_dir.name == "MacOS" and exe_dir.parent.name == "Contents":
            # 从 .app/Contents/MacOS 向上到 .app 的同级目录
            app_parent = exe_dir.parent.parent.parent
            external_models_path = app_parent / "models"
            if external_models_path.exists():
                print(f"✅ 使用外部模型文件夹: {external_models_path}", flush=True)
                return external_models_path
        
        # 常规路径（Windows/Linux 或直接运行）
        external_models_path = exe_dir / "models"
        if external_models_path.exists():
            print(f"✅ 使用外部模型文件夹: {external_models_path}", flush=True)
            return external_models_path
    else:
        # 开发环境：检查项目根目录的外部models文件夹
        project_root = Path(__file__).parent.parent
        external_models_path = project_root / "models"
        if external_models_path.exists():
            print(f"✅ 使用外部模型文件夹: {external_models_path}", flush=True)
            return external_models_path
    
    # 2. 检查打包内置的模型（如果有的话）
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
        models_path = base_path / "models"
        if models_path.exists():
            print(f"✅ 使用内置模型文件夹: {models_path}", flush=True)
            return models_path
    
    # 3. 开发环境路径
    current_dir = Path(__file__).parent
    models_path = current_dir / "models"
    if models_path.exists():
        print(f"✅ 使用开发环境模型文件夹: {models_path}", flush=True)
        return models_path
    
    # 4. 回退到默认缓存目录（自动下载）
    print("⚠️  未找到本地模型文件夹，将使用在线模型", flush=True)
    return None

def init_model():
    """初始化模型"""
    global model
    try:
        print("=" * 70, flush=True)
        print("🚀 开始初始化 SenseVoice 语音识别模型", flush=True)
        
        # ✅ 使用纯ONNX设备检测
        device = get_available_device()
        print(f"📱 使用设备: {device}", flush=True)

        # 获取模型路径
        models_path = get_model_path()
        
        if not models_path:
            print("❌ 未找到模型文件夹，请确保models目录存在", flush=True)
            return False

        print(f"📂 使用本地ONNX模型: {models_path}", flush=True)
        print("=" * 70, flush=True)

        # 初始化模型
        print("⏳ 正在加载模型到内存，请稍候...", flush=True)
        start_time = time.time()
        
        # 添加详细的错误追踪
        import traceback
        import sys
        
        try:
            # 只使用 ONNX 模型
            print("🚀 使用 ONNX 加速模型", flush=True)
            
            # 检查ONNX模型路径（嵌套目录）
            onnx_model_path = models_path / "models" / "iic" / "SenseVoiceSmall"
            if not onnx_model_path.exists():
                # 尝试非嵌套路径
                onnx_model_path = models_path / "iic" / "SenseVoiceSmall"
            
            if not onnx_model_path.exists():
                print(f"❌ ONNX模型目录不存在: {onnx_model_path}", flush=True)
                return False
                
            onnx_quant_path = onnx_model_path / "model_quant.onnx"
            onnx_path = onnx_model_path / "model.onnx"
            
            # ONNX模型会自动处理ITN，无需额外配置文件
            
            # 设备已在上面检测过了
            print(f"📱 使用设备: {device}", flush=True)
            
            if onnx_quant_path.exists():
                print(f"🔥 使用量化ONNX模型（最快）", flush=True)
                model = ONNXSenseVoiceSmall(
                    str(onnx_model_path),
                    batch_size=1,
                    quantize=False,
                    device=device,
                    intra_op_num_threads=8  # 限制线程数，防止CPU过载
                )
            elif onnx_path.exists():
                print(f"⚡ 使用标准ONNX模型", flush=True)
                model = ONNXSenseVoiceSmall(
                    str(onnx_model_path),
                    batch_size=1,
                    quantize=False,  # 启用量化以优化性能
                    device=device,
                    intra_op_num_threads=8  # 限制线程数，防止CPU过
                )
            else:
                print(f"❌ 未找到ONNX模型文件 (model.onnx 或 model_quant.onnx)", flush=True)
                return False
            
            print("✅ ONNX模型加载完成", flush=True)
            
            load_time = time.time() - start_time
            print(f"⏱️  模型加载完成！耗时: {load_time:.2f} 秒", flush=True)
            
        except Exception as e:
            print(f"❌ ONNX模型加载失败: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return False
        
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
        "model_type": "ONNX",
        "device": get_available_device()
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
            # 使用ONNX模型推理
            print("🚀 使用ONNX快速推理", flush=True)
            res = model(
                [tmp_path],  # ONNX模型需要列表格式
                language=language if language != "auto" else "auto",
                textnorm="withitn" if use_itn else "woitn"  # ONNX使用textnorm参数
            )
            
            if res and len(res) > 0:
                # ONNX版本直接返回处理后的文本字符串
                raw_text = res[0] if isinstance(res[0], str) else str(res[0])
                
                # 使用ONNX版本的后处理函数（已经包含ITN处理）
                text = rich_transcription_postprocess(raw_text)
                
                print(f"📝 ONNX识别结果: {text}", flush=True)
                
                return {
                    "text": text,
                    "filename": file.filename,
                    "language": language
                }
            else:
                raise HTTPException(status_code=500, detail="ONNX推理无结果")

        except FileNotFoundError as e:
            logger.error(f"📁 临时文件未找到: {tmp_path}, 错误: {e}")
            raise HTTPException(status_code=500, detail="文件处理错误")
        except ImportError as e:
            logger.error(f"📦 模型依赖缺失: {e}")
            raise HTTPException(status_code=503, detail="模型依赖错误")
        except Exception as e:
            import traceback
            logger.error(f"❌ 转录失败详情:")
            logger.error(f"   📄 文件名: {file.filename}")
            logger.error(f"   📊 文件大小: {file_size} bytes")
            logger.error(f"   🌐 语言: {language}, 使用ITN: {use_itn}")
            logger.error(f"   🏷️  错误类型: {type(e).__name__}")
            logger.error(f"   💬 错误信息: {str(e)}")
            logger.error(f"   📚 完整堆栈:")
            for line in traceback.format_exc().split('\n'):
                if line.strip():
                    logger.error(f"     {line}")
            raise HTTPException(status_code=500, detail=f"转录失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    from datetime import datetime
    
    print("\n" + "🎤" * 35 + "\n", flush=True)
    print("🚀 启动 Ohoo SenseVoice 语音识别服务...", flush=True)
    print(f"📅 启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("\n" + "🎤" * 35 + "\n", flush=True)
    
    # 调试信息
    print(f"🐍 Python版本: {sys.version}", flush=True)
    print(f"📁 工作目录: {os.getcwd()}", flush=True)
    print(f"🚀 可执行文件: {sys.executable}", flush=True)
    print(f"📦 是否打包: {getattr(sys, 'frozen', False)}", flush=True)
    print(f"💾 设备: {get_available_device()}", flush=True)
    
    # 模型路径调试
    model_path = get_model_path()
    print(f"📂 模型路径: {model_path}", flush=True)
    
    print("=" * 70, flush=True)
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=1758,
        log_level="info",
        access_log=True
    )