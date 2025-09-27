import React, { useState, useEffect, useRef, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/tauri';
import { appWindow } from '@tauri-apps/api/window';
import { 
  MicrophoneIcon, 
  StopIcon,
  ChevronDownIcon
} from '@heroicons/react/24/outline';
import { Copy, Check, Bookmark, X } from 'lucide-react';

function App() {
  const [currentText, setCurrentText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [pinnedItems, setPinnedItems] = useState([]);
  const [historyItems, setHistoryItems] = useState([]);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [showHistory, setShowHistory] = useState(false);
  const [isCopied, setIsCopied] = useState(false);
  const [hoveredBubble, setHoveredBubble] = useState(null);
  const [transcriptionMode, setTranscriptionMode] = useState('replace'); // 'replace' or 'append'
  const [copiedItems, setCopiedItems] = useState(new Set()); // 追踪已复制的条目ID
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const swipeStartX = useRef(null);

  // 添加到历史记录的辅助函数，带去重检查
  const addToHistory = (text) => {
    if (!text.trim()) return;
    
    const historyItem = {
      id: Date.now(),
      text: text.trim(),
      timestamp: new Date()
    };
    
    setHistoryItems(prev => {
      // 检查是否已存在相同文本
      const isDuplicate = prev.some(item => item.text === historyItem.text);
      if (isDuplicate) return prev;
      
      const updated = [historyItem, ...prev];
      return updated.length > 4 ? updated.slice(0, 4) : updated;
    });
  };

  // 点击历史记录气泡
  const selectHistoryItem = (text) => {
    // 如果当前文本框有内容且不在历史记录中，先保存
    if (currentText.trim() && !historyItems.some(item => item.text === currentText.trim())) {
      addToHistory(currentText);
    }
    setCurrentText(text);
  };

  useEffect(() => {
    // 检查是否在Tauri环境中
    if (window.__TAURI__) {
      invoke('start_python_service')
        .then(result => {
          console.log('Python service status:', result);
        })
        .catch(error => {
          console.error('Failed to start Python service:', error);
        });
    }
  }, []);


  const toggleRecording = async () => {
    if (!isRecording) {
      await startRecording();
    } else {
      await stopRecording();
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      audioChunksRef.current = [];
      
      mediaRecorderRef.current.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };
      
      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        await transcribeAudio(audioBlob);
        stream.getTracks().forEach(track => track.stop());
      };
      
      mediaRecorderRef.current.start();
      setIsRecording(true);
    } catch (error) {
      console.error('Error accessing microphone:', error);
      showToastMessage('无法访问麦克风');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const transcribeAudio = async (audioBlob) => {
    try {
      const formData = new FormData();
      formData.append('file', audioBlob, 'recording.webm');
      formData.append('language', 'auto');
      formData.append('use_itn', 'true');
      
      showToastMessage('转写中...');
      
      const response = await fetch('http://localhost:8001/transcribe/normal', {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error('Transcription failed');
      }
      
      const result = await response.json();
      
      // 根据模式处理转写结果
      if (transcriptionMode === 'replace') {
        // 覆盖模式：如果当前有文本内容，先保存到历史记录
        if (currentText.trim()) {
          addToHistory(currentText);
        }
        setCurrentText(result.text);
      } else {
        // 追加模式：在现有内容后追加新内容
        const newText = currentText.trim() 
          ? currentText + ' ' + result.text 
          : result.text;
        setCurrentText(newText);
      }
      showToastMessage('转写完成');
    } catch (error) {
      console.error('Transcription error:', error);
      showToastMessage('转写失败');
    }
  };

  const clearText = () => {
    setCurrentText('');
  };

  const pinCurrentText = () => {
    if (currentText.trim()) {
      const newItem = {
        id: Date.now(),
        text: currentText.trim(),
        timestamp: new Date()
      };
      
      // 用户主动保存到置顶列表，最多保留10条，带去重检查
      setPinnedItems(prev => {
        // 检查是否已存在相同文本
        const isDuplicate = prev.some(item => item.text === newItem.text);
        if (isDuplicate) {
          showToastMessage('内容已存在');
          return prev;
        }
        
        const updated = [newItem, ...prev];
        showToastMessage('已保存');
        return updated.length > 10 ? updated.slice(0, 10) : updated;
      });
    }
  };

  const copyToClipboard = async (text, itemId = null) => {
    try {
      await navigator.clipboard.writeText(text);
      
      if (itemId) {
        // 为特定条目设置复制状态
        setCopiedItems(prev => new Set(prev).add(itemId));
        setTimeout(() => {
          setCopiedItems(prev => {
            const newSet = new Set(prev);
            newSet.delete(itemId);
            return newSet;
          });
        }, 2000);
      } else {
        // 顶部复制按钮的原有逻辑
        setIsCopied(true);
        setTimeout(() => {
          setIsCopied(false);
        }, 2000);
      }
    } catch (error) {
      console.error('Copy failed:', error);
      showToastMessage('复制失败');
    }
  };

  const removePinned = (id) => {
    setPinnedItems(prev => prev.filter(item => item.id !== id));
  };

  const formatTime = (date) => {
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    
    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes}分钟前`;
    
    return date.toLocaleTimeString().slice(0, 5);
  };

  // 处理滑动手势
  const handleTouchStart = useCallback((e) => {
    swipeStartX.current = e.touches[0].clientX;
  }, []);

  const handleTouchEnd = useCallback((e) => {
    if (swipeStartX.current === null) return;
    
    const endX = e.changedTouches[0].clientX;
    const diffX = endX - swipeStartX.current;
    
    // 如果滑动距离超过50px，则切换模式
    if (Math.abs(diffX) > 50) {
      if (diffX > 0) {
        // 向右滑动 - 切换到覆盖模式
        setTranscriptionMode('replace');
      } else {
        // 向左滑动 - 切换到追加模式
        setTranscriptionMode('append');
      }
    }
    
    swipeStartX.current = null;
  }, []);

  const handleMouseDown = useCallback((e) => {
    swipeStartX.current = e.clientX;
  }, []);

  const handleMouseUp = useCallback((e) => {
    if (swipeStartX.current === null) return;
    
    const diffX = e.clientX - swipeStartX.current;
    
    // 如果滑动距离超过50px，则切换模式
    if (Math.abs(diffX) > 50) {
      if (diffX > 0) {
        // 向右滑动 - 切换到覆盖模式
        setTranscriptionMode('replace');
      } else {
        // 向左滑动 - 切换到追加模式
        setTranscriptionMode('append');
      }
    }
    
    swipeStartX.current = null;
  }, []);

  // 处理macOS触控板滑动
  const handleWheelSwipe = useCallback((e) => {
    // 检测是否为水平滑动（deltaX 大于 deltaY）
    if (Math.abs(e.deltaX) > Math.abs(e.deltaY) && Math.abs(e.deltaX) > 30) {
      e.preventDefault(); // 阻止默认的水平滚动
      
      if (e.deltaX > 0) {
        // 向右滑动 - 追加模式
        setTranscriptionMode('append');
      } else {
        // 向左滑动 - 覆盖模式
        setTranscriptionMode('replace');
      }
    }
  }, []);

  const showToastMessage = (message) => {
    setToastMessage(message);
    setShowToast(true);
    setTimeout(() => {
      setShowToast(false);
    }, 1500);
  };

  return (
    <div className="h-screen w-screen bg-white flex flex-col">
      {/* 主内容区 - 直接铺满窗口 */}
      <div className="flex-1 p-4 space-y-4">
          {/* 顶部操作区域 */}
          <div className="flex items-center gap-4">
            {/* 左侧：历史消息胶囊区域 */}
            <div className="flex-1 min-w-0 relative">
              <div className="flex items-center space-x-2 overflow-x-auto scrollbar-hide pr-8">
                {historyItems.length === 0 ? (
                  <span className="text-xs text-gray-400 px-3 py-1.5">暂无历史记录</span>
                ) : (
                  historyItems.slice(0, 4).map((item, index) => (
                  <div
                    key={item.id}
                    className="relative flex-shrink-0"
                    onMouseEnter={() => setHoveredBubble(item.id)}
                    onMouseLeave={() => setHoveredBubble(null)}
                  >
                    <div 
                      className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-full text-xs text-gray-700 cursor-pointer transition-colors whitespace-nowrap"
                      onClick={() => selectHistoryItem(item.text)}
                      title={item.text}
                    >
                      {item.text.length > 6 ? item.text.slice(0, 6) + '...' : item.text}
                    </div>
                    
                    {/* 悬浮提示框 */}
                    {hoveredBubble === item.id && (
                      <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg shadow-lg max-w-48 z-50">
                        <div className="line-clamp-3">{item.text}</div>
                        <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-2 h-2 bg-gray-900 rotate-45"></div>
                      </div>
                    )}
                  </div>
                  ))
                )}
              </div>
              {/* 右侧渐变虚化效果 */}
              {historyItems.length > 0 && (
                <div className="absolute right-0 top-0 bottom-0 w-8 bg-gradient-to-l from-white to-transparent pointer-events-none"></div>
              )}
            </div>

            {/* 右侧：按钮组 */}
            <div className="bg-gray-100 rounded-lg px-1 py-0.5 flex items-center space-x-1 flex-shrink-0">
              {/* 录音按钮 */}
              <button
                onClick={toggleRecording}
                className="relative group"
              >
                <div className={`w-7 h-7 rounded flex items-center justify-center transition-all duration-300 ${
                  isRecording 
                    ? 'bg-red-500 text-white' 
                    : 'hover:bg-gray-200 text-gray-600'
                }`}>
                  {!isRecording ? (
                    <MicrophoneIcon className="w-3.5 h-3.5" />
                  ) : (
                    <StopIcon className="w-3.5 h-3.5" />
                  )}
                </div>
                {/* 录音动画效果 */}
                {isRecording && (
                  <div className="absolute inset-0 rounded bg-red-500 animate-ping opacity-25" />
                )}
              </button>

              {/* 分隔线 */}
              <div className="w-px h-4 bg-gray-300"></div>

              {/* 复制按钮 */}
              <button
                onClick={() => copyToClipboard(currentText)}
                disabled={!currentText}
                className="w-7 h-7 rounded flex items-center justify-center hover:bg-gray-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                title={isCopied ? "已复制" : "复制"}
              >
                {isCopied ? (
                  <Check size={13} className="text-gray-600" />
                ) : (
                  <Copy size={13} className="text-gray-600" />
                )}
              </button>

              {/* 保存按钮 */}
              <button
                onClick={pinCurrentText}
                disabled={!currentText}
                className="w-7 h-7 rounded flex items-center justify-center hover:bg-gray-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                title="保存"
              >
                <Bookmark size={13} className="text-gray-600" />
              </button>
            </div>
          </div>

          {/* 文本显示区域 - 可编辑 */}
          <div className="relative">
            <div 
              className="bg-gray-50 rounded-lg relative group"
              onWheel={handleWheelSwipe}
              onTouchStart={handleTouchStart}
              onTouchEnd={handleTouchEnd}
              onMouseDown={handleMouseDown}
              onMouseUp={handleMouseUp}
            >
              <textarea
                value={currentText}
                onChange={(e) => setCurrentText(e.target.value)}
                placeholder="点击录音按钮开始转写"
                className="w-full text-sm text-gray-700 bg-transparent resize-none border-none outline-none p-3 min-h-[84px] max-h-32 overflow-y-auto placeholder-gray-400"
                style={{ lineHeight: '1.5rem' }}
              />
            </div>
            
            {/* 模式切换器 - SwiftUI风格 */}
            <div 
              className="absolute bottom-0 left-1/2 transform -translate-x-1/2 translate-y-full pt-3"
            >
              <div className="flex items-center space-x-3 select-none">
                {/* 覆盖模式指示器 */}
                <div 
                  onClick={() => setTranscriptionMode('replace')}
                  className="flex items-center space-x-1.5 cursor-pointer group"
                >
                  <div 
                    className={`h-1 rounded-full transition-all duration-300 ease-in-out ${
                      transcriptionMode === 'replace' 
                        ? 'w-5 bg-gray-800' 
                        : 'w-1.5 bg-gray-300'
                    }`}
                  />
                  <span 
                    className={`text-[10px] font-medium transition-all duration-300 ease-in-out select-none ${
                      transcriptionMode === 'replace' 
                        ? 'text-gray-800' 
                        : 'text-gray-400'
                    }`}
                  >
                    覆盖
                  </span>
                </div>

                {/* 追加模式指示器 */}
                <div 
                  onClick={() => setTranscriptionMode('append')}
                  className="flex items-center space-x-1.5 cursor-pointer group"
                >
                  <div 
                    className={`h-1 rounded-full transition-all duration-300 ease-in-out ${
                      transcriptionMode === 'append' 
                        ? 'w-5 bg-gray-800' 
                        : 'w-1.5 bg-gray-300'
                    }`}
                  />
                  <span 
                    className={`text-[10px] font-medium transition-all duration-300 ease-in-out select-none ${
                      transcriptionMode === 'append' 
                        ? 'text-gray-800' 
                        : 'text-gray-400'
                    }`}
                  >
                    追加
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* 置顶消息列表 - 极简风格 */}
          {pinnedItems.length > 0 && (
            <div className="space-y-1 max-h-48 overflow-y-auto mt-8">
              {pinnedItems.slice(0, 5).map((item) => (
                <div
                  key={item.id}
                  className="bg-gray-50 rounded-lg px-3 py-2 group flex items-center justify-between hover:bg-gray-100 transition-colors cursor-pointer"
                  onClick={() => copyToClipboard(item.text, item.id)}
                >
                  <p 
                    className="text-sm text-gray-600 truncate flex-1 mr-3"
                  >
                    {item.text}
                  </p>
                  <div className="flex items-center">
                    {/* 复制状态指示器 */}
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity text-xs text-gray-400">
                      {copiedItems.has(item.id) ? (
                        <Check size={12} className="text-green-500" />
                      ) : (
                        <Copy size={12} />
                      )}
                    </div>
                    {/* 取消置顶按钮 - 只在非hover复制状态时显示 */}
                    {!copiedItems.has(item.id) && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation(); // 阻止触发复制
                          removePinned(item.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 transition-opacity text-xs text-gray-400 hover:text-gray-600 ml-2"
                        title="取消置顶"
                      >
                        <X size={12} />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

      {/* Toast 通知 */}
      {showToast && (
        <div className="fixed top-4 left-1/2 transform -translate-x-1/2 bg-gray-900 text-white px-3 py-1 rounded-lg shadow-lg text-xs z-50 animate-pulse">
          {toastMessage}
        </div>
      )}
    </div>
  );
}

export default App;