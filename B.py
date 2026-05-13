import re
import sys
import subprocess

# 自动安装缺失的依赖
try:
    import librosa
except ImportError:
    print("librosa 未安装，正在安装...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "librosa", "--no-cache-dir"])
    import librosa

try:
    import numpy as np
except ImportError:
    print("numpy 未安装，正在安装...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy", "--no-cache-dir"])
    import numpy as np

from pathlib import Path
import argparse

# 修复 Windows 控制台编码问题
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 控制拖长音检测的开关
# 0: 关闭对应类型拖长音检测（不处理该类型拖长音）
# 1: 开启对应类型拖长音检测（根据音频分析结果动态分配K值）
ENABLE_BEGINNING_SUSTAIN_DETECTION = 0  # 句首延长音检测开关，默认为关闭
ENABLE_ENDING_SUSTAIN_DETECTION = 0  # 句末延长音检测开关，默认为关闭

# 对白字幕检测开关
# 0: 关闭对白字幕检测（正常处理所有字幕）
# 1: 开启对白字幕检测（识别混合K值情况，忽略无K值字幕，重新计算有K值字幕）
ENABLE_DIALOGUE_DETECTION = 1  # 默认为开启

# 拖长音相关参数配置
# 拖长音检测最小持续时间（秒）
SUSTAIN_MIN_DURATION = 0.5
# 拖长音最小持续时间（秒） - 小于此时间则采用整段效果
SUSTAIN_END_THRESHOLD = 0.8
# 长拖长音段持续时间阈值（秒）
SUSTAIN_LONG_THRESHOLD = 1.5
# 拖长音与字幕最小重叠时间（秒）
SUSTAIN_OVERLAP_THRESHOLD = 0.3
# 拖长音结束时间与字幕结束时间差阈值（秒）
SUSTAIN_END_TIME_DIFF = 0.5

# K值阈值配置（对应0.01秒/单位）
# 句首延长音最小K值 - 小于此值则采用整段效果
BEGINNING_SUSTAIN_MIN_K = 80  # 对应0.8秒
# 句末延长音最小K值 - 小于此值则采用整段效果
ENDING_SUSTAIN_MIN_K = 80    # 对应0.8秒

def format_time_seconds_to_minutes(seconds):
    """将秒数格式化为分钟:秒格式（例如：1:23.45）"""
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes}:{remaining_seconds:05.2f}"

