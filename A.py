import sys
import numpy as np
import librosa
from pathlib import Path
import chardet
import re
import io

# 修复 Windows 控制台编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='ignore')

# 禁用librosa和numpy的警告
import warnings
warnings.filterwarnings('ignore')


class SubtitleCalibrator:
    def __init__(self,
                 # 音频分析参数
                 energy_threshold=0.05,
                 min_silence_duration=0.3,
                 
                 # 静音段处理参数
                 merge_silence_threshold=0.1,
                 
                 # 字幕时间调整参数
                 min_gap=0.1,
                 
                 # 开始时间调整限制
                 max_start_adjustment=0.5,
                 start_time_near_silence_threshold=0.5,
                 start_time_lead=0.1,
                 
                 # 结束时间调整限制
                 max_end_extension=0.2,
                 
                 # 静音段匹配参数
                 silence_end_tolerance=0.8,
                 
                 # 整体时间偏移参数
                 overall_time_offset_threshold=0.2,
                 
                 # 最小显示时间参数
                 min_display_time_short=0.8,
                 min_display_time_long=1.0,
                 short_text_length_threshold=8,
                 
                 # 短持续时间阈值
                 min_duration_threshold=0.5,
                 
                 # 多行字幕合并参数
                 merge_multiline=1,
                 
                 # 调试模式
                 debug=True):
        
        # 音频分析参数
        self.energy_threshold = energy_threshold
        self.min_silence_duration = min_silence_duration
        
        # 静音段处理参数
        self.merge_silence_threshold = merge_silence_threshold
        
        # 字幕时间调整参数
        self.min_gap = min_gap
        
        # 开始时间调整限制
        self.max_start_adjustment = max_start_adjustment
        self.start_time_near_silence_threshold = start_time_near_silence_threshold
        self.start_time_lead = start_time_lead
        
        # 结束时间调整限制
        self.max_end_extension = max_end_extension
        
        # 静音段匹配参数
        self.silence_end_tolerance = silence_end_tolerance
        
        # 整体时间偏移参数
        self.overall_time_offset_threshold = overall_time_offset_threshold
        
        # 最小显示时间参数
        self.min_display_time_short = min_display_time_short
        self.min_display_time_long = min_display_time_long
        self.short_text_length_threshold = short_text_length_threshold
        
        # 短持续时间阈值
        self.min_duration_threshold = min_duration_threshold
        
        # 多行字幕合并参数
        self.merge_multiline = merge_multiline
        
        # 调试模式
        self.debug = debug
        
        # 定义优化后的ASS头部模板
        self.ASS_HEADER = [
            '[Script Info]',
            'Title:',
            'ScriptType: v4.00+',
            'Collisions: Normal',
            'PlayResX: 384',
            'PlayResY: 288',
            'Timer: 100.0000',
            'WrapStyle: 0',
            'ScaledBorderAndShadow: no',
            '',
            '[V4+ Styles]',
            'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
            'Style: Default,Microsoft YaHei,14,&H00FFFFFF,&H00000000,&H00804000,&H00000000,-1,0,0,0,100,100,0,0,1,2,1,2,5,5,2,134',
            'Style: Karaoke,Microsoft YaHei,14,&H00FF80FF,&H00FFFFFF,&H00804000,&H00000000,-1,0,0,0,100,100,0,0,1,2,1,2,5,5,2,134',
            '',
            '[Events]',
            'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text'
        ]
    
    # ============================
    # 时间格式化方法
    # ============================
    def seconds_to_minutes_str(self, seconds):
        """将秒数转换为分钟显示格式 MM:SS.mm"""
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes:02d}:{secs:05.2f}"
    
    def seconds_to_ass_time(self, seconds):
        """将秒数转换为ASS时间格式 H:MM:SS.cc"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:05.2f}"
    
    def ass_time_to_seconds(self, ass_time):
        """将ASS时间格式转换为秒数"""
        try:
            parts = ass_time.replace(',', '.').split(':')
            if len(parts) == 3:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
        except:
            pass
        return 0
    
    # ============================
    # 调试和日志方法
    # ============================
    def print_events_debug(self, events, step_name, max_display=5):
        """打印事件调试信息"""
        if not self.debug:
            return
            
        print(f"\n{'='*60}")
        print(f"调试信息: {step_name}")
        print(f"总事件数: {len(events)}")
        print(f"{'='*60}")
        
        for i, event in enumerate(events[:max_display]):
            print(f"[{i+1}] 开始: {event['start_time']}, 结束: {event['end_time']}")
            print(f"     文本: {self.safe_print(event['text'], 50)}")
            print(f"     原始行: {self.safe_print(event.get('original_line', 'N/A'), 50)}")
            print()
        
        if len(events) > max_display:
            print(f"... 还有 {len(events) - max_display} 个事件未显示")
            print(f"显示最后 {max_display} 个事件:")
            for i in range(-min(max_display, len(events)), 0):
                event = events[i]
                idx = len(events) + i + 1
                print(f"[{idx}] 开始: {event['start_time']}, 结束: {event['end_time']}")
                print(f"     文本: {self.safe_print(event['text'], 50)}")
                print()
    
    def safe_print(self, text, max_length=50):
        """安全打印函数，处理Unicode编码问题"""
        try:
            if len(text) > max_length:
                return f"{text[:max_length]}..."
            else:
                return text
        except UnicodeEncodeError:
            safe_text = text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
            if len(safe_text) > max_length:
                return f"{safe_text[:max_length]}..."
            else:
                return safe_text
    
    # ============================
    # 字幕文本处理方法
    # ============================
    def get_plain_text_length(self, text):
        """计算纯文本长度，排除所有ASS特效标签"""
        # 1. 移除所有大括号内的特效标签
        clean_text = re.sub(r'\{[^}]*\}', '', text)
        
        # 2. 移除所有反斜杠标签
        clean_text = re.sub(r'\\[a-zA-Z]+\([^)]*\)', '', clean_text)
        clean_text = re.sub(r'\\[a-zA-Z]+\d*', '', clean_text)
        
        # 3. 移除空白字符
        text_without_whitespace = re.sub(r'\s+', '', clean_text)
        
        return len(text_without_whitespace)
    
    def remove_ass_tags(self, text):
        """删除ASS特效标签，如{\K558}等，但保留文本中的正常空格"""
        return re.sub(r'\{[^}]*\}', '', text)
    
    def is_chinese_text(self, text):
        """检测文本是否为中文（纯中文或中英混合）"""
        clean_text = self.remove_ass_tags(text)
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', clean_text)
        
        if not clean_text:
            return False
        
        if chinese_chars:
            allowed_chars = re.sub(r'[^\u4e00-\u9fffa-zA-Z0-9\s\.,!?;:\'"\-]', '', clean_text)
            if len(allowed_chars) >= len(clean_text) * 0.8:
                return True
        
        return False
    
    def is_english_only(self, text):
        """检测文本是否只包含英文、数字、标点和空格"""
        clean_text = self.remove_ass_tags(text)
        non_english = re.sub(r'[a-zA-Z0-9\s\.,!?;:\'"\(\)\[\]\{\}\-\+=\*/@#$%^&_`~]+', '', clean_text)
        return len(non_english) == 0
    
    # ============================
    # 文件处理方法
    # ============================
    def detect_file_encoding(self, file_path):
        """检测文件编码"""
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                encoding = result['encoding'] if result['encoding'] else 'utf-8'
                return encoding
        except Exception as e:
            print(f"编码检测失败: {e}")
            return 'utf-8'
    
    def read_subtitle_file(self, subtitle_path):
        """读取字幕文件"""
        encoding = self.detect_file_encoding(subtitle_path)
        print(f"检测到字幕文件编码: {encoding}")
        
        try:
            with open(subtitle_path, 'r', encoding=encoding) as f:
                content = f.read()
            return content, encoding
        except UnicodeDecodeError:
            encodings = ['utf-8', 'gbk', 'gb2312', 'big5', 'latin-1']
            for enc in encodings:
                try:
                    with open(subtitle_path, 'r', encoding=enc) as f:
                        content = f.read()
                    print(f"使用编码 {enc} 成功读取")
                    return content, enc
                except UnicodeDecodeError:
                    continue
            raise Exception("无法解码字幕文件")
        except Exception as e:
            print(f"读取字幕文件失败: {e}")
            raise
    
    # ============================
    # 音频分析方法
    # ============================
    def analyze_audio_energy(self, audio_path):
        """分析音频能量分布"""
        print(f"分析音频能量: {audio_path}")
        
        try:
            y, sr = librosa.load(audio_path, sr=None, res_type='kaiser_fast')
            
            frame_length = int(0.025 * sr)
            hop_length = int(0.010 * sr)
            
            energy = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
            times = librosa.times_like(energy, sr=sr, hop_length=hop_length)
            
            return times, energy, sr
        except Exception as e:
            print(f"分析音频能量失败: {e}")
            return np.array([0]), np.array([0]), 22050
    
    def detect_voice_breaks(self, times, energy):
        """检测人声断点"""
        print("检测人声断点...")
        
        if len(times) == 0 or len(energy) == 0:
            print("警告: 音频数据为空，返回空静音段列表")
            return []
        
        voice_active = energy > self.energy_threshold
        
        silence_segments = []
        in_silence = False
        silence_start = 0
        
        for i, active in enumerate(voice_active):
            if not active and not in_silence:
                in_silence = True
                silence_start = times[i]
            elif active and in_silence:
                silence_end = times[i]
                silence_duration = silence_end - silence_start
                if silence_duration >= self.min_silence_duration:
                    silence_segments.append((silence_start, silence_end))
                    start_time_str = self.seconds_to_minutes_str(silence_start)
                    end_time_str = self.seconds_to_minutes_str(silence_end)
                    print(f"  静音段 {len(silence_segments)}: {start_time_str} - {end_time_str} (持续: {silence_duration:.2f}秒)")
                in_silence = False
        
        if in_silence:
            silence_end = times[-1]
            silence_duration = silence_end - silence_start
            if silence_duration >= self.min_silence_duration:
                silence_segments.append((silence_start, silence_end))
                start_time_str = self.seconds_to_minutes_str(silence_start)
                end_time_str = self.seconds_to_minutes_str(silence_end)
                print(f"  静音段 {len(silence_segments)}: {start_time_str} - {end_time_str} (持续: {silence_duration:.2f}秒)")
        
        print(f"总共检测到 {len(silence_segments)} 个静音段")
        return silence_segments
    
    # ============================
    # 静音段处理方法
    # ============================
    def merge_short_silences(self, silence_segments, events):
        """合并短静音段，只合并间隔小于0.1秒的段落"""
        print("合并短静音段...")
        
        if not silence_segments:
            return silence_segments
        
        print("合并前的静音段:")
        for i, (start, end) in enumerate(silence_segments):
            duration = end - start
            start_time_str = self.seconds_to_minutes_str(start)
            end_time_str = self.seconds_to_minutes_str(end)
            print(f"  [{i}] {start_time_str} - {end_time_str} (持续: {duration:.2f}秒)")
        
        event_times = []
        for event in events:
            start_seconds = self.ass_time_to_seconds(event['start_time'])
            end_seconds = self.ass_time_to_seconds(event['end_time'])
            event_times.append((start_seconds, end_seconds))
        
        merged_silences = []
        current_silence_start, current_silence_end = silence_segments[0]
        
        for i in range(1, len(silence_segments)):
            next_silence_start, next_silence_end = silence_segments[i]
            gap = next_silence_start - current_silence_end
            
            # 只合并间隔小于0.1秒的静音段
            if gap < self.merge_silence_threshold:
                should_merge = True
                for event_start, event_end in event_times:
                    if (current_silence_start < event_start < next_silence_end) or \
                       (current_silence_start < event_end < next_silence_end):
                        should_merge = False
                        event_start_str = self.seconds_to_minutes_str(event_start)
                        event_end_str = self.seconds_to_minutes_str(event_end)
                        print(f"  不合并: 跨越事件边界 {event_start_str}-{event_end_str}")
                        break
                
                if should_merge:
                    print(f"  合并: 间隔 {gap:.2f}秒 < {self.merge_silence_threshold}秒")
                    current_silence_end = next_silence_end
                else:
                    merged_silences.append((current_silence_start, current_silence_end))
                    current_silence_start, current_silence_end = next_silence_start, next_silence_end
            else:
                merged_silences.append((current_silence_start, current_silence_end))
                current_silence_start, current_silence_end = next_silence_start, next_silence_end
        
        merged_silences.append((current_silence_start, current_silence_end))
        
        print("合并后的静音段:")
        for i, (start, end) in enumerate(merged_silences):
            duration = end - start
            start_time_str = self.seconds_to_minutes_str(start)
            end_time_str = self.seconds_to_minutes_str(end)
            print(f"  [{i}] {start_time_str} - {end_time_str} (持续: {duration:.2f}秒)")
        
        print(f"静音段合并: {len(silence_segments)} -> {len(merged_silences)}")
        
        return merged_silences
    
    # ============================
    # 字幕处理核心方法
    # ============================
    def convert_to_ass(self, subtitle_content):
        """将各种字幕格式转换为统一的ASS格式"""
        lines = subtitle_content.split('\n')
        
        if '[Script Info]' in subtitle_content and '[Events]' in subtitle_content:
            print("检测到ASS格式字幕，统一使用自定义文件头...")
            return self._ass_to_unified_ass(subtitle_content)
        
        elif any(line.strip().isdigit() and '-->' in lines[i+1] 
                for i, line in enumerate(lines) if line.strip()):
            print("检测到SRT格式字幕，转换为ASS...")
            return self._srt_to_ass(subtitle_content)
        
        elif 'WEBVTT' in subtitle_content:
            print("检测到VTT格式字幕，转换为ASS...")
            return self._vtt_to_ass(subtitle_content)
        
        else:
            print("未知字幕格式，尝试通用转换...")
            return self._generic_to_ass(subtitle_content)
    
    def parse_ass_events(self, ass_content):
        """解析ASS事件，保存原始时间用于检测00:开头的事件"""
        print("解析ASS事件...")
        events = []
        lines = ass_content.split('\n')
        
        in_events = False
        for line in lines:
            line = line.strip()
            if line.startswith('[Events]'):
                in_events = True
                continue
            elif line.startswith('[') and in_events:
                break
            
            if in_events and line.startswith('Dialogue:'):
                parts = line.split(',', 9)
                if len(parts) >= 10:
                    original_start_time = parts[1].strip()
                    original_end_time = parts[2].strip()
                    text = parts[9].strip()
                    
                    # 标准化时间格式用于处理
                    normalized_start_time = self._normalize_ass_time(original_start_time)
                    normalized_end_time = self._normalize_ass_time(original_end_time)
                    
                    events.append({
                        'start_time': normalized_start_time,
                        'end_time': normalized_end_time,
                        'text': text,
                        'original_line': line,
                        'original_start_time': original_start_time,
                        'original_end_time': original_end_time
                    })
        
        print(f"解析到 {len(events)} 个字幕事件")
        self.print_events_debug(events, "解析ASS事件后")
        
        return events
    
    def detect_same_timing_groups(self, events):
        """检测时间轴相同的多行字幕组"""
        groups = []
        current_group = []
        
        for i, event in enumerate(events):
            current_start = self.ass_time_to_seconds(event['start_time'])
            current_end = self.ass_time_to_seconds(event['end_time'])
            
            if not current_group:
                current_group.append(i)
            else:
                first_idx = current_group[0]
                first_start = self.ass_time_to_seconds(events[first_idx]['start_time'])
                first_end = self.ass_time_to_seconds(events[first_idx]['end_time'])
                
                if (abs(current_start - first_start) < 0.05 and 
                    abs(current_end - first_end) < 0.05):
                    current_group.append(i)
                else:
                    if len(current_group) > 1:
                        groups.append(current_group)
                    current_group = [i]
        
        if len(current_group) > 1:
            groups.append(current_group)
        
        print(f"检测到 {len(groups)} 个多行字幕组")
        return groups
    
    def smart_deduplicate(self, events):
        """智能去重：删除文本相同且开始时间相同的重复字幕"""
        print("进行智能去重（基于文本和开始时间）...")
        self.print_events_debug(events, "智能去重前")
        
        # 使用字典跟踪已见过的（文本, 开始时间）组合
        seen_combinations = {}
        unique_events = []
        duplicate_count = 0
        
        for i, event in enumerate(events):
            text = event['text'].strip()
            start_time = event['start_time']
            
            # 创建唯一标识：文本+开始时间
            event_key = f"{text}|{start_time}"
            
            if event_key not in seen_combinations:
                seen_combinations[event_key] = i
                unique_events.append(event)
            else:
                duplicate_count += 1
                # 获取已保留的事件信息
                existing_idx = seen_combinations[event_key]
                existing_event = events[existing_idx]
                
                safe_text = self.safe_print(text, 40)
                print(f"  删除重复字幕 [{i+1}]: '{safe_text}'")
                print(f"    开始时间: {start_time} (与 [{existing_idx+1}] 完全相同)")
                print(f"    结束时间: {event['end_time']} (已保留事件的结束时间: {existing_event['end_time']})")
        
        if duplicate_count > 0:
            print(f"去重完成: 删除了 {duplicate_count} 个重复字幕")
            print(f"事件总数: {len(events)} -> {len(unique_events)}")
        else:
            print("未发现重复字幕")
        
        self.print_events_debug(unique_events, "智能去重后")
        
        return unique_events
    
    def sort_bilingual_subtitles(self, events):
        """对双语字幕进行排序 - 中文在最后一行（显示在上方），保持独立事件行"""
        print("\n步骤5: 检测并排序双语字幕...")
        self.print_events_debug(events, "双语字幕排序前")
        
        multiline_groups = self.detect_same_timing_groups(events)
        sorted_events = events.copy()
        
        for group_idx, group in enumerate(multiline_groups):
            if len(group) != 2:  # 只处理双行字幕组
                continue
                
            print(f"处理双语字幕组 {group_idx+1}: 事件索引 {group}")
            
            # 获取组内两行事件
            event1_idx, event2_idx = group[0], group[1]
            event1 = events[event1_idx]
            event2 = events[event2_idx]
            
            text1 = event1['text']
            text2 = event2['text']
            
            safe_text1 = self.safe_print(text1)
            safe_text2 = self.safe_print(text2)
            
            print(f"  行1: {safe_text1}")
            print(f"  行2: {safe_text2}")
            
            is_chinese1 = self.is_chinese_text(text1)
            is_chinese2 = self.is_chinese_text(text2)
            
            print(f"  行1: 中文={is_chinese1}")
            print(f"  行2: 中文={is_chinese2}")
            
            # 如果第一行是中文，第二行是外语，则交换
            if is_chinese1 and not is_chinese2:
                print(f"  交换顺序: 中文在前 -> 中文在后")
                sorted_events[event1_idx] = event2
                sorted_events[event2_idx] = event1
            elif not is_chinese1 and is_chinese2:
                print(f"  保持顺序: 外语在前，中文在后")
            else:
                print(f"  保持原顺序")
            
            print("")
        
        self.print_events_debug(sorted_events, "双语字幕排序后")
        
        return sorted_events
    
    # ============================
    # 字幕校准核心方法
    # ============================
    def calibrate_subtitles(self, events, silence_segments, audio_duration):
        """校准字幕开始和结束时间，优先使用大于2秒的静音段"""
        print("第一遍校准字幕开始和结束时间（优先使用大于2秒静音段）...")
        print(f"注意：原始持续时间小于{self.min_duration_threshold}秒的字幕将保持原始时间，不做处理")
        self.print_events_debug(events, "校准字幕时间前")
        
        print(f"字幕提前显示时间: {self.start_time_lead}秒")
        print("可用于校准的静音段:")
        for i, (silence_start, silence_end) in enumerate(silence_segments):
            duration = silence_end - silence_start
            start_time_str = self.seconds_to_minutes_str(silence_start)
            end_time_str = self.seconds_to_minutes_str(silence_end)
            duration_tag = ">2s" if duration >= 2.0 else ""
            print(f"  [{i}] {start_time_str} - {end_time_str} (持续: {duration:.2f}s) {duration_tag}")
        
        multiline_groups = self.detect_same_timing_groups(events)
        
        sentence_groups = []
        used_indices = set()
        
        for group in multiline_groups:
            sentence_groups.append(group)
            used_indices.update(group)

        for i in range(len(events)):
            if i not in used_indices:
                sentence_groups.append([i])

        sentence_groups.sort(key=lambda group: self.ass_time_to_seconds(events[group[0]]['start_time']))
        
        calibrated_events = events.copy()
        
        time_offset = 0
        if sentence_groups and silence_segments:
            first_group = sentence_groups[0]
            first_event_idx = first_group[0]
            original_first_start = self.ass_time_to_seconds(events[first_event_idx]['start_time'])
            
            for silence_start, silence_end in silence_segments:
                if silence_start <= original_first_start <= silence_end:
                    raw_offset = silence_end - original_first_start
                    
                    if abs(raw_offset) <= self.overall_time_offset_threshold:
                        time_offset = raw_offset
                        first_start_str = self.seconds_to_minutes_str(original_first_start)
                        silence_start_str = self.seconds_to_minutes_str(silence_start)
                        silence_end_str = self.seconds_to_minutes_str(silence_end)
                        print(f"\n整体时间偏移计算:")
                        print(f"  首次字幕时间: {first_start_str}")
                        print(f"  对应静音段: {silence_start_str} - {silence_end_str}")
                        print(f"  整体偏移量: {time_offset:.2f}s (应用偏移)")
                    else:
                        first_start_str = self.seconds_to_minutes_str(original_first_start)
                        silence_start_str = self.seconds_to_minutes_str(silence_start)
                        silence_end_str = self.seconds_to_minutes_str(silence_end)
                        print(f"\n整体时间偏移计算:")
                        print(f"  首次字幕时间: {first_start_str}")
                        print(f"  对应静音段: {silence_start_str} - {silence_end_str}")
                        print(f"  原始偏移量: {raw_offset:.2f}s (超过±{self.overall_time_offset_threshold}秒，不应用偏移)")
                    break
    
        # 存储每个组的原始结束时间（用于第二遍校验）
        group_info = []
        
        for group_idx, group in enumerate(sentence_groups):
            first_event_idx = group[0]
            original_start_seconds = self.ass_time_to_seconds(events[first_event_idx]['start_time'])
            original_end_seconds = self.ass_time_to_seconds(events[first_event_idx]['end_time'])
            
            # 检查原始持续时间是否小于阈值
            original_duration = original_end_seconds - original_start_seconds
            if original_duration < self.min_duration_threshold:
                print(f"\n字幕组 {group_idx+1}: 原始持续时间 {original_duration:.2f}秒 < {self.min_duration_threshold}秒，保持原始时间不做处理")
                
                # 保持原始时间，只应用整体偏移
                calibrated_start = original_start_seconds + time_offset
                calibrated_end = original_end_seconds + time_offset
                
                # 确保不重叠
                if group_idx + 1 < len(sentence_groups):
                    next_group_first_idx = sentence_groups[group_idx + 1][0]
                    next_start = self.ass_time_to_seconds(events[next_group_first_idx]['start_time']) + time_offset
                    if calibrated_end >= next_start - self.min_gap:
                        calibrated_end = next_start - self.min_gap
                
                for event_idx in group:
                    calibrated_event = calibrated_events[event_idx]
                    calibrated_event['start_time'] = self.seconds_to_ass_time(calibrated_start)
                    calibrated_event['end_time'] = self.seconds_to_ass_time(calibrated_end)
                    calibrated_event['original_line'] = f"Dialogue: 0,{calibrated_event['start_time']},{calibrated_event['end_time']},Default,,0000,0000,0000,,{calibrated_event['text']}"
                
                # 保存组信息，标记为短持续时间
                group_info.append({
                    'indices': group,
                    'adjusted_start': original_start_seconds + time_offset,
                    'adjusted_end': original_end_seconds + time_offset,
                    'calibrated_start': calibrated_start,
                    'calibrated_end': calibrated_end,
                    'is_short_duration': True
                })
                
                calibrated_start_str = self.seconds_to_minutes_str(calibrated_start)
                calibrated_end_str = self.seconds_to_minutes_str(calibrated_end)
                print(f"  保持时间: {calibrated_start_str} -> {calibrated_end_str} (持续: {calibrated_end - calibrated_start:.2f}秒)")
                continue  # 跳过后续校准处理
            
            # 正常处理（持续时间 >= 阈值）
            adjusted_start_seconds = original_start_seconds + time_offset
            adjusted_end_seconds = original_end_seconds + time_offset
            
            next_start = audio_duration
            if group_idx + 1 < len(sentence_groups):
                next_group_first_idx = sentence_groups[group_idx + 1][0]
                next_start = self.ass_time_to_seconds(events[next_group_first_idx]['start_time']) + time_offset
            
            calibrated_start = adjusted_start_seconds
            calibrated_end = adjusted_end_seconds
            start_decision_reason = "保持调整后开始时间"
            end_decision_reason = "保持调整后结束时间"
            
            candidate_silences = []
            seen_silences = set()
            
            for silence_start, silence_end in silence_segments:
                if silence_end > adjusted_start_seconds and silence_start < next_start:
                    silence_key = (silence_start, silence_end)
                    if silence_key not in seen_silences:
                        seen_silences.add(silence_key)
                        candidate_silences.append((silence_start, silence_end))
            
            start_time_str = self.seconds_to_minutes_str(adjusted_start_seconds)
            end_time_str = self.seconds_to_minutes_str(adjusted_end_seconds)
            print(f"\n字幕组 {group_idx+1}: {start_time_str} - {end_time_str} (原持续: {original_duration:.2f}s)")
            print(f"  候选静音段: {len(candidate_silences)} 个")
            for i, (silence_start, silence_end) in enumerate(candidate_silences):
                silence_duration = silence_end - silence_start
                silence_start_str = self.seconds_to_minutes_str(silence_start)
                silence_end_str = self.seconds_to_minutes_str(silence_end)
                duration_tag = ">2s" if silence_duration >= 2.0 else ""
                print(f"    候选[{i}]: {silence_start_str} - {silence_end_str} (持续: {silence_duration:.2f}s) {duration_tag}")
            
            if candidate_silences:
                for silence_start, silence_end in candidate_silences:
                    # 情况1：开始时间在静音段内
                    if silence_start <= adjusted_start_seconds <= silence_end:
                        adjustment = silence_end - adjusted_start_seconds
                        if adjustment > self.max_start_adjustment:
                            calibrated_start = adjusted_start_seconds
                            start_decision_reason = f"开始时间在静音段内，但调整量{adjustment:.2f}s>{self.max_start_adjustment}s，忽略调整"
                            adjusted_start_str = self.seconds_to_minutes_str(adjusted_start_seconds)
                            silence_start_str = self.seconds_to_minutes_str(silence_start)
                            silence_end_str = self.seconds_to_minutes_str(silence_end)
                            print(f"  开始时间校准: {adjusted_start_str} 在静音段 [{silence_start_str} - {silence_end_str}] 内")
                            print(f"    调整量 {adjustment:.2f}s > {self.max_start_adjustment}s，忽略调整，保持原开始时间")
                        else:
                            # 调整到静音段结束时间，然后提前start_time_lead秒
                            calibrated_start = max(silence_end - self.start_time_lead, silence_start)
                            # 确保不早于静音段开始时间
                            if calibrated_start < silence_start:
                                calibrated_start = silence_start

                            silence_end_str = self.seconds_to_minutes_str(silence_end)
                            calibrated_start_str = self.seconds_to_minutes_str(calibrated_start)
                            
                            # 计算实际提前量
                            actual_lead = silence_end - calibrated_start
                            if actual_lead > 0:
                                start_decision_reason = f"开始时间在静音段内，调整到静音结束时间并提前{actual_lead:.2f}s显示: {calibrated_start_str}"
                            else:
                                start_decision_reason = f"开始时间在静音段内，调整到静音段开始时间: {calibrated_start_str}"
                                
                            adjusted_start_str = self.seconds_to_minutes_str(adjusted_start_seconds)
                            silence_start_str = self.seconds_to_minutes_str(silence_start)
                            print(f"  开始时间校准: {adjusted_start_str} 在静音段 [{silence_start_str} - {silence_end_str}] 内")
                            print(f"    调整到 {silence_end_str} 并提前{self.start_time_lead}s -> {calibrated_start_str} (实际提前{actual_lead:.2f}s)")
                        break
                    
                    # 情况2：开始时间在静音段开始前阈值内
                    if (abs(adjusted_start_seconds - silence_start) <= self.start_time_near_silence_threshold and
                        adjusted_start_seconds <= silence_start):
                        adjustment = silence_end - adjusted_start_seconds
                        if adjustment > self.max_start_adjustment:
                            calibrated_start = adjusted_start_seconds
                            start_decision_reason = f"开始时间在静音段开始{self.start_time_near_silence_threshold}秒内，但调整量{adjustment:.2f}s>{self.max_start_adjustment}s，忽略调整"
                            adjusted_start_str = self.seconds_to_minutes_str(adjusted_start_seconds)
                            silence_start_str = self.seconds_to_minutes_str(silence_start)
                            print(f"  开始时间校准: {adjusted_start_str} 在静音段开始 [{silence_start_str}] {self.start_time_near_silence_threshold}秒内")
                            print(f"    调整量 {adjustment:.2f}s > {self.max_start_adjustment}s，忽略调整，保持原开始时间")
                        else:
                            # 调整到静音段结束时间，然后提前start_time_lead秒
                            calibrated_start = max(silence_end - self.start_time_lead, silence_start)
                            # 确保不早于静音段开始时间
                            if calibrated_start < silence_start:
                                calibrated_start = silence_start

                            silence_end_str = self.seconds_to_minutes_str(silence_end)
                            calibrated_start_str = self.seconds_to_minutes_str(calibrated_start)
                            
                            # 计算实际提前量
                            actual_lead = silence_end - calibrated_start
                            if actual_lead > 0:
                                start_decision_reason = f"开始时间在静音段开始{self.start_time_near_silence_threshold}秒内，调整到静音结束时间并提前{actual_lead:.2f}s显示: {calibrated_start_str}"
                            else:
                                start_decision_reason = f"开始时间在静音段开始{self.start_time_near_silence_threshold}秒内，调整到静音段开始时间: {calibrated_start_str}"
                                
                            adjusted_start_str = self.seconds_to_minutes_str(adjusted_start_seconds)
                            silence_start_str = self.seconds_to_minutes_str(silence_start)
                            print(f"  开始时间校准: {adjusted_start_str} 在静音段开始 [{silence_start_str}] {self.start_time_near_silence_threshold}秒内")
                            print(f"    调整到 {silence_end_str} 并提前{self.start_time_lead}s -> {calibrated_start_str} (实际提前{actual_lead:.2f}s)")
                        break
            
            # 修改结束时间选择逻辑：优先选择第一个大于2秒的长静音段
            if candidate_silences:
                # 寻找大于2秒的长静音段
                long_silences = []
                for silence_start, silence_end in candidate_silences:
                    silence_duration = silence_end - silence_start
                    if silence_duration >= 2.0 and silence_start > calibrated_start:
                        long_silences.append((silence_start, silence_end, silence_duration))
                
                if long_silences:
                    # 按出现顺序（时间先后）排序，选择第一个
                    long_silences.sort(key=lambda x: x[0])  # 按开始时间排序
                    best_silence_start, best_silence_end, best_duration = long_silences[0]
                    
                    calibrated_end = best_silence_start
                    best_silence_start_str = self.seconds_to_minutes_str(best_silence_start)
                    adjusted_end_str = self.seconds_to_minutes_str(adjusted_end_seconds)
                    end_decision_reason = f"找到大于2秒的静音段，选择第一个出现的静音段开始: {best_silence_start_str} (持续: {best_duration:.2f}s)"
                    print(f"  结束时间校准: 使用第一个大于2秒的静音段开始时间 {best_silence_start_str}")
                else:
                    # 没有大于2秒的静音段，寻找任何符合条件的静音段
                    sentence_end_silences = []
                    for silence_start, silence_end in candidate_silences:
                        if silence_start > calibrated_start and abs(silence_end - next_start) <= self.silence_end_tolerance:
                            distance_to_original = abs(silence_start - adjusted_end_seconds)
                            sentence_end_silences.append((silence_start, silence_end, distance_to_original))
                    
                    if sentence_end_silences:
                        # 按距离原始结束时间从近到远排序
                        sentence_end_silences.sort(key=lambda x: x[2])
                        
                        # 如果前两个候选距离很接近，选择静音段更长的
                        if len(sentence_end_silences) > 1:
                            first_dist = sentence_end_silences[0][2]
                            second_dist = sentence_end_silences[1][2]
                            if abs(first_dist - second_dist) < 0.3:
                                first_duration = sentence_end_silences[0][1] - sentence_end_silences[0][0]
                                second_duration = sentence_end_silences[1][1] - sentence_end_silences[1][0]
                                if second_duration > first_duration + 0.2:
                                    best_silence_start, best_silence_end, best_distance = sentence_end_silences[1]
                                    print(f"  结束时间校准: 选择更长的静音段 (持续: {second_duration:.2f}s)")
                                else:
                                    best_silence_start, best_silence_end, best_distance = sentence_end_silences[0]
                            else:
                                best_silence_start, best_silence_end, best_distance = sentence_end_silences[0]
                        else:
                            best_silence_start, best_silence_end, best_distance = sentence_end_silences[0]
                        
                        calibrated_end = best_silence_start
                        best_silence_start_str = self.seconds_to_minutes_str(best_silence_start)
                        adjusted_end_str = self.seconds_to_minutes_str(adjusted_end_seconds)
                        end_decision_reason = f"静音段结束时间在下一句开始±{self.silence_end_tolerance}秒内，选择最接近原始结束时间({adjusted_end_str})的静音段开始: {best_silence_start_str} (距离: {best_distance:.2f}s)"
                        print(f"  结束时间校准: 使用静音段开始时间 {best_silence_start_str} (最接近原始结束时间)")
                    else:
                        if adjusted_end_seconds < next_start - self.min_gap:
                            calibrated_end = adjusted_end_seconds
                            calibrated_end_str = self.seconds_to_minutes_str(calibrated_end)
                            end_decision_reason = f"未找到合适静音段，保持原始结束时间: {calibrated_end_str}"
                            print(f"  结束时间校准: 未找到合适静音段，保持原始时间")
                        else:
                            calibrated_end = next_start - self.min_gap
                            calibrated_end_str = self.seconds_to_minutes_str(calibrated_end)
                            end_decision_reason = f"未找到合适静音段且原始时间太接近下一句，调整到下一句前: {calibrated_end_str}"
                            print(f"  结束时间校准: 原始结束时间太接近下一句，调整到 {calibrated_end_str}")
            else:
                if adjusted_end_seconds < next_start - self.min_gap:
                    calibrated_end = adjusted_end_seconds
                    calibrated_end_str = self.seconds_to_minutes_str(calibrated_end)
                    end_decision_reason = f"无静音段，保持原始结束时间: {calibrated_end_str}"
                    print(f"  结束时间校准: 无静音段，但原始结束时间与下一句有足够间隔，保持原始时间")
                else:
                    calibrated_end = next_start - self.min_gap
                    calibrated_end_str = self.seconds_to_minutes_str(calibrated_end)
                    end_decision_reason = f"无静音段且原始时间太接近下一句，调整到下一句前: {calibrated_end_str}"
                    print(f"  结束时间校准: 原始结束时间太接近下一句，调整到 {calibrated_end_str}")
            
            # 第一遍限制：如果校准后的结束时间比原始结束时间晚了超过限制，限制只能延长指定时间
            if calibrated_end > adjusted_end_seconds + self.max_end_extension:
                limited_end = adjusted_end_seconds + self.max_end_extension
                if limited_end < next_start - self.min_gap:
                    calibrated_end_str = self.seconds_to_minutes_str(calibrated_end)
                    adjusted_end_str = self.seconds_to_minutes_str(adjusted_end_seconds)
                    limited_end_str = self.seconds_to_minutes_str(limited_end)
                    print(f"  第一遍限制: 校准后结束时间 {calibrated_end_str} 比原始结束时间 {adjusted_end_str} 晚了超过{self.max_end_extension}秒，限制只能延长{self.max_end_extension}秒")
                    calibrated_end = limited_end
                    calibrated_end_str = self.seconds_to_ass_time(calibrated_end)
                    end_decision_reason = f"第一遍限制延长{self.max_end_extension}秒，调整到: {calibrated_end_str}"

            if calibrated_start >= calibrated_end:
                calibrated_end = calibrated_start + 0.1
                end_decision_reason = "最小持续时间"
                print(f"  时间修正: 开始时间晚于结束时间，设置最小持续时间")
        
            if calibrated_end >= next_start - self.min_gap:
                calibrated_end = next_start - self.min_gap
                calibrated_end_str = self.seconds_to_minutes_str(calibrated_end)
                end_decision_reason = f"下一组前移 (距下一组 {next_start - calibrated_end:.2f}秒)"
                print(f"  时间修正: 结束时间太接近下一句，调整到 {calibrated_end_str}")
        
            for event_idx in group:
                calibrated_event = calibrated_events[event_idx]
                calibrated_event['start_time'] = self.seconds_to_ass_time(calibrated_start)
                calibrated_event['end_time'] = self.seconds_to_ass_time(calibrated_end)
                calibrated_event['original_line'] = f"Dialogue: 0,{calibrated_event['start_time']},{calibrated_event['end_time']},Default,,0000,0000,0000,,{calibrated_event['text']}"
        
            # 保存组信息用于第二遍校验
            group_info.append({
                'indices': group,
                'adjusted_start': adjusted_start_seconds,
                'adjusted_end': adjusted_end_seconds,
                'calibrated_start': calibrated_start,
                'calibrated_end': calibrated_end,
                'is_short_duration': False
            })
        
            group_size = len(group)
            group_type = "多行字幕组" if group_size > 1 else "单行字幕"
            final_duration = calibrated_end - calibrated_start
            calibrated_start_str = self.seconds_to_minutes_str(calibrated_start)
            calibrated_end_str = self.seconds_to_minutes_str(calibrated_end)
            print(f"{group_type} {group_idx+1} (包含{group_size}行): {calibrated_start_str} -> {calibrated_end_str}")
            print(f"  开始时间决策: {start_decision_reason}")
            print(f"  结束时间决策: {end_decision_reason}")
            print(f"  持续时间: 原始={original_duration:.2f}s, 校准后={final_duration:.2f}s")

        calibrated_events = self.second_pass_validation(calibrated_events, sentence_groups, group_info, silence_segments, audio_duration)

        self.print_events_debug(calibrated_events, "校准字幕后")

        return calibrated_events
    
    def second_pass_validation(self, calibrated_events, sentence_groups, group_info, silence_segments, audio_duration):
        """第二遍校验：根据文本长度调整最小显示时间"""
        print("\n" + "=" * 60)
        print("第二遍校验：根据文本长度调整最小显示时间")
        print(f"注意：原始持续时间小于{self.min_duration_threshold}秒的字幕组将跳过第二遍校验")
        print("=" * 60)
        
        validated_events = calibrated_events.copy()
        
        for group_idx, group in enumerate(sentence_groups):
            if not group:
                continue
                
            # 检查是否为短持续时间组
            if group_idx < len(group_info) and group_info[group_idx].get('is_short_duration', False):
                print(f"\n跳过短持续时间字幕组 {group_idx+1} (原始持续时间<{self.min_duration_threshold}秒)")
                continue
                
            first_event_idx = group[0]
            event = validated_events[first_event_idx]
            
            current_start = self.ass_time_to_seconds(event['start_time'])
            current_end = self.ass_time_to_seconds(event['end_time'])
            current_duration = current_end - current_start
            
            next_start = audio_duration
            if group_idx + 1 < len(sentence_groups):
                next_group_first_idx = sentence_groups[group_idx + 1][0]
                next_start = self.ass_time_to_seconds(validated_events[next_group_first_idx]['start_time'])
            
            # 获取第一遍校准的信息
            group_data = group_info[group_idx]
            adjusted_end = group_data['adjusted_end']
            
            first_event_text = event['text']
            if '\\N' in first_event_text:
                first_line = first_event_text.split('\\N')[0]
            else:
                first_line = first_event_text
            
            text_length = self.get_plain_text_length(first_line)
            
            current_start_str = self.seconds_to_minutes_str(current_start)
            current_end_str = self.seconds_to_minutes_str(current_end)
            adjusted_end_str = self.seconds_to_minutes_str(adjusted_end)
            next_start_str = self.seconds_to_minutes_str(next_start)
            
            print(f"\n校验字幕组 {group_idx+1}:")
            print(f"  当前时间: {current_start_str} - {current_end_str} (持续: {current_duration:.2f}s)")
            print(f"  第一行文本: '{self.safe_print(first_line, 30)}'")
            print(f"  纯文本长度: {text_length} 字符")
            print(f"  原始结束时间(调整偏移后): {adjusted_end_str}")
            print(f"  下一组开始时间: {next_start_str}")
            
            min_display_time = self.min_display_time_short if text_length <= self.short_text_length_threshold else self.min_display_time_long
            need_adjustment = current_duration < min_display_time
            
            # 检查是否是歌词模式的一部分
            is_lyrics = False
            lyrics_text_patterns = ["can't stop", "won't stop", "we can make your heart", "heart drop"]
            text_lower = first_line.lower()
            for pattern in lyrics_text_patterns:
                if pattern in text_lower:
                    is_lyrics = True
                    break
            
            # 检查是否是重复的短句模式
            if not is_lyrics and group_idx < len(sentence_groups) - 2:
                next_group_first_idx = sentence_groups[group_idx + 1][0]
                next_next_group_first_idx = sentence_groups[group_idx + 2][0]
                next_event = validated_events[next_group_first_idx]
                next_next_event = validated_events[next_next_group_first_idx]
                
                current_text = first_line[:15].lower()
                next_text = next_event['text'][:15].lower() if len(next_event['text']) > 15 else next_event['text'].lower()
                next_next_text = next_next_event['text'][:15].lower() if len(next_next_event['text']) > 15 else next_next_event['text'].lower()
                
                # 检测是否有相似的文本模式
                if (current_text in next_text or next_text in current_text or
                    current_text in next_next_text or next_next_text in current_text):
                    is_lyrics = True
            
            if is_lyrics:
                print(f"  检测到歌词模式，保持当前时间或使用原始时间")
                # 对于歌词，优先恢复到原始结束时间（如果合理）
                if current_end < adjusted_end:
                    # 检查原始结束时间是否合理
                    if adjusted_end < next_start - self.min_gap:
                        new_end = adjusted_end
                        extend_amount = new_end - current_end
                        if extend_amount > 0:
                            new_end_str = self.seconds_to_minutes_str(new_end)
                            print(f"  歌词模式: 恢复到原始结束时间 {new_end_str}")
                            for event_idx in group:
                                validated_event = validated_events[event_idx]
                                validated_event['end_time'] = self.seconds_to_ass_time(new_end)
                                validated_event['original_line'] = f"Dialogue: 0,{validated_event['start_time']},{validated_event['end_time']},Default,,0000,0000,0000,,{validated_event['text']}"
                        else:
                            print(f"  歌词模式: 当前结束时间已经晚于或等于原始结束时间，保持当前")
                    else:
                        # 如果原始结束时间太接近下一句，调整到合理位置
                        new_end = next_start - self.min_gap
                        new_end_str = self.seconds_to_minutes_str(new_end)
                        print(f"  歌词模式: 原始结束时间太接近下一句，调整到 {new_end_str}")
                        for event_idx in group:
                            validated_event = validated_events[event_idx]
                            validated_event['end_time'] = self.seconds_to_ass_time(new_end)
                            validated_event['original_line'] = f"Dialogue: 0,{validated_event['start_time']},{validated_event['end_time']},Default,,0000,0000,0000,,{validated_event['text']}"
                else:
                    print(f"  歌词模式: 当前结束时间已经合理，保持当前")
            
            elif need_adjustment:
                print(f"  需要调整: 当前持续时间({current_duration:.2f}s) < 最小显示时间({min_display_time}s)")
                
                # 计算期望结束时间
                desired_end = current_start + min_display_time
                
                # 最大允许结束时间
                max_allowed_end = next_start - self.min_gap
                
                if desired_end > max_allowed_end:
                    desired_end_str = self.seconds_to_minutes_str(desired_end)
                    max_allowed_end_str = self.seconds_to_minutes_str(max_allowed_end)
                    print(f"  期望结束时间 {desired_end_str} 超过最大允许值 {max_allowed_end_str}")
                    desired_end = max_allowed_end
                
                suitable_silences = []
                
                # 检查当前开始时间到下一句开始时间之间的静音段
                for silence_start, silence_end in silence_segments:
                    silence_duration = silence_end - silence_start
                    # 静音段开始时间在当前结束时间之后，且在下一句开始时间之前
                    if current_end <= silence_start <= next_start and silence_duration >= 0.3:
                        distance_to_desired = abs(silence_start - desired_end)
                        suitable_silences.append((silence_start, silence_end, silence_duration, distance_to_desired))
                
                print(f"  找到 {len(suitable_silences)} 个大于0.3秒的合适静音段")
                
                new_end = current_end
                
                if suitable_silences:
                    # 按距离期望结束时间从近到远排序
                    suitable_silences.sort(key=lambda x: x[3])
                    
                    # 选择最接近期望结束时间的静音段
                    best_silence = suitable_silences[0]
                    new_end = best_silence[0]
                    best_silence_start_str = self.seconds_to_minutes_str(best_silence[0])
                    distance_to_desired_str = self.seconds_to_minutes_str(best_silence[3])
                    print(f"  策略1: 选择最接近期望结束时间的静音段，使用 {best_silence_start_str} (距离期望结束时间: {distance_to_desired_str}s)")
                else:
                    # 新增规则：无合适静音段时，直接调整到下一句开始时间（提前0.1秒）
                    # 但是，如果期望结束时间早于这个时间，就使用期望结束时间
                    new_end = min(desired_end, max_allowed_end)
                    
                    if new_end == max_allowed_end:
                        new_end_str = self.seconds_to_minutes_str(new_end)
                        desired_end_str = self.seconds_to_minutes_str(desired_end)
                        print(f"  策略2: 无合适静音段，直接调整到下一句开始时间（提前{self.min_gap}秒）: {new_end_str}")
                        print(f"  原因: 期望结束时间 {desired_end_str} 超过下一句开始时间前{self.min_gap}秒")
                    else:
                        new_end_str = self.seconds_to_minutes_str(new_end)
                        print(f"  策略2: 无合适静音段，直接延长到期望结束时间: {new_end_str}")
                
                # 第二遍限制逻辑：
                # 如果第一遍错误地缩短了字幕（current_end < adjusted_end），允许延长回去，不受限制
                # 否则，限制最多延长指定时间
                extend_amount = new_end - current_end
                new_end_str = self.seconds_to_minutes_str(new_end)
                current_end_str = self.seconds_to_minutes_str(current_end)
                adjusted_end_str = self.seconds_to_minutes_str(adjusted_end)
                
                if current_end >= adjusted_end:
                    # 当前结束时间已经等于或晚于原始结束时间，限制最多延长指定时间
                    if extend_amount > self.max_end_extension:
                        print(f"  第二遍限制: 延长量 {extend_amount:.2f}s 超过{self.max_end_extension}秒限制，限制为{self.max_end_extension}秒")
                        new_end = current_end + self.max_end_extension
                        new_end_str = self.seconds_to_minutes_str(new_end)
                        extend_amount = self.max_end_extension
                else:
                    # 当前结束时间早于原始结束时间（第一遍可能错误缩短），允许延长回去
                    # 但限制不能超过原始结束时间
                    if new_end > adjusted_end:
                        print(f"  允许延长回原始结束时间: {adjusted_end_str}")
                        new_end = min(adjusted_end, new_end)
                        new_end_str = self.seconds_to_minutes_str(new_end)
                        extend_amount = new_end - current_end
                
                if extend_amount > 0:
                    if new_end >= next_start - self.min_gap:
                        new_end = next_start - self.min_gap
                        new_end_str = self.seconds_to_minutes_str(new_end)
                        print(f"  时间修正: 结束时间太接近下一句，调整到 {new_end_str}")
                    
                    if abs(new_end - current_end) > 0.01:
                        final_duration = new_end - current_start
                        print(f"  原结束时间: {current_end_str} -> 新结束时间: {new_end_str}")
                        print(f"  延长了 {extend_amount:.2f}s")
                        print(f"  最终持续时间: {final_duration:.2f}s")
                        
                        for event_idx in group:
                            validated_event = validated_events[event_idx]
                            validated_event['end_time'] = self.seconds_to_ass_time(new_end)
                            validated_event['original_line'] = f"Dialogue: 0,{validated_event['start_time']},{validated_event['end_time']},Default,,0000,0000,0000,,{validated_event['text']}"
                    else:
                        print(f"  未调整结束时间")
                else:
                    print(f"  延长量为0或负值，不调整")
            else:
                print(f"  无需调整: 当前持续时间({current_duration:.2f}s) ≥ 最小显示时间({min_display_time}s)")
            
            # 安全检查
            current_end_check = self.ass_time_to_seconds(validated_events[first_event_idx]['end_time'])
            if current_end_check >= next_start - self.min_gap:
                new_end_check = next_start - self.min_gap
                current_end_check_str = self.seconds_to_minutes_str(current_end_check)
                new_end_check_str = self.seconds_to_minutes_str(new_end_check)
                next_start_str = self.seconds_to_minutes_str(next_start)
                print(f"  安全检查: 结束时间 {current_end_check_str} 太接近下一句 {next_start_str}，调整到 {new_end_check_str}")
                
                for event_idx in group:
                    validated_event = validated_events[event_idx]
                    validated_event['end_time'] = self.seconds_to_ass_time(new_end_check)
                    validated_event['original_line'] = f"Dialogue: 0,{validated_event['start_time']},{validated_event['end_time']},Default,,0000,0000,0000,,{validated_event['text']}"

        return validated_events
    
    # ============================
    # 辅助方法
    # ============================
    def _normalize_ass_time(self, time_str):
        """标准化ASS时间格式为 H:MM:SS.cc"""
        time_str = time_str.strip()
        time_str = time_str.replace(',', '.')
        
        parts = time_str.split(':')
        
        if len(parts) == 3:
            hours = parts[0].lstrip('0')
            if not hours:
                hours = '0'
            
            minutes = parts[1].zfill(2)
            
            seconds_part = parts[2]
            if '.' in seconds_part:
                seconds, milliseconds = seconds_part.split('.')
                seconds = seconds.zfill(2)
                if len(milliseconds) > 2:
                    milliseconds = milliseconds[:2]
                elif len(milliseconds) < 2:
                    milliseconds = milliseconds.ljust(2, '0')
                return f"{hours}:{minutes}:{seconds}.{milliseconds}"
            else:
                seconds = seconds_part.zfill(2)
                return f"{hours}:{minutes}:{seconds}.00"
        
        return time_str
    
    def _normalize_time_format(self, time_str):
        """确保时间格式为 H:MM:SS.cc (毫秒2位)"""
        parts = time_str.split(':')
        if len(parts) == 3:
            hours = parts[0]
            minutes = parts[1]
            seconds_parts = parts[2].split('.')
            if len(seconds_parts) == 2:
                seconds = seconds_parts[0]
                milliseconds = seconds_parts[1]
                if len(milliseconds) > 2:
                    milliseconds = milliseconds[:2]
                elif len(milliseconds) < 2:
                    milliseconds = milliseconds.ljust(2, '0')
                return f"{hours}:{minutes}:{seconds}.{milliseconds}"
        return time_str
    
    # ============================
    # 格式转换方法
    # ============================
    def _ass_to_unified_ass(self, ass_content):
        """将ASS格式字幕转换为统一格式的ASS"""
        events = self.parse_ass_events(ass_content)
        ass_lines = self.ASS_HEADER.copy()
        
        for event in events:
            clean_text = self.remove_ass_tags(event['text'])
            ass_line = f"Dialogue: 0,{event['start_time']},{event['end_time']},Default,,0000,0000,0000,,{clean_text}"
            ass_lines.append(ass_line)
        
        return '\n'.join(ass_lines)
    
    def _srt_to_ass(self, srt_content):
        """转换SRT为ASS，根据merge_multiline参数决定是否合并多行"""
        print("转换SRT到ASS，多行字幕合并开关: {}".format("开启" if self.merge_multiline == 1 else "关闭"))
        lines = srt_content.split('\n')
        ass_lines = self.ASS_HEADER.copy()
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            
            if line.isdigit():
                if i + 1 < len(lines):
                    time_line = lines[i + 1].strip()
                    if '-->' in time_line:
                        start_time, end_time = self._parse_srt_time(time_line)
                        text_lines = []
                        j = i + 2
                        while j < len(lines) and lines[j].strip():
                            text_lines.append(lines[j].strip())
                            j += 1
                        
                        # 根据merge_multiline参数决定合并方式
                        if text_lines:
                            if self.merge_multiline == 1:
                                # 合并多行：用空格连接
                                combined_text = ' '.join(text_lines)
                            else:
                                # 不合并：用\N分隔多行
                                combined_text = r'\N'.join(text_lines)
                            
                            clean_text = self.remove_ass_tags(combined_text)
                            ass_line = f"Dialogue: 0,{start_time},{end_time},Default,,0000,0000,0000,,{clean_text}"
                            ass_lines.append(ass_line)
                        
                        i = j
                    else:
                        i += 1
                else:
                    i += 1
            else:
                i += 1
        
        return '\n'.join(ass_lines)
    
    def _vtt_to_ass(self, vtt_content):
        """转换VTT为ASS，根据merge_multiline参数决定是否合并多行"""
        print("转换VTT到ASS，多行字幕合并开关: {}".format("开启" if self.merge_multiline == 1 else "关闭"))
        lines = vtt_content.split('\n')
        ass_lines = self.ASS_HEADER.copy()
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line or line == 'WEBVTT' or line.startswith('NOTE') or line.startswith('STYLE'):
                i += 1
                continue
            
            if '-->' in line:
                parts = line.split('-->')
                if len(parts) == 2:
                    start_time = self._vtt_time_to_ass(parts[0].strip())
                    end_time = self._vtt_time_to_ass(parts[1].strip())
                    
                    text_lines = []
                    j = i + 1
                    while j < len(lines) and lines[j].strip():
                        text_lines.append(lines[j].strip())
                        j += 1
                    
                    # 根据merge_multiline参数决定合并方式
                    if text_lines:
                        if self.merge_multiline == 1:
                            # 合并多行：用空格连接
                            combined_text = ' '.join(text_lines)
                        else:
                            # 不合并：用\N分隔多行
                            combined_text = r'\N'.join(text_lines)
                        
                        clean_text = self.remove_ass_tags(combined_text)
                        ass_line = f"Dialogue: 0,{start_time},{end_time},Default,,0000,0000,0000,,{clean_text}"
                        ass_lines.append(ass_line)
                    
                    i = j
                else:
                    i += 1
            else:
                i += 1
        
        return '\n'.join(ass_lines)
    
    def _generic_to_ass(self, content):
        """通用转换，根据merge_multiline参数决定是否合并多行"""
        lines = content.split('\n')
        ass_lines = self.ASS_HEADER.copy()
        
        # 尝试检测是否有时间信息
        has_time_info = False
        for line in lines:
            if '-->' in line:
                has_time_info = True
                break
        
        if has_time_info:
            # 如果有时间信息，尝试解析
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if not line:
                    i += 1
                    continue
                
                if '-->' in line:
                    parts = line.split('-->')
                    if len(parts) == 2:
                        start_time = parts[0].strip()
                        end_time = parts[1].strip()
                        start_time = self._normalize_time_format(start_time)
                        end_time = self._normalize_time_format(end_time)
                        
                        text_lines = []
                        j = i + 1
                        while j < len(lines) and lines[j].strip():
                            text_lines.append(lines[j].strip())
                            j += 1
                        
                        # 根据merge_multiline参数决定合并方式
                        if text_lines:
                            if self.merge_multiline == 1:
                                # 合并多行：用空格连接
                                combined_text = ' '.join(text_lines)
                            else:
                                # 不合并：用\N分隔多行
                                combined_text = r'\N'.join(text_lines)
                            
                            clean_text = self.remove_ass_tags(combined_text)
                            ass_line = f"Dialogue: 0,{start_time},{end_time},Default,,0000,0000,0000,,{clean_text}"
                            ass_lines.append(ass_line)
                        
                        i = j
                    else:
                        i += 1
                else:
                    i += 1
        else:
            # 没有时间信息，按行处理
            for i, line in enumerate(lines):
                line = line.strip()
                if line:
                    start_time = self.seconds_to_ass_time(i * 3)
                    end_time = self.seconds_to_ass_time((i + 1) * 3)
                    clean_text = self.remove_ass_tags(line)
                    ass_line = f"Dialogue: 0,{start_time},{end_time},Default,,0000,0000,0000,,{clean_text}"
                    ass_lines.append(ass_line)
        
        return '\n'.join(ass_lines)
    
    def _parse_srt_time(self, time_line):
        parts = time_line.split('-->')
        if len(parts) != 2:
            return "0:00:00.00", "0:00:00.00"
        
        start_str = parts[0].strip().replace(',', '.')
        end_str = parts[1].strip().replace(',', '.')
        
        start_str = self._normalize_time_format(start_str)
        end_str = self._normalize_time_format(end_str)
        
        return start_str, end_str
    
    def _vtt_time_to_ass(self, vtt_time):
        vtt_time = vtt_time.split(' ')[0]
        vtt_time = vtt_time.replace(',', '.')
        return self._normalize_time_format(vtt_time)
    
    # ============================
    # 输出方法
    # ============================
    def create_calibrated_ass(self, original_ass, calibrated_events):
        """创建校准后的ASS文件内容"""
        lines = original_ass.split('\n')
        output_lines = []
        
        in_events = False
        event_index = 0
        
        for line in lines:
            if line.strip().startswith('[Events]'):
                in_events = True
                output_lines.append(line)
                continue
            elif line.strip().startswith('[') and in_events:
                in_events = False
        
            if in_events and line.strip().startswith('Dialogue:'):
                # 只使用校准后的事件，如果校准事件用完则跳过该行
                if event_index < len(calibrated_events):
                    dialogue_line = calibrated_events[event_index]['original_line']
                    output_lines.append(dialogue_line)
                    event_index += 1
                # 不保留原始行，直接跳过
                continue
            else:
                output_lines.append(line)
        
        # 如果还有未使用的校准事件（理论上不应该出现），添加到末尾
        while event_index < len(calibrated_events):
            output_lines.append(calibrated_events[event_index]['original_line'])
            event_index += 1
        
        return '\n'.join(output_lines)
    
    def remove_special_unicode_chars(self, text):
        """移除特殊Unicode字符"""
        import re
        cleaned = re.sub(r'[^\u0000-\uD7FF\uE000-\uFFFF]', '', text, flags=re.UNICODE)
        return cleaned
    
    # ============================
    # 主处理流程
    # ============================
    def process(self, audio_path, subtitle_path, output_path=None):
        """处理音频和字幕文件的主方法"""
        if output_path is None:
            output_path = Path(subtitle_path).parent / f"{Path(subtitle_path).stem}_calibrated.ass"
        
        print("=" * 60)
        print("音频断点检测与字幕校准工具（优化版）")
        print("校准策略：优先使用大于2秒的静音段，双语字幕保持独立")
        print(f"字幕提前显示时间: {self.start_time_lead}秒")
        print(f"短持续时间阈值: {self.min_duration_threshold}秒 (小于此值的不做处理)")
        print(f"多行字幕合并开关: {'开启' if self.merge_multiline == 1 else '关闭'}")
        print("=" * 60)
        print(f"音频文件: {audio_path}")
        print(f"字幕文件: {subtitle_path}")
        print(f"输出文件: {output_path}")
        
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            print("\n步骤1: 读取并转换字幕文件...")
            subtitle_content, encoding = self.read_subtitle_file(subtitle_path)
            ass_content = self.convert_to_ass(subtitle_content)
            
            print("\n步骤2: 分析音频能量分布...")
            times, energy, sr = self.analyze_audio_energy(audio_path)
            audio_duration = len(energy) * (times[1] - times[0]) if len(times) > 1 else times[-1]
            audio_duration_str = self.seconds_to_minutes_str(audio_duration)
            print(f"音频总时长: {audio_duration_str}")
            
            print("\n步骤3: 检测人声断点...")
            silence_segments = self.detect_voice_breaks(times, energy)
            print(f"检测到 {len(silence_segments)} 个静音段")
            
            print("\n步骤4: 解析字幕事件...")
            events = self.parse_ass_events(ass_content)
            print(f"解析到 {len(events)} 个字幕事件")
            
            print("\n步骤5: 合并短静音段...")
            silence_segments = self.merge_short_silences(silence_segments, events)
            
            print("\n步骤6: 双语字幕排序...")
            try:
                events = self.sort_bilingual_subtitles(events)
            except Exception as e:
                print(f"双语字幕排序失败: {e}，跳过排序")
            
            print("\n步骤7: 智能去重（基于文本和开始时间）...")
            events = self.smart_deduplicate(events)
            
            print("\n步骤8: 第一遍校准字幕时间（优先使用大于2秒静音段）...")
            calibrated_events = self.calibrate_subtitles(events, silence_segments, audio_duration)
            
            print("\n步骤9: 生成校准后的字幕文件...")
            calibrated_ass = self.create_calibrated_ass(ass_content, calibrated_events)
            
            try:
                safe_ass_content = self.remove_special_unicode_chars(calibrated_ass)
                with open(output_path, 'w', encoding='utf-8-sig', errors='ignore') as f:
                    f.write(safe_ass_content)
            except UnicodeEncodeError:
                try:
                    with open(output_path, 'w', encoding='utf-8', errors='ignore') as f:
                        f.write(safe_ass_content)
                except Exception as e:
                    print(f"文件写入失败: {e}")
                    raise
            
            print("\n" + "=" * 60)
            print("校准完成!")
            print("=" * 60)
            print(f"输出文件: {output_path}")
            
            # 打印最终结果的前几行
            print("\n最终结果预览（最后20行）:")
            lines = safe_ass_content.split('\n')
            for i, line in enumerate(lines[-20:]):
                if 'Dialogue:' in line:
                    print(line[:100] + "..." if len(line) > 100 else line)
            
            return output_path
            
        except Exception as e:
            print(f"\n处理失败: {e}")
            import traceback
            traceback.print_exc()
            return None


def parse_arguments():
    """解析命令行参数"""
    import argparse
    parser = argparse.ArgumentParser(description='音频断点检测与字幕校准工具')
    parser.add_argument('-a', '--audio', required=True, help='音频文件路径')
    parser.add_argument('-s', '--subtitle', required=True, help='字幕文件路径')
    parser.add_argument('-o', '--output', help='输出文件路径')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--merge-multiline', type=int, choices=[0, 1], default=1, 
                       help='合并多行字幕开关: 0=不合并, 1=合并(默认)')
    return parser.parse_args()


def command_line_main():
    """命令行主函数"""
    args = parse_arguments()
    calibrator = SubtitleCalibrator(debug=args.debug, merge_multiline=args.merge_multiline)
    try:
        result_path = calibrator.process(args.audio, args.subtitle, args.output)
        if result_path:
            print(f"字幕校准完成: {result_path}")
            return result_path
        else:
            print("字幕校准失败")
            return None
    except Exception as e:
        print(f"处理失败: {e}")
        return None


def get_user_input():
    """获取用户输入"""
    print("\n" + "-" * 40)
    print("请输入处理参数:")
    print("-" * 40)
    
    while True:
        audio_path = input("请输入人声音频文件路径: ").strip().strip('"')
        if not audio_path:
            print("路径不能为空")
            continue
        
        audio_path = Path(audio_path)
        if not audio_path.exists():
            print("文件不存在，请检查路径")
            continue
        break
    
    while True:
        subtitle_path = input("请输入字幕文件路径: ").strip().strip('"')
        if not subtitle_path:
            print("路径不能为空")
            continue
        
        subtitle_path = Path(subtitle_path)
        if not subtitle_path.exists():
            print("文件不存在，请检查路径")
            continue
        break
    
    output_path = input("请输入输出字幕文件路径(直接回车使用自动命名): ").strip().strip('"')
    if not output_path:
        output_path = None
    
    return {
        'audio_path': audio_path,
        'subtitle_path': subtitle_path,
        'output_path': output_path
    }


def main():
    """主函数"""
    if len(sys.argv) > 1 and ('-a' in sys.argv or '--audio' in sys.argv):
        result = command_line_main()
        sys.exit(0 if result else 1)
    else:
        print("=" * 60)
        print("音频断点检测与字幕校准工具")
        print("=" * 60)
        print("注意: 程序将直接开始处理，请按照提示输入参数。")
        print("如果需要命令行模式，请使用 -a 音频文件 -s 字幕文件 [-o 输出文件] [--debug] [--merge-multiline 0|1] 参数运行。")
        print()
        
        while True:
            print("\n" + "-" * 60)
            print("1. 开始新的字幕校准任务")
            print("2. 退出程序")
            print("-" * 60)
            
            choice = input("请选择 (1/2): ").strip()
            
            if choice == '2':
                print("程序退出。")
                break
            elif choice == '1':
                try:
                    user_input = get_user_input()
                    
                    calibrator = SubtitleCalibrator(
                        debug=True,
                        merge_multiline=1
                    )
                    
                    result = calibrator.process(
                        user_input['audio_path'],
                        user_input['subtitle_path'],
                        user_input['output_path']
                    )
                    
                    if result:
                        print("\n" + "=" * 60)
                        print("任务完成！")
                        print(f"输出文件: {result}")
                    else:
                        print("\n" + "=" * 60)
                        print("任务失败！")
                    
                    print("\n当前任务已完成，可以开始新的任务。")
                    
                except KeyboardInterrupt:
                    print("\n当前任务被用户中断")
                    continue
                except Exception as e:
                    print(f"\n程序运行出错: {e}")
                    import traceback
                    traceback.print_exc()
                    print("\n错误已记录，可以重新尝试。")
                    continue
            else:
                print("无效选择，请重新输入。")


if __name__ == "__main__":
    main()