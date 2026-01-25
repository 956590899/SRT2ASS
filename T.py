import os
import argparse
from pathlib import Path
import sys
import re

class ASSPrompterConverter:
    def __init__(self, verbose=False):
        """初始化提词器转换器"""
        self.verbose = verbose
        
        # ====================== 核心配置区域 ======================
        
        # ====================== 位置坐标配置 ======================
        self.positions = [
            (110, 900),   # 第一行：历史歌词位置
            (120, 960),   # 第二行：当前歌词第一行位置
            (110, 1020),  # 第三行：当前歌词第二行或下一句预备位置
            (100, 1060)   # 第四行：预备歌词位置
        ]
        
        # ====================== 标记符号配置 ======================
        self.marker = " "  # 当前演唱标记符号
        
        # ====================== 时间阈值配置 ======================
        self.seamless_threshold = 0.2   # 无缝衔接阈值（秒）
        self.preview_duration = 2.0     # 开头预览时长（秒）
        self.restart_threshold = 2.0    # 重新开始预览的间隔阈值（秒）
        self.preview_always_threshold = 2.0  # 始终显示预备阈值（秒）
        
        # ====================== 短间隙预备效果配置 ======================
        self.preview_gap_show_time = 0.5    # 短间隙预备：在下一句开始前0.5秒显示
        self.preview_gap_animation_duration = 0.5  # 短间隙预备：淡入动画时长
        self.preview_gap_row = 3  # 短间隙预备显示行：3=第3行，4=第4行
        
        # ====================== 字体配置 ======================
        self.default_font = "Microsoft YaHei"  # 默认字体
        self.custom_font_mode = 0  # 0=自动识别原ass字体，1=使用自定义字体
        
        # 生成样式模板
        self._generate_style_template()
    
    def set_font_mode(self, mode, font_name=None):
        """设置字体模式"""
        self.custom_font_mode = mode
        
        if mode == 1 and font_name:
            self.default_font = font_name
            if self.verbose:
                print(f"[配置] 使用自定义字体: {font_name}")
        elif mode == 1 and not font_name:
            if self.verbose:
                print(f"[配置] 自定义字体模式已启用，使用默认字体")
        
        self._generate_style_template()
        return self
    
    def set_positions(self, positions):
        """设置四行位置坐标"""
        if len(positions) >= 4:
            self.positions = positions[:4]
        return self
    
    def set_marker(self, marker):
        """设置当前演唱标记符号"""
        self.marker = marker
        return self
    
    def set_timing_thresholds(self, seamless=None, preview=None, restart=None, always=None):
        """设置时间阈值"""
        if seamless is not None:
            self.seamless_threshold = seamless
        if preview is not None:
            self.preview_duration = preview
        if restart is not None:
            self.restart_threshold = restart
        if always is not None:
            self.preview_always_threshold = always
        return self
    
    def set_preview_gap(self, show_time=None, animation_duration=None, row=None):
        """设置短间隙预备配置"""
        if show_time is not None:
            self.preview_gap_show_time = show_time
        if animation_duration is not None:
            self.preview_gap_animation_duration = animation_duration
        if row is not None and row in [3, 4]:
            self.preview_gap_row = row
        return self
    
    def _generate_style_template(self):
        """生成样式模板"""
        self.style_template = f"""[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: K1,{self.default_font},55,&H40FF80FF,&H40FFFFFF,&H00804000,&H00000000,0,0,0,0,100,100,0,0,1,3,0,1,120,30,180,1
Style: k1_Chinese,{self.default_font},50,&H40FF80FF,&H40FFFFFF,&H00804000,&H00000000,0,0,0,0,100,100,0,0,1,3,0,1,120,30,180,1
Style: Default,{self.default_font},30,&H80FFFFFF,&H80FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,2,0,1,120,30,0,1
"""
    
    def clean_text_for_history_preview(self, text):
        """清理历史歌词和预备歌词的文本，移除特效标签"""
        cleaned = re.sub(r'\{[^}]*\}', '', text)
        cleaned = cleaned.replace('\\N', ' ').replace('\\n', ' ').strip()
        return cleaned
    
    def clean_text_for_current(self, text):
        """清理当前歌词文本，保留所有特效标签"""
        return text.replace('\\N', ' ').replace('\\n', ' ').strip()
    
    def log(self, message, level="INFO"):
        """日志输出"""
        if level == "INFO":
            print(message)
        elif level == "VERBOSE" and self.verbose:
            print(f"[详细] {message}")
    
    def parse_config_from_file(self, filepath):
        """从文件读取配置"""
        if self.verbose:
            self.log(f"正在读取文件: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                content = f.read()
        except:
            try:
                with open(filepath, 'r', encoding='gbk') as f:
                    content = f.read()
            except:
                with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
        
        # 如果是自动识别字体模式，提取字体信息
        if self.custom_font_mode == 0:
            font_from_file = self._extract_font_from_content(content)
            if font_from_file:
                self.default_font = font_from_file
                self._generate_style_template()
                if self.verbose:
                    self.log(f"从文件中提取到字体: {font_from_file}")
        
        return content
    
    def _extract_font_from_content(self, content):
        """从ASS内容中提取字体信息"""
        lines = content.split('\n')
        in_styles = False
        
        for line in lines:
            line = line.strip()
            
            if line == '[V4+ Styles]' or line == '[V4 Styles]':
                in_styles = True
                continue
            elif line.startswith('[') and in_styles:
                in_styles = False
                continue
            
            if in_styles and line.startswith('Style:'):
                parts = line.split(',')
                if len(parts) > 1:
                    fontname = parts[1].strip()
                    if fontname and not fontname.startswith('@'):
                        return fontname
        
        return None
    
    def parse_positions_string(self, pos_str):
        """解析位置字符串"""
        positions = []
        
        if not pos_str:
            return None
        
        pos_str = pos_str.replace(';', ',').replace('，', ',')
        
        # 尝试用逗号分割
        parts = pos_str.split(',')
        if len(parts) == 8:
            try:
                for i in range(0, 8, 2):
                    x = int(parts[i].strip())
                    y = int(parts[i+1].strip())
                    positions.append((x, y))
                return positions
            except ValueError:
                pass
        
        # 尝试用空格分割
        parts = pos_str.split()
        if len(parts) >= 8:
            try:
                for i in range(0, 8, 2):
                    x = int(parts[i].strip())
                    y = int(parts[i+1].strip())
                    positions.append((x, y))
                return positions
            except ValueError:
                pass
        
        return None
    
    def time_to_seconds(self, time_str):
        """时间字符串转秒数"""
        try:
            time_str = time_str.replace(',', '.')
            if '.' in time_str:
                hms, cs = time_str.split('.')
                if len(cs) == 3:  # 毫秒格式
                    cs = cs[:2] + '0'
                elif len(cs) == 1:
                    cs = cs + '0'
                elif len(cs) > 3:
                    cs = cs[:2]
            else:
                hms, cs = time_str, "00"
            
            h, m, s = hms.split(':')
            cs = cs[:2].ljust(2, '0')
            return int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100.0
        except:
            return 0.0
    
    def adjust_time(self, time_str, delta_seconds):
        """调整时间"""
        try:
            total_seconds = self.time_to_seconds(time_str)
            total_seconds += delta_seconds
            total_seconds = max(0, total_seconds)
            
            h = int(total_seconds // 3600)
            m = int((total_seconds % 3600) // 60)
            s = int(total_seconds % 60)
            cs = int((total_seconds - int(total_seconds)) * 100)
            
            return f"{h:02d}:{m:02d}:{s:02d}.{cs:02d}"
        except:
            return time_str
    
    def clean_text(self, text):
        """清理文本 - 用于解析原文件"""
        return text.replace('\\N', ' ').replace('\\n', ' ').strip()
    
    def parse_ass_content(self, content):
        """解析ASS文件内容，按时间段分组"""
        events = []
        
        for line in content.split('\n'):
            line = line.strip()
            
            if line.startswith('[CONFIG]') or line.startswith('CONFIG:'):
                continue
            
            if line.startswith('Dialogue:'):
                parts = line.split(',', 9)
                if len(parts) >= 10:
                    start = parts[1].strip()
                    end = parts[2].strip()
                    text = parts[9].strip()
                    
                    cleaned_text = self.clean_text(text)
                    if cleaned_text:
                        events.append({
                            'start': start,
                            'end': end,
                            'start_sec': self.time_to_seconds(start),
                            'end_sec': self.time_to_seconds(end),
                            'text': cleaned_text
                        })
        
        # 按开始时间排序
        events.sort(key=lambda x: x['start_sec'])
        
        # 按时间段分组
        grouped_events = []
        i = 0
        
        while i < len(events):
            current = events[i]
            start_time = current['start']
            end_time = current['end']
            
            texts = []
            j = i
            while j < len(events) and events[j]['start'] == start_time and events[j]['end'] == end_time:
                texts.append(events[j]['text'])
                j += 1
            
            grouped_events.append({
                'start': start_time,
                'end': end_time,
                'start_sec': current['start_sec'],
                'end_sec': current['end_sec'],
                'line1': texts[0] if len(texts) > 0 else '',
                'line2': texts[1] if len(texts) > 1 else '',
                'is_bilingual': len(texts) >= 2
            })
            
            i = j
        
        if self.verbose:
            self.log(f"找到 {len(grouped_events)} 个时间段", "VERBOSE")
        
        return grouped_events
    
    def calculate_time_gap(self, prev_end, curr_start):
        """计算时间间隔"""
        return curr_start - prev_end
    
    def get_timing_info(self, i, events):
        """获取时间信息"""
        if i == 0:
            return {'start_time': events[i]['start'], 'is_reset': True}
        else:
            gap = self.calculate_time_gap(events[i-1]['end_sec'], events[i]['start_sec'])
            
            if gap <= self.seamless_threshold:
                return {'start_time': events[i-1]['end'], 'is_reset': False, 'gap': gap}
            elif gap <= 1.0:
                return {'start_time': events[i]['start'], 'is_reset': False, 'gap': gap}
            else:
                return {'start_time': events[i]['start'], 'is_reset': True, 'gap': gap}
    
    def generate_move_effect(self, row_index, is_reset=False, is_bilingual_line=False):
        """生成移动特效"""
        x, y = self.positions[row_index]
        
        if is_reset:
            start_y = y + 500 + row_index * 100
            return f"\\move({x},{start_y},{x},{y},0,300)"
        else:
            start_y = y + 120
            effect = f"\\move({x},{start_y},{x},{y},0,200)"
            
            if row_index == 0:
                effect += "\\fad(0,200)"
            if row_index == 1:
                effect += "\\fscx110\\fscy110"
            if row_index == 2 and is_bilingual_line:
                effect += "\\fscx105\\fscy105"
            
            return effect
    
    def generate_fade_effect(self, fade_duration):
        """生成淡入效果"""
        fade_duration_ms = int(fade_duration * 1000)
        return f"\\fad({fade_duration_ms},0)"
    
    def get_style_for_row(self, row_index, is_bilingual_line=False):
        """获取样式名"""
        if row_index == 0:
            return 'Default'
        elif row_index == 1:
            return 'K1'
        elif row_index == 2:
            return 'k1_Chinese' if is_bilingual_line else 'Default'
        elif row_index == 3:
            return 'Default'
        return 'Default'
    
    def should_show_history(self, i, events):
        """判断是否显示历史歌词"""
        if i == 0:
            return False
        
        gap = self.calculate_time_gap(events[i-1]['end_sec'], events[i]['start_sec'])
        return gap <= self.seamless_threshold
    
    def has_gap_after(self, i, events):
        """判断当前句之后是否有间隙"""
        if i + 1 >= len(events):
            return False
        
        gap = self.calculate_time_gap(events[i]['end_sec'], events[i+1]['start_sec'])
        return gap > self.seamless_threshold
    
    def is_gap_previous_sentence(self, i, events):
        """判断是否是间隙的上一句"""
        return self.has_gap_after(i, events)
    
    def is_gap_two_sentences_previous(self, i, events):
        """判断是否是间隙的上上一句"""
        if i + 2 >= len(events):
            return False
        
        gap1 = self.calculate_time_gap(events[i]['end_sec'], events[i+1]['start_sec'])
        gap2 = self.calculate_time_gap(events[i+1]['end_sec'], events[i+2]['start_sec'])
        return gap2 > self.seamless_threshold
    
    def should_show_preview(self, i, events, preview_type, is_bilingual):
        """判断是否显示预备歌词"""
        if preview_type == 'next1':
            if i + 1 >= len(events):
                return False
            
            time_to_next = events[i+1]['start_sec'] - events[i]['end_sec']
            
            if self.is_gap_previous_sentence(i, events):
                if time_to_next > self.preview_always_threshold:
                    return True
                elif self.seamless_threshold < time_to_next <= self.preview_always_threshold:
                    return True
                else:
                    return False
            
            if self.is_gap_two_sentences_previous(i, events):
                return time_to_next <= self.preview_always_threshold
            
            return time_to_next <= self.preview_always_threshold
            
        elif preview_type == 'next2':
            if is_bilingual:
                return False
            
            if i + 2 >= len(events):
                return False
            
            if self.is_gap_two_sentences_previous(i, events):
                return False
            
            if self.is_gap_previous_sentence(i, events):
                return False
            
            time_to_next = events[i+1]['start_sec'] - events[i]['end_sec']
            return time_to_next <= self.preview_always_threshold
        
        return False
    
    def should_show_preview_effect(self, i, events):
        """判断是否显示短间隙预备效果"""
        if i + 1 >= len(events):
            return False
        
        gap = self.calculate_time_gap(events[i]['end_sec'], events[i+1]['start_sec'])
        
        if gap <= self.seamless_threshold:
            return False
        
        return self.seamless_threshold < gap <= self.preview_always_threshold
    
    def should_restart_preview(self, i, events):
        """判断是否需要重新开始预览"""
        if i == 0:
            return True
        
        gap = self.calculate_time_gap(events[i-1]['end_sec'], events[i]['start_sec'])
        return gap > self.preview_always_threshold
    
    def add_preview_lines(self, output_lines, event, events, event_index):
        """添加长间隙预备字幕行"""
        if not event['line1']:
            return
        
        original_start_time = event['start']
        
        # 检查是否为长间隙
        is_long_gap = False
        if event_index > 0:
            gap = self.calculate_time_gap(events[event_index-1]['end_sec'], event['start_sec'])
            is_long_gap = gap > self.preview_always_threshold
        
        if event_index == 0 or is_long_gap:
            # 阶段1：提前2秒开始
            preview_start_1 = self.adjust_time(original_start_time, -self.preview_duration)
            preview_end_1 = self.adjust_time(original_start_time, -self.preview_duration/2)
            
            x, y = self.positions[3]
            effect = f"\\move({x},{y+500},{x},{y},0,300)"
            cleaned_text = self.clean_text_for_history_preview(event['line1'])
            
            output_lines.append(f"Dialogue: 0,{preview_start_1},{preview_end_1},Default,,0,0,0,,{{{effect}}}{cleaned_text}")
            
            # 阶段2：提前1秒开始
            preview_start_2 = preview_end_1
            preview_end_2 = original_start_time
            
            x, y = self.positions[2]
            effect = f"\\move({x},{y+300},{x},{y},0,200)"
            current_text = self.clean_text_for_current(event['line1'])
            
            output_lines.append(f"Dialogue: 0,{preview_start_2},{preview_end_2},Default,,0,0,0,,{{{effect}}}{current_text}")
            
            # 检查是否有下一句，并且下一句和当前句之间没有间隙
            if event_index + 1 < len(events):
                next_event = events[event_index + 1]
                time_to_next = next_event['start_sec'] - event['end_sec']
                
                # 只有当下一句和当前句之间是无缝衔接（间隔小于等于seamless_threshold）时，
                # 才在预览阶段显示下一句
                if time_to_next <= self.seamless_threshold:
                    x, y = self.positions[3]
                    effect = f"\\move({x},{y+200},{x},{y},0,200)"
                    cleaned_next_text = self.clean_text_for_history_preview(next_event['line1'])
                    
                    output_lines.append(f"Dialogue: 0,{preview_start_2},{preview_end_2},Default,,0,0,0,,{{{effect}}}{cleaned_next_text}")
                else:
                    # 如果和下一句有间隙，则不预备下一句
                    # 下一句会在短间隙预备效果中显示（如果适用）
                    if self.verbose:
                        self.log(f"[长间隙预备] 第{event_index+1}句与下一句有间隙({time_to_next:.2f}s > {self.seamless_threshold}s)，只预备当前句", "VERBOSE")
    
    def add_preview_effect_lines(self, output_lines, event, events, event_index):
        """添加短间隙预备效果行"""
        if event_index + 1 >= len(events):
            return
        
        current_event = event
        next_event = events[event_index + 1]
        
        gap = self.calculate_time_gap(current_event['end_sec'], next_event['start_sec'])
        
        if gap <= self.seamless_threshold:
            return
        
        if gap > self.preview_always_threshold:
            return
        
        row_index = self.preview_gap_row - 1
        show_before = min(gap, self.preview_gap_show_time)
        
        preview_start = self.adjust_time(next_event['start'], -show_before)
        preview_end = next_event['start']
        
        x, y = self.positions[row_index]
        fade_effect = self.generate_fade_effect(self.preview_gap_animation_duration)
        pos_effect = f"\\pos({x},{y})"
        effect = f"{pos_effect}{fade_effect}"
        
        cleaned_text = self.clean_text_for_history_preview(next_event['line1'])
        
        output_lines.append(f"Dialogue: 0,{preview_start},{preview_end},Default,,0,0,0,,{{{effect}}}{cleaned_text}")
    
    def convert_to_prompter(self, events, output_file):
        """转换为提词器格式"""
        if not events:
            self.log("错误：没有可处理的事件！")
            return
        
        output_lines = [
            "[Script Info]",
            "Title: 提词器模式",
            "ScriptType: v4.00+",
            "WrapStyle: 0",
            "ScaledBorderAndShadow: yes",
            "PlayResX: 1920",
            "PlayResY: 1080",
            "",
            self.style_template.strip(),
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
            ""
        ]
        
        # 添加第一句的预览
        if events:
            self.add_preview_lines(output_lines, events[0], events, 0)
        
        # 处理所有事件
        for i, event in enumerate(events):
            timing = self.get_timing_info(i, events)
            start_time = timing['start_time']
            end_time = event['end']
            is_reset = timing['is_reset']
            is_bilingual = event['is_bilingual']
            
            is_gap_prev = self.is_gap_previous_sentence(i, events)
            is_gap_prev2 = self.is_gap_two_sentences_previous(i, events)
            
            # 检查是否需要长间隙效果
            if i > 0 and self.should_restart_preview(i, events):
                self.add_preview_lines(output_lines, event, events, i)
            
            # 检查是否需要短间隙效果
            if self.should_show_preview_effect(i, events):
                self.add_preview_effect_lines(output_lines, event, events, i)
            
            # 确定四行显示内容
            texts = ['', '', '', '']
            
            # 第1行：历史歌词
            if self.should_show_history(i, events):
                texts[0] = self.clean_text_for_history_preview(events[i-1]['line1'])
            
            # 第2行：当前歌词第一行
            texts[1] = self.clean_text_for_current(event['line1'])
            
            # 判断是否有预备歌词
            has_preview_lyrics = False
            preview_text = ''
            
            if not is_gap_prev:
                if self.should_show_preview(i, events, 'next1', is_bilingual):
                    if i + 1 < len(events):
                        has_preview_lyrics = True
                        preview_text = self.clean_text_for_history_preview(events[i+1]['line1'])
            
            # 第3行和第4行显示逻辑
            if is_bilingual:
                if event['line2']:
                    texts[2] = self.clean_text_for_current(event['line2'])
                
                if has_preview_lyrics and event['line2']:
                    texts[3] = preview_text
                elif has_preview_lyrics and not event['line2']:
                    texts[2] = preview_text
            else:
                if has_preview_lyrics:
                    texts[2] = preview_text
                    
                    if not is_gap_prev2:
                        if self.should_show_preview(i, events, 'next2', is_bilingual):
                            if i + 2 < len(events):
                                texts[3] = self.clean_text_for_history_preview(events[i+2]['line1'])
            
            # 生成四行字幕
            for row in range(4):
                if texts[row]:
                    is_bilingual_line = (row == 2 and is_bilingual and event['line2'])
                    
                    if is_bilingual_line:
                        style = 'k1_Chinese'
                    else:
                        style = self.get_style_for_row(row, False)
                    
                    if is_reset and (row == 1 or is_bilingual_line):
                        effect = self.generate_move_effect(row, True, is_bilingual_line)
                    else:
                        effect = self.generate_move_effect(row, False, is_bilingual_line)
                    
                    is_current_line = (row == 1)
                    marked_text = texts[row]
                    if (is_current_line or is_bilingual_line) and self.marker:
                        marked_text = f"{self.marker}{texts[row]}"
                    
                    output_lines.append(f"Dialogue: 0,{start_time},{end_time},{style},,0,0,0,,{{{effect}}}{marked_text}")
        
        # 写入文件
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(output_lines))
            
            dialogue_count = len([l for l in output_lines if l.startswith('Dialogue:')])
            self.log(f"转换完成！生成 {dialogue_count} 行字幕")
            self.log(f"输出文件: {output_file}")
            
        except Exception as e:
            self.log(f"写入文件失败: {e}")


def clean_path(path):
    """清理路径"""
    if path and ((path.startswith('"') and path.endswith('"')) or 
                 (path.startswith("'") and path.endswith("'"))):
        path = path[1:-1]
    return path.strip() if path else ""


def main():
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    parser = argparse.ArgumentParser(description='ASS字幕转四行提词器')
    parser.add_argument('input_file', nargs='?', help='输入ASS文件路径')
    parser.add_argument('-o', '--output', help='输出文件路径')
    parser.add_argument('-p', '--positions', help='四行位置坐标，格式: "x1,y1 x2,y2 x3,y3 x4,y4"')
    parser.add_argument('-m', '--marker', help='当前演唱标记符号')
    parser.add_argument('-st', '--seamless-threshold', type=float, default=0.2, 
                       help='无缝衔接阈值（秒），默认0.2')
    parser.add_argument('-pd', '--preview-duration', type=float, default=2.0, 
                       help='开头预览时长（秒），默认2.0')
    parser.add_argument('-rt', '--restart-threshold', type=float, default=2.0, 
                       help='重新开始预览阈值（秒），默认2.0')
    parser.add_argument('-pat', '--preview-always-threshold', type=float, default=2.0, 
                       help='始终显示预备阈值（秒），默认2.0')
    parser.add_argument('-f', '--font-mode', type=int, default=0, choices=[0, 1], 
                       help='字体模式：0=自动识别原文件字体，1=使用自定义字体（默认为0）')
    parser.add_argument('-fn', '--font-name', help='自定义字体名称（仅当font-mode=1时有效）')
    parser.add_argument('-v', '--verbose', action='store_true', help='启用详细日志输出')
    
    parser.add_argument('-pgst', '--preview-gap-show-time', type=float, default=0.5, 
                       help='短间隙预备：在下一句开始前显示时间（秒），默认0.5')
    parser.add_argument('-pgad', '--preview-gap-animation-duration', type=float, default=0.5, 
                       help='短间隙预备：淡入动画时长（秒），默认0.5')
    parser.add_argument('-pgr', '--preview-gap-row', type=int, default=3, choices=[3, 4],
                       help='短间隙预备显示行：3=第3行，4=第4行，默认3')
    
    args = parser.parse_args()
    
    input_file = clean_path(args.input_file)
    
    if not input_file:
        print("ASS字幕转四行提词器")
        print("=" * 60)
        print("基本使用: python T.py <输入文件>")
        print("")
        print("常用参数:")
        print("  -v : 显示详细日志")
        print("  -f 1 -fn \"字体名\" : 使用自定义字体")
        print("  -p \"x1,y1 x2,y2 x3,y3 x4,y4\" : 设置四行位置")
        print("  -m \"标记\" : 设置当前演唱标记")
        print("")
        print("示例:")
        print("  python T.py input.ass -v")
        print("  python T.py input.ass -f 1 -fn \"Arial\"")
        print("  python T.py input.ass -p \"200,920 200,980 200,1020 200,1060\"")
        return
    
    if not os.path.exists(input_file):
        print(f"文件不存在: {input_file}")
        return
    
    # 创建转换器
    converter = ASSPrompterConverter(verbose=args.verbose)
    
    # 配置转换器
    if args.positions:
        positions = converter.parse_positions_string(args.positions)
        if positions:
            converter.set_positions(positions)
    
    if args.marker:
        converter.set_marker(args.marker)
    
    if args.font_mode == 1:
        converter.set_font_mode(1, args.font_name)
    
    converter.set_timing_thresholds(
        seamless=args.seamless_threshold,
        preview=args.preview_duration,
        restart=args.restart_threshold,
        always=args.preview_always_threshold
    )
    
    converter.set_preview_gap(
        show_time=args.preview_gap_show_time,
        animation_duration=args.preview_gap_animation_duration,
        row=args.preview_gap_row
    )
    
    # 读取文件内容
    content = converter.parse_config_from_file(input_file)
    
    # 生成输出文件路径
    input_path = Path(input_file)
    if args.output:
        output_file = clean_path(args.output)
    else:
        output_file = str(input_path.parent / f"{input_path.stem}_提词器.ass")
    
    try:
        events = converter.parse_ass_content(content)
        if events:
            converter.convert_to_prompter(events, output_file)
        else:
            converter.log("没有找到可处理的字幕内容")
    except Exception as e:
        converter.log(f"处理失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()