class SustainDetector:
    """拖长音检测器 - 独立模块"""
    def __init__(self, stability_threshold=0.95, min_duration=SUSTAIN_MIN_DURATION):
        # 移除 merge_threshold 参数，因为我们不再合并
        self.stability_threshold = stability_threshold
        self.min_duration = min_duration
    
    def detect(self, audio_path):
        """检测音频中的拖长音段"""
        try:
            print(f"正在分析音频文件: {audio_path}")
            
            # 加载音频
            y, sr = librosa.load(audio_path, sr=22050)
            audio_duration = len(y)/sr
            print(f"音频信息: 采样率={sr}Hz, 时长={format_time_seconds_to_minutes(audio_duration)}")
            
            # 计算频谱图 - 使用更小的hop_length提高时间分辨率
            print("正在计算频谱图...")
            stft = librosa.stft(y, n_fft=2048, hop_length=256)
            spectrogram = librosa.amplitude_to_db(np.abs(stft), ref=np.max)
            times = librosa.times_like(spectrogram, sr=sr, hop_length=256)
            
            # 计算频谱稳定性
            print("正在计算频谱稳定性...")
            stability_scores = self._compute_stability_scores(spectrogram)
            
            # 计算能量轮廓
            energy = np.sum(librosa.db_to_amplitude(spectrogram), axis=0)
            energy = energy / np.max(energy)
            
            # 调试输出：显示数值分布
            print(f"频谱稳定性统计: 最小={np.min(stability_scores):.3f}, 最大={np.max(stability_scores):.3f}, 平均={np.mean(stability_scores):.3f}")
            print(f"能量统计: 最小={np.min(energy):.3f}, 最大={np.max(energy):.3f}, 平均={np.mean(energy):.3f}")
            high_stability_count = np.sum(np.array(stability_scores) > 0.9)
            print(f"稳定性>0.9的帧数: {high_stability_count}/{len(stability_scores)}")
            
            # 检测拖长音段（使用基频标准差过滤）
            print("正在检测拖长音段...")
            sustain_segments = self._find_sustain_segments(stability_scores, energy, times, y, sr)
            
            # 显示检测结果
            if sustain_segments:
                print(f"检测到 {len(sustain_segments)} 个独立的拖长音段:")
                for i, seg in enumerate(sustain_segments, 1):
                    start_formatted = format_time_seconds_to_minutes(seg['start'])
                    end_formatted = format_time_seconds_to_minutes(seg['end'])
                    print(f"  段{i}: {start_formatted} - {end_formatted} (持续 {seg['duration']:.2f}秒)")
                    print(f"       稳定性: {seg['avg_stability']:.4f}, 能量: {seg['avg_energy']:.4f}, 基频标准差: {seg.get('pitch_std', 'N/A'):.2f}")
            else:
                print("未检测到拖长音段")
            
            # 注意：这里直接返回检测到的拖长音段，不进行合并
            return sustain_segments
            
        except Exception as e:
            print(f"拖长音检测失败: {e}")
            return []
    
    def _compute_stability_scores(self, spectrogram):
        """计算频谱稳定性分数"""
        stability_scores = []
        for i in range(1, spectrogram.shape[1]):
            current_frame = spectrogram[:, i]
            prev_frame = spectrogram[:, i-1]
            try:
                # 检查数据是否为常数或全零，避免相关系数计算错误
                if np.std(current_frame) == 0 or np.std(prev_frame) == 0:
                    stability_scores.append(0)
                    continue
                
                # 计算相关系数，添加异常处理
                corr = np.corrcoef(current_frame, prev_frame)[0, 1]
                stability_scores.append(0 if np.isnan(corr) or np.isinf(corr) else (corr + 1) / 2)
            except Exception as e:
                stability_scores.append(0)
        return [0] + stability_scores
    
    def _compute_pitch_std(self, segment, sr):
        """计算基频标准差"""
        pyin_result = librosa.pyin(segment, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7'))
        pitches = pyin_result[0]
        return np.nanstd(pitches) if len(pitches) > 0 else float('inf')

    def _find_sustain_segments(self, stability_scores, energy, times, y, sr):
        """查找拖长音段（使用基频标准差过滤）"""
        PITCH_STD_THRESHOLD = 12
        sustain_segments = []
        i = 0
        while i < len(stability_scores):
            if stability_scores[i] > self.stability_threshold and energy[i] > 0.20:
                start_idx = i
                while (i < len(stability_scores) and 
                       stability_scores[i] > self.stability_threshold and 
                       energy[i] > 0.20):
                    i += 1
                end_idx = i - 1
                duration = times[end_idx] - times[start_idx]
                
                if duration >= self.min_duration:
                    # 计算基频标准差进行过滤
                    seg_start_idx = int(times[start_idx] * sr)
                    seg_end_idx = int(times[end_idx] * sr)
                    segment_audio = y[seg_start_idx:seg_end_idx]
                    pitch_std = self._compute_pitch_std(segment_audio, sr)
                    
                    # 只有基频标准差小于阈值的才保留
                    if pitch_std < PITCH_STD_THRESHOLD:
                        sustain_segments.append({
                            'start': times[start_idx],
                            'end': times[end_idx],
                            'duration': duration,
                            'avg_stability': np.mean(stability_scores[start_idx:end_idx+1]),
                            'avg_energy': np.mean(energy[start_idx:end_idx+1]),
                            'pitch_std': pitch_std
                        })
            else:
                i += 1
        return sustain_segments

class KaraokeGenerator:
    """卡拉OK生成器 - 使用拖长音检测结果"""
    def __init__(self):
        pass
    
    def time_to_seconds(self, time_str):
        """ASS时间格式转秒数"""
        try:
            h, m, s = time_str.split(':')
            s, cs = s.split('.')
            return int(h)*3600 + int(m)*60 + int(s) + int(cs)/100
        except:
            return 0
    
    def find_matching_sustain(self, sustain_segments, start_sec, end_sec):
        """查找与字幕时间匹配的拖长音段，返回所有匹配的段，包含原始索引"""
        matching_segments = []
        for idx, seg in enumerate(sustain_segments):
            seg_start, seg_end = seg['start'], seg['end']
            # 检查是否有重叠
            if seg_start <= end_sec and seg_end >= start_sec:
                overlap = min(end_sec, seg_end) - max(start_sec, seg_start)
                if overlap >= SUSTAIN_OVERLAP_THRESHOLD:  # 至少SUSTAIN_OVERLAP_THRESHOLD秒重叠
                    # 添加原始索引到段信息中
                    seg_with_index = seg.copy()
                    seg_with_index['original_index'] = idx + 1  # 段号从1开始
                    matching_segments.append(seg_with_index)
        return matching_segments
    
    def apply_karaoke_effect(self, text, k_sequence, forced_ratio=None, sustain_type=None):
        """应用K值效果到文本，支持强制指定分割比例和拖长音类型"""
        # 移除整个{\K数字}标签
        clean_text = re.sub(r'\{\\K\d+\}', '', text).strip()
        
        if len(k_sequence) == 1:
            # 单K值：整句效果
            return f"{{\\K{k_sequence[0]}}}{clean_text}"
        
        elif len(k_sequence) == 2:
            print(f"歌词分割情况:")
            print(f"  原始文本: {clean_text}")
            print(f"  K值序列: {k_sequence}")
            
            if forced_ratio is not None:
                print(f"  强制使用分割比例: {forced_ratio:.2f}")
                # 强制使用指定比例分割
                result = self._split_by_ratio(clean_text, forced_ratio, k_sequence)
                print(f"  分割结果: {result}")
                print("=" * 50)
                return result
            
            # 检查是否为双语文本（使用换行符分隔）
            if '\\N' in clean_text:
                # 双语情况：按第一句分割点动态分割第二句
                lines = clean_text.split('\\N')
                if len(lines) == 2:
                    first_line, second_line = lines
                    print(f"  双语模式: 第一句='{first_line}', 第二句='{second_line}'")
                    
                    # 处理第一句
                    first_result, split_ratio = self._split_single_line(first_line, k_sequence, sustain_type)
                    
                    # 根据第一句的分割比例处理第二句
                    second_result = self._split_by_ratio(second_line, split_ratio, k_sequence)
                    
                    result = f"{first_result}\\N{second_result}"
                    print(f"  分割结果: {result}")
                    return result
            
            # 单语情况：直接分割
            result, split_ratio = self._split_single_line(clean_text, k_sequence, sustain_type)
            print(f"  分割比例: {split_ratio:.2f}")
            print(f"  分割结果: {result}")
            print("=" * 50)
            return result, split_ratio
        
        # 默认：整句效果
        total_k = sum(k_sequence)
        return f"{{\\K{total_k}}}{clean_text}", None
    
    def _split_single_line(self, text, k_sequence, sustain_type=None):
        """分割单行文本并返回分割结果和比例"""
        if not text:
            total_k = sum(k_sequence)
            return f"{{\\K{total_k}}}{text}", 0.5
        
        # 句首延长音处理：分割第一个单词或字
        if sustain_type == "start":
            print(f"  句首延长音分割模式: 分割第一个单词/字")
            
            # 检查第一个字符是否为英文
            first_char = text[0]
            is_english_start = first_char.isalpha() and first_char.isascii()
            
            if is_english_start:
                # 英文：找到第一个空格位置，分割第一个单词
                first_space = text.find(' ')
                if first_space != -1:
                    part1 = text[:first_space].strip()
                    part2 = text[first_space:].strip()
                    if part1 and part2:
                        # 计算分割比例（基于有效字符数，不计算空格）
                        valid_chars = text.replace(' ', '')
                        part1_valid = part1.replace(' ', '')
                        split_ratio = len(part1_valid) / len(valid_chars) if len(valid_chars) > 0 else 0.5
                        return f"{{\\K{k_sequence[0]}}}{part1}{{\\K{k_sequence[1]}}}{part2}", split_ratio
            
            # 中文或没有空格的英文：分割第一个字符
            if len(text) >= 1:
                part1 = text[:1]
                part2 = text[1:]
                # 计算分割比例
                split_ratio = len(part1) / len(text) if len(text) > 0 else 0.5
                return f"{{\\K{k_sequence[0]}}}{part1}{{\\K{k_sequence[1]}}}{part2}", split_ratio
        
        # 判断末尾是否为英文
        last_char = text[-1]
        is_english_end = last_char.isalpha() and last_char.isascii()
        
        if is_english_end:
            # 英文末尾：按最后一个空格分割
            last_space = text.rfind(' ')
            if last_space != -1:
                part1 = text[:last_space].strip()
                part2 = text[last_space+1:].strip()
                if part1 and part2:
                    # 计算分割比例（基于有效字符数，不计算空格）
                    valid_chars = text.replace(' ', '')
                    part1_valid = part1.replace(' ', '')
                    split_ratio = len(part1_valid) / len(valid_chars) if len(valid_chars) > 0 else 0.5
                    return f"{{\\K{k_sequence[0]}}}{part1} {{\\K{k_sequence[1]}}}{part2}", split_ratio
        
        # 非英文末尾或英文但没有空格：分割最后一个字符
        if len(text) >= 1:
            part1 = text[:-1]
            part2 = text[-1:]
            # 计算分割比例
            split_ratio = len(part1) / len(text) if len(text) > 0 else 0.5
            return f"{{\\K{k_sequence[0]}}}{part1}{{\\K{k_sequence[1]}}}{part2}", split_ratio
        else:
            total_k = sum(k_sequence)
            return f"{{\\K{total_k}}}{text}", 0.5
    
    def _split_by_ratio(self, text, split_ratio, k_sequence):
        """根据比例分割文本"""
        if not text:
            total_k = sum(k_sequence)
            return f"{{\\K{total_k}}}{text}"
        
        # 计算分割位置
        text_length = len(text)
        split_pos = int(round(text_length * split_ratio))
        
        # 确保分割位置有效
        split_pos = max(0, min(text_length, split_pos))
        
        # 处理边界情况
        if split_pos == 0:
            split_pos = 1
        elif split_pos == text_length:
            split_pos = text_length - 1
        
        part1 = text[:split_pos]
        part2 = text[split_pos:]
        
        return f"{{\\K{k_sequence[0]}}}{part1}{{\\K{k_sequence[1]}}}{part2}"
    
    def has_k_values(self, text):
        """检测文本中是否包含K值标签"""
        return bool(re.search(r'\{\\K\d+\}', text))
    
    def process_ass_file(self, ass_content, sustain_segments):
        """处理ASS文件，添加卡拉OK效果"""
        output_lines = []
        # 存储时间轴对应的分割比例，用于同一时间轴的字幕复用
        timeline_split_ratios = {}
        
        # 首先检测整个文件的K值分布情况
        all_lines = ass_content.split('\n')
        dialogue_lines = []
        has_k_count = 0
        no_k_count = 0
        
        for line in all_lines:
            if line.strip().startswith('Dialogue:'):
                parts = line.strip().split(',', 9)
                if len(parts) >= 10:
                    text = parts[9]
                    dialogue_lines.append((line.strip(), text))
                    if self.has_k_values(text):
                        has_k_count += 1
                    else:
                        no_k_count += 1
        
        # 判断是否为混合K值情况
        is_mixed_k = False
        if ENABLE_DIALOGUE_DETECTION == 1:
            is_mixed_k = has_k_count > 0 and no_k_count > 0
            if is_mixed_k:
                print(f"\n检测到混合K值情况: {has_k_count}个字幕有K值，{no_k_count}个字幕无K值")
                print("开启对白字幕检测，只处理有K值的字幕部分")
            elif has_k_count == 0:
                print(f"\n检测到所有字幕无K值: 共{no_k_count}个字幕")
            elif no_k_count == 0:
                print(f"\n检测到所有字幕已有K值: 共{has_k_count}个字幕")
        
        for line in all_lines:
            line = line.strip()
            
            if line.startswith('Dialogue:'):
                parts = line.split(',', 9)
                if len(parts) >= 10:
                    start_time, end_time, text = parts[1], parts[2], parts[9]
                    
                    # 检查是否需要处理该字幕
                    should_process = True
                    if ENABLE_DIALOGUE_DETECTION == 1 and is_mixed_k:
                        # 混合K值情况，只处理有K值的字幕
                        if not self.has_k_values(text):
                            should_process = False
                            print(f"\n跳过无K值字幕: 时间轴={start_time}->{end_time}")
                            print(f"  原歌词: {text}")
                    
                    if should_process:
                        # 计算时间
                        start_sec = self.time_to_seconds(start_time)
                        end_sec = self.time_to_seconds(end_time)
                        total_duration = end_sec - start_sec
                        
                        # 生成时间轴唯一标识
                        timeline_key = f"{start_time}->{end_time}"
                        
                        # 检查是否启用拖长音检测
                        # 检查是否开启了任何类型的拖长音检测
                        is_sustain_detection_enabled = ENABLE_BEGINNING_SUSTAIN_DETECTION == 1 or ENABLE_ENDING_SUSTAIN_DETECTION == 1
                        if not is_sustain_detection_enabled:
                            # 关闭拖长音检测：使用整句效果
                            total_k = int(total_duration * 100)
                            adjusted_total_k = max(10, total_k - 15)
                            k_sequence = [adjusted_total_k]
                        else:
                            # 开启拖长音检测：正常逻辑
                            # 查找匹配的拖长音
                            matching_segments = self.find_matching_sustain(sustain_segments, start_sec, end_sec)
                            
                            # 计算总K值（每个K值单位=0.01秒）
                            total_k = int(total_duration * 100)
                            adjusted_total_k = max(10, total_k - 15)  # 基础K值减15，最小10
                            
                            # 动态K值分配逻辑
                            selected_sustain = None
                            selected_sustain_type = None
                            if matching_segments:
                                # 选择最合适的拖长音段：优先选择末尾延长音，其次选择开始延长音，最后选择持续时间最长的
                                for seg in matching_segments:
                                    # 计算拖长音结束在字幕中的相对位置和到字幕结束的时间差
                                    seg_end_pos = (seg['end'] - start_sec) / total_duration
                                    end_time_diff = end_sec - seg['end']
                                    # 计算拖长音开始与字幕开始的时间差
                                    start_time_diff = abs(seg['start'] - start_sec)
                                    
                                    print(f"    段{seg['original_index']}位置: 结束={seg_end_pos:.0%}, 持续时间: {seg['duration']:.2f}秒")
                                    
                                    # 判断是否为末尾延长音：
                                    # 1. 结束位置在60%之后 或
                                    # 2. 结束时间距离字幕结束不足SUSTAIN_END_TIME_DIFF秒
                                    is_end_sustain = ENABLE_ENDING_SUSTAIN_DETECTION == 1 and (seg_end_pos >= 0.6 or end_time_diff < SUSTAIN_END_TIME_DIFF) and seg['duration'] >= SUSTAIN_END_THRESHOLD
                                    
                                    # 判断是否为开始延长音：拖长音开始时间与字幕开始时间误差在0.5秒内
                                    is_start_sustain = ENABLE_BEGINNING_SUSTAIN_DETECTION == 1 and start_time_diff <= 0.5 and seg['duration'] >= SUSTAIN_END_THRESHOLD
                                    
                                    if is_end_sustain:
                                        selected_sustain = seg
                                        selected_sustain_type = "end"
                                        print(f"    选中段{seg['original_index']}作为末尾延长音")
                                        break
                                    elif is_start_sustain:
                                        selected_sustain = seg
                                        selected_sustain_type = "start"
                                        print(f"    选中段{seg['original_index']}作为开始延长音")
                                        break
                                # 如果没有找到末尾延长音或开始延长音，选择持续时间最长的
                                if not selected_sustain:
                                    selected_sustain = max(matching_segments, key=lambda x: x['duration'])
                                    print(f"    未找到末尾延长音或开始延长音，选择持续时间最长的段{selected_sustain['original_index']}（{selected_sustain['duration']:.2f}秒）")
                            
                            if selected_sustain:
                                # 计算拖长音与字幕的重叠部分
                                overlap_start = max(selected_sustain['start'], start_sec)
                                overlap_end = min(selected_sustain['end'], end_sec)
                                overlap_duration = overlap_end - overlap_start
                                
                                # 只计算拖长音结束在字幕中的相对位置和到字幕结束的时间差
                                sustain_end_pos = (selected_sustain['end'] - start_sec) / total_duration
                                end_time_diff = end_sec - selected_sustain['end']
                                
                                # 计算拖长音覆盖率（占字幕的比例）
                                coverage_ratio = overlap_duration / total_duration
                                
                                # 计算拖长音强度（基于稳定性和能量）
                                sustain_strength = (selected_sustain['avg_stability'] + selected_sustain['avg_energy']) / 2
                                
                                # 判断拖长音类型
                                # 1. 末尾延长音：结束位置在60%之后，或结束时间距离字幕结束不足SUSTAIN_END_TIME_DIFF秒，且持续≥SUSTAIN_END_THRESHOLD秒
                                # 2. 开始延长音：拖长音开始时间与字幕开始时间误差在0.5秒内，且结束位置在40%之前
                                # 3. 长拖长音段：持续≥SUSTAIN_LONG_THRESHOLD秒
                                
                                # 限制结束位置在0-1之间，避免百分比超过100%
                                sustain_end_pos = max(0, min(1, sustain_end_pos))
                                
                                # 末尾延长音判断：优先级最高
                                is_end_sustain = (sustain_end_pos >= 0.6 or end_time_diff < SUSTAIN_END_TIME_DIFF) and selected_sustain['duration'] >= SUSTAIN_END_THRESHOLD
                                
                                # 开始延长音判断：只有当不是末尾延长音时才考虑，且结束位置在40%之前
                                is_start_sustain = not is_end_sustain and abs(selected_sustain['start'] - start_sec) <= 0.5 and sustain_end_pos < 0.4 and selected_sustain['duration'] >= SUSTAIN_END_THRESHOLD
                                
                                # 长拖长音段判断
                                is_long_sustain = selected_sustain['duration'] >= SUSTAIN_LONG_THRESHOLD
                                
                                if is_end_sustain or is_start_sustain or is_long_sustain:
                                    # 计算拖长音在字幕时间轴中的起始位置比例（限制在0-1之间）
                                    overlap_start = max(selected_sustain['start'], start_sec)
                                    overlap_end = min(selected_sustain['end'], end_sec)
                                    sustain_start_pos = max(0, min(1, (overlap_start - start_sec) / total_duration))
                                    sustain_end_pos = max(0, min(1, (overlap_end - start_sec) / total_duration))
                                    
                                    sustain_start_formatted = format_time_seconds_to_minutes(selected_sustain['start'])
                                    sustain_duration_formatted = format_time_seconds_to_minutes(selected_sustain['duration'])
                                    print(f"=== 延长音抉择日志 ===")
                                    print(f"时间轴: {start_time} -> {end_time} (总时长: {total_duration:.2f}秒)")
                                    print(f"原歌词: {text}")
                                    print(f"匹配拖长音段: 共{len(matching_segments)}个，选中段{selected_sustain['original_index']} (持续时间{selected_sustain['duration']:.2f}秒)")
                                    
                                    # 确定拖长音类型
                                    if is_end_sustain:
                                        sustain_type = "末尾拖长音"
                                        # 只显示结束位置信息
                                        print(f"检测到{sustain_type}: 结束={sustain_end_pos:.0%}, 距离结束={end_time_diff:.2f}秒, 持续={sustain_duration_formatted}, 覆盖={coverage_ratio:.0%}")
                                    elif is_start_sustain:
                                        sustain_type = "开始拖长音"
                                        # 显示开始位置信息
                                        print(f"检测到{sustain_type}: 开始={sustain_start_pos:.0%}, 距离开始={abs(selected_sustain['start'] - start_sec):.2f}秒, 持续={sustain_duration_formatted}, 覆盖={coverage_ratio:.0%}")
                                    else:
                                        sustain_type = f"长拖长音(持续{sustain_duration_formatted})"
                                        # 只显示结束位置信息
                                        print(f"检测到{sustain_type}: 结束={sustain_end_pos:.0%}, 持续={sustain_duration_formatted}, 覆盖={coverage_ratio:.0%}")
                                    print(f"拖长音强度: {sustain_strength:.2f}, 稳定性={selected_sustain['avg_stability']:.2f}, 能量={selected_sustain['avg_energy']:.2f}")
                                    
                                    # 动态计算K值，根据拖长音类型调整分配策略
                                    # 计算拖长音与字幕的实际重叠区域
                                    actual_overlap_duration = overlap_end - overlap_start
                                    
                                    # 根据实际重叠持续时间计算所需K值
                                    sustain_k_needed = int(actual_overlap_duration * 100 * 1.0)  # 使用实际重叠时间，不额外增加缓冲
                                    
                                    if is_start_sustain:
                                        # 开始延长音：将大部分K值分配给前面的第一个单词或字
                                        # 前面K值占60-80%，后面K值占20-40%
                                        front_ratio = 0.7  # 默认70%给前面
                                        min_front_k = max(20, int(adjusted_total_k * 0.6))
                                        max_front_k = int(adjusted_total_k * 0.8)
                                        front_k = int(adjusted_total_k * front_ratio)
                                        front_k = max(min_front_k, min(front_k, max_front_k))
                                        tail_k = adjusted_total_k - front_k
                                    else:
                                        # 末尾延长音或长拖长音：原有逻辑
                                        # 末尾K值不应超过总K值的70%，避免分配不合理
                                        max_tail_k = int(adjusted_total_k * 0.7)
                                        min_tail_k = max(20, sustain_k_needed)
                                        min_tail_k = min(min_tail_k, max_tail_k)
                                        
                                        # 根据拖长音起始位置调整前面文本的K值
                                        # 拖长音起始位置越靠后，前面文本的K值应该越小
                                        front_ratio = sustain_start_pos
                                        # 确保前面文本有足够的K值，至少占总K值的30%
                                        min_front_k = max(15, int(adjusted_total_k * 0.3))
                                        max_front_k = int(adjusted_total_k * 0.8)
                                        
                                        # 计算前面文本的K值
                                        front_k = int(adjusted_total_k * front_ratio)
                                        front_k = max(min_front_k, min(front_k, max_front_k))
                                        
                                        # 计算末尾拖长音的K值
                                        tail_k = adjusted_total_k - front_k
                                        # 确保拖长音部分获得合适的K值
                                        if tail_k < min_tail_k:
                                            tail_k = min_tail_k
                                            front_k = adjusted_total_k - tail_k
                                            # 确保前面文本仍有足够的K值
                                            front_k = max(min_front_k, front_k)
                                        elif tail_k > max_tail_k:
                                            tail_k = max_tail_k
                                            front_k = adjusted_total_k - tail_k
                                    
                                    # 重新调整tail_k以确保总和正确
                                    tail_k = adjusted_total_k - front_k
                                    
                                    # 根据拖长音类型分别检查K值和开关状态
                                    use_whole_effect = False
                                    if is_start_sustain:
                                        # 检查句首延长音开关是否开启
                                        if ENABLE_BEGINNING_SUSTAIN_DETECTION != 1:
                                            print(f"  句首延长音检测已关闭，采用整段效果")
                                            use_whole_effect = True
                                        elif front_k < BEGINNING_SUSTAIN_MIN_K:
                                            print(f"  检测到句首延长音K值小于{BEGINNING_SUSTAIN_MIN_K}: 前面={front_k}，采用整段效果")
                                            use_whole_effect = True
                                    elif is_end_sustain:
                                        # 检查句末延长音开关是否开启
                                        if ENABLE_ENDING_SUSTAIN_DETECTION != 1:
                                            print(f"  句末延长音检测已关闭，采用整段效果")
                                            use_whole_effect = True
                                        elif tail_k < ENDING_SUSTAIN_MIN_K:
                                            print(f"  检测到句末延长音K值小于{ENDING_SUSTAIN_MIN_K}: 末尾={tail_k}，采用整段效果")
                                            use_whole_effect = True
                                    else:
                                        # 其他情况：检查任意K值是否小于最小阈值
                                        min_k = min(BEGINNING_SUSTAIN_MIN_K, ENDING_SUSTAIN_MIN_K)
                                        if front_k < min_k or tail_k < min_k:
                                            print(f"  检测到K值小于{min_k}: 前面={front_k}, 末尾={tail_k}，采用整段效果")
                                            use_whole_effect = True
                                     
                                    if use_whole_effect:
                                        k_sequence = [adjusted_total_k]
                                    else:
                                        k_sequence = [front_k, tail_k]
                                        
                                        front_time = front_k/100
                                        tail_time = tail_k/100
                                        front_time_formatted = format_time_seconds_to_minutes(front_time)
                                        tail_time_formatted = format_time_seconds_to_minutes(tail_time)
                                        print(f"动态分配: 前面={front_k} ({front_time_formatted}), 末尾={tail_k} ({tail_time_formatted})")
                            else:
                                # 非拖长音或持续时间不足0.8秒：使用整句效果
                                k_sequence = [adjusted_total_k]
                                # 忽略整句效果的日志
                            
                            # 检查是否已经处理过相同时间轴的字幕
                            forced_ratio = timeline_split_ratios.get(timeline_key, None)
                            if forced_ratio is not None:
                                print(f"  同一时间轴，复用分割比例: {forced_ratio:.2f}")
                        
                        # 根据拖长音类型分别检查K值和开关状态
                        should_use_whole_effect = False
                        if len(k_sequence) > 1:
                            front_k_val = k_sequence[0]
                            tail_k_val = k_sequence[1]
                            
                            if is_end_sustain:
                                # 检查句末延长音开关是否开启
                                if ENABLE_ENDING_SUSTAIN_DETECTION != 1:
                                    print(f"  句末延长音检测已关闭，采用整段效果")
                                    should_use_whole_effect = True
                                # 句末延长音：只检查后面的K值是否小于ENDING_SUSTAIN_MIN_K
                                elif tail_k_val < ENDING_SUSTAIN_MIN_K:
                                    print(f"  检测到句末延长音K值小于{ENDING_SUSTAIN_MIN_K}: 末尾={tail_k_val}，采用整段效果")
                                    should_use_whole_effect = True
                            elif is_start_sustain:
                                # 检查句首延长音开关是否开启
                                if ENABLE_BEGINNING_SUSTAIN_DETECTION != 1:
                                    print(f"  句首延长音检测已关闭，采用整段效果")
                                    should_use_whole_effect = True
                                # 句首延长音：只检查前面的K值是否小于BEGINNING_SUSTAIN_MIN_K
                                elif front_k_val < BEGINNING_SUSTAIN_MIN_K:
                                    print(f"  检测到句首延长音K值小于{BEGINNING_SUSTAIN_MIN_K}: 前面={front_k_val}，采用整段效果")
                                    should_use_whole_effect = True
                            else:
                                # 其他情况：检查任意K值是否小于最小阈值
                                min_k = min(BEGINNING_SUSTAIN_MIN_K, ENDING_SUSTAIN_MIN_K)
                                if front_k_val < min_k or tail_k_val < min_k:
                                    print(f"  检测到K值小于{min_k}: 前面={front_k_val}, 末尾={tail_k_val}，采用整段效果")
                                    should_use_whole_effect = True
                        
                        if should_use_whole_effect and len(k_sequence) > 1:
                            k_sequence = [sum(k_sequence)]
                        
                        # 应用K值效果
                        if len(k_sequence) == 1:
                            karaoke_text = self.apply_karaoke_effect(text, k_sequence)
                        else:
                            # 处理双K值情况，可能返回元组
                            # 根据拖长音类型设置sustain_type参数
                            sustain_type_param = None
                            # 首先判断是否为末尾延长音（优先级更高）
                            if is_end_sustain:
                                sustain_type_param = "end"
                            elif is_start_sustain:
                                sustain_type_param = "start"
                            
                            # 确保拖长音类型正确，避免类型错误
                            print(f"  使用拖长音类型: {sustain_type_param}")
                            
                            result = self.apply_karaoke_effect(text, k_sequence, forced_ratio, sustain_type_param)
                            if isinstance(result, tuple):
                                karaoke_text, split_ratio = result
                                # 存储分割比例，供同一时间轴的其他字幕使用
                                if timeline_key not in timeline_split_ratios:
                                    timeline_split_ratios[timeline_key] = split_ratio
                            else:
                                karaoke_text = result
                        
                        parts[3] = 'Karaoke'  # 修改样式
                        parts[9] = karaoke_text
                        line = ','.join(parts)
            
            output_lines.append(line)
        
        return '\n'.join(output_lines)
    
    def generate_karaoke(self, subtitle_path, audio_path=None, sustain_segments=None, output_path=None):
        """生成卡拉OK字幕"""
        # 读取字幕文件
        with open(subtitle_path, 'r', encoding='utf-8') as f:
            ass_content = f.read()
        
        # 如果没有提供拖长音段，且提供了音频文件，则进行检测（仅当开启任何一种检测时）
        is_sustain_detection_enabled = ENABLE_BEGINNING_SUSTAIN_DETECTION == 1 or ENABLE_ENDING_SUSTAIN_DETECTION == 1
        if sustain_segments is None and audio_path is not None and is_sustain_detection_enabled:
            print("检测拖长音段...")
            sustain_detector = SustainDetector()
            sustain_segments = sustain_detector.detect(audio_path)
        elif sustain_segments is None:
            sustain_segments = []
        
        # 处理ASS文件
        print("正在生成卡拉OK效果...")
        karaoke_ass = self.process_ass_file(ass_content, sustain_segments)
        
        # 设置输出路径
        if output_path is None:
            input_path = Path(subtitle_path)
            output_path = input_path.parent / f"{input_path.stem}_karaoke.ass"
        
        # 保存文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(karaoke_ass)
        
        print(f"卡拉OK字幕生成完成: {output_path}")
        return output_path

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='智能卡拉OK字幕生成器')
    parser.add_argument('--input', '-i', help='字幕文件路径')
    parser.add_argument('--audio', '-a', help='音频文件路径')
    parser.add_argument('--output', '-o', help='输出文件路径')
    parser.add_argument('--karaoke', '-k', action='store_true', help='启用卡拉OK效果')
    parser.add_argument('--dialogue', '-d', type=int, choices=[0, 1], default=ENABLE_DIALOGUE_DETECTION, help='对白字幕检测开关 (0:关闭, 1:开启)')
    
    return parser.parse_args()

