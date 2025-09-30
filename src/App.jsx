import React, { useState, useEffect, useRef, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/tauri';
import { appWindow } from '@tauri-apps/api/window';
import { Store } from 'tauri-plugin-store-api';
import { 
  MicrophoneIcon, 
  StopIcon
} from '@heroicons/react/24/outline';
import { Copy, Check, Bookmark, X, ArrowUp, Trash2, GripVertical, Cloud, HardDrive } from 'lucide-react';

// 在组件外部创建 store 实例
const store = new Store('.settings.dat');

function App() {
  const [currentText, setCurrentText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [pinnedItems, setPinnedItems] = useState([]);
  const [historyItems, setHistoryItems] = useState([]);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [isCopied, setIsCopied] = useState(false);
  const [hoveredBubble, setHoveredBubble] = useState(null);
  const [transcriptionMode, setTranscriptionMode] = useState('replace'); // 'replace' or 'append'
  const [copiedItems, setCopiedItems] = useState(new Set()); // 追踪已复制的条目ID
  const [isWindowHovered, setIsWindowHovered] = useState(false); // 追踪窗口悬停状态
  const [isUsingRemoteService, setIsUsingRemoteService] = useState(false); // 是否使用远程服务
  
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

  // 从Tauri Store加载置顶内容
  useEffect(() => {
    const loadPinnedItems = async () => {
      try {
        const saved = await store.get('pinnedItems');
        if (saved) {
          setPinnedItems(saved);
        }
      } catch (error) {
        console.error('Failed to load pinned items:', error);
      }
    };
    loadPinnedItems();
  }, []);

  // 保存置顶内容到Tauri Store
  useEffect(() => {
    const savePinnedItems = async () => {
      try {
        await store.set('pinnedItems', pinnedItems);
        await store.save(); // 确保立即保存到磁盘
      } catch (error) {
        console.error('Failed to save pinned items:', error);
      }
    };
    
    if (pinnedItems.length > 0) {
      savePinnedItems();
    }
  }, [pinnedItems]);


  useEffect(() => {
    // 检查是否在Tauri环境中
    if (window.__TAURI__) {
      invoke('start_python_service')
        .then(result => {
          console.log('Python service status:', result);
          // 检查是否使用远程服务
          if (result.includes('Remote service') || result.includes('115.190.136.178')) {
            setIsUsingRemoteService(true);
          }
        })
        .catch(error => {
          console.error('Failed to start Python service:', error);
        });
    }
  }, []);


  const toggleRecording = async () => {
    // 转写中时禁止录音操作
    if (isTranscribing) return;
    
    if (!isRecording) {
      await startRecording();
    } else {
      await stopRecording();
    }
  };

  const startRecording = async () => {
    try {
      // 使用 Rust 原生音频 API
      await invoke('start_audio_recording');
      setIsRecording(true);
      console.log('开始录音 - 使用 Rust 原生接口');
    } catch (error) {
      console.error('Error starting recording:', error);
      showToastMessage('无法开始录音');
    }
  };

  const stopRecording = async () => {
    try {
      setIsRecording(false);
      setIsTranscribing(true);
      
      // 使用 Rust 原生音频 API 停止录音并获取转写结果
      const result = await invoke('stop_audio_recording');
      console.log('录音停止 - 使用 Rust 原生接口');
      
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
    } catch (error) {
      console.error('Error stopping recording:', error);
      showToastMessage('录音停止失败');
    } finally {
      setIsTranscribing(false);
    }
  };


  const clearText = () => {
    setCurrentText('');
  };

  const pinCurrentText = () => {
    if (currentText.trim()) {
      const newItem = {
        id: Date.now(),
        text: currentText.trim(),  // 保存完整内容
        timestamp: new Date()
      };
      
      // 用户主动保存到置顶列表，最多保留10条，带去重检查
      setPinnedItems(prev => {
        // 检查是否已存在相同文本
        const isDuplicate = prev.some(item => item.text === newItem.text);
        if (isDuplicate) {
          return prev;
        }
        
        const updated = [newItem, ...prev];
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

  // 将置顶内容填入转写框
  const fillToTextbox = (text) => {
    if (transcriptionMode === 'replace') {
      // 覆盖模式：先保存当前内容到历史记录，然后替换
      if (currentText.trim()) {
        addToHistory(currentText);
      }
      setCurrentText(text);
    } else {
      // 追加模式：在现有内容后追加
      const newText = currentText.trim() 
        ? currentText + ' ' + text 
        : text;
      setCurrentText(newText);
    }
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
    <div className="w-screen h-screen flex flex-col "
         onMouseEnter={() => setIsWindowHovered(true)}
         onMouseLeave={() => setIsWindowHovered(false)}
         onMouseDown={async (e) => {
           // 只在非交互元素上允许拖动
           const target = e.target;
           const isInteractive = 
             target.tagName === 'BUTTON' ||
             target.tagName === 'TEXTAREA' ||
             target.tagName === 'INPUT' ||
             target.closest('button') ||
             target.closest('textarea');
           
           if (!isInteractive) {
             try {
               await appWindow.startDragging();
             } catch (error) {
               console.error('拖动失败:', error);
             }
           }
         }}>
      {/* 主内容区 */}
      <div className="flex-1">
        <div className="p-4">
          {/* 文本显示区域 - 可编辑 */}
          <div className="relative rounded-2xl ">
            {/* 关闭按钮 - 悬浮时显示 */}
            {/* {isWindowHovered && (
              <button
                onClick={async () => {
                  try {
                    await appWindow.close();
                  } catch (error) {
                    console.error('关闭窗口失败:', error);
                  }
                }}
                className="absolute -top-2 -left-2 w-6 h-6 rounded-full flex items-center justify-center transition-all duration-200 shadow-sm hover:shadow-md z-50 opacity-80 hover:opacity-100"
                style={{ backgroundColor: '#F5F5F5' }}
              >
                <X size={12} className="text-gray-600" />
              </button>
            )} */}
            
            <div 
              className="rounded-2xl"
              style={{ backgroundColor: '#F5F5F5' }}
              onWheel={handleWheelSwipe}
              onTouchStart={handleTouchStart}
              onTouchEnd={handleTouchEnd}
              onMouseDown={handleMouseDown}
              onMouseUp={handleMouseUp}
            >
              {/* 历史记录胶囊区域 */}
              <div className="relative px-3 pt-2 pb-1.5 rounded-t-lg">
                <div className="flex items-center space-x-1.5 overflow-x-auto scrollbar-hide relative">
                  {historyItems.length === 0 ? (
                    <span className="text-[10px] text-gray-400 px-2 py-0.5">暂无历史记录</span>
                  ) : (
                    historyItems.slice(0, 4).map((item, index) => (
                    <div
                      key={item.id}
                      className="relative flex-shrink-0"
                      onMouseEnter={() => setHoveredBubble(item.id)}
                      onMouseLeave={() => setHoveredBubble(null)}
                    >
                      <div 
                        className="px-2 py-0.5 border border-dashed border-gray-300 hover:border-transparent hover:bg-blue-50 rounded-full text-[10px] text-gray-400 hover:text-blue-600 cursor-pointer transition-all whitespace-nowrap"
                        onClick={() => selectHistoryItem(item.text)}
                        title={item.text}
                      >
                        {item.text.length > 6 ? item.text.slice(0, 6) + '...' : item.text}
                      </div>
                      
                      {/* 悬浮提示框 */}
                      {hoveredBubble === item.id && (
                        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-1.5 px-2 py-1.5 bg-gray-800 text-white text-[11px] rounded-md max-w-40 z-50">
                          <div className="line-clamp-2">{item.text}</div>
                        </div>
                      )}
                    </div>
                    ))
                  )}
                </div>
                
                {/* 右侧渐变虚化效果 */}
                {historyItems.length > 0 && (
                  <div className="absolute right-0 top-0 bottom-0 w-8 bg-gradient-to-l from-[#F5F5F5] to-transparent pointer-events-none rounded-lg"></div>
                )}
                
                {/* 拖拽图标 - 悬浮时显示 */}
                {isWindowHovered && (
                  <div 
                    className="absolute right-2 top-1/2 -translate-y-1/2 cursor-move opacity-40 hover:opacity-70 transition-opacity"
                    onMouseDown={async (e) => {
                      e.stopPropagation();
                      try {
                        await appWindow.startDragging();
                      } catch (error) {
                        console.error('拖动失败:', error);
                      }
                    }}
                    title="拖动窗口"
                  >
                    <GripVertical size={14} className="text-gray-500" />
                  </div>
                )}
              </div>

              {/* 转写内容 */}
              <textarea
                value={currentText}
                onChange={(e) => setCurrentText(e.target.value)}
                placeholder="点击录音按钮开始转写"
                className="w-full text-sm text-gray-700 bg-transparent resize-none border-none outline-none px-3 pt-1 pb-3 min-h-[84px] max-h-32 overflow-y-auto placeholder-gray-400"
                style={{ lineHeight: '1.5rem' }}
              />
              
              {/* 底部工具栏 - 模式切换器在左边，按钮组在右边 */}
              <div className="flex items-center justify-between px-3 pb-3 pt-1">
                {/* 左侧：模式切换器 */}
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

                {/* 右侧：按钮组 */}
                <div className="bg-gray-100 rounded-lg px-1 py-0.5 flex items-center space-x-1">
                  {/* 录音按钮 */}
<button
  onClick={toggleRecording}
  disabled={isTranscribing}
  className="relative group"
>
  <div className={`w-7 h-7 rounded flex items-center justify-center transition-all duration-300 relative ${
    !isRecording && !isTranscribing
      ? 'hover:bg-gray-200 text-gray-600'
      : isRecording 
        ? 'text-red-500'  // 录音时图标变红
        : 'text-gray-600'
  } ${isTranscribing ? 'opacity-50' : ''}`}>
    {isTranscribing ? (
      <div className="w-3.5 h-3.5 border border-gray-400 border-t-transparent rounded-full animate-spin" />
    ) : (
      <>
        <MicrophoneIcon className="w-3.5 h-3.5 z-10" />
        {/* 中心呼吸红点 - 改小 */}
        {isRecording && (
          <div className="absolute w-1 h-1 bg-red-500 rounded-full animate-pulse" />
        )}
      </>
    )}
  </div>
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

                  {/* 分隔线 */}
                  <div className="w-px h-4 bg-gray-300"></div>

                  {/* 模型状态指示器 */}
                  <div 
                    className="w-7 h-7 rounded flex items-center justify-center cursor-help"
                    title={isUsingRemoteService ? "使用云端模型" : "使用本地模型"}
                  >
                    {isUsingRemoteService ? (
                      <Cloud size={13} className="text-blue-500" />
                    ) : (
                      <HardDrive size={13} className="text-green-600" />
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 置顶消息列表 - 带优雅装饰 */}
          {pinnedItems.length > 0 && (
            <>

              {/* 置顶内容 - Flow Layout */}
              <div className="mt-4">
                <div className="flex flex-wrap gap-2 max-h-48 overflow-y-auto">
                  {pinnedItems.slice(0, 10).map((item, index) => (
                    <div
                      key={item.id}
                      className="inline-flex items-center rounded-full px-2.5 py-1 group relative transition-all duration-200 hover:bg-gray-100 cursor-pointer"
                      style={{ backgroundColor: '#F5F5F5' }}
                      onClick={() => fillToTextbox(item.text)}
                    >
                      {/* 左侧小圆点 */}
                      <div 
                        className="w-1.5 h-1.5 rounded-full mr-2 flex-shrink-0"
                        style={{ backgroundColor: '#FF6600' }}
                      ></div>
                      
                      {/* 文字内容 - 显示时截断 */}
                      <span 
                        className="text-[12px] font-mono text-gray-700 group-hover:opacity-0 transition-opacity whitespace-nowrap"
                        title={item.text}  // 完整内容显示在 tooltip
                      >
                        {item.text.length > 10 
                          ? item.text.slice(0, 10) + '…' 
                          : item.text}
                      </span>
                      
                      {/* 按钮组 - hover状态覆盖显示 */}
                      <div className="absolute inset-0 flex items-center justify-center space-x-2 opacity-0 group-hover:opacity-100 transition-opacity bg-white rounded-full border border-gray-200">
                        {/* 复制按钮 */}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            copyToClipboard(item.text, item.id);
                          }}
                          className="text-gray-400 hover:text-gray-600 p-1 rounded transition-colors"
                          title="复制"
                        >
                          {copiedItems.has(item.id) ? (
                            <Check size={12} className="text-green-500" />
                          ) : (
                            <Copy size={12} />
                          )}
                        </button>

                        {/* 删除按钮 */}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            removePinned(item.id);
                          }}
                          className="text-gray-400 hover:text-red-500 p-1 rounded transition-colors"
                          title="删除"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
          
          {/* 添加底部安全边距，确保最后内容可见 */}
          <div className="h-4"></div>
        </div>
      </div>

      {/* Toast 通知 - 保持固定定位 */}
      {showToast && (
        <div className="fixed top-4 left-1/2 transform -translate-x-1/2 bg-gray-900 text-white px-3 py-1 rounded-lg shadow-lg text-xs z-50 animate-pulse">
          {toastMessage}
        </div>
      )}
    </div>
  );
}

export default App;