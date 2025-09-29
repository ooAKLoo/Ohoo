# coding: utf-8
'''
多语言逆文本正则化 (Multilingual ITN)
统一处理中文、日语、英语的数字转换

用法示例：
from multilingual_itn import MultilingualITN

itn = MultilingualITN()
result = itn.process("一二三 twenty three 五時二十分", language="auto")
'''

import re

class MultilingualITN:
    def __init__(self):
        """初始化多语言ITN处理器"""
        self.chinese_available = False
        self.japanese_available = False
        self.english_available = False
        
        # 尝试导入各语言模块
        try:
            from chinese_itn import chinese_to_num
            self.chinese_to_num = chinese_to_num
            self.chinese_available = True
            print("✅ 中文ITN模块加载成功", flush=True)
        except ImportError:
            print("⚠️ 中文ITN模块不可用", flush=True)
        
        try:
            from japanese_itn import japanese_to_num
            self.japanese_to_num = japanese_to_num
            self.japanese_available = True
            print("✅ 日语ITN模块加载成功", flush=True)
        except ImportError:
            print("⚠️ 日语ITN模块不可用", flush=True)
        
        try:
            from english_itn import english_to_num
            self.english_to_num = english_to_num
            self.english_available = True
            print("✅ 英语ITN模块加载成功", flush=True)
        except ImportError:
            print("⚠️ 英语ITN模块不可用", flush=True)
    
    def detect_language(self, text):
        """简单的语言检测"""
        # 检测中文字符
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        # 检测日语字符（平假名、片假名）
        japanese_chars = len(re.findall(r'[\u3040-\u309f\u30a0-\u30ff]', text))
        # 检测英语单词
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
        
        total_chars = len(text.replace(' ', ''))
        if total_chars == 0:
            return "unknown"
        
        # 判断主要语言
        if chinese_chars / total_chars > 0.3:
            return "chinese"
        elif japanese_chars / total_chars > 0.2:
            return "japanese"
        elif english_words > 0:
            return "english"
        else:
            return "mixed"
    
    def process(self, text, language="auto"):
        """
        处理多语言文本
        
        Args:
            text: 输入文本
            language: 指定语言 ("auto", "chinese", "japanese", "english", "mixed")
        
        Returns:
            处理后的文本
        """
        if not text:
            return text
        
        if language == "auto":
            language = self.detect_language(text)
        
        original_text = text
        
        # 根据语言选择处理方式
        if language == "chinese" and self.chinese_available:
            text = self.chinese_to_num(text)
        elif language == "japanese" and self.japanese_available:
            text = self.japanese_to_num(text)
        elif language == "english" and self.english_available:
            text = self.english_to_num(text)
        elif language == "mixed":
            # 混合语言：按顺序应用所有可用的处理器
            if self.chinese_available:
                text = self.chinese_to_num(text)
            if self.japanese_available:
                text = self.japanese_to_num(text)
            if self.english_available:
                text = self.english_to_num(text)
        
        # 如果文本有变化，显示处理结果
        if text != original_text:
            print(f"🔢 {language.title()}ITN处理: {original_text} -> {text}", flush=True)
        
        return text
    
    def is_available(self):
        """检查是否有可用的ITN模块"""
        return self.chinese_available or self.japanese_available or self.english_available

# 便利函数
def process_multilingual_itn(text, language="auto"):
    """便利函数：处理多语言ITN"""
    itn = MultilingualITN()
    return itn.process(text, language)

if __name__ == "__main__":
    # 测试用例
    itn = MultilingualITN()
    
    test_cases = [
        ("一二三四五", "chinese"),
        ("twenty three point five", "english"),
        ("三時二十分", "japanese"),
        ("一二三 and twenty four", "mixed"),
        ("百分之五十", "auto"),
        ("fifty percent", "auto"),
        ("五十パーセント", "auto")
    ]
    
    for text, lang in test_cases:
        result = itn.process(text, lang)
        print(f"[{lang}] '{text}' -> '{result}'")