def command_line_main():
    """命令行主函数"""
    args = parse_arguments()
    
    if not args.input:
        print("错误: 必须提供字幕文件路径")
        return None
    
    # 处理包含"|"分隔符的特殊格式（ASS文件路径|音频文件路径）
    ass_path = args.input
    audio_path = args.audio
    
    if "|" in args.input:
        try:
            ass_path, audio_path = args.input.split("|", 1)
        except Exception as e:
            print(f"处理路径格式失败: {e}")
            return None
    
    if not Path(ass_path).exists():
        print(f"错误: 字幕文件不存在: {ass_path}")
        return None
    
    # 设置对白字幕检测开关
    global ENABLE_DIALOGUE_DETECTION
    ENABLE_DIALOGUE_DETECTION = args.dialogue
    
    karaoke_generator = KaraokeGenerator()
    
    try:
        result = karaoke_generator.generate_karaoke(
            subtitle_path=ass_path,
            audio_path=audio_path if audio_path and Path(audio_path).exists() else None,
            output_path=args.output
        )
        print(f"卡拉OK字幕生成完成: {result}")
        return result
    except Exception as e:
        print(f"处理失败: {e}")
        return None

def select_file(title, filetypes):
    """文件选择对话框 - 仅在没有命令行参数时使用"""
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        file_path = filedialog.askopenfilename(title=title, filetypes=filetypes)
        return file_path
    except ImportError:
        print(f"请选择{title}: ")
        return input().strip()

