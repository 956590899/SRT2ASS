import os
import sys
import subprocess
import shutil

# 设置环境变量，确保Python使用UTF-8编码
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LANG'] = 'zh_CN.UTF-8'
os.environ['LC_ALL'] = 'zh_CN.UTF-8'

# 确保标准输出/错误使用UTF-8编码
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# 自动安装缺失的依赖
try:
    import torch
except ImportError:
    print("torch 未安装，正在安装...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "torch", "torchaudio", "--no-cache-dir"])
    import torch

try:
    import torchaudio
except ImportError:
    print("torchaudio 未安装，正在安装...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "torchaudio", "--no-cache-dir"])
    import torchaudio

try:
    import scipy
    import scipy.io.wavfile
except ImportError:
    print("scipy 未安装，正在安装...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "scipy", "--no-cache-dir"])
    import scipy
    import scipy.io.wavfile

from pathlib import Path
import argparse
import tempfile
import time
import json
import io
import re
from datetime import datetime, timedelta

# ==================== 配置变量 ====================
# Demucs日志显示开关
# True: 显示详细日志
# False: 只显示基本信息，不显示详细的分离过程
DEMUCS_VERBOSE = True

# 进度条显示方式
# True: 单行刷新方式显示进度条
# False: 逐行显示进度条
SINGLE_LINE_PROGRESS = True

class ProgressOutputRedirector:
    """终极优化版：支持 Unicode 块、强制单行覆盖、防止多进度条并排"""
    def __init__(self, original_stream):
        self.original_stream = original_stream
        self.last_is_progress = False
        self.encoding = getattr(original_stream, 'encoding', 'utf-8')

    def isatty(self):
        """欺骗 tqdm 启用 Unicode 块 (█)"""
        return True

    def write(self, text):
        if not text:
            return

        # 核心逻辑：检测是否包含 tqdm 进度条特征
        if '|' in text and ('%' in text or 'it/s' in text or 'seconds/s' in text):
            # 1. 处理可能夹杂在一起的多个进度更新
            # 将回车符替换为换行，方便分割处理
            segments = text.replace('\r', '\n').split('\n')
            # 提取所有包含进度特征的行，并取最后一行（最新的状态）
            progress_lines = [line.strip() for line in segments if '|' in line and '%' in line]
            
            if progress_parts := progress_lines:
                latest_bar = progress_parts[-1]
                # 使用 \r 回到行首 + 最新进度条内容 + 足够长的空格(ljust) 彻底覆盖旧内容
                # 120个字符通常足以覆盖任何控制台的进度条宽度
                self.original_stream.write(f'\r{latest_bar}'.ljust(120))
                self.original_stream.flush()
                self.last_is_progress = True
                return
        
        # 处理非进度条的普通文本
        # 只有在文本包含实质内容（非纯空格/换行）时才输出
        clean_text = text.strip('\r\n')
        if clean_text:
            if self.last_is_progress:
                # 如果上一行是进度条，输出新文本前强制换行，避免文字卡在进度条后面
                self.original_stream.write('\n')
                self.last_is_progress = False
            
            self.original_stream.write(text)
            self.original_stream.flush()

    def flush(self):
        self.original_stream.flush()
    
    def fileno(self):
        try: return self.original_stream.fileno()
        except: return 1

    def close(self):
        pass

# 模型配置 - 格式：(编号, 模型名称, 中文描述)
MODEL_CONFIGS = [
    (1, "htdemucs", "高质量分离 (推荐)"),
    (2, "htdemucs_ft", "精细调优版本"),
    (3, "hdemucs_mmi", "混合模型"),
    (4, "htdemucs_6s", "六源音频")
]
DEFAULT_MODEL_ID = 1  # 默认使用第一个模型

# 输出模式配置 - 格式：(编号, 模式标识, 中文描述)
OUTPUT_MODE_CONFIGS = [
    (1, "vocals", "仅人声"),
    (2, "accompaniment", "仅伴奏"),
    (3, "both", "人声和伴奏"),
    (4, "all", "全部分离 (人声、鼓、贝斯、其他)")
]
DEFAULT_OUTPUT_MODE_ID = 1  # 默认选择第1个模式

# 音轨名称映射
STEM_NAMES = {
    "drums": "鼓声",
    "bass": "贝斯", 
    "other": "其他",
    "vocals": "人声",
    "guitar": "吉他",
    "piano": "钢琴"
}

# 支持的音视频格式
SUPPORTED_FORMATS = {
    # 音频格式
    '.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma', '.aiff', '.ape', '.opus',
    # 视频格式
    '.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.m4v', '.mpg', '.mpeg', '.3gp',
    '.webm', '.ts', '.mts', '.m2ts', '.vob', '.ogv', '.rm', '.rmvb', '.asf', '.divx'
}

# 从配置中提取默认值
def get_default_config(configs, default_id):
    """从配置列表中获取默认配置"""
    for config in configs:
        if config[0] == default_id:
            return config
    return configs[0]  # 如果找不到，返回第一个

# 获取默认模型和输出模式
DEFAULT_MODEL_CONFIG = get_default_config(MODEL_CONFIGS, DEFAULT_MODEL_ID)
DEFAULT_MODEL = DEFAULT_MODEL_CONFIG[1]  # 模型名称
MODEL_NAMES = [config[1] for config in MODEL_CONFIGS]

DEFAULT_OUTPUT_MODE_CONFIG = get_default_config(OUTPUT_MODE_CONFIGS, DEFAULT_OUTPUT_MODE_ID)
DEFAULT_OUTPUT_MODE = DEFAULT_OUTPUT_MODE_CONFIG[1]  # 模式标识
OUTPUT_MODES = {config[1]: config[2] for config in OUTPUT_MODE_CONFIGS}

# 方便函数：根据编号获取配置项
def get_model_by_id(model_id):
    """根据编号获取模型配置"""
    for config in MODEL_CONFIGS:
        if config[0] == model_id:
            return config
    return None

def get_output_mode_by_id(mode_id):
    """根据编号获取输出模式配置"""
    for config in OUTPUT_MODE_CONFIGS:
        if config[0] == mode_id:
            return config
    return None

# 检测FFmpeg路径
def detect_ffmpeg_path():
    """检测FFmpeg路径"""
    # 项目自带的ffmpeg路径
    project_ffmpeg = Path(__file__).parent / "Python" / "ffmpeg" / "ffmpeg.exe"
    if project_ffmpeg.exists():
        return str(project_ffmpeg)
    # 系统PATH中的ffmpeg
    return "ffmpeg"

# FFmpeg转换参数
FFMPEG_PATH = detect_ffmpeg_path()
FFMPEG_ARGS = [
    FFMPEG_PATH, '-i', '%INPUT%',
    '-acodec', 'pcm_s16le',
    '-ar', '44100',
    '-ac', '2',
    '-y', '%OUTPUT%'
]
# =================================================

# 修复Windows系统下的编码问题
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        else:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass


class GPUOptimizedDemucs:
    """GPU优化的音频分离器"""
    
    def __init__(self, project_dir=None):
        """初始化分离器"""
        self.project_dir = Path(project_dir) if project_dir else Path(__file__).parent
        self.cache_dir = self.project_dir / "Python" / "demucs_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置环境变量
        os.environ['DEMUCS_CACHE_DIR'] = str(self.cache_dir)
        os.environ['TORCH_HOME'] = str(self.cache_dir)
        os.environ['MPG123_IGNORE_WARNINGS'] = '1'
        
        # GPU优化设置
        torch.backends.cudnn.benchmark = True
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        
        # 检查FFmpeg（不显示输出）
        self.ffmpeg_available = self.check_ffmpeg()
        
        # 设置GPU信息（简化版本）
        self.setup_gpu_info()
    
    def check_ffmpeg(self):
        """检查FFmpeg是否可用（静默检查）"""
        try:
            result = subprocess.run(
                [FFMPEG_PATH, '-version'], 
                capture_output=True, 
                text=True, 
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False
    
    def setup_gpu_info(self):
        """设置GPU信息（简化版本）"""
        if torch.cuda.is_available():
            self.device = "cuda"
        else:
            self.device = "cpu"

    def _cleanup_separator_cache(self):
        """清理分离器缓存目录中的临时文件"""
        if not self.cache_dir or not self.cache_dir.exists():
            return
        try:
            import time
            current_time = time.time()
            for item in self.cache_dir.iterdir():
                try:
                    if item.is_file():
                        age = current_time - item.stat().st_mtime
                        if age > 86400:
                            item.unlink()
                    elif item.is_dir():
                        if item.name.startswith('tmp'):
                            shutil.rmtree(item)
                except Exception:
                    pass
        except Exception:
            pass

    def progress_callback(self, fraction):
        """自定义进度回调函数，实现单行刷新"""
        if SINGLE_LINE_PROGRESS and DEMUCS_VERBOSE:
            percent = int(fraction * 100)
            bar_length = 50
            filled_length = int(bar_length * fraction)
            bar = '█' * filled_length + ' ' * (bar_length - filled_length)
            sys.stdout.write(f'  {percent}%|{bar}| {fraction:.1f}/{1.0} [处理中...\r')
            sys.stdout.flush()
            if percent == 100:
                sys.stdout.write('\n')
                sys.stdout.flush()

    def setup_demucs(self):
        """设置Demucs环境"""
        try:
            import demucs
            import soundfile
            return True
        except ImportError:
            print("Demucs 未安装，正在安装...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "demucs", "soundfile", "--upgrade", "--no-cache-dir"])
                import demucs
                import soundfile
                return True
            except Exception as e:
                print(f"安装失败: {e}")
                return False

    def optimize_for_gpu(self):
        """GPU专用优化"""
        if self.device == "cuda":
            torch.cuda.empty_cache()

    def load_model(self, model_name=DEFAULT_MODEL):
        """加载模型"""
        if not self.setup_demucs():
            return None
        
        self.optimize_for_gpu()
        
        try:
            if DEMUCS_VERBOSE:
                print(f"正在加载模型: {model_name}...")
            
            # 尝试使用Demucs API
            try:
                import demucs.api
                separator = demucs.api.Separator(
                    model=model_name,
                    device=self.device,
                    progress=DEMUCS_VERBOSE,  # 根据日志开关控制进度显示
                    shifts=1,
                    split=True,
                    overlap=0.25,
                    jobs=1
                )
                
                if DEMUCS_VERBOSE:
                    print(f"✓ 模型加载成功")
                return separator
                
            except ImportError:
                if DEMUCS_VERBOSE:
                    print("警告: 使用传统方式加载模型")
                from demucs import pretrained
                model = pretrained.get_model(model_name)
                model.to(self.device)
                model.eval()
                
                if DEMUCS_VERBOSE:
                    print(f"✓ 模型加载成功")
                return model
                    
        except Exception as e:
            print(f"模型加载失败: {e}")
            
            if "CUDA out of memory" in str(e):
                print("GPU 内存不足，尝试使用 CPU")
                self.device = "cpu"
                return self.load_model(model_name)
            
            return None

    def convert_with_ffmpeg(self, input_path, output_path):
        """使用FFmpeg转换音频格式"""
        try:
            cmd = [
                FFMPEG_PATH, '-i', str(input_path),
                '-acodec', 'pcm_s16le',
                '-ar', '44100',
                '-ac', '2',
                '-y',
                str(output_path)
            ]
            
            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            result = subprocess.run(cmd, capture_output=True, timeout=300,
                                   creationflags=creation_flags)
            
            return result.returncode == 0
                
        except Exception as e:
            return False

    def safe_delete_file(self, file_path, max_retries=5, delay=1):
        """安全删除文件"""
        for i in range(max_retries):
            try:
                if file_path.exists():
                    file_path.unlink()
                    return True
            except PermissionError:
                if i < max_retries - 1:
                    time.sleep(delay)
                else:
                    return False
        return False
    
    def save_audio_with_scipy(self, file_path, audio, sample_rate):
        """使用scipy保存音频文件，避免torchcodec依赖"""
        import scipy.io.wavfile
        import numpy as np
        
        # 确保音频数据是正确的格式
        audio_np = audio.detach().cpu().numpy()
        
        # 转换形状：[channels, samples] -> [samples, channels]
        if len(audio_np.shape) == 2:
            audio_np = audio_np.T
        
        # 归一化到 [-32768, 32767]
        audio_np = np.clip(audio_np * 32768.0, -32768, 32767).astype(np.int16)
        
        # 保存为WAV文件
        scipy.io.wavfile.write(str(file_path), sample_rate, audio_np)
    
    def load_audio_file(self, file_path):
        """加载音频文件"""
        file_path = Path(file_path)
        
        print(f"  加载音频文件: {file_path}")
        print(f"  文件存在: {file_path.exists()}")
        print(f"  文件大小: {file_path.stat().st_size if file_path.exists() else 'N/A'} bytes")
        print(f"  FFmpeg可用: {self.ffmpeg_available}")
        
        # 优先使用FFmpeg转换所有音频文件为WAV，避免使用torchaudio.load的torchcodec依赖
        temp_path = None
        
        try:
            print(f"  尝试使用FFmpeg转换音频文件")
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = Path(temp_file.name)
            
            print(f"  临时文件: {temp_path}")
            if self.convert_with_ffmpeg(file_path, temp_path):
                print(f"  FFmpeg转换成功")
                # 使用scipy.io.wavfile替代torchaudio.load，避免torchcodec依赖
                try:
                    import scipy.io.wavfile
                    sample_rate, data = scipy.io.wavfile.read(temp_path)
                    print(f"  音频加载成功: {sample_rate}Hz, {data.shape[0]} samples")
                    # 转换为torch tensor并调整形状
                    import torch
                    waveform = torch.tensor(data, dtype=torch.float32)
                    # 如果是立体声，确保形状为 [channels, samples]
                    if len(waveform.shape) == 2:
                        waveform = waveform.T  # 转换为 [channels, samples]
                    else:
                        waveform = waveform.unsqueeze(0)  # 单声道添加通道维度
                    # 归一化到 [-1, 1]
                    waveform = waveform / 32768.0
                    return waveform, sample_rate
                except Exception as e:
                    print(f"  scipy加载失败: {e}")
                    # 尝试使用torchaudio.load，但捕获torchcodec错误
                    try:
                        waveform, sample_rate = torchaudio.load(temp_path)
                        print(f"  音频加载成功: {sample_rate}Hz, {waveform.shape[1]} samples")
                        return waveform, sample_rate
                    except Exception as e2:
                        print(f"  torchaudio加载失败: {e2}")
                        raise Exception(f"无法加载转换后的音频文件: {temp_path}\n详细错误: {e2}")
            else:
                print(f"  FFmpeg转换失败")
                raise Exception(f"FFmpeg转换失败: {file_path}")
        except Exception as e:
            print(f"  转换异常: {e}")
            # 尝试直接使用torchaudio.load
            try:
                print(f"  尝试直接加载音频文件")
                waveform, sample_rate = torchaudio.load(file_path)
                print(f"  音频加载成功: {sample_rate}Hz, {waveform.shape[1]} samples")
                return waveform, sample_rate
            except Exception as e2:
                print(f"  直接加载失败: {e2}")
                raise Exception(f"无法加载音频文件: {file_path}\n详细错误: {e2}")
        finally:
            if temp_path and temp_path.exists():
                self.safe_delete_file(temp_path)

    def find_audio_files(self, input_path):
        """查找所有音视频文件"""
        input_path = Path(input_path)
        
        if input_path.is_file():
            if input_path.suffix.lower() in SUPPORTED_FORMATS:
                return [input_path]
            else:
                return []
        elif input_path.is_dir():
            audio_files_set = set()
            
            for file_path in input_path.iterdir():
                if file_path.is_file():
                    ext = file_path.suffix.lower()
                    if ext in SUPPORTED_FORMATS:
                        audio_files_set.add(file_path.resolve())
            
            audio_files = [Path(file_path) for file_path in audio_files_set]
            return sorted(audio_files)
        
        return []

    def format_time(self, seconds):
        """格式化时间显示"""
        seconds = int(seconds)
        
        if seconds < 60:
            return f"{seconds}秒"
        else:
            td = timedelta(seconds=seconds)
            total_seconds = td.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            secs = int(total_seconds % 60)
            
            if hours > 0:
                return f"{hours}:{minutes:02d}:{secs:02d}"
            else:
                return f"{minutes}:{secs:02d}"

    def separate_audio(self, input_path, model_name=DEFAULT_MODEL, output_mode="vocals", output_dir=None):
        """
        分离音频

        Args:
            input_path: 输入文件或目录
            model_name: 模型名称
            output_mode: 输出模式
                - "vocals": 仅人声
                - "accompaniment": 仅伴奏
                - "both": 人声和伴奏
                - "all": 全部分离
            output_dir: 输出目录
        """
        print("\n" + "=" * 70)
        print("音频分离处理开始".center(70))
        print("=" * 70)

        self._cleanup_separator_cache()
        
        # 全部分离模式强制使用htdemucs_6s模型
        if output_mode == "all":
            model_name = "htdemucs_6s"
            print(f"  全部分离模式，使用模型: {model_name}")
        
        # 加载模型
        model = self.load_model(model_name)
        if model is None:
            return []
        
        input_path = Path(input_path)
        is_single_file = input_path.is_file()
        
        # 查找音频文件
        files_to_process = self.find_audio_files(input_path)
        
        if not files_to_process:
            print("没有找到支持的音频文件！")
            return []
        
        # 确定输出目录
        if is_single_file:
            final_output_dir = Path(output_dir) if output_dir else input_path.parent
        else:
            base_output_dir = Path(output_dir) if output_dir else input_path
            final_output_dir = base_output_dir / "音频分离结果"
        
        final_output_dir.mkdir(parents=True, exist_ok=True)
        
        all_saved_files = []
        
        # 处理每个文件
        for i, audio_file in enumerate(files_to_process, 1):
            print(f"\n[{i}/{len(files_to_process)}] 处理文件: {audio_file.name}")
            
            try:
                # 加载音频
                waveform, orig_sr = self.load_audio_file(audio_file)
                duration = waveform.shape[1] / orig_sr
                print(f"  音频信息: {orig_sr}Hz, {duration:.1f}秒")
                
                file_start_time = time.time()
                
                # 尝试使用Demucs API
                try:
                    import demucs.api
                    if isinstance(model, demucs.api.Separator):
                        # 重定向标准错误（tqdm默认使用stderr）
                        original_stderr = sys.stderr
                        sys.stderr = ProgressOutputRedirector(original_stderr)
                        
                        try:
                            # 分离音频
                            result = model.separate_audio_file(str(audio_file))
                            
                            # 获取分离结果
                            sources = {stem: track for stem, track in result.items()}
                        finally:
                            # 恢复流
                            sys.stderr = original_stderr
                            # 关键：手动补一个换行，确保后续的"分离完成"不会接在进度条后面
                            print()
                        
                        # 保存文件
                        saved_files = []
                        
                        if output_mode == "vocals":
                            if "vocals" in sources:
                                output_path = final_output_dir / f"{audio_file.stem}_人声.wav"
                                self.save_audio_with_scipy(output_path, sources["vocals"], model.samplerate)
                                print(f"  ✓ 已保存人声: {output_path.name}")
                                saved_files.append(output_path)
                                
                        elif output_mode == "accompaniment":
                            instrumental = None
                            for stem, track in sources.items():
                                if stem != "vocals":
                                    instrumental = track if instrumental is None else instrumental + track
                            
                            if instrumental is not None:
                                output_path = final_output_dir / f"{audio_file.stem}_伴奏.wav"
                                self.save_audio_with_scipy(output_path, instrumental, model.samplerate)
                                print(f"  ✓ 已保存伴奏: {output_path.name}")
                                saved_files.append(output_path)
                                
                        elif output_mode == "both":
                            if "vocals" in sources:
                                output_path = final_output_dir / f"{audio_file.stem}_人声.wav"
                                self.save_audio_with_scipy(output_path, sources["vocals"], model.samplerate)
                                print(f"  ✓ 已保存人声: {output_path.name}")
                                saved_files.append(output_path)
                            
                            instrumental = None
                            for stem, track in sources.items():
                                if stem != "vocals":
                                    instrumental = track if instrumental is None else instrumental + track
                            
                            if instrumental is not None:
                                output_path = final_output_dir / f"{audio_file.stem}_伴奏.wav"
                                self.save_audio_with_scipy(output_path, instrumental, model.samplerate)
                                print(f"  ✓ 已保存伴奏: {output_path.name}")
                                saved_files.append(output_path)
                                
                        elif output_mode == "all":
                            print("  保存分离结果...")
                            for stem, track in sources.items():
                                chinese_name = STEM_NAMES.get(stem, stem)
                                output_path = final_output_dir / f"{audio_file.stem}_{chinese_name}.wav"
                                self.save_audio_with_scipy(output_path, track, model.samplerate)
                                saved_files.append(output_path)
                                print(f"  ✓ 已保存{chinese_name}")
                        
                        all_saved_files.extend(saved_files)
                        continue
                except:
                    pass
                
                # 传统分离方式
                print("  分离中...")
                try:
                    from demucs.audio import convert_audio
                    waveform = convert_audio(waveform, orig_sr, model.samplerate, model.audio_channels)
                except:
                    import torch.nn.functional as F
                    if orig_sr != model.samplerate:
                        waveform = F.interpolate(
                            waveform.unsqueeze(0), 
                            size=int(waveform.shape[1] * model.samplerate / orig_sr), 
                            mode='linear', 
                            align_corners=False
                        ).squeeze(0)
                
                waveform = waveform.unsqueeze(0).to(self.device)
                
                # 重定向标准错误（tqdm默认使用stderr）
                original_stderr = sys.stderr
                sys.stderr = ProgressOutputRedirector(original_stderr)
                
                try:
                    from demucs.apply import apply_model
                    with torch.no_grad():
                        # 核心：确保 progress=True
                        sources = apply_model(model, waveform, progress=DEMUCS_VERBOSE, split=True)
                except Exception as e:
                    # 如果 apply_model 失败的备选方案
                    with torch.no_grad():
                        sources = model(waveform)
                finally:
                    # 恢复流
                    sys.stderr = original_stderr
                    # 关键：手动补一个换行，确保后续的"分离完成"不会接在进度条后面
                    print()
                
                # 完成提示
                elapsed_time = time.time() - file_start_time
                elapsed_str = self.format_time(elapsed_time)
                print(f"  分离完成 | 用时: {elapsed_str}")
                
                sources = sources.squeeze(0).cpu()
                
                # 获取音轨名称
                try:
                    track_names = model.sources if hasattr(model, 'sources') else ["drums", "bass", "other", "vocals"]
                except:
                    track_names = ["drums", "bass", "other", "vocals"]
                
                saved_files = []
                
                if output_mode == "vocals":
                    try:
                        vocals_idx = track_names.index("vocals")
                        stem_audio = sources[vocals_idx]
                    except:
                        stem_audio = sources[-1]
                        
                    output_path = final_output_dir / f"{audio_file.stem}_人声.wav"
                    self.save_audio_with_scipy(output_path, stem_audio, model.samplerate)
                    print(f"  ✓ 已保存人声: {output_path.name}")
                    saved_files.append(output_path)
                    
                elif output_mode == "accompaniment":
                    instrumental = torch.zeros_like(sources[0])
                    for i, stem in enumerate(track_names):
                        if stem != "vocals":
                            instrumental += sources[i]
                    
                    output_path = final_output_dir / f"{audio_file.stem}_伴奏.wav"
                    self.save_audio_with_scipy(output_path, instrumental, model.samplerate)
                    print(f"  ✓ 已保存伴奏: {output_path.name}")
                    saved_files.append(output_path)
                    
                elif output_mode == "both":
                    try:
                        vocals_idx = track_names.index("vocals")
                        vocals = sources[vocals_idx]
                    except:
                        vocals = sources[-1]
                        
                    output_path = final_output_dir / f"{audio_file.stem}_人声.wav"
                    self.save_audio_with_scipy(output_path, vocals, model.samplerate)
                    print(f"  ✓ 已保存人声: {output_path.name}")
                    saved_files.append(output_path)
                    
                    instrumental = torch.zeros_like(sources[0])
                    for i, stem in enumerate(track_names):
                        if stem != "vocals":
                            instrumental += sources[i]
                    
                    output_path = final_output_dir / f"{audio_file.stem}_伴奏.wav"
                    self.save_audio_with_scipy(output_path, instrumental, model.samplerate)
                    print(f"  ✓ 已保存伴奏: {output_path.name}")
                    saved_files.append(output_path)
                    
                elif output_mode == "all":
                    print("  保存分离结果...")
                    for i, stem in enumerate(track_names):
                        stem_audio = sources[i]
                        chinese_name = STEM_NAMES.get(stem, stem)
                        output_path = final_output_dir / f"{audio_file.stem}_{chinese_name}.wav"
                        self.save_audio_with_scipy(output_path, stem_audio, model.samplerate)
                        saved_files.append(output_path)
                        print(f"  ✓ 已保存{chinese_name}")
                
                all_saved_files.extend(saved_files)
                
            except Exception as e:
                print(f"\n✗ 处理失败: {e}")
                continue
        
        # 清理GPU内存
        if self.device == "cuda":
            torch.cuda.empty_cache()
        
        # 显示完成信息
        print("\n" + "=" * 70)
        print("音频分离处理完成".center(70))
        print(f"共处理 {len(files_to_process)} 个文件".center(70))
        print(f"输出目录: {final_output_dir}".center(70))
        print("=" * 70)
        
        return all_saved_files


def main():
    """命令行主函数"""
    if sys.platform == "win32":
        # 强制让 tqdm 认为它是连接到终端的
        import colorama
        colorama.init()
        
    parser = argparse.ArgumentParser(description="Demucs 人声分离工具")
    parser.add_argument("input", help="输入文件或目录路径")
    parser.add_argument("-o", "--output", help="输出目录")
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL, 
                       choices=MODEL_NAMES,
                       help="模型选择")
    parser.add_argument("--mode", default=DEFAULT_OUTPUT_MODE,
                       choices=list(OUTPUT_MODES.keys()),
                       help="分离模式")
    parser.add_argument("--cpu", action="store_true", help="强制使用 CPU")
    
    args = parser.parse_args()
    
    separator = GPUOptimizedDemucs()
    
    # 如果强制使用CPU
    if args.cpu:
        separator.device = "cpu"
    
    separator.separate_audio(args.input, args.model, args.mode, args.output)


if __name__ == "__main__":
    if sys.platform == "win32":
        # 强制让 tqdm 认为它是连接到终端的
        import colorama
        colorama.init()
        
    if len(sys.argv) > 1:
        main()
    else:
        # 交互模式
        print("\n" + "═" * 70)
        print("Demucs 人声分离工具".center(70))
        print("═" * 70 + "\n")
        
        separator = GPUOptimizedDemucs()
        
        # 用户输入
        input_path = input("请输入音频文件或目录路径: ").strip().strip('"')
        
        if not os.path.exists(input_path):
            print("✗ 路径不存在!")
            input("按回车键退出...")
            sys.exit(1)
        
        # 模型选择
        print("\n请选择模型:")
        for i, config in enumerate(MODEL_CONFIGS, 1):
            num, name, desc = config
            default_mark = " (默认)" if num == DEFAULT_MODEL_ID else ""
            print(f"{num}. {desc}{default_mark}")
        
        choice = input(f"请选择 ({MODEL_CONFIGS[0][0]}-{MODEL_CONFIGS[-1][0]}, 默认为{DEFAULT_MODEL_ID}): ").strip()
        if choice == "":
            choice = str(DEFAULT_MODEL_ID)
        
        model_config = get_model_by_id(int(choice)) if choice.isdigit() else DEFAULT_MODEL_CONFIG
        if not model_config:
            model_config = DEFAULT_MODEL_CONFIG
        
        # 分离模式选择
        print("\n请选择分离模式:")
        for i, config in enumerate(OUTPUT_MODE_CONFIGS, 1):
            num, mode_key, desc = config
            default_mark = " (默认)" if num == DEFAULT_OUTPUT_MODE_ID else ""
            print(f"{num}. {desc}{default_mark}")
        
        mode_choice = input(f"请选择 ({OUTPUT_MODE_CONFIGS[0][0]}-{OUTPUT_MODE_CONFIGS[-1][0]}, 默认为{DEFAULT_OUTPUT_MODE_ID}): ").strip()
        if mode_choice == "":
            mode_choice = str(DEFAULT_OUTPUT_MODE_ID)
        
        mode_config = get_output_mode_by_id(int(mode_choice)) if mode_choice.isdigit() else DEFAULT_OUTPUT_MODE_CONFIG
        if not mode_config:
            mode_config = DEFAULT_OUTPUT_MODE_CONFIG
        
        # 显示配置信息
        print(f"\n配置信息:")
        print(f"  - 输入路径: {input_path}")
        print(f"  - 模型: {model_config[2]} ({model_config[1]})")
        print(f"  - 模式: {mode_config[2]} ({mode_config[1]})")
        print(f"  - 使用设备: {separator.device.upper()}")
        
        print("\n开始处理...\n")
        
        # 开始处理（使用默认输出目录）
        separator.separate_audio(input_path, model_config[1], mode_config[1], None)
        
        print("\n处理完成!")
        input("按回车键退出程序...")