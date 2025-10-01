use std::sync::{Arc, Mutex};
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use rubato::{SincFixedIn, Resampler, SincInterpolationParameters, SincInterpolationType, WindowFunction};

pub struct AudioManager {
    stream: Option<cpal::Stream>,
    is_recording: Arc<Mutex<bool>>,
    audio_buffer: Arc<Mutex<Vec<f32>>>,
    actual_sample_rate: u32,  // 实际使用的采样率
}

impl AudioManager {
    pub fn new() -> Result<Self, String> {
        Ok(Self {
            stream: None,
            is_recording: Arc::new(Mutex::new(false)),
            audio_buffer: Arc::new(Mutex::new(Vec::new())),
            actual_sample_rate: 48000,  // 默认值，将被实际值覆盖
        })
    }
    
    pub fn initialize(&mut self) -> Result<(), String> {
        let host = cpal::default_host();
        let device = host.default_input_device()
            .ok_or("未找到音频输入设备")?;
        
        // 获取设备默认配置（使用设备支持的配置）
        let default_config = device.default_input_config()
            .map_err(|e| format!("获取音频配置失败: {}", e))?;
        
        // 记录实际的采样率
        self.actual_sample_rate = default_config.sample_rate().0;
        println!("设备默认采样率: {}Hz", self.actual_sample_rate);
        
        // 使用设备的默认配置
        let config: cpal::StreamConfig = default_config.config();
        
        let is_recording = self.is_recording.clone();
        let buffer = self.audio_buffer.clone();
        let channels = config.channels as usize;
        
        // 根据实际的采样格式创建流
        let stream = match default_config.sample_format() {
            cpal::SampleFormat::I16 => {
                let buffer_clone = buffer.clone();
                let is_recording_clone = is_recording.clone();
                device.build_input_stream(
                    &config,
                    move |data: &[i16], _: &cpal::InputCallbackInfo| {
                        if *is_recording_clone.lock().unwrap() {
                            let mut audio_buffer = buffer_clone.lock().unwrap();
                            // 如果是多声道，只取第一个声道
                            for chunk in data.chunks(channels) {
                                if let Some(&sample) = chunk.first() {
                                    let normalized = sample as f32 / i16::MAX as f32;
                                    audio_buffer.push(normalized);
                                }
                            }
                        }
                    },
                    |err| eprintln!("音频流错误: {}", err),
                    None
                )
            },
            cpal::SampleFormat::U16 => {
                let buffer_clone = buffer.clone();
                let is_recording_clone = is_recording.clone();
                device.build_input_stream(
                    &config,
                    move |data: &[u16], _: &cpal::InputCallbackInfo| {
                        if *is_recording_clone.lock().unwrap() {
                            let mut audio_buffer = buffer_clone.lock().unwrap();
                            for chunk in data.chunks(channels) {
                                if let Some(&sample) = chunk.first() {
                                    let normalized = (sample as f32 - 32768.0) / 32768.0;
                                    audio_buffer.push(normalized);
                                }
                            }
                        }
                    },
                    |err| eprintln!("音频流错误: {}", err),
                    None
                )
            },
            cpal::SampleFormat::F32 => {
                let buffer_clone = buffer.clone();
                let is_recording_clone = is_recording.clone();
                device.build_input_stream(
                    &config,
                    move |data: &[f32], _: &cpal::InputCallbackInfo| {
                        if *is_recording_clone.lock().unwrap() {
                            let mut audio_buffer = buffer_clone.lock().unwrap();
                            // 如果是多声道，只取第一个声道
                            for chunk in data.chunks(channels) {
                                if let Some(&sample) = chunk.first() {
                                    audio_buffer.push(sample);
                                }
                            }
                        }
                    },
                    |err| eprintln!("音频流错误: {}", err),
                    None
                )
            },
            sample_format => return Err(format!("不支持的音频格式: {:?}", sample_format)),
        }.map_err(|e| format!("创建音频流失败: {}", e))?;
        
        // 立即暂停流（不显示录音指示器）
        stream.pause().map_err(|e| format!("暂停流失败: {}", e))?;
        
        self.stream = Some(stream);
        println!("音频管理器初始化完成");
        println!("  采样率: {}Hz", self.actual_sample_rate);
        println!("  声道数: {}", config.channels);
        println!("  采样格式: {:?}", default_config.sample_format());
        
        Ok(())
    }
    
    pub fn start_recording(&mut self) -> Result<(), String> {
        if *self.is_recording.lock().unwrap() {
            return Err("Already recording".to_string());
        }
        
        // 清空缓冲区准备新的录音
        self.audio_buffer.lock().unwrap().clear();
        
        // 设置录音状态
        *self.is_recording.lock().unwrap() = true;
        
        // 启动音频流（现在才显示录音指示器）
        if let Some(stream) = &self.stream {
            stream.play().map_err(|e| format!("启动音频流失败: {}", e))?;
        }
        
        println!("开始录音");
        Ok(())
    }
    
