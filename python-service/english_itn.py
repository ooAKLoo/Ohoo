# coding: utf-8
'''
英语逆文本正则化 (English ITN)
将英语中的数字表达转换为阿拉伯数字

用法示例：
from english_itn import english_to_num
result = english_to_num('twenty three point five')  # -> 23.5
'''

import re

__all__ = ['english_to_num']

# 英语数字映射
en_num_mapper = {
    'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
    'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
    'ten': '10', 'eleven': '11', 'twelve': '12', 'thirteen': '13',
    'fourteen': '14', 'fifteen': '15', 'sixteen': '16', 'seventeen': '17',
    'eighteen': '18', 'nineteen': '19', 'twenty': '20', 'thirty': '30',
    'forty': '40', 'fifty': '50', 'sixty': '60', 'seventy': '70',
    'eighty': '80', 'ninety': '90', 'point': '.', 'dot': '.'
}

# 英语数值映射（计算用）
en_value_mapper = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
    'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
    'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13,
    'fourteen': 14, 'fifteen': 15, 'sixteen': 16, 'seventeen': 17,
    'eighteen': 18, 'nineteen': 19, 'twenty': 20, 'thirty': 30,
    'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70,
    'eighty': 80, 'ninety': 90,
    'hundred': 100, 'thousand': 1000, 'million': 1000000,
    'billion': 1000000000, 'trillion': 1000000000000
}

# 避免误转的英语固定表达
en_idioms = [
    'one way or another', 'two peas in a pod', 'three strikes',
    'four leaf clover', 'high five', 'six feet under',
    'seven seas', 'behind the eight ball', 'nine lives',
    'perfect ten', 'eleven o\'clock', 'twelve apostles'
]

def convert_en_pure_num(text):
    """转换纯数字序列"""
    words = text.lower().split()
    result = []
    for word in words:
        if word in en_num_mapper:
            result.append(en_num_mapper[word])
        else:
            result.append(word)
    return ' '.join(result)

def calculate_en_value(text):
    """计算英语数值"""
    words = text.lower().split()
    
    total = 0
    current = 0
    
    for word in words:
        if word in en_value_mapper:
            value = en_value_mapper[word]
            
            if value == 100:
                current = (current if current > 0 else 1) * 100
            elif value == 1000:
                total += current if current > 0 else 1
                total *= 1000
                current = 0
            elif value == 1000000:  # million
                total += current if current > 0 else 1
                total *= 1000000
                current = 0
            elif value == 1000000000:  # billion
                total += current if current > 0 else 1
                total *= 1000000000
                current = 0
            elif value == 1000000000000:  # trillion
                total += current if current > 0 else 1
                total *= 1000000000000
                current = 0
            else:
                current += value
    
    return total + current

def convert_en_value_num(text):
    """转换英语数值表达"""
    text_lower = text.lower()
    
    # 处理小数
    if 'point' in text_lower or 'dot' in text_lower:
        parts = re.split(r'\s*(?:point|dot)\s*', text_lower)
        integer_part = parts[0].strip() if parts[0].strip() else 'zero'
        decimal_part = parts[1].strip() if len(parts) > 1 else ''
        
        integer_value = calculate_en_value(integer_part)
        
        # 小数部分按单个数字处理
        decimal_str = ''
        if decimal_part:
            decimal_words = decimal_part.split()
            for word in decimal_words:
                if word in en_num_mapper and word not in ['point', 'dot']:
                    decimal_str += en_num_mapper[word]
        
        result = str(integer_value)
        if decimal_str:
            result += '.' + decimal_str
        return result
    else:
        return str(calculate_en_value(text))

def convert_en_percent(text):
    """转换百分比 percent -> %"""
    pattern = r'([a-zA-Z\s]+)\s+percent'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        num_part = match.group(1).strip()
        percentage = convert_en_value_num(num_part) + '%'
        return re.sub(pattern, percentage, text, flags=re.IGNORECASE)
    return text

def convert_en_time(text):
    """转换时间表达"""
    # 处理 "three thirty" -> "3:30"
    time_pattern = r'\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+(o\'clock|thirty|fifteen|forty five|[a-z]+)\b'
    
    def time_replace(match):
        hour_word = match.group(1)
        minute_word = match.group(2)
        
        if hour_word in en_value_mapper:
            hour = en_value_mapper[hour_word]
            
            if minute_word == "o'clock":
                return f"{hour}:00"
            elif minute_word == "thirty":
                return f"{hour}:30"
            elif minute_word == "fifteen":
                return f"{hour}:15"
            elif minute_word == "forty five":
                return f"{hour}:45"
            elif minute_word in en_value_mapper:
                minute = en_value_mapper[minute_word]
                return f"{hour}:{minute:02d}"
        
        return match.group(0)
    
    return re.sub(time_pattern, time_replace, text, flags=re.IGNORECASE)

def convert_en_ordinal(text):
    """转换序数词 first -> 1st, second -> 2nd"""
    ordinal_map = {
        'first': '1st', 'second': '2nd', 'third': '3rd', 'fourth': '4th',
        'fifth': '5th', 'sixth': '6th', 'seventh': '7th', 'eighth': '8th',
        'ninth': '9th', 'tenth': '10th', 'eleventh': '11th', 'twelfth': '12th',
        'thirteenth': '13th', 'fourteenth': '14th', 'fifteenth': '15th',
        'sixteenth': '16th', 'seventeenth': '17th', 'eighteenth': '18th',
        'nineteenth': '19th', 'twentieth': '20th', 'thirtieth': '30th'
    }
    
    result = text
    for ordinal, number in ordinal_map.items():
        result = re.sub(r'\b' + ordinal + r'\b', number, result, flags=re.IGNORECASE)
    
    return result

def english_to_num(text):
    """主函数：英语ITN处理"""
    if not text:
        return text
    
    # 避免处理固定表达
    text_lower = text.lower()
    for idiom in en_idioms:
        if idiom in text_lower:
            return text
    
    # 处理百分比
    text = convert_en_percent(text)
    
    # 处理时间
    text = convert_en_time(text)
    
    # 处理序数词
    text = convert_en_ordinal(text)
    
    # 处理一般数值
    # 匹配英语数字模式
    pattern = r'\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|trillion|point|dot)(?:\s+(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|trillion|point|dot))*\b'
    
    def replace_match(match):
        matched_text = match.group(0)
        # 如果包含point或dot，作为小数处理
        if 'point' in matched_text.lower() or 'dot' in matched_text.lower():
            return convert_en_value_num(matched_text)
        # 检查是否为简单的单个数字
        elif len(matched_text.split()) == 1 and matched_text.lower() in en_num_mapper:
            return en_num_mapper[matched_text.lower()]
        # 复杂数值
        else:
            return convert_en_value_num(matched_text)
    
    result = re.sub(pattern, replace_match, text, flags=re.IGNORECASE)
    return result

if __name__ == "__main__":
    # 测试用例
    test_cases = [
        "twenty three",
        "one hundred twenty three",
        "three point five",
        "fifty percent",
        "three thirty",
        "first place",
        "two thousand twenty four",
        "one million five hundred thousand",
        "zero point five"
    ]
    
    for case in test_cases:
        result = english_to_num(case)
        print(f"'{case}' -> '{result}'")