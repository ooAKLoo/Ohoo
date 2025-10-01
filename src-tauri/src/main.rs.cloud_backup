#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Mutex;
use tauri::{Manager, State};
// 删除不需要的导入

mod audio_manager;
use audio_manager::AudioManager;

struct AppState {
    audio_manager: Mutex<AudioManager>,
}

#[tauri::command]
async fn start_python_service() -> Result<String, String> {
    // 远程服务模式，无需启动本地服务
    let remote_url = std::env::var("REMOTE_SERVICE_URL")
        .unwrap_or_else(|_| "http://115.190.136.178:8001".to_string());
    
    println!("使用远程语音识别服务: {}", remote_url);
    
    // 检查远程服务是否可用
    match reqwest::get(&remote_url).await {
        Ok(_) => Ok(format!("Remote service available at {}", remote_url)),
        Err(e) => Err(format!("Remote service not available: {}", e))
    }
}

#[tauri::command]
async fn stop_python_service() -> Result<String, String> {
    // 远程服务模式，无需停止本地服务
    Ok("Using remote service, no local service to stop".to_string())
}

#[tauri::command]
async fn start_audio_recording(state: State<'_, AppState>) -> Result<String, String> {
    let mut audio_manager = state.audio_manager.lock().unwrap();
    audio_manager.start_recording()?;
    Ok("Recording started".to_string())
}

#[tauri::command]
async fn stop_audio_recording(state: State<'_, AppState>) -> Result<serde_json::Value, String> {
    // 先获取音频数据，然后释放锁
    let wav_data = {
        let mut audio_manager = state.audio_manager.lock().unwrap();
        audio_manager.stop_recording()?
    };
    
    // 使用远程服务
    let service_url = std::env::var("REMOTE_SERVICE_URL")
        .unwrap_or_else(|_| "http://115.190.136.178:8001".to_string());
    
    println!("使用语音识别服务: {}", service_url);
    
    // 发送到服务进行转写
    let client = reqwest::Client::new();
    let form = reqwest::multipart::Form::new()
        .part("file", reqwest::multipart::Part::bytes(wav_data)
            .file_name("recording.wav")
            .mime_str("audio/wav").unwrap())
        .text("language", "auto")
        .text("use_itn", "true");
    
    let response = client
        .post(format!("{}/transcribe/normal", service_url))
        .multipart(form)
        .send()
        .await
        .map_err(|e| format!("发送转写请求失败: {}", e))?;
    
    if !response.status().is_success() {
        return Err(format!("转写服务返回错误: {}", response.status()));
    }
    
    let result: serde_json::Value = response
        .json()
        .await
        .map_err(|e| format!("解析转写结果失败: {}", e))?;
    
    Ok(result)
}

#[tauri::command]
async fn is_audio_recording(state: State<'_, AppState>) -> Result<bool, String> {
    let audio_manager = state.audio_manager.lock().unwrap();
    Ok(audio_manager.is_recording())
}

fn main() {
    // 初始化音频管理器
    let mut audio_manager = AudioManager::new().expect("创建音频管理器失败");
    audio_manager.initialize().expect("初始化音频系统失败");
    
    tauri::Builder::default()
        .manage(AppState {
            audio_manager: Mutex::new(audio_manager),
        })
        .plugin(tauri_plugin_store::Builder::default().build())
        .setup(|app| {
            let window = app.get_window("main").unwrap();
            
            // 移除窗口阴影
            #[cfg(any(windows, target_os = "macos"))]
            {
                use window_shadows::set_shadow;
                set_shadow(&window, false).expect("Unsupported platform!");
            }
            
            #[cfg(debug_assertions)] // 只在调试构建中包含此代码
            {
                window.open_devtools();
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            start_python_service, 
            stop_python_service,
            start_audio_recording,
            stop_audio_recording,
            is_audio_recording
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}