use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::path::PathBuf;
use tauri::api::path::resource_dir;
use tauri::{Config, Env, PackageInfo};

pub struct ServerManager {
    process: Arc<Mutex<Option<Child>>>,
    server_path: PathBuf,
    models_path: PathBuf,
    config: ServerConfig,
}

#[derive(Debug, Clone)]
pub struct ServerConfig {
    pub host: String,
    pub port: u16,
    pub thread_num: u8,
    pub model_dir: String,
    pub vad_dir: String,
}

impl Default for ServerConfig {
    fn default() -> Self {
        Self {
            host: "127.0.0.1".to_string(),  // 只监听本地，提高安全性
            port: 10095,
            thread_num: 4,  // 降低线程数，适合桌面应用
            model_dir: "iic/SenseVoiceSmall".to_string(),  // 去掉 models/ 前缀
            vad_dir: "iic/speech_fsmn_vad_zh-cn-16k-common-onnx".to_string(),  // 去掉 models/ 前缀
        }
    }
}

impl ServerManager {
    pub fn new(package_info: &PackageInfo, config: &Config) -> Result<Self, String> {
        // 获取资源目录路径
        let resource_dir = resource_dir(package_info, &Env::default())
            .ok_or("无法获取资源目录")?;
        
        // 构建服务器可执行文件路径
        let server_path = if cfg!(target_os = "macos") {
            resource_dir.join("_up_").join("resources").join("bin").join("funasr-http-server")
        } else if cfg!(target_os = "windows") {
            resource_dir.join("_up_").join("resources").join("bin").join("funasr-http-server.exe")
        } else {
            resource_dir.join("_up_").join("resources").join("bin").join("funasr-http-server")
        };
        
        // 模型目录路径
        let models_path = resource_dir.join("_up_").join("resources").join("models");
        
        Ok(Self {
            process: Arc::new(Mutex::new(None)),
            server_path,
            models_path,
            config: ServerConfig::default(),
        })
    }
    
    pub fn update_config(&mut self, config: ServerConfig) {
        self.config = config;
    }
    
    pub fn start_server(&self) -> Result<String, String> {
        let mut process_guard = self.process.lock().unwrap();
        
        // 检查是否已经在运行
        if let Some(ref mut child) = *process_guard {
            if let Ok(None) = child.try_wait() {
                return Ok("服务器已在运行".to_string());
            }
        }
        
        // 检查服务器可执行文件是否存在
        if !self.server_path.exists() {
            return Err(format!("服务器可执行文件不存在: {:?}", self.server_path));
        }
        
        // 构建模型路径
        let model_dir = self.models_path.join(&self.config.model_dir);
        let vad_dir = self.models_path.join(&self.config.vad_dir);
        
        // 检查模型是否存在
        if !model_dir.exists() {
            return Err(format!("SenseVoice模型不存在: {:?}", model_dir));
        }
        
        println!("🚀 启动 FunASR HTTP 服务器...");
        println!("📂 服务器路径: {:?}", self.server_path);
        println!("📂 模型路径: {:?}", model_dir);
        println!("📂 VAD路径: {:?}", vad_dir);
        
        // 构建启动命令
        let mut cmd = Command::new(&self.server_path);
        cmd.arg("--model-dir").arg(&model_dir)
           .arg("--host").arg(&self.config.host)
           .arg("--port").arg(self.config.port.to_string())
           .arg("--thread-num").arg(self.config.thread_num.to_string())
           .stdout(Stdio::piped())
           .stderr(Stdio::piped());
        
        // 如果VAD模型存在，添加VAD参数
        if vad_dir.exists() {
            cmd.arg("--vad-dir").arg(&vad_dir);
            println!("✅ 启用VAD模型");
        } else {
            println!("⚠️  VAD模型不存在，跳过");
        }
        
        // 启动进程
        match cmd.spawn() {
            Ok(child) => {
                *process_guard = Some(child);
                let server_url = format!("http://{}:{}", self.config.host, self.config.port);
                println!("✅ 服务器启动成功: {}", server_url);
                Ok(format!("FunASR服务器已启动: {}", server_url))
            }
            Err(e) => {
                let error_msg = format!("启动服务器失败: {}", e);
                println!("❌ {}", error_msg);
                Err(error_msg)
            }
        }
    }
    
    pub fn stop_server(&self) -> Result<String, String> {
        let mut process_guard = self.process.lock().unwrap();
        
        if let Some(mut child) = process_guard.take() {
            match child.kill() {
                Ok(_) => {
                    let _ = child.wait(); // 等待进程完全结束
                    println!("✅ 服务器已停止");
                    Ok("服务器已停止".to_string())
                }
                Err(e) => {
                    let error_msg = format!("停止服务器失败: {}", e);
                    println!("❌ {}", error_msg);
                    Err(error_msg)
                }
            }
        } else {
            Ok("服务器未运行".to_string())
        }
    }
    
    pub fn is_running(&self) -> bool {
        let mut process_guard = self.process.lock().unwrap();
        
        if let Some(ref mut child) = *process_guard {
            match child.try_wait() {
                Ok(None) => true,  // 进程仍在运行
                Ok(Some(_)) => {
                    // 进程已结束，清理
                    *process_guard = None;
                    false
                }
                Err(_) => false,
            }
        } else {
            false
        }
    }
    
    pub fn restart_server(&self) -> Result<String, String> {
        println!("🔄 重启服务器...");
        
        // 先停止
        if self.is_running() {
            self.stop_server()?;
            
            // 等待一下确保完全停止
            std::thread::sleep(std::time::Duration::from_millis(1000));
        }
        
        // 再启动
        self.start_server()
    }
    
    pub fn get_server_status(&self) -> serde_json::Value {
        let is_running = self.is_running();
        let server_url = format!("http://{}:{}", self.config.host, self.config.port);
        
        serde_json::json!({
            "running": is_running,
            "server_url": server_url,
            "config": {
                "host": self.config.host,
                "port": self.config.port,
                "thread_num": self.config.thread_num,
                "model_dir": self.config.model_dir,
                "vad_dir": self.config.vad_dir
            }
        })
    }
}

// 确保进程在应用退出时被清理
impl Drop for ServerManager {
    fn drop(&mut self) {
        let _ = self.stop_server();
    }
}

unsafe impl Send for ServerManager {}
unsafe impl Sync for ServerManager {}