    pub fn stop_recording(&mut self) -> Result<Vec<u8>, String> {
        if !*self.is_recording.lock().unwrap() {
            return Err("Not recording".to_string());
        }
        
        // 停止录音状态
        *self.is_recording.lock().unwrap() = false;
        
        // 暂停音频流（隐藏录音指示器）
        if let Some(stream) = &self.stream {
            stream.pause().map_err(|e| format!("暂停音频流失败: {}", e))?;
        }
        
        // 等待一点时间确保所有音频数据都被处理
        std::thread::sleep(std::time::Duration::from_millis(100));
        
        // 获取录音数据
        let audio_data = {
            let buffer = self.audio_buffer.lock().unwrap();
            buffer.clone()
        };
        
        println!("停止录音 - 采集了 {} 个样本 ({:.2}秒)", 
                audio_data.len(), 
                audio_data.len() as f32 / self.actual_sample_rate as f32);
        
        if audio_data.is_empty() {
            return Err("没有录制到音频数据".to_string());
        }
        
        // 如果采样率不是16kHz，需要重采样
        let resampled_data = if self.actual_sample_rate != 16000 {
            self.resample(&audio_data, self.actual_sample_rate, 16000)
        } else {
            audio_data
        };
        
        // 直接转换为PCM格式（无WAV头）
        self.create_pcm(resampled_data)
    }
    
    // 高质量专业重采样（使用rubato库）
    fn resample(&self, data: &[f32], from_rate: u32, to_rate: u32) -> Vec<f32> {
        if from_rate == to_rate {
            return data.to_vec();
        }
        
        let resample_ratio = to_rate as f64 / from_rate as f64;
        
        // 创建高质量重采样器
        let mut resampler = match SincFixedIn::<f32>::new(
            resample_ratio,
            2.0,  // 最大重采样比率相对变化
            SincInterpolationParameters {
                sinc_len: 256,           // 增加sinc长度提高质量
                f_cutoff: 0.95,          // 截止频率
                interpolation: SincInterpolationType::Linear,
                oversampling_factor: 256,
                window: WindowFunction::BlackmanHarris2,  // 高质量窗函数
            },
            data.len(),
            1,  // 单声道
        ) {
            Ok(r) => r,
            Err(e) => {
                println!("创建重采样器失败: {:?}, 回退到简单重采样", e);
                return self.resample_simple(data, from_rate, to_rate);
            }
        };
        
        // 准备输入数据（二维向量格式，单声道）
        let input = vec![data.to_vec()];
        
        // 执行重采样
        match resampler.process(&input, None) {
            Ok(output) => {
                let resampled = output[0].clone();
                println!("高质量重采样: {}Hz -> {}Hz ({} -> {} 样本)", 
                        from_rate, to_rate, data.len(), resampled.len());
                resampled
            },
            Err(e) => {
                println!("重采样处理失败: {:?}, 回退到简单重采样", e);
                self.resample_simple(data, from_rate, to_rate)
            }
        }
    }
    
    // 简单线性插值重采样（备用方案）
    fn resample_simple(&self, data: &[f32], from_rate: u32, to_rate: u32) -> Vec<f32> {
        let ratio = from_rate as f32 / to_rate as f32;
        let new_len = (data.len() as f32 / ratio) as usize;
        let mut resampled = Vec::with_capacity(new_len);
        
        for i in 0..new_len {
            let src_pos = i as f32 * ratio;
            let src_idx = src_pos as usize;
            
            if src_idx < data.len() - 1 {
                let frac = src_pos - src_idx as f32;
                let sample = data[src_idx] * (1.0 - frac) + data[src_idx + 1] * frac;
                resampled.push(sample);
            } else if src_idx < data.len() {
                resampled.push(data[src_idx]);
            }
        }
        
        println!("简单重采样: {}Hz -> {}Hz ({} -> {} 样本)", 
                from_rate, to_rate, data.len(), resampled.len());
        resampled
    }
    
    fn create_pcm(&self, audio_data: Vec<f32>) -> Result<Vec<u8>, String> {
        // 直接转换f32到16位PCM，无需WAV头
        let pcm_data: Vec<u8> = audio_data.iter()
            .map(|&sample| {
                let clamped = sample.clamp(-1.0, 1.0);
                let amplitude = (clamped * i16::MAX as f32) as i16;
                amplitude.to_le_bytes()
            })
            .flatten()
            .collect();
        
        println!("生成PCM数据: {} 字节 (原始样本: {})", pcm_data.len(), audio_data.len());
        
        Ok(pcm_data)
    }
    
    pub fn is_recording(&self) -> bool {
        *self.is_recording.lock().unwrap()
    }
}

unsafe impl Send for AudioManager {}
unsafe impl Sync for AudioManager {}