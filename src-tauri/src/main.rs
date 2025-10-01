#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Mutex;
use tauri::{Manager, State};
use regex::Regex;

mod audio_manager;
use audio_manager::AudioManager;

struct AppState {
    audio_manager: Mutex<AudioManager>,
}

// 清理转写结果中的标识符号
fn clean_transcription_text(text: &str) -> String {
    // 创建正则表达式模式，匹配类似 <|zh|><|NEUTRAL|><|Speech|> 的标签
    let patterns = [
        r"<\|[^|]+\|>",           // 匹配 <|任何内容|>
        r"<\|zh\|>",              // 匹配语言标识
        r"<\|NEUTRAL\|>",         // 匹配情感标识
        r"<\|Speech\|>",          // 匹配语音类型标识
        r"<\|en\|>",              // 英文标识
        r"<\|HAPPY\|>",           // 其他情感标识
        r"<\|SAD\|>",
        r"<\|ANGRY\|>",
        r"<\|CALM\|>",
    ];
    
    let mut cleaned_text = text.to_string();
    
    // 应用所有正则表达式模式
    for pattern in &patterns {
        if let Ok(re) = Regex::new(pattern) {
            cleaned_text = re.replace_all(&cleaned_text, "").to_string();
        }
    }
    
    // 清理多余的空格和标点
    cleaned_text = cleaned_text.trim().to_string();
    
    // 移除连续的空格
    if let Ok(space_re) = Regex::new(r"\s+") {
        cleaned_text = space_re.replace_all(&cleaned_text, " ").to_string();
    }
    
    cleaned_text
}

#[tauri::command]
async fn start_python_service() -> Result<String, String> {
    // 本地服务模式，检查本地C++ FunASR服务
    let local_url = std::env::var("LOCAL_SERVICE_URL")
        .unwrap_or_else(|_| "http://localhost:10095".to_string());
    
    println!("使用本地FunASR语音识别服务: {}", local_url);
    
    // 检查本地服务是否可用
    let client = reqwest::Client::new();
    let test_form = reqwest::multipart::Form::new()
        .part("file", reqwest::multipart::Part::bytes(vec![])
            .file_name("test.wav")
            .mime_str("audio/wav").unwrap());
    
    match client
        .post(format!("{}/transcribe/normal", local_url))
        .multipart(test_form)
        .send()
        .await
    {
        Ok(_) => Ok(format!("Local FunASR service available at {}", local_url)),
        Err(e) => Err(format!("Local FunASR service not available: {}. Please start the server with ./run_http_server.sh", e))
    }
}

#[tauri::command]
async fn stop_python_service() -> Result<String, String> {
    // 本地服务模式，提醒手动停止本地服务
    Ok("Local FunASR service running independently. Stop manually if needed.".to_string())
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
    let pcm_data = {
        let mut audio_manager = state.audio_manager.lock().unwrap();
        audio_manager.stop_recording()?
    };
    
    // 使用本地FunASR服务
    let service_url = std::env::var("LOCAL_SERVICE_URL")
        .unwrap_or_else(|_| "http://localhost:10095".to_string());
    
    println!("使用本地FunASR语音识别服务: {}", service_url);
    
    // 发送到本地FunASR服务进行转写（multipart form格式，直接发送PCM数据）
    let client = reqwest::Client::new();
    let form = reqwest::multipart::Form::new()
        .part("file", reqwest::multipart::Part::bytes(pcm_data)
            .file_name("recording.pcm")
            .mime_str("audio/pcm").unwrap())
        .text("wav_format", "pcm")  // 明确指定PCM格式
        .text("itn", "true")
        .text("audio_fs", "16000")
        .text("svs_lang", "auto")
        .text("svs_itn", "true");
    
    let response = client
        .post(format!("{}/transcribe/normal", service_url))
        .multipart(form)
        .send()
        .await
        .map_err(|e| format!("发送转写请求失败: {}", e))?;
    
    if !response.status().is_success() {
        return Err(format!("转写服务返回错误: {}", response.status()));
    }
    
    let mut result: serde_json::Value = response
        .json()
        .await
        .map_err(|e| format!("解析转写结果失败: {}", e))?;
    
    // 清理转写结果中的标识符号
    if let Some(text) = result.get("text").and_then(|t| t.as_str()) {
        let original_text = text.to_string();
        let cleaned_text = clean_transcription_text(&original_text);
        result["text"] = serde_json::Value::String(cleaned_text.clone());
        println!("原始转写结果: {}", original_text);
        println!("清理后结果: {}", cleaned_text);
    }
    
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