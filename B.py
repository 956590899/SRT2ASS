import re
import librosa
import numpy as np
from pathlib import Path
import argparse
import sys

# 控制拖长音检测的开关
# 0: 关闭拖长音检测（所有字幕使用整句效果）
# 1: 开启拖长音检测（根据音频分析结果动态分配K值）
ENABLE_SUSTAIN_DETECTION = 0  # 默认为开启

def format_time_seconds_to_minutes(seconds):
    """将秒数格式化为分钟:秒格式（例如：1:23.45）"""
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes}:{remaining_seconds:05.2f}"

class SustainDetector:
    """拖长音检测器 - 独立模块"""
    def __init__(self, stability_threshold=0.89, min_duration=0.5):
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
            
            # 计算频谱图
            print("正在计算频谱图...")
            stft = librosa.stft(y, n_fft=2048, hop_length=512)
            spectrogram = librosa.amplitude_to_db(np.abs(stft), ref=np.max)
            times = librosa.times_like(spectrogram, sr=sr, hop_length=512)
            
            # 计算频谱稳定性
            print("正在计算频谱稳定性...")
            stability_scores = self._compute_stability_scores(spectrogram)
            
            # 计算能量轮廓
            energy = np.sum(librosa.db_to_amplitude(spectrogram), axis=0)
            energy = energy / np.max(energy)
            
            # 检测拖长音段
            print("正在检测拖长音段...")
            sustain_segments = self._find_sustain_segments(stability_scores, energy, times)
            
            # 显示检测结果
            if sustain_segments:
                print(f"检测到 {len(sustain_segments)} 个独立的拖长音段:")
                for i, seg in enumerate(sustain_segments, 1):
                    start_formatted = format_time_seconds_to_minutes(seg['start'])
                    end_formatted = format_time_seconds_to_minutes(seg['end'])
                    print(f"  段{i}: {start_formatted} - {end_formatted} (持续 {seg['duration']:.2f}秒)")
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
                corr = np.corrcoef(current_frame, prev_frame)[0, 1]
                stability_scores.append(0 if np.isnan(corr) else (corr + 1) / 2)
            except:
                stability_scores.append(0)
        return [0] + stability_scores
    
    def _find_sustain_segments(self, stability_scores, energy, times):
        """查找拖长音段"""
        sustain_segments = []
        i = 0
        while i < len(stability_scores):
            if stability_scores[i] > self.stability_threshold and energy[i] > 0.15:
                start_idx = i
                while (i < len(stability_scores) and 
                       stability_scores[i] > self.stability_threshold and 
                       energy[i] > 0.15):
                    i += 1
                end_idx = i - 1
                duration = times[end_idx] - times[start_idx]
                if duration >= self.min_duration:
                    sustain_segments.append({
                        'start': times[start_idx],
                        'end': times[end_idx],
                        'duration': duration,
                        'avg_stability': np.mean(stability_scores[start_idx:end_idx+1]),
                        'avg_energy': np.mean(energy[start_idx:end_idx+1])
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
        """查找与字幕时间匹配的拖长音段"""
        for seg in sustain_segments:
            seg_start, seg_end = seg['start'], seg['end']
            # 检查是否有重叠
            if seg_start <= end_sec and seg_end >= start_sec:
                overlap = min(end_sec, seg_end) - max(start_sec, seg_start)
                if overlap >= 0.3:  # 至少0.3秒重叠
                    return seg
        return None
    
    def apply_karaoke_effect(self, text, k_sequence):
        """应用K值效果到文本"""
        clean_text = re.sub(r'\\K\d+', '', text).strip()
        
        if len(k_sequence) == 1:
            # 单K值：整句效果
            return f"{{\\K{k_sequence[0]}}}{clean_text}"
        
        elif len(k_sequence) == 2:
            # 检查是否为纯英文文本（包含常用英文符号）
            def is_english_with_symbols(text):
                # 定义英文允许的字符集：字母、数字、空格和常用英文标点符号
                english_pattern = re.compile(r'^[a-zA-Z0-9\s\.,!?;:\'"\-\(\)]+$')
                return bool(english_pattern.match(text))
            
            # 双K值：分割文本
            if is_english_with_symbols(clean_text) and clean_text and clean_text[-1].isalnum():
                # 纯英文（含符号）：按最后一个空格分割
                last_space = clean_text.rfind(' ')
                if last_space != -1:
                    part1, part2 = clean_text[:last_space], clean_text[last_space+1:]
                    return f"{{\\K{k_sequence[0]}}}{part1} {{\\K{k_sequence[1]}}}{part2}"
            
            # 非纯英文文本：一律取倒数1个字符
            if len(clean_text) >= 1:
                part1, part2 = clean_text[:-1], clean_text[-1:]
                return f"{{\\K{k_sequence[0]}}}{part1}{{\\K{k_sequence[1]}}}{part2}"
            else:
                # 文本太短：整句效果
                total_k = sum(k_sequence)
                return f"{{\\K{total_k}}}{clean_text}"
        
        # 默认：整句效果
        total_k = sum(k_sequence)
        return f"{{\\K{total_k}}}{clean_text}"
    
    def process_ass_file(self, ass_content, sustain_segments):
        """处理ASS文件，添加卡拉OK效果"""
        output_lines = []
        
        for line in ass_content.split('\n'):
            line = line.strip()
            
            if line.startswith('Dialogue:'):
                parts = line.split(',', 9)
                if len(parts) >= 10:
                    start_time, end_time, text = parts[1], parts[2], parts[9]
                    
                    # 计算时间
                    start_sec = self.time_to_seconds(start_time)
                    end_sec = self.time_to_seconds(end_time)
                    total_duration = end_sec - start_sec
                    
                    # 检查是否启用拖长音检测
                    if ENABLE_SUSTAIN_DETECTION == 0:
                        # 关闭拖长音检测：使用整句效果
                        total_k = int(total_duration * 100)
                        adjusted_total_k = max(10, total_k - 15)
                        k_sequence = [adjusted_total_k]
                    else:
                        # 开启拖长音检测：正常逻辑
                        # 查找匹配的拖长音
                        sustain = self.find_matching_sustain(sustain_segments, start_sec, end_sec)
                        
                        # 计算总K值（每个K值单位=0.01秒）
                        total_k = int(total_duration * 100)
                        adjusted_total_k = max(10, total_k - 15)  # 基础K值减15，最小10
                        
                        # 动态K值分配逻辑
                        if sustain:
                            # 计算拖长音与字幕的重叠部分
                            overlap_start = max(sustain['start'], start_sec)
                            overlap_end = min(sustain['end'], end_sec)
                            overlap_duration = overlap_end - overlap_start
                            
                            # 计算拖长音在字幕中的相对位置
                            sustain_position = (sustain['start'] - start_sec) / total_duration
                            
                            # 计算拖长音覆盖率（占字幕的比例）
                            coverage_ratio = overlap_duration / total_duration
                            
                            # 计算拖长音强度（基于稳定性和能量）
                            sustain_strength = (sustain['avg_stability'] + sustain['avg_energy']) / 2
                            
                            # 判断是否为末尾延长音
                            if sustain_position >= 0.6:  # 60%位置后开始，认为是末尾
                                sustain_start_formatted = format_time_seconds_to_minutes(sustain['start'])
                                sustain_duration_formatted = format_time_seconds_to_minutes(sustain['duration'])
                                print(f"检测到末尾拖长音 (位置: {sustain_position:.0%}, 持续: {sustain_duration_formatted}, 覆盖: {coverage_ratio:.0%})")
                                
                                # 动态计算末尾K值
                                # 基础部分：根据覆盖率和强度计算
                                base_k = int(adjusted_total_k * coverage_ratio * 0.8)
                                
                                # 增强部分：根据拖长音强度增加
                                enhance_k = int(base_k * sustain_strength * 0.3)
                                
                                # 计算末尾K值（末尾两个字符）
                                tail_k = base_k + enhance_k
                                
                                # 限制范围：不少于20，不超过总K值的75%
                                tail_k = max(20, min(tail_k, int(adjusted_total_k * 0.75)))
                                
                                # 确保前面部分至少有15
                                front_k = max(15, adjusted_total_k - tail_k)
                                
                                # 重新调整tail_k以确保总和正确
                                tail_k = adjusted_total_k - front_k
                                
                                k_sequence = [front_k, tail_k]
                                
                                front_time = front_k/100
                                tail_time = tail_k/100
                                front_time_formatted = format_time_seconds_to_minutes(front_time)
                                tail_time_formatted = format_time_seconds_to_minutes(tail_time)
                                print(f"  动态分配: 前面={front_k} ({front_time_formatted}), 末尾={tail_k} ({tail_time_formatted})")
                                
                            else:
                                # 非末尾拖长音：根据拖长音持续时间决定
                                if sustain['duration'] >= 1.5:
                                    # 长拖长音：给末尾更多时间
                                    tail_ratio = min(0.6, 0.3 + coverage_ratio)
                                    tail_k = int(adjusted_total_k * tail_ratio)
                                    tail_k = max(20, min(tail_k, int(adjusted_total_k * 0.7)))
                                    front_k = max(15, adjusted_total_k - tail_k)
                                    tail_k = adjusted_total_k - front_k
                                    k_sequence = [front_k, tail_k]
                                    print(f"检测到长拖长音: 使用动态分配 (前面{front_k}, 末尾{tail_k})")
                                elif sustain['duration'] >= 0.8:
                                    # 中等拖长音：平衡分配
                                    tail_k = int(adjusted_total_k * 0.4)
                                    tail_k = max(20, min(tail_k, int(adjusted_total_k * 0.6)))
                                    front_k = max(15, adjusted_total_k - tail_k)
                                    tail_k = adjusted_total_k - front_k
                                    k_sequence = [front_k, tail_k]
                                    print(f"检测到中等拖长音: 使用动态分配 (前面{front_k}, 末尾{tail_k})")
                                else:
                                    # 短拖长音：忽略，使用整句效果
                                    k_sequence = [adjusted_total_k]
                                    print(f"检测到短拖长音: 使用整句效果")
                        else:
                            # 无拖长音：整句效果
                            k_sequence = [adjusted_total_k]
                    
                    # 应用K值效果
                    karaoke_text = self.apply_karaoke_effect(text, k_sequence)
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
        
        # 如果没有提供拖长音段，且提供了音频文件，则进行检测（仅当开启检测时）
        if sustain_segments is None and audio_path is not None and ENABLE_SUSTAIN_DETECTION == 1:
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
    
    return parser.parse_args()

def command_line_main():
    """命令行主函数"""
    args = parse_arguments()
    
    if not args.input:
        print("错误: 必须提供字幕文件路径")
        return None
    
    if not Path(args.input).exists():
        print(f"错误: 字幕文件不存在: {args.input}")
        return None
    
    karaoke_generator = KaraokeGenerator()
    
    try:
        result = karaoke_generator.generate_karaoke(
            subtitle_path=args.input,
            audio_path=args.audio,
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
    print(f"拖长音检测: {'开启' if ENABLE_SUSTAIN_DETECTION == 1 else '关闭'}")
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
    
    # 1. 检测拖长音（仅当开启检测时）
    sustain_segments = []
    if ENABLE_SUSTAIN_DETECTION == 1:
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
        # 命令行模式
        result = command_line_main()
        sys.exit(0 if result else 1)
    else:
        # 交互模式
        interactive_main()

if __name__ == "__main__":
    main()