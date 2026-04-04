import os
import sys

# 设置环境变量，确保Python使用UTF-8编码
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LANG'] = 'zh_CN.UTF-8'
os.environ['LC_ALL'] = 'zh_CN.UTF-8'

# 确保标准输出/错误使用UTF-8编码
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import torch
import torchaudio
import numpy as np
from pathlib import Path
import argparse
import subprocess
import tempfile
import time
import json
from scipy import signal
from enum import Enum
import shutil

# 导入现有的分离程序
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    try:
        from x import GPUOptimizedDemucs
        print("✅ 成功导入音频分离模块 (x.py)")
    except ImportError:
        from X import GPUOptimizedDemucs
        print("✅ 成功导入音频分离模块 (X.py)")
except ImportError as e:
    print(f"❌ 无法导入音频分离模块: {e}")
    print("请确保 x.py 或 X.py 在同一目录下")
    sys.exit(1)

# 检测FFmpeg路径
def detect_ffmpeg_path():
    """检测FFmpeg路径"""
    # 项目自带的ffmpeg路径
    project_ffmpeg = Path(__file__).parent / "Python" / "ffmpeg" / "ffmpeg.exe"
    if project_ffmpeg.exists():
        return str(project_ffmpeg)
    # 系统PATH中的ffmpeg
    return "ffmpeg"

# 设置FFmpeg路径
FFMPEG_PATH = detect_ffmpeg_path()


class Channel5_1(Enum):
    """5.1声道定义"""
    FL = 0  # 前左
    FR = 1  # 前右
    C = 2   # 中置
    LFE = 3 # 低音炮
    SL = 4  # 环绕左
    SR = 5  # 环绕右