def interactive_main():
    """交互式主程序"""
    print("智能卡拉OK字幕生成器")
    print("=" * 40)
    
    # 显示当前设置
    print(f"句首延长音检测: {'开启' if ENABLE_BEGINNING_SUSTAIN_DETECTION == 1 else '关闭'}")
    print(f"句末延长音检测: {'开启' if ENABLE_ENDING_SUSTAIN_DETECTION == 1 else '关闭'}")
    print(f"对白字幕检测: {'开启' if ENABLE_DIALOGUE_DETECTION == 1 else '关闭'}")
    print("=" * 40)
    
    # 选择字幕文件
    subtitle_file = select_file(
        "选择字幕文件", 
        [("ASS字幕文件", "*.ass"), ("所有文件", "*.*")]
    )
    if not subtitle_file:
        print("未选择字幕文件，程序退出")
        input("\n按回车键退出...")
        return
    
    # 选择音频文件
    audio_file = select_file(
        "选择音频文件", 
        [("音频文件", "*.wav *.mp3 *.flac *.m4a"), ("所有文件", "*.*")]
    )
    if not audio_file:
        print("未选择音频文件，程序退出")
        input("\n按回车键退出...")
        return
    
    # 检查文件是否存在
    if not Path(subtitle_file).exists():
        print(f"错误: 字幕文件不存在: {subtitle_file}")
        input("\n按回车键退出...")
        return
        
    if not Path(audio_file).exists():
        print(f"错误: 音频文件不存在: {audio_file}")
        input("\n按回车键退出...")
        return
    
    print(f"字幕文件: {subtitle_file}")
    print(f"音频文件: {audio_file}")
    print("-" * 40)
    
    # 1. 检测拖长音（仅当开启任何一种检测时）
    sustain_segments = []
    is_sustain_detection_enabled = ENABLE_BEGINNING_SUSTAIN_DETECTION == 1 or ENABLE_ENDING_SUSTAIN_DETECTION == 1
    if is_sustain_detection_enabled:
        print("第一步: 检测拖长音")
        sustain_detector = SustainDetector()
        sustain_segments = sustain_detector.detect(audio_file)
    else:
        print("第一步: 拖长音检测已关闭，跳过音频分析")
    
    # 2. 生成卡拉OK字幕
    print("\n第二步: 生成卡拉OK字幕")
    karaoke_generator = KaraokeGenerator()
    output_file = karaoke_generator.generate_karaoke(subtitle_file, audio_file, sustain_segments)
    
    print("\n处理完成!")
    print(f"输出文件: {output_file}")
    
    # 等待用户按键后再退出
    input("\n按回车键退出...")

def main():
    """主函数"""
    # 检查是否是命令行调用
    if len(sys.argv) > 1:
        # 检查第一个参数是否包含"|"分隔符（GUI传递的格式）
        if "|" in sys.argv[1]:
            # 从GUI传递的格式：ASS文件路径|音频文件路径
            try:
                ass_path, audio_path = sys.argv[1].split("|", 1)
                
                # 检查文件是否存在
                if not Path(ass_path).exists():
                    print(f"错误: ASS字幕文件不存在: {ass_path}")
                    return None
                
                # 创建卡拉OK生成器
                karaoke_generator = KaraokeGenerator()
                
                # 执行卡拉OK生成
                result = karaoke_generator.generate_karaoke(
                    subtitle_path=ass_path,
                    audio_path=audio_path if audio_path and Path(audio_path).exists() else None
                )
                print(f"卡拉OK字幕生成完成: {result}")
                return result
            except Exception as e:
                print(f"处理失败: {e}")
                return None
        else:
            # 标准命令行模式
            result = command_line_main()
            sys.exit(0 if result else 1)
    else:
        # 交互模式
        interactive_main()

if __name__ == "__main__":
    main()