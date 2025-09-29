# coding: utf-8
'''
日语逆文本正则化 (Japanese ITN)
将日语中的数字表达转换为阿拉伯数字

用法示例：
from japanese_itn import japanese_to_num
result = japanese_to_num('一二三四五六七八九十')  # -> 12345678910
'''

import re

__all__ = ['japanese_to_num']

# 日语数字映射
jp_num_mapper = {
    '零': '0', '〇': '0', 'ゼロ': '0',
    '一': '1', '壱': '1', 'いち': '1', 'イチ': '1',
    '二': '2', '弐': '2', 'に': '2', 'ニ': '2',
    '三': '3', '参': '3', 'さん': '3', 'サン': '3',
    '四': '4', '肆': '4', 'よん': '4', 'ヨン': '4', 'し': '4', 'シ': '4',
    '五': '5', '伍': '5', 'ご': '5', 'ゴ': '5',
    '六': '6', '陸': '6', 'ろく': '6', 'ロク': '6',
    '七': '7', '漆': '7', 'なな': '7', 'ナナ': '7', 'しち': '7', 'シチ': '7',
    '八': '8', '捌': '8', 'はち': '8', 'ハチ': '8',
    '九': '9', '玖': '9', 'きゅう': '9', 'キュウ': '9', 'く': '9', 'ク': '9',
    '点': '.', '・': '.',
}

# 日语数值映射（计算用）
jp_value_mapper = {
    '零': 0, '〇': 0, 'ゼロ': 0,
    '一': 1, '壱': 1, 'いち': 1, 'イチ': 1,
    '二': 2, '弐': 2, 'に': 2, 'ニ': 2,
    '三': 3, '参': 3, 'さん': 3, 'サン': 3,
    '四': 4, '肆': 4, 'よん': 4, 'ヨン': 4, 'し': 4, 'シ': 4,
    '五': 5, '伍': 5, 'ご': 5, 'ゴ': 5,
    '六': 6, '陸': 6, 'ろく': 6, 'ロク': 6,
    '七': 7, '漆': 7, 'なな': 7, 'ナナ': 7, 'しち': 7, 'シチ': 7,
    '八': 8, '捌': 8, 'はち': 8, 'ハチ': 8,
    '九': 9, '玖': 9, 'きゅう': 9, 'キュウ': 9, 'く': 9, 'ク': 9,
    '十': 10, '拾': 10, 'じゅう': 10, 'ジュウ': 10,
    '百': 100, 'ひゃく': 100, 'ヒャク': 100,
    '千': 1000, 'せん': 1000, 'セン': 1000,
    '万': 10000, 'まん': 10000, 'マン': 10000,
    '億': 100000000, 'おく': 100000000, 'オク': 100000000,
}

# 日语常用单位
jp_units = r'個円時分秒年月日'

# 避免误转的日语固定表达
jp_idioms = [
    '一期一会', '十人十色', '一石二鳥', '二束三文', '三寒四温',
    '四面楚歌', '五里霧中', '六甲台', '七転八倒', '八方美人',
    '九死一生', '十中八九'
]

def convert_jp_pure_num(text):
    """转换纯数字序列"""
    result = ""
    for char in text:
        if char in jp_num_mapper:
            result += jp_num_mapper[char]
        else:
            result += char
    return result

def convert_jp_value_num(text):
    """转换日语数值表达"""
    # 处理十、百、千、万等单位
    if '点' in text or '・' in text:
        # 处理小数
        parts = re.split('[点・]', text)
        integer_part = parts[0] if parts[0] else '0'
        decimal_part = parts[1] if len(parts) > 1 else ''
        
        integer_value = calculate_jp_value(integer_part)
        decimal_str = convert_jp_pure_num(decimal_part)
        
        result = str(integer_value)
        if decimal_str:
            result += '.' + decimal_str
        return result
    else:
        return str(calculate_jp_value(text))

def calculate_jp_value(text):
    """计算日语数值"""
    value = 0
    temp = 0
    
    i = 0
    while i < len(text):
        char = text[i]
        
        # 处理多字符匹配（平假名/片假名）
        matched = False
        for length in [3, 2, 1]:  # 优先匹配长的
            if i + length <= len(text):
                substr = text[i:i+length]
                if substr in jp_value_mapper:
                    char_value = jp_value_mapper[substr]
                    
                    if substr in ['十', 'じゅう', 'ジュウ', '拾']:
                        temp = 10 if temp == 0 else temp * 10
                    elif substr in ['百', 'ひゃく', 'ヒャク']:
                        temp = (temp if temp > 0 else 1) * 100
                    elif substr in ['千', 'せん', 'セン']:
                        temp = (temp if temp > 0 else 1) * 1000
                    elif substr in ['万', 'まん', 'マン']:
                        value += temp if temp > 0 else 1
                        value *= 10000
                        temp = 0
                    elif substr in ['億', 'おく', 'オク']:
                        value += temp if temp > 0 else 1
                        value *= 100000000
                        temp = 0
                    else:  # 基础数字
                        temp += char_value
                    
                    i += length
                    matched = True
                    break
        
        if not matched:
            i += 1
    
    return value + temp

def convert_jp_percent(text):
    """转换百分比 パーセント -> %"""
    if 'パーセント' in text:
        num_part = text.replace('パーセント', '')
        return convert_jp_value_num(num_part) + '%'
    return text

def convert_jp_time(text):
    """转换时间表达 三時二十分 -> 3:20"""
    time_pattern = r'([零〇一二三四五六七八九十]+)時([零〇一二三四五六七八九十]+)分?'
    match = re.search(time_pattern, text)
    if match:
        hour = calculate_jp_value(match.group(1))
        minute = calculate_jp_value(match.group(2))
        replacement = f"{hour}:{minute:02d}"
        return re.sub(time_pattern, replacement, text)
    return text

def japanese_to_num(text):
    """主函数：日语ITN处理"""
    if not text:
        return text
    
    # 避免处理固定表达
    for idiom in jp_idioms:
        if idiom in text:
            return text
    
    # 处理百分比
    text = convert_jp_percent(text)
    
    # 处理时间
    text = convert_jp_time(text)
    
    # 处理一般数值
    # 匹配日语数字模式
    pattern = r'[零〇一二三四五六七八九十百千万億壱弐参肆伍陸漆捌玖拾いちにさんよんごろくななはちきゅうじゅうひゃくせんまんおくイチニサンヨンゴロクナナハチキュウジュウヒャクセンマンオクしちしくゼロ点・]+'
    
    def replace_match(match):
        matched_text = match.group(0)
        # 简单数字序列
        if re.match(r'^[零〇一二三四五六七八九ゼロ点・]+$', matched_text):
            return convert_jp_pure_num(matched_text)
        # 复杂数值
        else:
            return convert_jp_value_num(matched_text)
    
    result = re.sub(pattern, replace_match, text)
    return result

if __name__ == "__main__":
    # 测试用例
    test_cases = [
        "一二三四五",
        "十二",
        "二十三",
        "一百二十三",
        "一千二百三十四",
        "三時二十分",
        "五十パーセント",
        "二点五",
        "一万二千三百四十五"
    ]
    
    for case in test_cases:
        result = japanese_to_num(case)
        print(f"{case} -> {result}")