class StereoTo5_1Converter:
    """立体声转5.1声道转换器"""
    
    def __init__(self):
        # 获取系统临时目录
        self.temp_dir = Path(tempfile.gettempdir()) / "stereo_to_51_temp"
        self.temp_dir.mkdir(exist_ok=True)
        
        # 初始化音频分离器
        try:
            self.separator = GPUOptimizedDemucs()
        except Exception as e:
            print(f"❌ 初始化音频分离器失败: {e}")
            self.separator = None
        
        # 声道映射配置
        # 格式: {"weight": 整体权重, "channels": {声道: {"weight": 声道权重, "gain_db": 增益dB}}}
        self.channel_mapping = {
            "vocals": {
                "weight": 1.0,  # 整体权重 - 可调整增益
                "channels": {
                    Channel5_1.C.value: {"weight": 0.2, "gain_db": 0},    # 中置，20%人声
                    Channel5_1.FL.value: {"weight": 1.0, "gain_db": 0},   # 前左，100%人声
                    Channel5_1.FR.value: {"weight": 1.0, "gain_db": 0}    # 前右，100%人声
                }
            },
            "drums": {
                "weight": 1.0,  # 整体权重 - 可调整增益
                "channels": {
                    Channel5_1.SL.value: {"weight": 1.0, "gain_db": 0},   # 环绕左，100%鼓声
                    Channel5_1.SR.value: {"weight": 1.0, "gain_db": 0},   # 环绕右，100%鼓声
                    Channel5_1.LFE.value: {"weight": 0.4, "gain_db": 0}   # 低音炮，40%鼓声
                }
            },
            "bass": {
                "weight": 1.0,  # 整体权重 - 可调整增益
                "channels": {
                    Channel5_1.SL.value: {"weight": 1.0, "gain_db": 0},   # 环绕左，100%贝斯
                    Channel5_1.SR.value: {"weight": 1.0, "gain_db": 0},   # 环绕右，100%贝斯
                    Channel5_1.LFE.value: {"weight": 0.8, "gain_db": 0}   # 低音炮，80%贝斯
                }
            },
            "guitar": {
                "weight": 1.0,  # 整体权重 - 可调整增益
                "channels": {
                    Channel5_1.FL.value: {"weight": 1.0, "gain_db": 0},   # 前左，100%吉他
                    Channel5_1.FR.value: {"weight": 1.0, "gain_db": 0},   # 前右，100%吉他
                    Channel5_1.SL.value: {"weight": 0.2, "gain_db": 0},   # 环绕左，20%吉他（辅助）
                    Channel5_1.SR.value: {"weight": 0.2, "gain_db": 0}    # 环绕右，20%吉他（辅助）
                }
            },
            "piano": {
                "weight": 1.0,  # 整体权重 - 可调整增益
                "channels": {
                    Channel5_1.C.value: {"weight": 0.6, "gain_db": 0},    # 中置，60%钢琴
                    Channel5_1.FL.value: {"weight": 0.5, "gain_db": 0},   # 前左，50%钢琴
                    Channel5_1.FR.value: {"weight": 0.5, "gain_db": 0}    # 前右，50%钢琴
                }
            },
            "other": {
                "weight": 1.0,  # 整体权重 - 可调整增益
                "channels": {
                    Channel5_1.SL.value: {"weight": 1.0, "gain_db": 0},   # 环绕左，100%其他
                    Channel5_1.SR.value: {"weight": 1.0, "gain_db": 0}    # 环绕右，100%其他
                }
            }
        }
        
        # 全局增益参数
        self.global_gain_db = 0  # 全局增益，可调整，默认0dB
        
        # 声道特定增益
        self.channel_gains_db = {
            Channel5_1.FL.value: 0,  # 前左声道增益，可调整
            Channel5_1.FR.value: 0,  # 前右声道增益，可调整
            Channel5_1.C.value: 0,   # 中置声道增益，可调整
            Channel5_1.LFE.value: 0, # 低音炮增益，可调整
            Channel5_1.SL.value: 0,  # 环绕左增益，可调整
            Channel5_1.SR.value: 0   # 环绕右增益，可调整
        }
        
        # 原始音频增益
        self.original_gain_db = 0  # 原始音频增益，可调整，默认0dB
        
        # 分离音轨增益
        self.separated_track_gains_db = {
            "vocals": 0,   # 人声音轨增益，可调整
            "drums": 0,    # 鼓声音轨增益，可调整
            "bass": 0,     # 贝斯音轨增益，可调整
            "guitar": 0,   # 吉他音轨增益，可调整
            "piano": 0,    # 钢琴音轨增益，可调整
            "other": 0     # 其他音轨增益，可调整
        }
        
        # 左右前声道原始音频权重（原立体声）
        self.original_stereo_weight = 0.2
        
        # 原始音频文件路径（转换后的WAV）
        self.original_audio_wav = None
    
    def convert_to_wav(self, input_path):
        """将输入文件转换为WAV格式，用于加载原始音频"""
        try:
            wav_path = self.temp_dir / f"original_audio.wav"
            
            # 使用FFmpeg提取音频并转换为WAV
            cmd = [
                FFMPEG_PATH, '-i', str(input_path),
                '-vn',  # 忽略视频
                '-acodec', 'pcm_s16le',  # 16位PCM
                '-ar', '44100',  # 44.1kHz采样率
                '-ac', '2',  # 立体声
                '-y',  # 覆盖现有文件
                str(wav_path)
            ]
            
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            result = subprocess.run(cmd, capture_output=True, timeout=60, env=env)
            
            if result.returncode == 0:
                print(f"✅ 已提取音频为WAV: {Path(input_path).name}")
                self.original_audio_wav = wav_path
                return wav_path
            else:
                try:
                    error_msg = result.stderr.decode('utf-8', errors='ignore')
                except:
                    error_msg = "无法解码错误信息"
                print(f"❌ 音频提取失败: {error_msg}")
                return None
                
        except subprocess.TimeoutExpired:
            print("❌ 音频提取超时")
            return None
        except Exception as e:
            print(f"❌ 音频提取失败: {e}")
            return None
    
    def db_to_linear(self, db):
        """分贝值转换为线性比例"""
        try:
            return 10 ** (db / 20)
        except Exception as e:
            print(f"⚠️  db_to_linear转换出错: {e}, 使用默认值1.0")
            return 1.0
    
    def clear_temp_dir(self):
        """清理临时目录"""
        try:
            if self.temp_dir.exists():
                for item in self.temp_dir.iterdir():
                    try:
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            shutil.rmtree(item)
                    except Exception as e:
                        print(f"⚠️  清理临时文件失败 {item}: {e}")
                        pass
                # 重置原始音频路径
                self.original_audio_wav = None
        except Exception as e:
            print(f"⚠️  清理临时目录失败: {e}")
            pass
    
    def separate_audio_components(self, input_path):
        """使用现有程序分离音频组件"""
        print(f"🎵 分离音频: {Path(input_path).name}")
        
        # 清理临时目录
        self.clear_temp_dir()
        
        if self.separator is None:
            print("❌ 音频分离器未初始化")
            return None
        
        # 调用现有的分离程序，输出所有音轨
        try:
            saved_files = self.separator.separate_audio(
                input_path=input_path,
                model_name="htdemucs_6s",  # 使用htdemucs_6s模型获取6个音源
                output_mode="all",      # 全部分离
                output_dir=self.temp_dir
            )
            
            if not saved_files:
                print("❌ 音频分离失败")
                return None
            
            # 整理分离出的音轨文件
            audio_components = {}
            stem_mapping = {
                "人声": "vocals",
                "鼓声": "drums",
                "贝斯": "bass",
                "吉他": "guitar",
                "钢琴": "piano",
                "其他": "other"
            }
            
            for file_path in saved_files:
                file_name = file_path.name.lower()
                for chinese, english in stem_mapping.items():
                    if chinese.lower() in file_name:
                        audio_components[english] = file_path
                        print(f"  ✅ {chinese}音轨")
                        break
            
            # 检查是否所有音轨都已找到
            missing = [stem for stem in stem_mapping.values() if stem not in audio_components]
            if missing:
                print(f"⚠️  缺少音轨: {missing}")
            
            return audio_components
            
        except Exception as e:
            print(f"❌ 音频分离失败: {e}")
            return None
    
    def load_audio_component(self, file_path, target_sr=44100):
        """加载音频文件"""
        try:
            if not Path(file_path).exists():
                print(f"❌ 文件不存在: {file_path}")
                return None, None
                
            waveform, sr = torchaudio.load(file_path)
            
            # 转换采样率
            if sr != target_sr:
                waveform = torchaudio.functional.resample(waveform, sr, target_sr)
            
            # 确保是立体声（2声道）
            if waveform.shape[0] == 1:
                waveform = waveform.repeat(2, 1)
            elif waveform.shape[0] > 2:
                waveform = waveform[:2, :]
            
            return waveform, target_sr
        except Exception as e:
            print(f"❌ 加载失败 {file_path}: {e}")
            return None, None
    
    def create_lfe_channel(self, audio, sr, cutoff_freq=120):
        """创建低音炮声道（LFE）"""
        try:
            if audio is None:
                return torch.zeros(1, 1000)  # 返回默认值
            
            # 将音频转换为numpy数组
            audio_np = audio.numpy()
            
            # 设计低通滤波器
            nyquist = sr / 2
            normalized_cutoff = cutoff_freq / nyquist
            
            # 使用巴特沃斯滤波器
            b, a = signal.butter(4, normalized_cutoff, btype='low', analog=False)
            
            # 对每个声道应用滤波器
            lfe_channels = []
            for channel in audio_np:
                filtered = signal.filtfilt(b, a, channel)
                lfe_channels.append(filtered)
            
            # 合并声道并衰减
            lfe = np.mean(lfe_channels, axis=0) * 0.7
            
            # 转换为单声道
            lfe = torch.tensor(lfe).unsqueeze(0)
            
            return lfe
            
        except Exception as e:
            print(f"❌ 创建LFE声道失败: {e}")
            return torch.zeros(1, audio.shape[1] if audio is not None else 1000)
    
    def create_5_1_mix(self, audio_components, input_path):
        """创建5.1声道混音"""
        print("🎚️ 创建5.1声道混音...")
        
        if audio_components is None or len(audio_components) == 0:
            print("❌ 没有可用的音频组件")
            return None, None
        
        # 加载原始音频（用于前声道20%原立体声）
        # 如果还没有提取WAV，先提取
        if self.original_audio_wav is None or not self.original_audio_wav.exists():
            print("⏳ 提取原始音频为WAV格式...")
            wav_path = self.convert_to_wav(input_path)
            if wav_path is None:
                print("❌ 无法提取原始音频")
                return None, None
        else:
            wav_path = self.original_audio_wav
        
        original_audio, sample_rate = self.load_audio_component(wav_path, 44100)
        if original_audio is None:
            print("❌ 无法加载原始音频")
            return None, None
        
        max_length = original_audio.shape[1]
        
        print(f"📊 音频参数: 长度={max_length}采样点, 采样率={sample_rate}Hz")
        
        # 初始化5.1声道矩阵 [6, max_length]
        try:
            channels_5_1 = torch.zeros(6, max_length)
        except Exception as e:
            print(f"❌ 初始化声道矩阵失败: {e}")
            return None, None
        
        # 步骤1: 前声道加入20%原始立体声
        original_gain_linear = self.db_to_linear(self.original_gain_db + self.global_gain_db)
        fl_gain = self.db_to_linear(self.channel_gains_db[Channel5_1.FL.value])
        fr_gain = self.db_to_linear(self.channel_gains_db[Channel5_1.FR.value])
        
        # 应用原始立体声20%权重
        channels_5_1[Channel5_1.FL.value] = original_audio[0] * self.original_stereo_weight * original_gain_linear * fl_gain
        channels_5_1[Channel5_1.FR.value] = original_audio[1] * self.original_stereo_weight * original_gain_linear * fr_gain
        
        # 打印原始立体声信息
        print(f"✅ 左右前声道: 20%原始立体声 (权重={self.original_stereo_weight}, 增益={self.original_gain_db}dB)")
        
        # 初始化声道信息字典，用于收集每个声道的所有音频组件信息
        channel_info = {
            Channel5_1.C.value: [],    # 中置声道
            Channel5_1.FL.value: [],   # 前左声道
            Channel5_1.FR.value: [],   # 前右声道
            Channel5_1.SL.value: [],   # 环绕左声道
            Channel5_1.SR.value: [],   # 环绕右声道
            Channel5_1.LFE.value: []   # 低音炮声道
        }
        
        # 步骤2: 加载所有分离的音轨
        component_data = {}
        for component_name, file_path in audio_components.items():
            audio, sr = self.load_audio_component(file_path, sample_rate)
            if audio is None:
                continue
            component_data[component_name] = audio
        
        # 为每个分离的音轨应用映射
        for component_name, audio in component_data.items():
            if component_name not in self.channel_mapping:
                continue
            
            config = self.channel_mapping[component_name]
            overall_weight = config["weight"]
            channel_configs = config["channels"]
            
            # 调整音频长度以匹配原始音频
            current_length = audio.shape[1]
            if current_length < max_length:
                # 填充静音
                padding = torch.zeros(2, max_length - current_length)
                padded_audio = torch.cat([audio, padding], dim=1)
            elif current_length > max_length:
                # 截断
                padded_audio = audio[:, :max_length]
            else:
                padded_audio = audio
            
            # 应用整体权重和音轨增益
            track_gain = self.db_to_linear(self.separated_track_gains_db[component_name])
            weighted_audio = padded_audio * overall_weight * track_gain * self.db_to_linear(self.global_gain_db)
            
            # 分离左右声道
            left_channel = weighted_audio[0]
            right_channel = weighted_audio[1]
            
            # 分配到各个声道
            for channel_idx, channel_config in channel_configs.items():
                try:
                    channel_idx = int(channel_idx)
                    channel_weight = channel_config["weight"]
                    channel_gain_db = channel_config["gain_db"]
                    channel_gain_linear = self.db_to_linear(channel_gain_db + self.channel_gains_db[channel_idx])
                    final_weight = channel_weight * channel_gain_linear
                    
                    if channel_idx == Channel5_1.C.value:  # 中置声道
                        # 混合左右声道 (各50%)
                        center_mix = (left_channel + right_channel) * 0.5
                        channels_5_1[channel_idx] += center_mix * final_weight
                        # 收集声道信息
                        if component_name == "vocals":
                            channel_info[channel_idx].append(f"人声20% (权重={channel_weight}, 增益={channel_gain_db}dB)")
                        elif component_name == "piano":
                            channel_info[channel_idx].append(f"钢琴60% (权重={channel_weight}, 增益={channel_gain_db}dB)")
                    
                    elif channel_idx == Channel5_1.FL.value:  # 前左声道
                        # 使用左声道
                        channels_5_1[channel_idx] += left_channel * final_weight
                        # 收集声道信息
                        if component_name == "vocals":
                            channel_info[channel_idx].append(f"人声100% (权重={channel_weight}, 增益={channel_gain_db}dB)")
                        elif component_name == "guitar":
                            channel_info[channel_idx].append(f"吉他100% (权重={channel_weight}, 增益={channel_gain_db}dB)")
                        elif component_name == "piano":
                            channel_info[channel_idx].append(f"钢琴50% (权重={channel_weight}, 增益={channel_gain_db}dB)")
                    
                    elif channel_idx == Channel5_1.FR.value:  # 前右声道
                        # 使用右声道
                        channels_5_1[channel_idx] += right_channel * final_weight
                        # 收集声道信息
                        if component_name == "vocals":
                            channel_info[channel_idx].append(f"人声100% (权重={channel_weight}, 增益={channel_gain_db}dB)")
                        elif component_name == "guitar":
                            channel_info[channel_idx].append(f"吉他100% (权重={channel_weight}, 增益={channel_gain_db}dB)")
                        elif component_name == "piano":
                            channel_info[channel_idx].append(f"钢琴50% (权重={channel_weight}, 增益={channel_gain_db}dB)")
                    
                    elif channel_idx == Channel5_1.SL.value:  # 环绕左声道
                        # 使用左声道
                        channels_5_1[channel_idx] += left_channel * final_weight
                        # 收集声道信息
                        if component_name == "drums":
                            channel_info[channel_idx].append(f"鼓声100% (权重={channel_weight}, 增益={channel_gain_db}dB)")
                        elif component_name == "bass":
                            channel_info[channel_idx].append(f"贝斯100% (权重={channel_weight}, 增益={channel_gain_db}dB)")
                        elif component_name == "guitar":
                            channel_info[channel_idx].append(f"吉他20% (权重={channel_weight}, 增益={channel_gain_db}dB)")
                        elif component_name == "other":
                            channel_info[channel_idx].append(f"其他100% (权重={channel_weight}, 增益={channel_gain_db}dB)")
                    
                    elif channel_idx == Channel5_1.SR.value:  # 环绕右声道
                        # 使用右声道
                        channels_5_1[channel_idx] += right_channel * final_weight
                        # 收集声道信息
                        if component_name == "drums":
                            channel_info[channel_idx].append(f"鼓声100% (权重={channel_weight}, 增益={channel_gain_db}dB)")
                        elif component_name == "bass":
                            channel_info[channel_idx].append(f"贝斯100% (权重={channel_weight}, 增益={channel_gain_db}dB)")
                        elif component_name == "guitar":
                            channel_info[channel_idx].append(f"吉他20% (权重={channel_weight}, 增益={channel_gain_db}dB)")
                        elif component_name == "other":
                            channel_info[channel_idx].append(f"其他100% (权重={channel_weight}, 增益={channel_gain_db}dB)")
                    
                    elif channel_idx == Channel5_1.LFE.value:  # 低音炮声道
                        # 创建LFE声道
                        lfe_audio = self.create_lfe_channel(weighted_audio, sample_rate)
                        if lfe_audio.shape[1] == max_length:
                            channels_5_1[channel_idx] += lfe_audio[0] * final_weight
                        # 收集声道信息
                        if component_name == "drums":
                            channel_info[channel_idx].append(f"鼓声40% (权重={channel_weight}, 增益={channel_gain_db}dB)")
                        elif component_name == "bass":
                            channel_info[channel_idx].append(f"贝斯80% (权重={channel_weight}, 增益={channel_gain_db}dB)")
                except Exception as e:
                    print(f"⚠️  分配{component_name}到声道{channel_idx}失败: {e}")
                    continue
        
        # 统一输出每个声道的所有音频组件信息
        channel_names = {
            Channel5_1.C.value: "中置声道",
            Channel5_1.FL.value: "前左声道",
            Channel5_1.FR.value: "前右声道",
            Channel5_1.SL.value: "环绕左声道",
            Channel5_1.SR.value: "环绕右声道",
            Channel5_1.LFE.value: "低音炮"
        }
        
        print("\n🎵 声道音频分配:")
        for channel_idx, name in channel_names.items():
            if channel_info[channel_idx]:
                info_str = " + ".join(channel_info[channel_idx])
                print(f"✅ {name}: {info_str}")
        
        # 检查音量平衡
        print("\n📊 声道音量检查:")
        channel_names = ["前左(FL)", "前右(FR)", "中置(C)", "低音炮(LFE)", "环绕左(SL)", "环绕右(SR)"]
        for i, name in enumerate(channel_names):
            try:
                rms = torch.sqrt(torch.mean(channels_5_1[i] ** 2)).item()
                peak = torch.max(torch.abs(channels_5_1[i])).item()
                print(f"  {name}: RMS={rms:.4f}, Peak={peak:.4f}")
            except Exception as e:
                print(f"  {name}: 检查失败 - {e}")
        
        # 归一化以防止削波
        try:
            max_val = torch.max(torch.abs(channels_5_1))
            if max_val > 0.95:
                print(f"⚠️  检测到削波风险 ({max_val:.2f})，进行归一化")
                channels_5_1 = channels_5_1 / max_val * 0.98
        except Exception as e:
            print(f"⚠️  归一化失败: {e}")
        
        return channels_5_1, sample_rate
    
    def save_5_1_ac3(self, channels_5_1, sample_rate, output_path):
        """保存5.1声道为AC3格式"""
        try:
            if channels_5_1 is None or sample_rate is None:
                print("❌ 无效的音频数据")
                return False
            
            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 先保存为临时WAV文件
            temp_wav = self.temp_dir / "temp_5_1.wav"
            torchaudio.save(
                str(temp_wav),
                channels_5_1,
                sample_rate,
                bits_per_sample=16  # 修改为16位，避免警告和错误
            )
            
            # 使用FFmpeg转换为AC3，指定UTF-8编码避免解码错误
            cmd = [
                FFMPEG_PATH, '-i', str(temp_wav),
                '-c:a', 'ac3',
                '-b:a', '320k',  # 320kbps比特率
                '-y',
                str(output_path)
            ]
            
            # 设置编码为UTF-8，避免解码错误
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            result = subprocess.run(cmd, capture_output=True, timeout=120, env=env)
            
            if result.returncode == 0:
                print(f"✅ AC3已保存: {output_path.name}")
                return True
            else:
                # 尝试用UTF-8解码错误信息，失败时忽略错误
                try:
                    error_msg = result.stderr.decode('utf-8', errors='ignore')
                except:
                    error_msg = "无法解码错误信息"
                
                print(f"❌ AC3转换失败: {error_msg}")
                print("尝试保存为WAV...")
                # 如果AC3失败，保存为WAV
                wav_path = output_path.with_suffix('.wav')
                torchaudio.save(
                    str(wav_path),
                    channels_5_1,
                    sample_rate,
                    bits_per_sample=16
                )
                print(f"✅ WAV已保存: {wav_path.name}")
                return True  # 仍然返回成功，因为WAV保存成功
                
        except subprocess.TimeoutExpired:
            print("❌ AC3转换超时")
            return False
        except Exception as e:
            print(f"❌ 保存5.1声道失败: {e}")
            return False
    
    def process_single_file(self, input_path, output_dir=None):
        """处理单个文件"""
        try:
            input_path = Path(input_path)
            
            if not input_path.exists():
                print(f"❌ 输入文件不存在: {input_path}")
                return False
            
            # 确定输出路径
            if output_dir is not None:
                # 如果指定了输出目录，则使用该目录
                output_dir = Path(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / f"{input_path.stem} 5.1.ac3"
            else:
                # 否则直接在同级目录
                output_path = input_path.parent / f"{input_path.stem} 5.1.ac3"
            
            print(f"📁 输出到: {output_path}")
            
            # 分离音频组件
            audio_components = self.separate_audio_components(input_path)
            if audio_components is None:
                print("⚠️  无法分离音频组件，跳过此文件")
                return False
            
            # 创建5.1声道混音
            channels_5_1, sample_rate = self.create_5_1_mix(audio_components, input_path)
            if channels_5_1 is None:
                print("⚠️  无法创建5.1声道混音，跳过此文件")
                return False
            
            # 保存为AC3
            success = self.save_5_1_ac3(channels_5_1, sample_rate, output_path)
            
            if success:
                print(f"\n🎉 转换完成: {output_path}")
                
                # 显示声道详细信息
                print(f"\n⚙️  增益配置:")
                print(f"  - 全局增益: {self.global_gain_db}dB")
                print(f"  - 原始音频增益: {self.original_gain_db}dB")
                for name, gain in self.separated_track_gains_db.items():
                    if gain != 0:
                        print(f"  - {name}增益: {gain}dB")
            
            # 清理临时文件
            self.clear_temp_dir()
            
            return success
            
        except Exception as e:
            print(f"❌ 处理文件时出错: {e}")
            return False
    
    def process_directory(self, input_dir):
        """处理目录中的所有音频文件"""
        try:
            input_dir = Path(input_dir)
            
            if not input_dir.exists():
                print(f"❌ 输入目录不存在: {input_dir}")
                return False
            
            # 创建输出目录
            output_dir = input_dir / "多声道混音"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"📂 目录模式: 输出到 {output_dir}")
            
            if self.separator is None:
                print("❌ 音频分离器未初始化，无法查找音频文件")
                return False
            
            # 查找音频文件
            try:
                audio_files = self.separator.find_audio_files(input_dir)
            except Exception as e:
                print(f"❌ 查找音频文件失败: {e}")
                audio_files = []
            
            if not audio_files:
                print(f"❌ 未找到支持的音频文件: {input_dir}")
                return False
            
            print(f"📁 找到 {len(audio_files)} 个音频文件")
            
            # 处理每个文件
            success_count = 0
            for i, audio_file in enumerate(audio_files, 1):
                print(f"\n[{i}/{len(audio_files)}] 处理: {audio_file.name}")
                
                try:
                    # 传入输出目录参数
                    result = self.process_single_file(audio_file, output_dir)
                    if result:
                        success_count += 1
                        print(f"✅ 完成: {audio_file.name}")
                    else:
                        print(f"⚠️  处理失败: {audio_file.name}")
                    
                except Exception as e:
                    print(f"❌ 处理文件 {audio_file.name} 时出错: {e}")
                    continue
                
                # 清理临时文件
                self.clear_temp_dir()
            
            print(f"\n✨ 处理完成: {success_count}/{len(audio_files)} 个文件成功")
            print(f"📂 输出位置: {output_dir}")
            return success_count > 0
            
        except Exception as e:
            print(f"❌ 处理目录时出错: {e}")
            return False
    
    def convert(self, input_path):
        """主转换函数"""
        print("=" * 60)
        print("🚀 立体声转5.1声道转换器")
        print("=" * 60)
        
        try:
            input_path = Path(input_path)
            if not input_path.exists():
                print(f"❌ 路径不存在: {input_path}")
                return False
            
            print(f"🎯 输入路径: {input_path}")
            print(f"⚙️  声道分配逻辑:")
            print(f"📀 输出格式: AC3 320kbps (失败时自动保存为WAV)")
            print(f"🔊 增益配置: 所有增益默认为0dB，可根据需要调整")
            print(f"🔧 注意: 前声道包含20%原始立体声")
            
            if input_path.is_file():
                return self.process_single_file(input_path)
            else:
                return self.process_directory(input_path)
                
        except Exception as e:
            print(f"❌ 转换过程中出错: {e}")
            return False
        finally:
            # 最终清理
            try:
                self.clear_temp_dir()
            except Exception as e:
                print(f"⚠️  最终清理失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="立体声转5.1声道转换器")
    parser.add_argument("input", help="输入文件或目录路径")
    parser.add_argument("--global-gain", type=float, default=0, help="全局增益 (dB)")
    parser.add_argument("--original-gain", type=float, default=0, help="原始音频增益 (dB)")
    parser.add_argument("--vocals-gain", type=float, default=0, help="人声音轨增益 (dB)")
    parser.add_argument("--drums-gain", type=float, default=0, help="鼓声音轨增益 (dB)")
    parser.add_argument("--bass-gain", type=float, default=0, help="贝斯音轨增益 (dB)")
    parser.add_argument("--guitar-gain", type=float, default=0, help="吉他音轨增益 (dB)")
    parser.add_argument("--piano-gain", type=float, default=0, help="钢琴音轨增益 (dB)")
    parser.add_argument("--other-gain", type=float, default=0, help="其他音轨增益 (dB)")
    parser.add_argument("--original-weight", type=float, default=0.2, help="原始立体声在前声道的权重 (默认0.2)")
    
    args = parser.parse_args()
    
    # 创建转换器
    converter = StereoTo5_1Converter()
    
    # 应用命令行增益参数
    converter.global_gain_db = args.global_gain
    converter.original_gain_db = args.original_gain
    converter.separated_track_gains_db["vocals"] = args.vocals_gain
    converter.separated_track_gains_db["drums"] = args.drums_gain
    converter.separated_track_gains_db["bass"] = args.bass_gain
    converter.separated_track_gains_db["guitar"] = args.guitar_gain
    converter.separated_track_gains_db["piano"] = args.piano_gain
    converter.separated_track_gains_db["other"] = args.other_gain
    
    # 应用原始立体声权重参数
    converter.original_stereo_weight = args.original_weight
    
    # 执行转换
    success = converter.convert(args.input)
    
    if success:
        print("\n✨ 处理完成!")
    else:
        print("\n⚠️  处理过程中遇到错误，但程序继续执行完成")
    # 注意：这里不调用sys.exit，让程序正常结束


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            main()
        else:
            # 交互模式
            print("=" * 60)
            print("🎧 立体声转5.1声道转换器")
            print("=" * 60)
            
            converter = StereoTo5_1Converter()
            
            input_path = input("\n🎵 请输入音频文件或目录路径: ").strip().strip('"')
            if not os.path.exists(input_path):
                print("❌ 路径不存在!")
            else:
                print("\n⚙️  配置信息:")
                print("- 固定模型: htdemucs_6s (六源音频分离)")
                print("- 输出格式: AC3 320KB (失败时自动保存为WAV)")
                print("- 声道分配:")
                print("\n开始处理...\n")
                
                # 执行转换
                success = converter.convert(input_path)
                
                if success:
                    print("\n✨ 处理完成!")
                else:
                    print("\n⚠️  处理过程中遇到错误，但程序继续执行完成")
                    
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
    finally:
        print("\n程序结束")
        # 不调用sys.exit，让程序自然结束