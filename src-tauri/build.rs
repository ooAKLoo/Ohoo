fn main() {
    // macOS Info.plist权限设置
    #[cfg(target_os = "macos")]
    {
        println!("cargo:rustc-env=MACOSX_DEPLOYMENT_TARGET=10.13");
    }
    
    tauri_build::build()
}