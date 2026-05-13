import os
import sys
import subprocess
from pathlib import Path
import argparse
import json
import re

# 自动安装缺失的依赖
try:
    import chardet
except ImportError:
    print("chardet 未安装，正在安装...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "chardet", "--no-cache-dir"])
    import chardet

# ====== 字体配置 ======
# 这里可以方便地修改字体配置
FONT_CONFIG = {
    "simplified_chinese": {
        "font_name": "方正准圆简体",
        "font_file": "方正准圆简体.ttf",
        "default_font_name": "Microsoft YaHei"
    },
    "japanese_traditional": {
        "font_name": "夏花绚烂前程似锦",
        "font_file": "夏花绚烂前程似锦.ttf",
        "default_font_name": "Microsoft YaHei"
    }
}

class SubtitleConverter:
    """字幕转换器类"""
    def __init__(self):
        self.supported_input_formats = {'.srt', '.vtt', '.lrc', '.ssa', '.ass', '.txt'}
        self.fonts_dir = Path(__file__).parent / "TTF"
    
    def process_output_filename(self, input_path, karaoke_mode=False, is_batch=False, real_karaoke_effect=0, output_dir=None):
        """处理输出文件名"""
        input_path = Path(input_path)
        stem = input_path.stem
        
        # 如果是批量模式且文件名包含 (ASS)，则跳过处理
        if is_batch and '(ASS)' in stem:
            return None
        
        # 根据real_karaoke_effect确定目标标记
        if real_karaoke_effect == 'A':  # 全选模式
            target_marker = ' (ASS)'
            if ' (ASS)' in stem:
                new_stem = stem.replace(' (ASS)', target_marker)
            elif '(ASS)' in stem:
                new_stem = stem.replace('(ASS)', target_marker)
            else:
                new_stem = stem + target_marker
        elif real_karaoke_effect == 1 or real_karaoke_effect == 2 or str(real_karaoke_effect) in ['1', '2']:  # KTV效果或提词器效果
            target_marker = ' (ASS_1)'
            if ' (ASS)' in stem:
                new_stem = stem.replace(' (ASS)', target_marker)
            elif '(ASS)' in stem:
                new_stem = stem.replace('(ASS)', target_marker)
            else:
                new_stem = stem + target_marker
        else:  # 默认效果
            if karaoke_mode:
                target_marker = ' (ASS)'
            else:
                target_marker = ' (SSA)'
            
            if ' (ASS)' in stem and karaoke_mode:
                new_stem = stem
            elif '(ASS)' in stem and karaoke_mode:
                new_stem = stem
            else:
                new_stem = stem
                replace_markers = [' (SSA)', ' (SRT)', '(SSA)', '(SRT)']
                for replace_marker in replace_markers:
                    if replace_marker in new_stem:
                        new_stem = new_stem.replace(replace_marker, target_marker)
                        break
                if new_stem == stem and karaoke_mode:
                    new_stem = f"{stem}{target_marker}"
        
        # 确定输出目录
        if output_dir:
            output_dir = Path(output_dir)
            output_path = output_dir / f"{new_stem}.ass"
        else:
            output_path = input_path.parent / f"{new_stem}.ass"
        
        return output_path
    
    def detect_encoding(self, file_path):
        """检测文件编码"""
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                return result['encoding'] or 'utf-8'
        except:
            return 'utf-8'
    
    def contains_japanese_text(self, text):
        """精确检测文本是否包含日文字符（仅平假名、片假名）"""
        if not text:
            return False
        
        # 精确的日文字符范围（只包含平假名和片假名）
        japanese_ranges = [
            (0x3040, 0x309F),  # 平假名 (Hiragana)
            (0x30A0, 0x30FF),  # 片假名 (Katakana)
            (0x31F0, 0x31FF),  # 片假名音标扩展
            (0xFF66, 0xFF9F),  # 半角片假名
        ]
        
        # 常用日语标点（这些单独出现时不应触发日语字体）
        japanese_punctuation = {'・', '。', '、', '！', '？', '（', '）', '「', '」', '『', '』'}
        
        # 统计日文字符数量
        japanese_count = 0
        non_punctuation_japanese_count = 0
        total_chars = 0
        detected_japanese_chars = []
        
        for char in text:
            total_chars += 1
            code_point = ord(char)
            is_japanese = False
            for start, end in japanese_ranges:
                if start <= code_point <= end:
                    is_japanese = True
                    break
            
            if is_japanese:
                japanese_count += 1
                detected_japanese_chars.append(f"{char} (0x{code_point:04X})")
                # 检查是否为非标点日文字符
                if char not in japanese_punctuation:
                    non_punctuation_japanese_count += 1
        
        # 显示关键识别逻辑（无论是否满足阈值）
        if japanese_count > 0:
            print(f"      识别逻辑: 检测到 {japanese_count} 个日文字符，占比 {japanese_count/total_chars*100:.1f}%")
            if detected_japanese_chars:
                print(f"      示例日文字符: {', '.join(detected_japanese_chars[:3])}")
            if non_punctuation_japanese_count > 0:
                print(f"      其中非标点日文字符: {non_punctuation_japanese_count} 个")
            else:
                print(f"      全部为日文标点，采用简体字体")
        
        # 如果包含非标点日文字符，无论数量多少，都认为是日文
        if non_punctuation_japanese_count > 0:
            return True
        
        # 只有当日文字符占比超过10%时才认为是日文
        if total_chars > 0 and japanese_count / total_chars > 0.1:
            return True
        
        return False
    
    def contains_traditional_chinese_text(self, text):
        """精确检测文本是否包含繁体中文"""
        if not text:
            return False
        
        # 繁体中文常见字符范围（基于Unicode区块）
        traditional_ranges = [
            (0x4E00, 0x9FFF),   # CJK统一表意文字（包含简繁）
        ]
        
        # 繁体中文特有字符（一些在简体中不常用或写法不同的字）
        traditional_chars = set('麼麼為為於於裡裡後後個個時體國學與麼麼')
        
        # 检查繁体特有字符
        detected_traditional_chars = []
        for char in text:
            if char in traditional_chars:
                detected_traditional_chars.append(char)
        
        # 显示关键识别逻辑（无论是否满足阈值）
        if detected_traditional_chars:
            print(f"      识别逻辑: 检测到 {len(detected_traditional_chars)} 个繁体特有字符")
            print(f"      示例繁体字符: {', '.join(detected_traditional_chars[:3])}")
            return True
        
        # 基于字符使用频率的简单检测（可扩展更复杂的检测逻辑）
        traditional_indicators = ['麼', '為', '於', '裡', '後', '個', '體', '國', '學', '與']
        traditional_count = sum(1 for char in text if char in traditional_indicators)
        
        # 显示关键识别逻辑（无论是否满足阈值）
        if traditional_count > 0:
            print(f"      识别逻辑: 检测到 {traditional_count} 个繁体特征字符，占比 {traditional_count/len(text)*100:.1f}%")
        
        # 如果包含繁体特征字符，无论数量多少，都认为是繁体中文
        if traditional_count > 0:
            return True
        
        return False

    def detect_language_from_content(self, content):
        """从字幕内容精确检测语言"""
        if not content:
            return 'chinese'  # 默认简体中文
        
        # 移除ASS标签和特殊字符
        clean_content = re.sub(r'\{[^}]*\}', '', content)  # 移除ASS标签
        clean_content = re.sub(r'[^\u4e00-\u9fff\u3040-\u30ff\u3100-\u312f\u31f0-\u31ff\uff00-\uffef]', '', clean_content)  # 只保留中日文字符
        
        if not clean_content:
            return 'chinese'  # 如果没有检测到字符，默认简体中文
        
        # 检测是否包含日文字符（平假名、片假名）
        if self.contains_japanese_text(clean_content):
            return 'japanese'
        
        # 检测是否包含繁体中文
        if self.contains_traditional_chinese_text(clean_content):
            return 'traditional_chinese'
        
        # 如果只包含中文字符，则为简体中文
        chinese_pattern = re.compile(r'[\u4e00-\u9fff]')
        if chinese_pattern.search(clean_content):
            return 'chinese'
        
        return 'chinese'  # 默认简体中文

    def detect_language_from_filename(self, filename):
        """从文件名识别语言标识"""
        filename_lower = filename.lower()
        
        # 语言标识映射
        language_patterns = {
            'chi': ['chi', 'chs', 'zh', 'zh-cn', 'chinese', '中文', '简体'],
            'kor': ['kor', 'ko', 'korean', '韩语', '韩文'],
            'jpn': ['jpn', 'ja', 'japanese', '日语', '日文'],
            'eng': ['eng', 'en', 'english', '英语', '英文'],
            'fre': ['fre', 'fr', 'french', '法语', '法文'],
            'ger': ['ger', 'de', 'german', '德语', '德文'],
            'spa': ['spa', 'es', 'spanish', '西班牙语', '西文'],
            'ita': ['ita', 'it', 'italian', '意大利语', '意文'],
            'rus': ['rus', 'ru', 'russian', '俄语', '俄文'],
        }
        
        for lang_code, patterns in language_patterns.items():
            for pattern in patterns:
                if pattern in filename_lower:
                    return lang_code
        
        return 'und'  # 未知语言
    
    def detect_subtitle_language(self, subtitle_path):
        """检测字幕文件的语种"""
        try:
            # 首先从文件名检测
            filename = Path(subtitle_path).name
            lang_from_filename = self.detect_language_from_filename(filename)
            if lang_from_filename != 'und':
                return lang_from_filename
            
            # 从内容精确检测
            encoding = self.detect_encoding(subtitle_path)
            with open(subtitle_path, 'r', encoding=encoding, errors='ignore') as f:
                content = f.read(10000)  # 读取前10000个字符进行检测
            
            # 使用精确的内容检测
            if self.contains_japanese_text(content):
                return 'jpn'
            else:
                # 检查是否包含中文字符
                chinese_pattern = re.compile(r'[\u4e00-\u9fff]')
                if chinese_pattern.search(content):
                    return 'chi'
                else:
                    return 'und'  # 未知语言
        except:
            return 'chi'  # 默认使用中文
    
    def get_language_name(self, language_code):
        """获取语言代码对应的语言名称"""
        language_names = {
            'chi': '中文', 'zh': '中文', 'chs': '中文', 'chinese': '中文',
            'kor': '韩语', 'ko': '韩语', 'korean': '韩语',
            'jpn': '日语', 'ja': '日语', 'japanese': '日语',
            'eng': '英语', 'en': '英语', 'english': '英语',
            'fre': '法语', 'fr': '法语', 'french': '法语',
            'ger': '德语', 'de': '德语', 'german': '德语',
            'spa': '西班牙语', 'es': '西班牙语', 'spanish': '西班牙语',
            'ita': '意大利语', 'it': '意大利语', 'italian': '意大利语',
            'rus': '俄语', 'ru': '俄语', 'russian': '俄语',
            'und': '未知语言'
        }
        
        return language_names.get(language_code.lower(), f"语言{language_code}")
    
    def get_language_type_from_content(self, subtitle_path):
        """从字幕内容精确检测语言类型"""
        try:
            encoding = self.detect_encoding(subtitle_path)
            with open(subtitle_path, 'r', encoding=encoding, errors='ignore') as f:
                content = f.read(10000)  # 读取前10000个字符进行检测
            
            # 使用精确的语言检测
            return self.detect_language_from_content(content)
        except:
            return 'chinese'
    
    def generate_ass_header(self, language_type, enable_custom_font=True):
        """生成ASS文件头部"""
        if enable_custom_font:
            if language_type in ['japanese', 'traditional_chinese']:
                font_config = FONT_CONFIG['japanese_traditional']
                font_name = font_config['font_name']
            else:
                font_config = FONT_CONFIG['simplified_chinese']
                font_name = font_config['font_name']
        else:
            # 不使用自定义字体时的默认字体
            if language_type in ['japanese', 'traditional_chinese']:
                font_config = FONT_CONFIG['japanese_traditional']
                font_name = font_config['default_font_name']
            else:
                font_config = FONT_CONFIG['simplified_chinese']
                font_name = font_config['default_font_name']
        
        header = f"""[Script Info]
; Generated by Subtitle Converter
Title:
ScriptType: v4.00+
Collisions: Normal
PlayResX: 1920
PlayResY: 1080
Timer: 100.0000
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke,{font_name},50,&H00FF80FF,&H00FFFFFF,&H00804000,&H00000000,-1,0,0,0,100,100,0,0,1,2,1,2,5,5,2,134
Style: Default,{font_name},50,&H00FFFFFF,&H00000000,&H00804000,&H00000000,-1,0,0,0,100,100,0,0,1,2,1,2,5,5,2,134

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        return header
    
    def srt_to_ass(self, srt_content):
        """将SRT格式转换为ASS格式"""
        lines = srt_content.split('\n')
        ass_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # 跳过空行和序号行
            if not line or line.isdigit():
                i += 1
                continue
            
            # 检查是否是时间轴行
            if '-->' in line:
                # 解析时间轴
                time_parts = line.split('-->')
                if len(time_parts) == 2:
                    start_time = self.srt_time_to_ass(time_parts[0].strip())
                    end_time = self.srt_time_to_ass(time_parts[1].strip())
                    
                    # 读取文本行
                    i += 1
                    text_lines = []
                    while i < len(lines) and lines[i].strip():
                        text_lines.append(lines[i].strip())
                        i += 1
                    
                    if text_lines:
                        text = '\\N'.join(text_lines)
                        ass_line = f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}"
                        ass_lines.append(ass_line)
                else:
                    i += 1
            else:
                i += 1
        
        return ass_lines
    
    def srt_time_to_ass(self, srt_time):
        """将SRT时间格式转换为ASS时间格式"""
        # SRT格式: 00:00:01,000
        # ASS格式: 0:00:01.00
        srt_time = srt_time.replace(',', '.')
        parts = srt_time.split(':')
        
        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds_parts = parts[2].split('.')
            seconds = int(seconds_parts[0])
            milliseconds = seconds_parts[1] if len(seconds_parts) > 1 else "00"
            
            # 确保毫秒是2位数
            if len(milliseconds) > 2:
                milliseconds = milliseconds[:2]
            elif len(milliseconds) == 1:
                milliseconds = milliseconds + "0"
            
            return f"{hours}:{minutes:02d}:{seconds:02d}.{milliseconds}"
        
        return srt_time
    
    def vtt_to_ass(self, vtt_content):
        """将VTT格式转换为ASS格式"""
        lines = vtt_content.split('\n')
        ass_lines = []
        i = 0
        
        # 跳过WEBVTT头部
        while i < len(lines) and lines[i].strip().upper() != 'WEBVTT':
            i += 1
        
        if i < len(lines):
            i += 1  # 跳过WEBVTT行
        
        while i < len(lines):
            line = lines[i].strip()
            
            # 跳过空行和提示标识行
            if not line or '-->' not in line:
                i += 1
                continue
            
            # 解析时间轴
            if '-->' in line:
                time_parts = line.split('-->')
                if len(time_parts) == 2:
                    start_time = self.vtt_time_to_ass(time_parts[0].strip())
                    end_time = self.vtt_time_to_ass(time_parts[1].strip())
                    
                    # 读取文本行
                    i += 1
                    text_lines = []
                    while i < len(lines) and lines[i].strip():
                        text_lines.append(lines[i].strip())
                        i += 1
                    
                    if text_lines:
                        text = '\\N'.join(text_lines)
                        ass_line = f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}"
                        ass_lines.append(ass_line)
                else:
                    i += 1
            else:
                i += 1
        
        return ass_lines
    
    def vtt_time_to_ass(self, vtt_time):
        """将VTT时间格式转换为ASS时间格式"""
        # VTT格式: 00:00:01.000
        # ASS格式: 0:00:01.00
        vtt_time = vtt_time.replace('.', ':').replace(',', '.')
        parts = vtt_time.split(':')
        
        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds_parts = parts[2].split('.')
            seconds = int(seconds_parts[0])
            milliseconds = seconds_parts[1] if len(seconds_parts) > 1 else "00"
            
            # 确保毫秒是2位数
            if len(milliseconds) > 2:
                milliseconds = milliseconds[:2]
            elif len(milliseconds) == 1:
                milliseconds = milliseconds + "0"
            
            return f"{hours}:{minutes:02d}:{seconds:02d}.{milliseconds}"
        
        return vtt_time
    
    def detect_file_content_format(self, file_path):
        """检测文件内容格式"""
        try:
            encoding = self.detect_encoding(file_path)
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                content = f.read(10000)  # 读取前10000个字符进行检测
            
            if '[Script Info]' in content and '[Events]' in content:
                return 'ass'
            elif any('--> ' in line for line in content.split('\n')):
                return 'srt'
            elif any('WEBVTT' in line for line in content.split('\n')):
                return 'vtt'
            elif any(re.match(r'^\[\d{2}:\d{2}\.\d{2}\]', line) for line in content.split('\n')):
                return 'lrc'
            else:
                return 'txt'
        except Exception:
            return 'txt'
    
    def convert_subtitle(self, input_path, output_path=None, enable_custom_font=True, karaoke_mode=False, is_batch=False):
        """转换单个字幕文件为ASS格式"""
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"字幕文件不存在: {input_path}")
        
        # 处理输出文件名
        if output_path is None:
            output_path = self.process_output_filename(input_path, karaoke_mode, is_batch)
            if output_path is None:  # 跳过处理
                print(f"跳过处理 (已包含ASS): {input_path.name}")
                return None
        
        output_path = Path(output_path)
        
        # 从内容精确检测语言类型
        language_type = self.get_language_type_from_content(input_path)
        
        # 语言名称映射
        language_names = {
            'japanese': '日文',
            'traditional_chinese': '繁体中文', 
            'chinese': '简体中文'
        }
        language_name = language_names.get(language_type, '简体中文')
        
        # 字体名称
        if enable_custom_font:
            if language_type in ['japanese', 'traditional_chinese']:
                font_config = FONT_CONFIG['japanese_traditional']
                font_used = font_config['font_name']
            else:
                font_config = FONT_CONFIG['simplified_chinese']
                font_used = font_config['font_name']
        else:
            if language_type in ['japanese', 'traditional_chinese']:
                font_config = FONT_CONFIG['japanese_traditional']
                font_used = font_config['default_font_name']
            else:
                font_config = FONT_CONFIG['simplified_chinese']
                font_used = font_config['default_font_name']
        
        # 检测文件内容格式
        content_format = self.detect_file_content_format(input_path)
        file_ext = input_path.suffix.lower()
        
        print(f"转换字幕: {input_path.name}")
        print(f"文件扩展名: {file_ext}")
        print(f"内容格式: {content_format}")
        print(f"检测语言: {language_name} (基于内容精确分析)")
        print(f"使用字体: {font_used}")
        print(f"输出文件: {output_path.name}")
        
        # 读取原始文件
        encoding = self.detect_encoding(input_path)
        with open(input_path, 'r', encoding=encoding, errors='ignore') as f:
            content = f.read()
        
        # 根据文件类型转换
        if content_format == 'ass':
            # 已经是ASS格式，直接复制并更新样式
            ass_content = content
        elif content_format == 'srt':
            ass_events = self.srt_to_ass(content)
            ass_content = self.generate_ass_header(language_type, enable_custom_font)
            ass_content += '\n'.join(ass_events)
        elif content_format == 'vtt':
            ass_events = self.vtt_to_ass(content)
            ass_content = self.generate_ass_header(language_type, enable_custom_font)
            ass_content += '\n'.join(ass_events)
        else:
            # 对于不支持的格式，尝试作为文本处理
            lines = content.split('\n')
            ass_events = []
            for line in lines:
                if line.strip():
                    # 简单地将每行文本作为独立的字幕行，持续1秒
                    ass_events.append(f"Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,{line.strip()}")
            
            ass_content = self.generate_ass_header(language_type, enable_custom_font)
            ass_content += '\n'.join(ass_events)
        
        # 写入输出文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(ass_content)
        
        print(f"转换完成: {output_path.name}")
        return output_path
    
    def batch_convert_subtitles(self, input_dir, output_dir=None, enable_custom_font=True, karaoke_mode=False):
        """批量转换字幕文件"""
        input_dir = Path(input_dir)
        
        if not input_dir.exists():
            raise FileNotFoundError(f"输入目录不存在: {input_dir}")
        
        if output_dir is None:
            output_dir = input_dir / "converted"
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"批量转换字幕文件:")
        print(f"输入目录: {input_dir}")
        print(f"输出目录: {output_dir}")
        print(f"卡拉OK模式: {'启用' if karaoke_mode else '禁用'}")
        
        converted_files = []
        
        # 查找所有支持的字幕文件
        for ext in self.supported_input_formats:
            for file_path in input_dir.glob(f"*{ext}"):
                try:
                    # 处理输出文件名
                    output_filename = self.process_output_filename(file_path, karaoke_mode, is_batch=True)
                    if output_filename is None:  # 跳过处理
                        continue
                    
                    output_path = output_dir / output_filename.name
                    result = self.convert_subtitle(
                        file_path, output_path, enable_custom_font, karaoke_mode, is_batch=True
                    )
                    if result:  # 只有成功转换才添加到列表
                        converted_files.append(result)
                except Exception as e:
                    print(f"转换失败 {file_path.name}: {e}")
        
        print(f"\n批量转换完成: {len(converted_files)} 个文件")
        return converted_files

class MKVPacker:
    def __init__(self):
        self.supported_video_formats = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
        self.supported_subtitle_formats = {'.ass', '.srt', '.ssa', '.vtt'}
        self.fonts_dir = Path(__file__).parent / "TTF"
        self.subtitle_converter = SubtitleConverter()
        # 初始化工具路径
        self.mkvmerge_path = self.detect_mkvmerge_path()
        self.mkvextract_path = self.detect_mkvextract_path()
    
    def detect_mkvmerge_path(self):
        """检测MKVToolNix路径"""
        # 项目自带的MKVToolNix路径
        project_mkvmerge = Path(__file__).parent / "Python" / "MKVToolNix" / "mkvmerge.exe"
        if project_mkvmerge.exists():
            return str(project_mkvmerge)
        # 尝试在上级目录的Python文件夹中查找
        python_mkvmerge = Path(__file__).parent.parent / "Python" / "MKVToolNix" / "mkvmerge.exe"
        if python_mkvmerge.exists():
            return str(python_mkvmerge)
        # 系统PATH中的mkvmerge
        return "mkvmerge"
    
    def detect_mkvextract_path(self):
        """检测mkvextract路径"""
        # 项目自带的mkvextract路径
        project_mkvextract = Path(__file__).parent / "Python" / "MKVToolNix" / "mkvextract.exe"
        if project_mkvextract.exists():
            return str(project_mkvextract)
        # 尝试在上级目录的Python文件夹中查找
        python_mkvextract = Path(__file__).parent.parent / "Python" / "MKVToolNix" / "mkvextract.exe"
        if python_mkvextract.exists():
            return str(python_mkvextract)
        # 系统PATH中的mkvextract
        return "mkvextract"
        
    def check_mkvtoolnix_available(self):
        """检查MKVToolNix是否可用"""
        try:
            result = subprocess.run([self.mkvmerge_path, '--version'], 
                                  capture_output=True, text=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def safe_decode(self, byte_string):
        """安全解码字节字符串"""
        if not byte_string:
            return ""
        
        encodings = ['utf-8', 'gbk', 'gb2312', 'big5', 'latin-1']
        
        for encoding in encodings:
            try:
                return byte_string.decode(encoding, errors='ignore')
            except UnicodeDecodeError:
                continue
        
        return ""
    
    def contains_japanese_text(self, text):
        """精确检测文本是否包含日文字符（仅平假名、片假名）"""
        return self.subtitle_converter.contains_japanese_text(text)
    
    def detect_language_from_content(self, content):
        """从字幕内容精确检测语言"""
        return self.subtitle_converter.detect_language_from_content(content)
    
    def detect_subtitle_language(self, subtitle_path):
        """检测字幕文件的语种"""
        return self.subtitle_converter.detect_subtitle_language(subtitle_path)
    
    def get_language_type_from_content(self, subtitle_path):
        """从字幕内容精确检测语言类型"""
        try:
            encoding = self.subtitle_converter.detect_encoding(subtitle_path)
            with open(subtitle_path, 'r', encoding=encoding, errors='ignore') as f:
                content = f.read(10000)  # 读取前10000个字符进行检测
            
            # 使用精确的语言检测
            return self.detect_language_from_content(content)
        except:
            return 'chinese'
    
    def update_ass_styles(self, subtitle_path, language_type, enable_custom_font=True):
        """更新ASS文件的样式（只修改字体名称，不修改字体大小）"""
        try:
            with open(subtitle_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 根据语言类型选择字体配置
            if language_type in ['japanese', 'traditional_chinese']:
                font_config = FONT_CONFIG['japanese_traditional']
            else:
                font_config = FONT_CONFIG['simplified_chinese']
            
            # 确定字体名称
            if enable_custom_font:
                font_name = font_config['font_name']
            else:
                font_name = font_config['default_font_name']
            
            print(f"  更新ASS字幕字体: {font_name}")
            
            # 修复关键BUG：正确识别和处理Format行和Style行
            lines = content.split('\n')
            updated_lines = []
            
            # 首先找到[V4+ Styles]部分
            in_styles_section = False
            
            for line in lines:
                stripped_line = line.strip()
                
                # 检测是否进入[V4+ Styles]部分
                if stripped_line == '[V4+ Styles]':
                    in_styles_section = True
                    updated_lines.append(line)
                    continue
                    
                # 检测是否离开[V4+ Styles]部分
                elif stripped_line.startswith('[') and stripped_line.endswith(']') and stripped_line != '[V4+ Styles]':
                    in_styles_section = False
                
                # 在[V4+ Styles]部分内，只处理Style行，不处理Format行
                if in_styles_section and stripped_line.startswith('Style:'):
                    # 这是样式行，分割字段
                    parts = stripped_line.split(',')
                    if len(parts) >= 3:
                        # 第一个字段是 "Style: Default" 或 "Style: 样式名"
                        # 第二个字段是字体名（索引1）
                        # 第三个字段是字体大小（索引2）
                        
                        # 替换字体名（第二个字段）
                        old_font = parts[1]
                        parts[1] = font_name
                        
                        # 重新组合行，保持原始缩进
                        if line.startswith(' '):
                            indent_len = len(line) - len(line.lstrip())
                            indent = line[:indent_len]
                            updated_line = indent + ','.join(parts)
                        else:
                            updated_line = ','.join(parts)
                            
                        updated_lines.append(updated_line)
                        continue
                
                # 其他行（包括Format行）保持不变
                updated_lines.append(line)
        
            # 重新组合内容
            updated_content = '\n'.join(updated_lines)
            
            # 验证更新是否正确
            style_lines = [line for line in updated_content.split('\n') if line.strip().startswith('Style:')]
            font_updated_count = 0
            for style_line in style_lines:
                parts = style_line.strip().split(',')
                if len(parts) >= 2 and parts[1] == font_name:
                    font_updated_count += 1
            
            if font_updated_count == len(style_lines) and len(style_lines) > 0:
                print(f"  成功更新 {font_updated_count} 个样式行的字体为: {font_name}")
            else:
                print(f"  字体更新可能失败，检查格式是否正确")
                # 调试输出前几行
                print(f"  前5行内容:")
                for i, line in enumerate(updated_content.split('\n')[:5]):
                    print(f"    行{i+1}: {line}")
                return content
            
            # 写回文件
            with open(subtitle_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            return updated_content
            
        except Exception as e:
            print(f"更新ASS样式失败: {e}")
            import traceback
            traceback.print_exc()
            return content
    
    def get_font_file(self, language_type):
        """根据语言类型获取字体文件路径"""
        if language_type in ['japanese', 'traditional_chinese']:
            font_config = FONT_CONFIG['japanese_traditional']
            font_file_name = font_config['font_file']
        else:
            font_config = FONT_CONFIG['simplified_chinese']
            font_file_name = font_config['font_file']
        
        # 如果字体文件名为空，则不添加字体
        if not font_file_name:
            return None
        
        font_file = self.fonts_dir / font_file_name
        
        if font_file.exists():
            return font_file
        else:
            print(f"提示: 字体文件不存在或未配置: {font_file}")
            return None
    
    def process_subtitle_fonts(self, subtitle_tracks, enable_custom_font=True):
        """处理字幕字体"""
        if not enable_custom_font:
            print("\n禁用自定义字体模式，使用系统默认字体...")
            return subtitle_tracks, []
        
        print("\n启用个性化字体模式...")
        
        processed_tracks = []
        font_files = set()
        
        for track in subtitle_tracks:
            subtitle_path = Path(track['path'])
            
            # 如果不是ASS格式，先转换
            if subtitle_path.suffix.lower() != '.ass':
                print(f"  转换字幕格式: {subtitle_path.name} -> ASS")
                try:
                    converted_path = subtitle_path.with_suffix('.ass')
                    self.subtitle_converter.convert_subtitle(
                        subtitle_path, converted_path, enable_custom_font, 
                        karaoke_mode=False, is_batch=False
                    )
                    track['path'] = str(converted_path)
                    subtitle_path = converted_path
                except Exception as e:
                    print(f"  转换失败: {e}")
                    continue
            
            # 精确检测语言类型（根据实际内容）
            language_type = self.get_language_type_from_content(subtitle_path)
            
            # 语言名称显示
            if language_type == 'japanese':
                lang_name = "日文"
            elif language_type == 'traditional_chinese':
                lang_name = "繁体中文"
            else:
                lang_name = "简体中文"
                
            print(f"  检测字幕 {subtitle_path.name}: {lang_name} (基于内容精确分析)")
            
            # 更新ASS样式（只修改字体名称，不修改大小）
            self.update_ass_styles(subtitle_path, language_type, enable_custom_font)
            print(f"  更新{lang_name}样式成功（只修改字体名称）")
            
            # 获取字体文件（可能为空）
            font_file = self.get_font_file(language_type)
            if font_file:
                font_files.add(font_file)
                print(f"  使用字体文件: {font_file.name}")
            else:
                print(f"  提示: 未配置字体文件或字体文件不存在，仅替换字体名称")
            
            processed_tracks.append(track)
        
        if font_files:
            print(f"  总计添加 {len(font_files)} 个字体文件")
        else:
            print(f"  提示: 无字体文件添加，仅替换ASS字体名称")
        
        return processed_tracks, list(font_files)
    
    def package_subtitles_only(self, video_path, subtitle_tracks, output_path=None, enable_custom_font=True):
        """
        只替换字幕，保留原视频和原音频，完全保持原始轨道顺序和默认状态
        
        Args:
            video_path: 视频文件路径
            subtitle_tracks: 字幕轨道列表，每个元素包含:
                {'path': 字幕文件路径, 'language': 语言代码, 'is_default': 是否默认, 'original_track_id': 原始轨道ID}
            output_path: 输出文件路径
            enable_custom_font: 是否启用自定义字体
        """
        if not self.check_mkvtoolnix_available():
            raise Exception("MKVToolNix未安装或不在PATH中")
        
        video_path = Path(video_path)
        
        if not video_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        # 验证字幕文件
        for track in subtitle_tracks:
            subtitle_path = Path(track['path'])
            if not subtitle_path.exists():
                raise FileNotFoundError(f"字幕文件不存在: {subtitle_path}")
        
        # 设置输出路径
        if output_path is None:
            base_name = video_path.stem
            output_path = video_path.parent / f"{base_name} (ASS).mkv"
        else:
            output_path = Path(output_path)
        
        print("=" * 60)
        print("MKV字幕替换工具 - 完全保持原始轨道设置")
        print("=" * 60)
        print(f"视频文件: {video_path.name}")
        print(f"字幕轨道数: {len(subtitle_tracks)}")
        print(f"输出文件: {output_path}")
        print(f"自定义字体: {'启用' if enable_custom_font else '禁用'}")
        
        # 处理字幕字体
        processed_tracks, font_files = self.process_subtitle_fonts(subtitle_tracks, enable_custom_font)
        
        # 构建mkvmerge命令
        cmd = [self.mkvmerge_path, '-o', str(output_path)]
        
        # 添加视频轨道（保留原音频，移除原字幕和字体）
        cmd.extend(['--no-subtitles', '--no-attachments', str(video_path)])
        
        # 按照原始轨道ID排序，保持原始顺序
        subtitle_tracks_sorted = sorted(
            processed_tracks,
            key=lambda x: int(x.get('original_track_id', 0)) if x.get('original_track_id') and x.get('original_track_id').isdigit() else 0
        )
        
        print("\n最终轨道设置:")
        for i, track in enumerate(subtitle_tracks_sorted):
            language = track.get('language', 'und')
            is_default = track.get('is_default', False)
            original_id = track.get('original_track_id', '未知')
            track_name = track.get('track_name', f'{language}字幕')
            status = "默认" if is_default else "非默认"
            print(f"  轨道{original_id}: {language} - {status} - 名称: {track_name}")
        
        # 添加所有字幕轨道，完全保持原始默认状态
        for track in subtitle_tracks_sorted:
            subtitle_path = Path(track['path'])
            language = track.get('language', 'und')
            is_default = track.get('is_default', False)
            original_id = track.get('original_track_id', '未知')
            track_name = track.get('track_name', f'{language}字幕')
            
            # 添加轨道参数
            cmd.extend(['--language', f'0:{language}'])
            cmd.extend(['--track-name', f'0:{track_name}'])
            
            # 完全保持原始默认状态
            if is_default:
                cmd.extend(['--default-track', '0:yes'])
                print(f"添加字幕轨道 {original_id}: 语言={language}, 默认=是, 名称={track_name}")
            else:
                cmd.extend(['--default-track', '0:no'])
                print(f"添加字幕轨道 {original_id}: 语言={language}, 默认=否, 名称={track_name}")
            
            cmd.append(str(subtitle_path))
        
        # 添加字体文件（如果存在）
        if enable_custom_font and font_files:
            print("\n添加字体文件:")
            for font_file in font_files:
                cmd.extend(['--attachment-mime-type', 'application/x-truetype-font'])
                cmd.extend(['--attach-file', str(font_file)])
                print(f"  [OK] {font_file.name}")
        elif enable_custom_font and not font_files:
            print("\n提示: 启用了自定义字体但未配置字体文件，仅替换ASS字体名称")
        
        try:
            print("\n执行MKV打包命令...")
            print("命令:", ' '.join(cmd))
            
            # 修复编码问题：设置环境变量确保UTF-8编码
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                env=env
            )
            
            timeout = 300
            try:
                stdout_bytes, stderr_bytes = process.communicate(timeout=timeout)
                
                stdout = self.safe_decode(stdout_bytes)
                stderr = self.safe_decode(stderr_bytes)
                
                if process.returncode == 0:
                    print(f"\nMKV打包完成: {output_path}")
                    
                    # 验证输出文件的轨道设置
                    self.verify_output_tracks(output_path, subtitle_tracks_sorted)
                    
                    return output_path
                else:
                    raise Exception(f"MKV打包失败: {stderr}")
                    
            except subprocess.TimeoutExpired:
                print("MKV打包超时，强制终止进程")
                process.kill()
                raise Exception("MKV打包超时")
                
        except Exception as e:
            print(f"MKV打包失败: {e}")
            raise
    
    def verify_output_tracks(self, output_path, expected_tracks):
        """验证输出文件的轨道设置是否正确"""
        try:
            print("\n验证输出文件的轨道设置...")
            cmd = [self.mkvmerge_path, '--identification-format', 'json', '--identify', str(output_path)]
            
            # 设置环境变量确保UTF-8编码
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            result = subprocess.run(cmd, capture_output=True, env=env, check=True)
            
            # 安全解码输出
            stdout = self.safe_decode(result.stdout)
            if not stdout:
                print("无法获取轨道信息，跳过验证")
                return
                
            info = json.loads(stdout)
            output_subtitle_tracks = []
            
            for track in info.get('tracks', []):
                if track.get('type') == 'subtitles':
                    track_id = str(track.get('id'))
                    language = track.get('properties', {}).get('language', 'und')
                    is_default = track.get('properties', {}).get('default_track', False)
                    output_subtitle_tracks.append({
                        'track_id': track_id,
                        'language': language,
                        'default': is_default
                    })
            
            print("输出文件的字幕轨道:")
            for track in output_subtitle_tracks:
                status = "默认" if track['default'] else "非默认"
                print(f"  轨道{track['track_id']}: {track['language']} - {status}")
            
            # 检查默认轨道是否匹配
            expected_defaults = [t for t in expected_tracks if t.get('is_default')]
            actual_defaults = [t for t in output_subtitle_tracks if t['default']]
            
            if len(expected_defaults) == len(actual_defaults):
                print("默认轨道设置正确")
            else:
                print("默认轨道设置不匹配")
                print(f"  期望的默认轨道数: {len(expected_defaults)}")
                print(f"  实际的默认轨道数: {len(actual_defaults)}")
                
        except subprocess.CalledProcessError as e:
            print(f"无法验证轨道信息: {e}")
        except json.JSONDecodeError as e:
            print(f"解析JSON失败: {e}")
        except Exception as e:
            print(f"验证轨道设置时出错: {e}")
    
    def package_to_mkv(self, video_path, audio_path=None, subtitle_path=None, output_path=None):
        """
        传统的MKV打包（兼容旧接口）
        """
        # 构建字幕轨道列表
        subtitle_tracks = []
        if subtitle_path:
            subtitle_tracks.append({
                'path': subtitle_path,
                'language': 'und',
                'is_default': True,
                'original_track_id': '1'
            })
        
        return self.package_subtitles_only(video_path, subtitle_tracks, output_path)

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='MKV字幕替换工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 打包命令
    pack_parser = subparsers.add_parser('pack', help='MKV打包模式')
    pack_parser.add_argument('-v', '--video', required=True, help='视频文件路径')
    pack_parser.add_argument('-s', '--subtitle', action='append', help='字幕文件路径（可多次使用）')
    pack_parser.add_argument('--subtitle-language', action='append', help='字幕语言代码（与--subtitle对应）')
    pack_parser.add_argument('--default-subtitle', action='append', help='默认字幕轨道（yes/no，与--subtitle对应）')
    pack_parser.add_argument('--original-track-id', action='append', help='原始轨道ID（与--subtitle对应）')
    pack_parser.add_argument('--track-name', action='append', help='字幕轨道名称（与--subtitle对应）')
    pack_parser.add_argument('--no-custom-font', action='store_true', help='禁用自定义字体')
    pack_parser.add_argument('--karaoke-mode', action='store_true', help='启用卡拉OK文件名模式')
    pack_parser.add_argument('-o', '--output', help='输出文件路径')
    
    # 转换命令
    convert_parser = subparsers.add_parser('convert', help='字幕转换模式')
    convert_parser.add_argument('-i', '--input', required=True, help='输入字幕文件或目录')
    convert_parser.add_argument('-o', '--output', help='输出文件或目录')
    convert_parser.add_argument('--batch', action='store_true', help='批量转换模式')
    convert_parser.add_argument('--no-custom-font', action='store_true', help='禁用自定义字体')
    convert_parser.add_argument('--karaoke-mode', action='store_true', help='启用卡拉OK文件名模式')
    
    return parser.parse_args()

def command_line_main():
    """命令行主函数"""
    args = parse_arguments()
    
    if args.command == 'pack':
        packer = MKVPacker()
        
        try:
            # 构建字幕轨道列表
            subtitle_tracks = []
            
            if args.subtitle:
                for i, subtitle_path in enumerate(args.subtitle):
                    track = {'path': subtitle_path}
                    
                    # 设置语言
                    if args.subtitle_language and i < len(args.subtitle_language):
                        track['language'] = args.subtitle_language[i]
                    else:
                        track['language'] = 'und'
                    
                    # 设置原始轨道ID
                    if args.original_track_id and i < len(args.original_track_id):
                        track['original_track_id'] = args.original_track_id[i]
                    else:
                        track['original_track_id'] = str(i + 1)
                    
                    # 设置默认轨道
                    if args.default_subtitle and i < len(args.default_subtitle):
                        track['is_default'] = (args.default_subtitle[i].lower() == 'yes')
                    else:
                        track['is_default'] = False
                    
                    # 设置轨道名称：如果轨道名称为空，不添加默认名称，只保留语言信息
                    if args.track_name and i < len(args.track_name):
                        track['track_name'] = args.track_name[i]
                    else:
                        track['track_name'] = ""  # 默认字幕不添加任何效果名称，只保留语言信息
                    
                    subtitle_tracks.append(track)
            
            # 执行打包
            result_path = packer.package_subtitles_only(
                video_path=args.video,
                subtitle_tracks=subtitle_tracks,
                output_path=args.output,
                enable_custom_font=not args.no_custom_font
            )
            
            print(f"MKV打包完成: {result_path}")
            return result_path
            
        except Exception as e:
            print(f"处理失败: {e}")
            return None
    
    elif args.command == 'convert':
        converter = SubtitleConverter()
        
        try:
            if args.batch:
                # 批量转换模式
                result = converter.batch_convert_subtitles(
                    input_dir=args.input,
                    output_dir=args.output,
                    enable_custom_font=not args.no_custom_font,
                    karaoke_mode=args.karaoke_mode
                )
                print(f"批量转换完成: {len(result)} 个文件")
                return result
            else:
                # 单个文件转换模式
                result = converter.convert_subtitle(
                    input_path=args.input,
                    output_path=args.output,
                    enable_custom_font=not args.no_custom_font,
                    karaoke_mode=args.karaoke_mode,
                    is_batch=False
                )
                if result:
                    print(f"转换完成: {result}")
                return result
                
        except Exception as e:
            print(f"转换失败: {e}")
            return None
    
    else:
        print("请使用 'pack' 或 'convert' 子命令")
        return None

def main():
    """主函数"""
    # 检查是否是命令行调用
    if len(sys.argv) > 1:
        # 命令行模式
        result = command_line_main()
        sys.exit(0 if result else 1)
    else:
        # 交互模式 - 直接进入MKV打包模式
        print("MKV打包工具 - 完全保持原始轨道设置")
        print("=" * 40)
        
        packer = MKVPacker()
        
        while True:
            print("\nMKV打包模式 (输入空行退出)")
            
            video_path = input("请输入视频文件路径: ").strip().strip('"')
            if not video_path:
                print("退出程序!")
                break
            
            subtitle_tracks = []
            track_counter = 1
            
            while True:
                subtitle_path = input("请输入字幕文件路径(输入空行结束添加字幕): ").strip().strip('"')
                if not subtitle_path:
                    break
                
                # 语言代码输入（设置默认值）
                language_input = input("请输入字幕语言代码(如 zh, ko, ja, 默认chi): ").strip()
                if not language_input:
                    language = 'chi'  # 默认中文
                else:
                    language = language_input
                
                # 原始轨道ID输入（设置默认值）
                original_id_input = input(f"请输入原始轨道ID(默认{track_counter}): ").strip()
                if not original_id_input:
                    original_id = str(track_counter)  # 默认递增ID
                else:
                    original_id = original_id_input
                
                # 默认轨道设置（设置默认值）
                default_input = input("是否设为默认轨道? (y=是, n=否, 默认y): ").strip().lower()
                if not default_input:
                    is_default = True  # 默认是
                else:
                    is_default = default_input == 'y'
                
                subtitle_tracks.append({
                    'path': subtitle_path,
                    'language': language,
                    'is_default': is_default,
                    'original_track_id': original_id
                })
                
                track_counter += 1
            
            if not subtitle_tracks:
                print("未添加任何字幕轨道，请重新输入")
                continue
            
            # 询问是否使用自定义字体（设置默认值）
            use_custom_font_input = input("是否使用自定义字体? (y=是, n=否, 默认n): ").strip().lower()
            if not use_custom_font_input:
                enable_font = False  # 默认不启用
            else:
                enable_font = use_custom_font_input == 'y'
            
            # 输出文件路径（设置默认值）
            output_path_input = input("请输入输出文件路径(直接回车使用自动命名): ").strip().strip('"')
            if not output_path_input:
                output_path = None  # 使用自动命名
            else:
                output_path = output_path_input
            
            try:
                result = packer.package_subtitles_only(
                    video_path=video_path,
                    subtitle_tracks=subtitle_tracks,
                    output_path=output_path,
                    enable_custom_font=enable_font
                )
                print(f"打包完成: {result}")
            except Exception as e:
                print(f"打包失败: {e}")

if __name__ == "__main__":
    main()
