fn main() {
    // macOS Info.plist权限设置
    #[cfg(target_os = "macos")]
    {
        println!("cargo:rustc-env=MACOSX_DEPLOYMENT_TARGET=10.13");
        
        // 确保二进制文件有执行权限
        use std::process::Command;
        let _ = Command::new("chmod")
            .args(&["+x", "../resources/bin/funasr-http-server"])
            .status();
    }
    
    // 自动复制资源文件到构建目录
    println!("cargo:rerun-if-changed=../resources");
    
    tauri_build::build()
}