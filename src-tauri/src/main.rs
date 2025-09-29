#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Mutex;
use tauri::{Manager, State};

struct AppState {
    sidecar_handle: Mutex<Option<(tauri::async_runtime::Receiver<tauri::api::process::CommandEvent>, tauri::api::process::CommandChild)>>,
}

#[tauri::command]
async fn start_python_service(_state: State<'_, AppState>) -> Result<String, String> {
    #[cfg(debug_assertions)]
    {
        // 开发模式：检查Python服务是否在运行
        match reqwest::get("http://localhost:8001/").await {
            Ok(_) => Ok("Python service already running".to_string()),
            Err(_) => Ok("Please start Python service manually: python python-service/server.py".to_string())
        }
    }
    
    #[cfg(not(debug_assertions))]
    {
        use tauri::api::process::Command;
        
        let mut handle = _state.sidecar_handle.lock().unwrap();
        
        if handle.is_none() {
            match Command::new_sidecar("sense_voice_server")
                .expect("failed to create sidecar")
                .args(&["--host", "0.0.0.0", "--port", "8001"])
                .spawn()
            {
                Ok((receiver, child)) => {
                    *handle = Some((receiver, child));
                    std::thread::sleep(std::time::Duration::from_secs(5));
                    Ok("Python service started".to_string())
                }
                Err(e) => Err(format!("Failed to start service: {}", e))
            }
        } else {
            Ok("Service already running".to_string())
        }
    }
}

#[tauri::command]
async fn stop_python_service(state: State<'_, AppState>) -> Result<String, String> {
    let mut handle = state.sidecar_handle.lock().unwrap();
    
    if let Some((_, mut child)) = handle.take() {
        match child.kill() {
            Ok(_) => Ok("Python service stopped".to_string()),
            Err(e) => Err(format!("Failed to stop service: {}", e))
        }
    } else {
        Ok("Service not running".to_string())
    }
}

fn main() {
    tauri::Builder::default()
        .manage(AppState {
            sidecar_handle: Mutex::new(None),
        })
        .plugin(tauri_plugin_store::Builder::default().build())
        .setup(|app| {
            #[cfg(debug_assertions)] // 只在调试构建中包含此代码
            {
                let window = app.get_window("main").unwrap();
                window.open_devtools();
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            start_python_service, 
            stop_python_service
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}