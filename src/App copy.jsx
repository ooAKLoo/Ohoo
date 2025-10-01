import React, { useState, useEffect, useRef, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/tauri';
import { appWindow } from '@tauri-apps/api/window';
import { Store } from 'tauri-plugin-store-api';
import { 
  MicrophoneIcon, 
  StopIcon
} from '@heroicons/react/24/outline';
import { 
  Copy, Check, Bookmark, X, ArrowUp, Trash2, GripVertical, 
  Cloud, HardDrive, ChevronRight, ChevronLeft, Code, FileText, 
  CheckSquare, Image, MoreVertical, Pin, Maximize2, Layout, FolderOpen
} from 'lucide-react';

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
  const [transcriptionMode, setTranscriptionMode] = useState('replace');
  const [copiedItems, setCopiedItems] = useState(new Set());
  const [isWindowHovered, setIsWindowHovered] = useState(false);
  const [isUsingRemoteService, setIsUsingRemoteService] = useState(false);
  
  // 新增状态
  const [showDrawer, setShowDrawer] = useState(false);
  const [selectedWorkspace, setSelectedWorkspace] = useState('all');
  const [workspaces] = useState([
    { id: 'all', name: '全部', icon: Layout },
    { id: 'work', name: '工作', icon: FileText },
    { id: 'personal', name: '个人', icon: CheckSquare },
    { id: 'temp', name: '临时', icon: FolderOpen }
  ]);
  const [hoveredCard, setHoveredCard] = useState(null);
  const [floatingCards, setFloatingCards] = useState(new Set());
  
  const swipeStartX = useRef(null);
  const pinnedScrollRef = useRef(null);

  // 获取卡片类型图标
  const getCardTypeIcon = (type) => {
    switch(type) {
      case 'code': return Code;
      case 'todo': return CheckSquare;
      case 'image': return Image;
      default: return FileText;
    }
  };

  // 获取卡片类型颜色
  const getCardTypeColor = (type) => {
    switch(type) {
      case 'code': return 'text-blue-600 bg-blue-50';
      case 'todo': return 'text-green-600 bg-green-50';
      case 'image': return 'text-purple-600 bg-purple-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const addToHistory = (text) => {
    if (!text.trim()) return;
    
    const historyItem = {
      id: Date.now(),
      text: text.trim(),
      timestamp: new Date()
    };
    
    setHistoryItems(prev => {
      const isDuplicate = prev.some(item => item.text === historyItem.text);
      if (isDuplicate) return prev;
      
      const updated = [historyItem, ...prev];
      return updated.length > 4 ? updated.slice(0, 4) : updated;
    });
  };

  const selectHistoryItem = (text) => {
    if (currentText.trim() && !historyItems.some(item => item.text === currentText.trim())) {
      addToHistory(currentText);
    }
    setCurrentText(text);
  };

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

  useEffect(() => {
    const savePinnedItems = async () => {
      try {
        await store.set('pinnedItems', pinnedItems);
        await store.save();
      } catch (error) {
        console.error('Failed to save pinned items:', error);
      }
    };
    
    if (pinnedItems.length > 0) {
      savePinnedItems();
    }
  }, [pinnedItems]);

  useEffect(() => {
    if (window.__TAURI__) {
      invoke('start_python_service')
        .then(result => {
          console.log('Python service status:', result);
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
    if (isTranscribing) return;
    
    if (!isRecording) {
      await startRecording();
    } else {
      await stopRecording();
    }
  };

  const startRecording = async () => {
    try {
      await invoke('start_audio_recording');
      setIsRecording(true);
      console.log('开始录音');
    } catch (error) {
      console.error('Error starting recording:', error);
      showToastMessage('无法开始录音');
    }
  };

  const stopRecording = async () => {
    try {
      setIsRecording(false);
      setIsTranscribing(true);
      
      const result = await invoke('stop_audio_recording');
      console.log('录音停止');
      
      if (transcriptionMode === 'replace') {
        if (currentText.trim()) {
          addToHistory(currentText);
        }
        setCurrentText(result.text);
      } else {
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
        text: currentText.trim(),
        timestamp: new Date(),
        type: 'note', // 默认类型
        workspace: 'temp' // 默认工作区
      };
      
      setPinnedItems(prev => {
        const isDuplicate = prev.some(item => item.text === newItem.text);
        if (isDuplicate) return prev;
        
        const updated = [newItem, ...prev];
        return updated.length > 20 ? updated.slice(0, 20) : updated;
      });
      
      showToastMessage('已保存');
    }
  };

  const copyToClipboard = async (text, itemId = null) => {
    try {
      await navigator.clipboard.writeText(text);
      
      if (itemId) {
        setCopiedItems(prev => new Set(prev).add(itemId));
        setTimeout(() => {
          setCopiedItems(prev => {
            const newSet = new Set(prev);
            newSet.delete(itemId);
            return newSet;
          });
        }, 2000);
      } else {
        setIsCopied(true);
        setTimeout(() => setIsCopied(false), 2000);
      }
    } catch (error) {
      console.error('Copy failed:', error);
      showToastMessage('复制失败');
    }
  };

  const removePinned = (id) => {
    setPinnedItems(prev => prev.filter(item => item.id !== id));
    setFloatingCards(prev => {
      const newSet = new Set(prev);
      newSet.delete(id);
      return newSet;
    });
  };

  const fillToTextbox = (text) => {
    if (transcriptionMode === 'replace') {
      if (currentText.trim()) {
        addToHistory(currentText);
      }
      setCurrentText(text);
    } else {
      const newText = currentText.trim() 
        ? currentText + ' ' + text 
        : text;
      setCurrentText(newText);
    }
  };

  // 更新卡片类型
  const updateCardType = (id, type) => {
    setPinnedItems(prev => prev.map(item => 
      item.id === id ? { ...item, type } : item
    ));
  };

  // 更新卡片工作区
  const updateCardWorkspace = (id, workspace) => {
    setPinnedItems(prev => prev.map(item => 
      item.id === id ? { ...item, workspace } : item
    ));
  };

  // 切换悬浮状态
  const toggleFloating = (id) => {
    setFloatingCards(prev => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  // 过滤卡片
  const filteredCards = pinnedItems.filter(item => {
    if (selectedWorkspace === 'all') return true;
    return item.workspace === selectedWorkspace;
  });

  const handleTouchStart = useCallback((e) => {
    swipeStartX.current = e.touches[0].clientX;
  }, []);

  const handleTouchEnd = useCallback((e) => {
    if (swipeStartX.current === null) return;
    
    const endX = e.changedTouches[0].clientX;
    const diffX = endX - swipeStartX.current;
    
    if (Math.abs(diffX) > 50) {
      if (diffX > 0) {
        setTranscriptionMode('replace');
      } else {
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
    
    if (Math.abs(diffX) > 50) {
      if (diffX > 0) {
        setTranscriptionMode('replace');
      } else {
        setTranscriptionMode('append');
      }
    }
    
    swipeStartX.current = null;
  }, []);

  const handleWheelSwipe = useCallback((e) => {
    if (Math.abs(e.deltaX) > Math.abs(e.deltaY) && Math.abs(e.deltaX) > 30) {
      e.preventDefault();
      
      if (e.deltaX > 0) {
        setTranscriptionMode('append');
      } else {
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
    <div className="w-screen h-screen flex flex-col overflow-hidden bg-transparent"
         onMouseEnter={() => setIsWindowHovered(true)}
         onMouseLeave={() => setIsWindowHovered(false)}
         onMouseDown={async (e) => {
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
      <div className="flex-1 overflow-hidden">
        <div className="p-4 h-full flex flex-col">
          {/* 语音转写区域 */}
          <div className="relative rounded-2xl">
            <div 
              className="rounded-2xl"
              style={{ backgroundColor: '#FFFFFF' }}
              onWheel={handleWheelSwipe}
              onTouchStart={handleTouchStart}
              onTouchEnd={handleTouchEnd}
              onMouseDown={handleMouseDown}
              onMouseUp={handleMouseUp}
            >
              {/* 历史记录气泡区域 */}
              <div className="relative px-3 pt-2 pb-1.5 rounded-t-lg">
                <div className="flex items-center space-x-1.5 overflow-x-auto scrollbar-hide relative">
                  {historyItems.length === 0 ? (
                    <span className="text-[10px] text-gray-400 px-2 py-0.5">暂无历史记录</span>
                  ) : (
                    historyItems.slice(0, 4).map((item) => (
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
                        
                        {hoveredBubble === item.id && (
                          <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-1.5 px-2 py-1.5 bg-gray-800 text-white text-[11px] rounded-md max-w-40 z-50">
                            <div className="line-clamp-2">{item.text}</div>
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
                
                {historyItems.length > 0 && (
                  <div className="absolute right-0 top-0 bottom-0 w-8 bg-gradient-to-l from-[#FFFFFF] to-transparent pointer-events-none rounded-lg"></div>
                )}
                
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
              
              {/* 底部工具栏 */}
              <div className="flex items-center justify-between px-3 pb-3 pt-1">
                {/* 左侧：模式切换器 */}
                <div className="flex items-center space-x-3 select-none">
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
                  <button
                    onClick={toggleRecording}
                    disabled={isTranscribing}
                    className="relative group"
                  >
                    <div className={`w-7 h-7 rounded flex items-center justify-center transition-all duration-300 relative ${
                      !isRecording && !isTranscribing
                        ? 'hover:bg-gray-200 text-gray-600'
                        : isRecording 
                          ? 'text-red-500'
                          : 'text-gray-600'
                    } ${isTranscribing ? 'opacity-50' : ''}`}>
                      {isTranscribing ? (
                        <div className="w-3.5 h-3.5 border border-gray-400 border-t-transparent rounded-full animate-spin" />
                      ) : (
                        <>
                          <MicrophoneIcon className="w-3.5 h-3.5 z-10" />
                          {isRecording && (
                            <div className="absolute w-1 h-1 bg-red-500 rounded-full animate-pulse" />
                          )}
                        </>
                      )}
                    </div>
                  </button>

                  <div className="w-px h-4 bg-gray-300"></div>

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

                  <button
                    onClick={pinCurrentText}
                    disabled={!currentText}
                    className="w-7 h-7 rounded flex items-center justify-center hover:bg-gray-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    title="保存"
                  >
                    <Bookmark size={13} className="text-gray-600" />
                  </button>

                  <div className="w-px h-4 bg-gray-300"></div>

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

          {/* 置顶内容卡片列表 */}
          {pinnedItems.length > 0 && (
            <div className="mt-4 flex-1 overflow-hidden">
              <div className="flex items-center justify-between mb-2 px-1">
                <span className="text-[10px] text-gray-500 font-medium">
                  保存的内容 ({filteredCards.length})
                </span>
                <button
                  onClick={() => setShowDrawer(!showDrawer)}
                  className="text-[10px] text-blue-600 hover:text-blue-700 flex items-center gap-0.5"
                >
                  {showDrawer ? '收起' : '展开'}
                  {showDrawer ? <ChevronLeft size={10} /> : <ChevronRight size={10} />}
                </button>
              </div>

              <div 
                ref={pinnedScrollRef}
                className="h-full max-h-48 overflow-y-auto scrollbar-thin"
              >
                <div className="flex flex-wrap gap-2 pb-2">
                  {filteredCards.map((item) => {
                    const TypeIcon = getCardTypeIcon(item.type);
                    const isFloating = floatingCards.has(item.id);
                    
                    return (
                      <div
                        key={item.id}
                        className="relative inline-flex items-center rounded-full px-2.5 py-1 group transition-all duration-200 hover:bg-gray-100 cursor-pointer"
                        style={{ backgroundColor: '#FFFFFF' }}
                        onClick={() => fillToTextbox(item.text)}
                        onMouseEnter={() => setHoveredCard(item.id)}
                        onMouseLeave={() => setHoveredCard(null)}
                      >
                        {/* 左侧类型图标 */}
                        <div className={`w-4 h-4 rounded flex items-center justify-center mr-1.5 flex-shrink-0 ${getCardTypeColor(item.type)}`}>
                          <TypeIcon size={9} />
                        </div>
                        
                        {/* 悬浮标记 */}
                        {isFloating && (
                          <Pin size={8} className="mr-1 text-blue-600" />
                        )}
                        
                        {/* 文字内容 */}
                        <span 
                          className="text-[12px] font-mono text-gray-700 group-hover:opacity-0 transition-opacity whitespace-nowrap"
                          title={item.text}
                        >
                          {item.text.length > 8 
                            ? item.text.slice(0, 8) + '…' 
                            : item.text}
                        </span>
                        
                        {/* 按钮组 - hover状态覆盖显示 */}
                        {hoveredCard === item.id && (
                          <div className="absolute inset-0 flex items-center justify-center space-x-1 bg-white rounded-full border border-gray-200 shadow-sm">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                copyToClipboard(item.text, item.id);
                              }}
                              className="text-gray-400 hover:text-gray-600 p-1 rounded transition-colors"
                              title="复制"
                            >
                              {copiedItems.has(item.id) ? (
                                <Check size={11} className="text-green-500" />
                              ) : (
                                <Copy size={11} />
                              )}
                            </button>

                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleFloating(item.id);
                              }}
                              className={`p-1 rounded transition-colors ${
                                isFloating
                                  ? 'text-blue-600 hover:text-blue-700'
                                  : 'text-gray-400 hover:text-gray-600'
                              }`}
                              title={isFloating ? '取消悬浮' : '悬浮'}
                            >
                              <Maximize2 size={11} />
                            </button>

                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                removePinned(item.id);
                              }}
                              className="text-gray-400 hover:text-red-500 p-1 rounded transition-colors"
                              title="删除"
                            >
                              <Trash2 size={11} />
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 侧边抽屉 - 工作区切换 */}
      {showDrawer && (
        <div className="absolute right-4 top-16 bg-white rounded-lg shadow-xl border border-gray-200 p-2 z-50 animate-in fade-in slide-in-from-right duration-200">
          <div className="text-[10px] text-gray-500 font-medium mb-2 px-2">工作区</div>
          <div className="space-y-1">
            {workspaces.map(ws => {
              const Icon = ws.icon;
              const count = ws.id === 'all' 
                ? pinnedItems.length 
                : pinnedItems.filter(item => item.workspace === ws.id).length;
              
              return (
                <button
                  key={ws.id}
                  onClick={() => {
                    setSelectedWorkspace(ws.id);
                    setShowDrawer(false);
                  }}
                  className={`w-full flex items-center gap-2 px-2 py-1.5 rounded text-[11px] transition-all ${
                    selectedWorkspace === ws.id
                      ? 'bg-gray-900 text-white'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  <Icon size={12} />
                  <span className="flex-1 text-left">{ws.name}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                    selectedWorkspace === ws.id
                      ? 'bg-white/20'
                      : 'bg-gray-200'
                  }`}>
                    {count}
                  </span>
                </button>
              );
            })}
          </div>
          
          <div className="mt-2 pt-2 border-t border-gray-200">
            <div className="text-[10px] text-gray-500 font-medium mb-2 px-2">卡片类型</div>
            <div className="grid grid-cols-2 gap-1">
              {[
                { type: 'note', label: '笔记', icon: FileText },
                { type: 'code', label: '代码', icon: Code },
                { type: 'todo', label: '待办', icon: CheckSquare },
                { type: 'image', label: '图片', icon: Image }
              ].map(({ type, label, icon: Icon }) => {
                const count = pinnedItems.filter(item => item.type === type).length;
                return (
                  <div
                    key={type}
                    className="flex items-center gap-1.5 px-2 py-1 text-[10px] text-gray-600 bg-gray-50 rounded"
                  >
                    <Icon size={10} />
                    <span>{label}</span>
                    <span className="ml-auto text-gray-400">{count}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* 悬浮卡片显示区 */}
      {Array.from(floatingCards).length > 0 && (
        <div className="absolute bottom-4 right-4 space-y-2 z-40 max-w-[200px]">
          {Array.from(floatingCards).map(cardId => {
            const card = pinnedItems.find(item => item.id === cardId);
            if (!card) return null;
            
            const TypeIcon = getCardTypeIcon(card.type);
            
            return (
              <div
                key={card.id}
                className="bg-white rounded-lg shadow-lg border-2 border-blue-200 p-2 backdrop-blur-sm"
              >
                <div className="flex items-start gap-2">
                  <div className={`w-5 h-5 rounded flex items-center justify-center flex-shrink-0 ${getCardTypeColor(card.type)}`}>
                    <TypeIcon size={11} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-[11px] font-medium text-gray-900 line-clamp-2">
                      {card.text}
                    </div>
                  </div>
                  <button
                    onClick={() => toggleFloating(card.id)}
                    className="p-0.5 hover:bg-gray-100 rounded transition-colors flex-shrink-0"
                  >
                    <X size={12} className="text-gray-400" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

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