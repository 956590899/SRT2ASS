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

import re
import json
import shutil
import logging
import tempfile
import subprocess
from pathlib import Path

# ============================================
# 用户配置参数
# ============================================

# === 输出设置 ===
ASK_OUTPUT_DIR = 0                # 0=使用默认目录，1=每次询问输出目录
OUTPUT_DIR_FILTER_MARKER = ' (ASS_1)'  # 目录模式下过滤包含此标记的文件
OUTPUT_REPLACE_MARKERS = [' (SSA)', ' (SRT)', '(SSA)', '(SRT)']  # 输出时替换这些标记

# === 字幕效果设置 ===
# 真实卡拉OK效果设置：
# 0: 默认效果
# 1: 真实卡拉OK效果
# 2: 提词器效果
# -1: 全选，同时处理所有效果
KARAOKE_EFFECT = 1                # 0=不启用，1=启用卡拉OK效果
REAL_KARAOKE_EFFECT = -1           # 真实卡拉OK效果设置：0=默认效果，1=真实卡拉OK式样，2=提词器式样，-1=全选
NO_KARAOKE_SUFFIX = ' (SSA)'      # 未启用卡拉OK时的后缀
KARAOKE_SUFFIX = ' (ASS)'         # 启用卡拉OK时的后缀

# === 字体与格式设置 ===
CUSTOM_FONT = 1                   # 0=不启用，1=启用自定义字体
MULTI_SUBTITLE = 1                # 多字幕处理设置：0=不启用，1=启用

# === 强制开启功能 ===
USE_VOCAL_SEPARATION = True       # 人声分离
ENABLE_PACKING = True             # MKV打包

# ============================================
# 以下代码保持不变
# ============================================

# 禁用TensorFlow和spleeter的警告
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

logging.getLogger('tensorflow').setLevel(logging.ERROR)
logging.getLogger('librosa').setLevel(logging.ERROR)

class VoiceSeparator:
    def __init__(self):
        self.demucs_available = False
        self.current_engine = 'demucs'
        self._init_demucs()
        if self.demucs_available:
            print("✅ Demucs人声分离功能已启用 (质量模式)")
        else:
            print("❌ 警告: demucs 未安装，人声分离功能将不可用")

    def _init_demucs(self):
        try:
            import importlib.util
            x_path = Path(__file__).parent / "x.py"
            if not x_path.exists():
                print("❌ x.py 文件未找到，无法使用Demucs引擎")
                return False
            spec = importlib.util.spec_from_file_location("x", str(x_path))
            x_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(x_module)
            self.demucs_separator = x_module.GPUOptimizedDemucs()
            self.demucs_available = True
            return True
        except Exception as e:
            print(f"❌ demucs 初始化失败: {e}")
            return False

    def extract_audio_from_video(self, video_path, output_audio_path):
        """使用FFmpeg提取音频"""
        return self.extract_audio_with_ffmpeg(video_path, output_audio_path)
    
    def extract_audio_with_ffmpeg(self, video_path, output_audio_path):
        """使用FFmpeg提取音频"""
        try:
            import subprocess
            import sys
            cmd = [
                'ffmpeg', '-i', str(video_path),
                '-ac', '2', '-ar', '44100',
                '-acodec', 'pcm_s16le',
                '-y', str(output_audio_path)
            ]
            # 隐藏FFmpeg输出，使用UTF-8编码
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300, creationflags=creationflags)
            if result.returncode == 0:
                print(f"  ✓ FFmpeg提取音频成功: {output_audio_path}")
                return True
            else:
                print(f"  ✗ FFmpeg提取失败: {result.stderr}")
                return False
        except Exception as e:
            print(f"  ✗ FFmpeg提取异常: {e}")
            return False

    def find_separated_files(self, separation_dir):
        for root, dirs, files in os.walk(separation_dir):
            for file in files:
                file_path = Path(root) / file
                if '人声' in file and file.endswith('.wav'):
                    return file_path
        return None

    def separate_voice(self, input_path, output_path=None):
        if not self.demucs_available:
            raise Exception("demucs未初始化")
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"文件不存在: {input_path}")
        if output_path is None:
            output_path = input_path.parent / f"{input_path.stem}_人声.wav"
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"🎵 使用Demucs处理文件: {input_path.name}")
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
        audio_extensions = {'.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma'}
        file_extension = input_path.suffix.lower()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            if file_extension in video_extensions:
                temp_audio = temp_path / "temp_audio.wav"
                if not self.extract_audio_from_video(str(input_path), str(temp_audio)):
                    raise Exception("无法提取视频音频")
                input_audio = temp_audio
            elif file_extension in audio_extensions:
                input_audio = input_path
            else:
                raise Exception(f"不支持的文件格式: {file_extension}")
            print("🔄 正在进行人声分离 (Demucs)...")
            saved_files = self.demucs_separator.separate_audio(
                str(input_audio), 
                model_name="htdemucs", 
                output_mode="vocals", 
                output_dir=str(temp_path)
            )
            if not saved_files:
                raise Exception("Demucs分离失败")
            vocals_path = self.find_separated_files(temp_path)
            if not vocals_path or not vocals_path.exists():
                if saved_files:
                    vocals_path = Path(saved_files[0])
                else:
                    raise Exception("分离失败，未找到人声文件")
            shutil.copy2(str(vocals_path), str(output_path))
            print(f"✅ Demucs人声分离完成: {output_path}")
            return output_path

    def get_engine_info(self):
        info = {
            'current_engine': 'demucs',
            'demucs_available': self.demucs_available,
            'description': 'Demucs (质量模式)',
            'speed': '较慢',
            'quality': '高质量'
        }
        return info

class MainProcessor:
    def __init__(self):
        self.voice_separator = VoiceSeparator()
        self.python_path = self.detect_python_path()
        self.subtitle_calibrator_path = self.detect_module_path("a.py")
        self.karaoke_converter_path = self.detect_module_path("b.py")
        self.mkv_packer_path = self.detect_module_path("c.py")
        self.karaoke_processor_path = self.detect_module_path("k.py")
        self.prompter_converter_path = self.detect_module_path("T.py")  # 新增提词器转换器
        self.cache_dir = None
        # 初始化工具路径
        self.mkvmerge_path = self.detect_mkvmerge_path()
        self.ffmpeg_path = self.detect_ffmpeg_path()
    
    def detect_mkvmerge_path(self):
        """检测MKVToolNix路径"""
        # 项目自带的MKVToolNix路径
        project_mkvmerge = Path(__file__).parent.parent / "SRT" / "Python" / "MKVToolNix" / "mkvmerge.exe"
        if project_mkvmerge.exists():
            return str(project_mkvmerge)
        # 尝试在Python目录下查找
        python_mkvmerge = Path(__file__).parent.parent / "Python" / "MKVToolNix" / "mkvmerge.exe"
        if python_mkvmerge.exists():
            return str(python_mkvmerge)
        # 系统PATH中的mkvmerge
        return "mkvmerge"
    
    def detect_ffmpeg_path(self):
        """检测ffmpeg路径"""
        # 项目自带的ffmpeg路径
        project_ffmpeg = Path(__file__).parent.parent / "SRT" / "Python" / "ffmpeg" / "ffmpeg.exe"
        if project_ffmpeg.exists():
            return str(project_ffmpeg)
        # 尝试在Python目录下查找
        python_ffmpeg = Path(__file__).parent.parent / "Python" / "ffmpeg" / "ffmpeg.exe"
        if python_ffmpeg.exists():
            return str(python_ffmpeg)
        # 系统PATH中的ffmpeg
        return "ffmpeg"

    def detect_python_path(self):
        python_path = sys.executable
        if python_path and os.path.exists(python_path):
            return python_path
        return "python"

    def detect_module_path(self, module_name):
        current_dir = Path(__file__).parent
        module_path = current_dir / module_name
        if module_path.exists():
            return str(module_path)
        return module_name
    
    def extract_audio_with_ffmpeg(self, video_path, output_audio_path):
        """使用FFmpeg提取音频"""
        try:
            import subprocess
            import sys
            cmd = [
                self.ffmpeg_path, '-i', str(video_path),
                '-ac', '2', '-ar', '44100',
                '-acodec', 'pcm_s16le',
                '-y', str(output_audio_path)
            ]
            # 隐藏FFmpeg输出，使用UTF-8编码
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300, creationflags=creationflags)
            if result.returncode == 0:
                print(f"  ✓ FFmpeg提取音频成功: {output_audio_path}")
                return True
            else:
                print(f"  ✗ FFmpeg提取失败: {result.stderr}")
                return False
        except Exception as e:
            print(f"  ✗ FFmpeg提取异常: {e}")
            return False

    def setup_cache(self, output_dir=None):
        import datetime
        temp_dir = tempfile.gettempdir()
        self.cache_dir = Path(temp_dir) / "srt2ass"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.cache_dir = self.cache_dir / f"cache_{timestamp}"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        print(f"缓存目录: {self.cache_dir}")
        self._cleanup_old_cache_files()

    def _cleanup_old_cache_files(self):
        """清理旧的缓存文件，防止残留文件影响后续处理"""
        if not self.cache_dir or not self.cache_dir.exists():
            self.cache_dir = Path(tempfile.gettempdir()) / "srt2ass_temp_cache"
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            return
        try:
            for item in self.cache_dir.iterdir():
                try:
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                except Exception as e:
                    pass
        except Exception as e:
            pass

    def cleanup_cache(self):
        if self.cache_dir and self.cache_dir.exists():
            try:
                shutil.rmtree(self.cache_dir)
                print(f"缓存已清理: {self.cache_dir}")
            except Exception as e:
                print(f"缓存清理失败: {e}")

    def run_command_safe(self, cmd, timeout=30, capture_output=True):
        try:
            if capture_output:
                # 使用PIPE捕获输出
                result = subprocess.run(
                    cmd, 
                    capture_output=True,
                    timeout=timeout,
                    shell=False,
                    encoding='utf-8',
                    errors='ignore'
                )
                # 过滤掉进度信息
                filtered_stdout = []
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    # 过滤掉Progress: X%和其他不需要的输出
                    if line and not line.startswith('Progress: ') and not line.startswith('Extracting track'):
                        filtered_stdout.append(line)
                filtered_stderr = []
                for line in result.stderr.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('Progress: ') and not line.startswith('Extracting track'):
                        filtered_stderr.append(line)
                return result.returncode, '\n'.join(filtered_stdout), '\n'.join(filtered_stderr)
            else:
                # 对于不捕获输出的情况，使用PIPE并手动处理
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=False,
                    encoding='utf-8',
                    errors='ignore'
                )
                
                stdout_lines = []
                stderr_lines = []
                
                try:
                    # 等待命令完成，同时处理输出
                    stdout, stderr = process.communicate(timeout=timeout)
                    
                    # 过滤掉进度信息
                    for line in stdout.split('\n'):
                        line = line.strip()
                        if line and not line.startswith('Progress: ') and not line.startswith('Extracting track'):
                            stdout_lines.append(line)
                    for line in stderr.split('\n'):
                        line = line.strip()
                        if line and not line.startswith('Progress: ') and not line.startswith('Extracting track'):
                            stderr_lines.append(line)
                except subprocess.TimeoutExpired:
                    process.kill()
                    return -1, "", "命令执行超时"
                except Exception as e:
                    process.kill()
                    return -1, "", f"命令执行失败: {str(e)}"
                
                return process.returncode, '\n'.join(stdout_lines), '\n'.join(stderr_lines)
        except Exception as e:
            return -1, "", f"命令执行失败: {str(e)}"

    def is_subtitle_file(self, file_path):
        subtitle_extensions = {'.srt', '.ass', '.ssa', '.vtt', '.lrc', '.txt'}
        return Path(file_path).suffix.lower() in subtitle_extensions
    
    def detect_file_content_format(self, file_path):
        """检测文件内容格式"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
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

    def clean_subtitle_filename(self, filename):
        patterns_to_remove = [
            r'_轨道\d+',           # _轨道3
            r'_track\d+',          # _track3  
            r'\[.*?\]',            # [chi] 或任何方括号内容
            r'\(\d+\)',            # (1) 数字括号
            r'\.\w{2,3}$'          # 语言代码如 .chi .eng
        ]
        cleaned = filename
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned)
        cleaned = re.sub(r'_{2,}', '_', cleaned)
        cleaned = re.sub(r' - $', '', cleaned)
        cleaned = re.sub(r'__+', '_', cleaned)
        cleaned = cleaned.strip(' _-')
        return cleaned

    def detect_subtitle_language(self, subtitle_path):
        subtitle_path = Path(subtitle_path)
        filename = subtitle_path.stem.lower()
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
                if pattern in filename:
                    return lang_code
        return 'chi'

    def get_download_directory(self):
        try:
            if os.name == 'nt':
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                    r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders')
                downloads_path, _ = winreg.QueryValueEx(key, '{374DE290-123F-4565-9164-39C4925E467B}')
                return Path(downloads_path)
            elif sys.platform == 'darwin':
                return Path.home() / 'Downloads'
            else:
                return Path.home() / 'Downloads'
        except Exception:
            return None

    def find_video_by_subtitle(self, subtitle_path):
        subtitle_path = Path(subtitle_path)
        subtitle_stem = subtitle_path.stem
        current_dir = subtitle_path.parent
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
        print(f"查找与字幕文件匹配的视频: {subtitle_path.name}")
        for ext in video_extensions:
            video_file = current_dir / f"{subtitle_stem}{ext}"
            if video_file.exists():
                print(f"✓ 精确匹配找到视频: {video_file.name}")
                return video_file
        clean_stem = self.clean_subtitle_filename(subtitle_stem)
        if clean_stem and clean_stem != subtitle_stem:
            for ext in video_extensions:
                video_file = current_dir / f"{clean_stem}{ext}"
                if video_file.exists():
                    print(f"✓ 模糊匹配找到视频: {video_file.name}")
                    return video_file
        advanced_matches = self.advanced_video_matching(subtitle_stem, current_dir, video_extensions)
        if advanced_matches:
            return advanced_matches[0]
        download_dir = self.get_download_directory()
        if download_dir and download_dir.exists():
            print(f"在当前目录未找到，尝试在下载目录中查找: {download_dir}")
            for ext in video_extensions:
                video_file = download_dir / f"{subtitle_stem}{ext}"
                if video_file.exists():
                    print(f"✓ 在下载目录中精确匹配找到视频: {video_file.name}")
                    return video_file
            if clean_stem and clean_stem != subtitle_stem:
                for ext in video_extensions:
                    video_file = download_dir / f"{clean_stem}{ext}"
                    if video_file.exists():
                        print(f"✓ 在下载目录中模糊匹配找到视频: {video_file.name}")
                        return video_file
            advanced_matches_download = self.advanced_video_matching(subtitle_stem, download_dir, video_extensions)
            if advanced_matches_download:
                print(f"✓ 在下载目录中高级匹配找到视频: {advanced_matches_download[0].name}")
                return advanced_matches_download[0]
        return None

    def advanced_video_matching(self, subtitle_stem, current_dir, video_extensions):
        matches = []
        # 使用集合避免重复收集同一文件（Windows文件系统不区分大小写）
        video_files = set()
        for ext in video_extensions:
            # 只需要查找小写扩展名，因为glob在Windows上不区分大小写
            video_files.update(current_dir.glob(f"*{ext}"))
        if not video_files:
            return []
        subtitle_clean = self.clean_subtitle_filename(subtitle_stem).lower()
        for video_file in video_files:
            video_stem = video_file.stem
            video_clean = self.clean_subtitle_filename(video_stem).lower()
            # 检查文件是否已经在匹配列表中
            if video_file in matches:
                continue
            # 精确匹配优先
            if subtitle_clean == video_clean:
                matches.append(video_file)
                continue
            # 包含关系匹配
            if subtitle_clean in video_clean or video_clean in subtitle_clean:
                matches.append(video_file)
                continue
            # 更严格的公共部分匹配：要求至少有2个公共部分，且占总部分的70%以上
            subtitle_parts = [part for part in re.split(r'[_\-\s\.\(\)\[\]]+', subtitle_clean) if part]
            video_parts = [part for part in re.split(r'[_\-\s\.\(\)\[\]]+', video_clean) if part]
            if subtitle_parts and video_parts:
                common_parts = set(subtitle_parts) & set(video_parts)
                if len(common_parts) >= 2 and len(common_parts) >= max(2, min(len(subtitle_parts), len(video_parts)) * 0.7):
                    matches.append(video_file)
                    continue
            # 改进的艺术家歌曲模式匹配：要求艺术家或歌曲名至少有50%的字符匹配
            if self.match_artist_song_pattern(subtitle_clean, video_clean):
                matches.append(video_file)
        # 对匹配结果进行排序，分数高的排在前面
        matches.sort(key=lambda x: self.calculate_match_score(subtitle_clean, x.stem.lower()), reverse=True)
        # 去重，确保每个文件只出现一次
        unique_matches = []
        seen_files = set()
        for match in matches:
            # 使用文件的绝对路径作为唯一标识
            file_key = str(match.absolute())
            if file_key not in seen_files:
                seen_files.add(file_key)
                unique_matches.append(match)
        matches = unique_matches
        if matches:
            print(f"✓ 高级匹配找到 {len(matches)} 个候选视频")
            for i, match in enumerate(matches[:3]):
                print(f"  候选 {i+1}: {match.name}")
        return matches

    def match_artist_song_pattern(self, subtitle_clean, video_clean):
        patterns = [
            r'(.+?)\s*-\s*(.+)',  # "Artist - Song"
            r'(.+?)\s*_\s*(.+)',  # "Artist_Song"
        ]
        for pattern in patterns:
            sub_match = re.match(pattern, subtitle_clean)
            vid_match = re.match(pattern, video_clean)
            if sub_match and vid_match:
                sub_artist, sub_song = sub_match.groups()
                vid_artist, vid_song = vid_match.groups()
                
                # 计算字符串相似度，要求至少50%匹配
                def calculate_similarity(str1, str2):
                    if not str1 or not str2:
                        return 0.0
                    # 使用集合计算交集
                    intersection = set(str1) & set(str2)
                    # 使用最长字符串长度作为分母
                    max_len = max(len(str1), len(str2))
                    return len(intersection) / max_len
                
                # 要求艺术家或歌曲名至少有50%的字符匹配
                artist_similarity = calculate_similarity(sub_artist, vid_artist)
                song_similarity = calculate_similarity(sub_song, vid_song)
                
                if artist_similarity >= 0.5 or song_similarity >= 0.5:
                    return True
        return False

    def calculate_match_score(self, subtitle_clean, video_stem):
        if not subtitle_clean or not video_stem:
            return 0
        
        score = 0
        
        # 1. 精确匹配奖励
        if subtitle_clean == video_stem:
            return 1000
        
        # 2. 长度差异惩罚（更严格）
        length_diff = abs(len(subtitle_clean) - len(video_stem))
        max_len = max(len(subtitle_clean), len(video_stem))
        length_ratio = length_diff / max_len if max_len > 0 else 0
        score -= length_ratio * 50
        
        # 3. 前缀匹配奖励（连续匹配更重要）
        min_len = min(len(subtitle_clean), len(video_stem))
        prefix_score = 0
        for i in range(min_len):
            if subtitle_clean[i] == video_stem[i]:
                prefix_score += 5  # 连续匹配字符奖励更高
            else:
                break  # 停止计数不连续的匹配
        score += prefix_score
        
        # 4. 公共字符奖励（考虑字符频率）
        common_chars = set(subtitle_clean) & set(video_stem)
        if common_chars:
            common_ratio = len(common_chars) / max_len
            score += common_ratio * 30
        
        # 5. 整体相似度（使用编辑距离概念）
        # 简化的编辑距离计算：计算相同字符的位置数量
        match_positions = 0
        for char in common_chars:
            match_positions += min(subtitle_clean.count(char), video_stem.count(char))
        similarity = match_positions / max_len if max_len > 0 else 0
        score += similarity * 20
        
        return score

    def manual_select_video(self, directory):
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
        video_files = [f for f in directory.iterdir() if f.is_file() and f.suffix.lower() in video_extensions]
        if not video_files:
            print("× 目录中未找到任何视频文件")
            return None
        print("\n目录中找到以下视频文件:")
        for i, video_file in enumerate(video_files, 1):
            print(f"  {i}. {video_file.name}")
        print(" 0. 跳过视频选择，仅转换字幕")
        while True:
            try:
                choice = input("\n请选择视频文件（输入编号）: ").strip()
                if not choice:
                    print("使用第一个视频文件")
                    return video_files[0]
                if choice == '0':
                    print("跳过视频选择，仅进行字幕转换")
                    return None
                if choice.isdigit():
                    index = int(choice) - 1
                    if 0 <= index < len(video_files):
                        selected_file = video_files[index]
                        print(f"✓ 选择视频: {selected_file.name}")
                        return selected_file
                    else:
                        print(f"请输入 0-{len(video_files)} 之间的数字")
                else:
                    matched_files = [f for f in video_files if choice.lower() in f.name.lower()]
                    if matched_files:
                        if len(matched_files) == 1:
                            print(f"✓ 找到匹配视频: {matched_files[0].name}")
                            return matched_files[0]
                        else:
                            print(f"找到多个匹配文件:")
                            for i, f in enumerate(matched_files, 1):
                                print(f"  {i}. {f.name}")
                            sub_choice = input("请选择（输入编号）: ").strip()
                            if sub_choice.isdigit():
                                sub_index = int(sub_choice) - 1
                                if 0 <= sub_index < len(matched_files):
                                    return matched_files[sub_index]
                    else:
                        print("未找到匹配文件，请重新选择")
            except (ValueError, IndexError):
                print("无效选择，请重新输入")

    def generate_incremental_filename(self, input_path, marker, extension, output_dir=None):
        input_path = Path(input_path)
        stem = input_path.stem
        # 清理stem，移除现有的标记和计数器
        clean_stem = re.sub(rf'{re.escape(marker)}\s*(\(\d+\))?\s*$', '', stem).strip()
        clean_stem = re.sub(r'\s+\(\d+\)\s*$', '', clean_stem).strip()
        # 处理(ASS)标记
        if ' (ASS)' in clean_stem:
            clean_stem = clean_stem.replace(' (ASS)', '')
        # 处理(ASS_1)标记
        if ' (ASS_1)' in clean_stem:
            clean_stem = clean_stem.replace(' (ASS_1)', '')
        counter = 1
        # 确定检查目录
        check_dir = Path(output_dir) if output_dir else input_path.parent
        while True:
            if counter == 1:
                new_filename = f"{clean_stem}{marker}{extension}"
            else:
                new_filename = f"{clean_stem}{marker} ({counter}){extension}"
            new_path = check_dir / new_filename
            if not new_path.exists():
                return new_path
            counter += 1

    def process_output_video_filename(self, input_path, karaoke_mode=True, real_karaoke_effect=0, output_dir=None):
        input_path = Path(input_path)
        stem = input_path.stem
        
        # 根据real_karaoke_effect确定目标标记
        if real_karaoke_effect == 'A' or real_karaoke_effect == -1 or str(real_karaoke_effect) == '-1':  # 全选模式
            # 全选模式：使用 (ASS) 标记
            target_marker = ' (ASS)'
            # 替换所有标记 (SRT) 和 (SSA) 为 (ASS)
            new_stem = stem
            for replace_marker in OUTPUT_REPLACE_MARKERS:
                if replace_marker in new_stem:
                    new_stem = new_stem.replace(replace_marker, target_marker)
                    break
            if new_stem == stem:
                new_stem = stem + target_marker
        elif real_karaoke_effect == 1 or real_karaoke_effect == 2 or str(real_karaoke_effect) in ['1', '2']:  # KTV效果或提词器效果
            # 非默认效果：使用 (ASS_1) 标记
            target_marker = ' (ASS_1)'
            # 替换所有标记 (SRT) 和 (SSA) 为 (ASS_1)
            new_stem = stem
            for replace_marker in OUTPUT_REPLACE_MARKERS:
                if replace_marker in new_stem:
                    new_stem = new_stem.replace(replace_marker, target_marker)
                    break
            if new_stem == stem:
                new_stem = stem + target_marker
        else:  # 默认效果
            if karaoke_mode:
                target_marker = KARAOKE_SUFFIX
            else:
                target_marker = NO_KARAOKE_SUFFIX
            # 如果是默认效果源文件带(ASS) 则无需添加(ASS)
            if ' (ASS)' in stem and karaoke_mode:
                new_stem = stem
            else:
                new_stem = stem
                for replace_marker in OUTPUT_REPLACE_MARKERS:
                    if replace_marker in new_stem:
                        new_stem = new_stem.replace(replace_marker, target_marker)
                        break
                if new_stem == stem and karaoke_mode:
                    new_stem = f"{stem}{target_marker}"
        
        # 检查输出目录是否指定
        if output_dir:
            output_dir = Path(output_dir)
            output_path = output_dir / f"{new_stem}.mkv"
        else:
            output_dir = input_path.parent
            output_path = output_dir / f"{new_stem}.mkv"
        
        # 检查文件是否存在，如果存在则生成递增文件名
        if output_path.exists():
            # 直接在输出目录生成递增文件名
            return self.generate_incremental_filename(input_path, target_marker, '.mkv', output_dir)
        return output_path

    def process_output_filename(self, input_path, karaoke_mode=False, is_batch=False, real_karaoke_effect=0, output_dir=None):
        input_path = Path(input_path)
        stem = input_path.stem
        
        # 根据real_karaoke_effect确定目标标记
        if real_karaoke_effect == 'A' or real_karaoke_effect == -1 or str(real_karaoke_effect) == '-1':  # 全选模式
            # 全选模式：使用 (ASS) 标记
            target_marker = ' (ASS)'
            # 替换所有标记 (SRT) 和 (SSA) 为 (ASS)
            new_stem = stem
            for replace_marker in OUTPUT_REPLACE_MARKERS:
                if replace_marker in new_stem:
                    new_stem = new_stem.replace(replace_marker, target_marker)
                    break
            if new_stem == stem:
                new_stem = stem + target_marker
        elif real_karaoke_effect == 1 or real_karaoke_effect == 2 or str(real_karaoke_effect) in ['1', '2']:  # KTV效果或提词器效果
            # 非默认效果：使用 (ASS_1) 标记
            target_marker = ' (ASS_1)'
            # 替换所有标记 (SRT) 和 (SSA) 为 (ASS_1)
            new_stem = stem
            for replace_marker in OUTPUT_REPLACE_MARKERS:
                if replace_marker in new_stem:
                    new_stem = new_stem.replace(replace_marker, target_marker)
                    break
            if new_stem == stem:
                new_stem = stem + target_marker
        else:  # 默认效果
            if karaoke_mode:
                target_marker = KARAOKE_SUFFIX
            else:
                target_marker = NO_KARAOKE_SUFFIX
            # 如果是默认效果源文件带(ASS) 则无需添加(ASS)
            if ' (ASS)' in stem and karaoke_mode:
                new_stem = stem
            else:
                new_stem = stem
                for replace_marker in OUTPUT_REPLACE_MARKERS:
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
            output_dir = input_path.parent
            output_path = output_dir / f"{new_stem}.ass"
        
        # 与原文件重名则在后面 添加（1）序列号（）
        if output_path.exists():
            return self.generate_incremental_filename(input_path, target_marker, '.ass', output_dir)
        return output_path

    def get_subtitle_converter(self):
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("c", self.mkv_packer_path)
            c_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(c_module)
            return c_module.SubtitleConverter()
        except Exception as e:
            print(f"导入字幕转换器失败: {e}")
            return SimpleSubtitleConverter()

    def convert_subtitle_only(self, subtitle_path, karaoke_effect=True, output_dir=None, real_karaoke_effect=0):
        subtitle_path = Path(subtitle_path)
        if output_dir is None:
            output_dir = subtitle_path.parent
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        print("=" * 60)
        print("字幕文件转换模式")
        print("=" * 60)
        print(f"输入字幕: {subtitle_path.name}")
        print(f"卡拉OK效果: {'开启' if karaoke_effect else '关闭'}")
        if real_karaoke_effect == 'A':
            print(f"真实卡拉OK效果: 全部效果打包")
        else:
            print(f"真实卡拉OK效果: {'KTV效果' if real_karaoke_effect == 1 or real_karaoke_effect == '1' else '提词器效果' if real_karaoke_effect == 2 or real_karaoke_effect == '2' else '默认'}")
        print(f"输出目录: {output_dir}")
        try:
            converter = self.get_subtitle_converter()
            output_filename = converter.process_output_filename(subtitle_path, karaoke_effect, False, real_karaoke_effect)
            if output_filename is None:
                output_filename = subtitle_path.parent / f"{subtitle_path.stem}_converted.ass"
            output_path = output_dir / output_filename.name
            print(f"转换字幕: {subtitle_path.name} -> {output_path.name}")
            result = converter.convert_subtitle(
                subtitle_path, 
                output_path, 
                enable_custom_font=True,
                karaoke_mode=karaoke_effect,
                is_batch=False,
                real_karaoke_effect=real_karaoke_effect
            )
            if result:
                print(f"\n✓ 字幕转换完成: {result}")
                return {
                    'input_subtitle': subtitle_path,
                    'output_subtitle': result,
                    'karaoke_effect': karaoke_effect,
                    'real_karaoke_effect': real_karaoke_effect
                }
            else:
                print("× 字幕转换失败")
                return None
        except Exception as e:
            print(f"× 字幕转换失败: {e}")
            return None

    def get_media_info_with_mkvmerge(self, video_path):
        try:
            if not self.check_mkvtoolnix_available():
                return {'subtitle_tracks': []}
            cmd = [self.mkvmerge_path, '--identification-format', 'json', '--identify', str(video_path)]
            returncode, stdout, stderr = self.run_command_safe(cmd, timeout=60)
            if returncode == 0 and stdout:
                try:
                    info = json.loads(stdout)
                    return self.parse_mkvmerge_json_info(info)
                except json.JSONDecodeError:
                    print("mkvmerge JSON 解析失败，使用文本模式")
                    return self.parse_mkvmerge_text_info(video_path)
            else:
                print(f"mkvmerge JSON 模式失败: {stderr}")
                return self.parse_mkvmerge_text_info(video_path)
        except Exception as e:
            print(f"mkvmerge 获取媒体信息失败: {e}")
            return {'subtitle_tracks': []}

    def parse_mkvmerge_json_info(self, info):
        subtitle_tracks = []
        if 'tracks' in info:
            for track in info['tracks']:
                if track.get('type') == 'subtitles':
                    track_id = str(track.get('id'))
                    language = track.get('properties', {}).get('language', 'und')
                    if language == 'und' and 'language_ietf' in track.get('properties', {}):
                        language = track.get('properties', {}).get('language_ietf', 'und')
                    is_default = track.get('properties', {}).get('default_track', False)
                    codec = track.get('codec', 'unknown')
                    track_name = track.get('properties', {}).get('track_name', '')
                    subtitle_tracks.append({
                        'track_id': track_id,
                        'language': language,
                        'default': is_default,
                        'codec': codec,
                        'track_name': track_name
                    })
        subtitle_tracks.sort(key=lambda x: int(x['track_id']) if x['track_id'].isdigit() else 0)
        return {'subtitle_tracks': subtitle_tracks}

    def parse_mkvmerge_text_info(self, video_path):
        try:
            cmd = [self.mkvmerge_path, '-i', str(video_path)]
            returncode, stdout, stderr = self.run_command_safe(cmd)
            if returncode != 0:
                return {'subtitle_tracks': []}
            subtitle_tracks = []
            lines = stdout.split('\n')
            for line in lines:
                line = line.strip()
                if 'subtitles' in line.lower():
                    track_match = re.search(r'Track ID (\d+):', line)
                    if track_match:
                        track_id = track_match.group(1)
                        language = 'und'
                        lang_match = re.search(r'language:([a-z]{2,3})', line, re.IGNORECASE)
                        if lang_match:
                            language = lang_match.group(1).lower()
                        is_default = 'default track: yes' in line.lower()
                        track_name = ''
                        name_match = re.search(r'name:([^,]+)', line, re.IGNORECASE)
                        if name_match:
                            track_name = name_match.group(1).strip()
                        subtitle_tracks.append({
                            'track_id': track_id,
                            'language': language,
                            'default': is_default,
                            'track_name': track_name
                        })
            subtitle_tracks.sort(key=lambda x: int(x['track_id']) if x['track_id'].isdigit() else 0)
            return {'subtitle_tracks': subtitle_tracks}
        except Exception as e:
            print(f"mkvmerge 文本解析失败: {e}")
            return {'subtitle_tracks': []}

    def extract_subtitle_with_mkvextract(self, video_path, track_id, output_path):
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if output_path.exists():
                output_path.unlink()
            # 检测mkvextract路径
            mkvextract_path = self.mkvmerge_path.replace('mkvmerge.exe', 'mkvextract.exe')
            if not os.path.exists(mkvextract_path):
                mkvextract_path = 'mkvextract'
            cmd = [
                mkvextract_path, 'tracks', str(video_path),
                f"{track_id}:{output_path}"
            ]
            returncode, stdout, stderr = self.run_command_safe(cmd, timeout=60, capture_output=False)
            if returncode == 0 and output_path.exists():
                return True
            else:
                print(f"mkvextract 提取失败: {stderr}")
                return False
        except Exception as e:
            print(f"mkvextract 提取字幕轨道 {track_id} 失败: {e}")
            return False

    def extract_all_internal_subtitles(self, video_path):
        print("使用 MKVToolNix 分析媒体文件信息...")
        media_info = self.get_media_info_with_mkvmerge(video_path)
        subtitle_tracks_info = media_info.get('subtitle_tracks', [])
        if not subtitle_tracks_info:
            print("未检测到内置字幕轨道")
            return []
        print(f"检测到 {len(subtitle_tracks_info)} 个字幕轨道")
        
        # 检查文件名是否包含 (ASS) 标签
        video_path = Path(video_path)
        is_ass_a_file = '(ASS)' in video_path.name
        
        # 过滤字幕轨道：如果是 (ASS) 文件，忽略 KTV 和提词器效果字幕
        filtered_tracks_info = []
        if is_ass_a_file:
            print("\n检测到 (ASS) 文件，应用多效果逻辑...")
            for track in subtitle_tracks_info:
                track_name = track.get('track_name', '').lower()
                # 忽略 KTV 效果和提词器效果的字幕轨道
                if 'ktv' not in track_name and '提词器' not in track_name and 'prompter' not in track_name:
                    filtered_tracks_info.append(track)
                    print(f"  保留轨道 {track['track_id']}: 名称='{track.get('track_name', '')}'")
                else:
                    print(f"  忽略轨道 {track['track_id']}: 名称='{track.get('track_name', '')}'")
            
            # 如果过滤后没有轨道，保留所有轨道
            if not filtered_tracks_info:
                print("  过滤后没有轨道，保留所有轨道")
                filtered_tracks_info = subtitle_tracks_info
        else:
            filtered_tracks_info = subtitle_tracks_info
        
        # 提取过滤后的字幕轨道
        extracted_subtitles = []
        for track_info in filtered_tracks_info:
            track_id = track_info['track_id']
            language = track_info['language']
            is_default = track_info['default']
            track_name = track_info.get('track_name', '')
            if language == 'und':
                language = 'chi'
                track_info['language'] = language
            print(f"处理字幕轨道 {track_id}: 语言={language}, 默认={is_default}, 名称='{track_name}'")
            output_subtitle = self.cache_dir / f"subtitle_{track_id}_{language}.ass"
            if self.extract_subtitle_with_mkvextract(video_path, track_id, output_subtitle):
                track_info['path'] = output_subtitle
                extracted_subtitles.append(track_info)
                print(f"✓ 成功提取字幕轨道 {track_id}")
            else:
                print(f"× 提取字幕轨道 {track_id} 失败")
        return extracted_subtitles

    def _validate_audio_file(self, audio_path, min_size=1000):
        """验证音频文件是否有效"""
        audio_path = Path(audio_path)
        if not audio_path.exists():
            return False, "文件不存在"
        if audio_path.stat().st_size < min_size:
            return False, f"文件大小太小 ({audio_path.stat().st_size} bytes)"
        try:
            import struct
            with open(audio_path, 'rb') as f:
                header = f.read(12)
                if len(header) < 12:
                    return False, "文件太短，无法读取头部"
                if header[0:4] == b'RIFF' and header[8:12] == b'WAVE':
                    return True, "WAV格式有效"
                elif header[0:4] in [b'\xff\xfb', b'\xff\xf3', b'\ff\xf2', b'ID3', b'\x00\x00']:
                    return True, "MP3/其他音频格式有效"
                else:
                    return True, "文件存在且有内容"
        except Exception as e:
            return False, f"验证失败: {e}"

    def extract_audio_for_calibration(self, video_path, use_vocal_separation=True):
        video_path = Path(video_path)
        if use_vocal_separation and self.voice_separator.demucs_available:
            output_audio_path = self.cache_dir / f"{video_path.stem}_vocal_calibration.wav"
            print("启用人声分离功能...")
            try:
                if output_audio_path.exists():
                    try:
                        output_audio_path.unlink()
                    except:
                        pass
                temp_audio = self.cache_dir / "temp_audio.wav"

                if not self.extract_audio_with_ffmpeg(video_path, temp_audio):
                    print("FFmpeg提取失败，使用原始音频")
                    return self.extract_audio_for_calibration(video_path, False)

                is_valid, msg = self._validate_audio_file(temp_audio)
                if not is_valid:
                    print(f"临时音频文件无效: {msg}，使用原始音频")
                    return self.extract_audio_for_calibration(video_path, False)

                vocal_audio = self.voice_separator.separate_voice(temp_audio, output_audio_path)

                if temp_audio.exists():
                    try:
                        temp_audio.unlink()
                    except:
                        pass

                is_valid, msg = self._validate_audio_file(output_audio_path)
                if not is_valid:
                    print(f"人声音频文件无效: {msg}，使用原始音频")
                    return self.extract_audio_for_calibration(video_path, False)

                print(f"提取人声音频: {output_audio_path}")
                return output_audio_path
            except Exception as e:
                print(f"人声分离失败: {e}，使用原始音频")
                return self.extract_audio_for_calibration(video_path, False)
        else:
            output_audio_path = self.cache_dir / f"{video_path.stem}_calibration.wav"
            try:
                if output_audio_path.exists():
                    try:
                        output_audio_path.unlink()
                    except:
                        pass

                if not self.extract_audio_with_ffmpeg(video_path, output_audio_path):
                    print("FFmpeg提取失败")
                    return None

                is_valid, msg = self._validate_audio_file(output_audio_path)
                if not is_valid:
                    print(f"音频文件无效: {msg}")
                    return None

                print(f"提取校准用音频: {output_audio_path}")
                return output_audio_path
            except Exception as e:
                print(f"音频提取失败: {e}")
                return None

    def validate_output_dir(self, user_output_dir, default_output_dir, input_path=None):
        if user_output_dir is None:
            print(f"使用默认输出目录: {default_output_dir}")
            return default_output_dir
        if isinstance(user_output_dir, Path):
            user_output_dir = str(user_output_dir)
        elif isinstance(user_output_dir, str):
            user_output_dir = user_output_dir.strip('"\'')
        else:
            print(f"⚠️ 警告：输出目录类型未知: {type(user_output_dir)}")
            print(f"   将使用默认输出目录: {default_output_dir}")
            return default_output_dir
        if not user_output_dir or user_output_dir.strip() == "":
            print(f"使用默认输出目录: {default_output_dir}")
            return default_output_dir
        if (len(user_output_dir) <= 2 and 
            not os.path.isabs(user_output_dir) and 
            ':' not in user_output_dir and
            os.path.sep not in user_output_dir):
            print(f"⚠️ 警告：输出目录 '{user_output_dir}' 看起来像是错误输入")
            print(f"   将使用默认输出目录: {default_output_dir}")
            return default_output_dir
        try:
            output_path = Path(user_output_dir)
            if not output_path.is_absolute():
                if input_path:
                    output_path = input_path.parent / user_output_dir
                else:
                    output_path = Path.cwd() / user_output_dir
            try:
                output_path.mkdir(parents=True, exist_ok=True)
                test_file = output_path / ".write_test"
                try:
                    test_file.touch()
                    test_file.unlink()
                    print(f"✓ 输出目录有效: {output_path}")
                    return output_path
                except:
                    print(f"⚠️ 警告：无法写入到目录 '{output_path}'")
                    print(f"   将使用默认输出目录: {default_output_dir}")
                    return default_output_dir
            except Exception as e:
                print(f"⚠️ 警告：无法创建输出目录 '{output_path}': {e}")
                print(f"   将使用默认输出目录: {default_output_dir}")
                return default_output_dir
        except Exception as e:
            print(f"⚠️ 警告：输出目录解析失败: {e}")
            print(f"   将使用默认输出目录: {default_output_dir}")
            return default_output_dir

    def process_with_external_subtitle(self, video_path, subtitle_path, karaoke_effect=True, output_dir=None, enable_packing=True, enable_custom_font=True, use_vocal_separation=True, real_karaoke_effect=False):
        video_path = Path(video_path)
        subtitle_path = Path(subtitle_path)
        
        # 检查文件是否包含(ASS_1)标签
        has_ass1_tag = ' (ASS_1)' in video_path.name or ' (ASS_1)' in subtitle_path.name
        if has_ass1_tag:
            print("⚠️  检测到(ASS_1)标签，暂时不支持效果转换")
            # 跳过效果转换，但保留其他操作
            karaoke_effect = False
            real_karaoke_effect = 0
        
        default_output_dir = video_path.parent
        output_dir = self.validate_output_dir(output_dir, default_output_dir, video_path)
        print("=" * 60)
        print("外部字幕文件处理模式")
        print("=" * 60)
        print(f"视频文件: {video_path.name}")
        print(f"字幕文件: {subtitle_path.name}")
        print(f"卡拉OK效果: {'开启' if karaoke_effect else '关闭'}")
        if real_karaoke_effect == 'A':
            print(f"真实卡拉OK效果: 全部效果打包")
        else:
            print(f"真实卡拉OK效果: {'KTV效果' if real_karaoke_effect == 1 or real_karaoke_effect == '1' else '提词器效果' if real_karaoke_effect == 2 or real_karaoke_effect == '2' else '默认'}")
        print(f"MKV打包: {'开启' if enable_packing else '关闭'}")
        print(f"输出目录: {output_dir}")
        subtitle_language = 'chi'
        print(f"字幕语言: {self.get_language_name(subtitle_language)}")
        print("\n步骤1: 提取音频用于字幕校准")
        print("-" * 30)
        calibration_audio = self.extract_audio_for_calibration(video_path, use_vocal_separation)
        if not calibration_audio:
            print("音频提取失败，无法进行字幕校准")
            return None
        print("\n步骤2: 字幕校准")
        print("-" * 30)
        calibrated_subtitle_path = self.cache_dir / f"calibrated_{subtitle_path.stem}.ass"
        if calibrated_subtitle_path.exists():
            try:
                calibrated_subtitle_path.unlink()
            except:
                pass
        if not subtitle_path.exists():
            raise FileNotFoundError(f"字幕文件不存在: {subtitle_path}，无法继续处理")
        calibrated_subtitle = self.call_subtitle_calibrator(
            calibration_audio, subtitle_path, calibrated_subtitle_path, not karaoke_effect
        )
        if not calibrated_subtitle:
            raise RuntimeError("字幕校准失败，无法继续处理")
        print("\n步骤3: 卡拉OK转换")
        print("-" * 30)
        # 处理卡拉OK转换
        final_subtitles = []
        if karaoke_effect:
            if str(real_karaoke_effect) == 'A':  # 全选模式，生成所有效果
                print("\n启用全选模式，生成所有卡拉OK效果...")
                
                # 生成默认效果
                print("\n1. 生成默认效果...")
                karaoke_subtitle_path_0 = self.cache_dir / f"karaoke_default_{subtitle_path.stem}.ass"
                if karaoke_subtitle_path_0.exists():
                    karaoke_subtitle_path_0.unlink()
                default_subtitle = self.call_karaoke_converter(
                    calibrated_subtitle, calibration_audio, karaoke_subtitle_path_0, karaoke_effect=True
                )
                if default_subtitle:
                    final_subtitles.append({
                        'language': subtitle_language,
                        'final_subtitle': default_subtitle,
                        'is_default': True,
                        'original_track_id': '1',
                        'effect': 'default'
                    })
                
                # 生成KTV效果
                print("\n2. 生成KTV效果...")
                ktv_subtitle = self.process_real_karaoke(
                    calibrated_subtitle, calibration_audio, None
                )
                if not ktv_subtitle:
                    print("KTV效果处理失败，使用标准卡拉OK流程")
                    karaoke_subtitle_path_1 = self.cache_dir / f"karaoke_ktv_{subtitle_path.stem}.ass"
                    if karaoke_subtitle_path_1.exists():
                        karaoke_subtitle_path_1.unlink()
                    ktv_subtitle = self.call_karaoke_converter(
                        calibrated_subtitle, calibration_audio, karaoke_subtitle_path_1, karaoke_effect=True
                    )
                if ktv_subtitle:
                    final_subtitles.append({
                        'language': subtitle_language,
                        'final_subtitle': ktv_subtitle,
                        'is_default': False,
                        'original_track_id': '2',
                        'effect': 'ktv'
                    })
                
                # 生成提词器效果
                print("\n3. 生成提词器效果...")
                prompter_subtitle = self.process_prompter_effect(
                    calibrated_subtitle, calibration_audio, None
                )
                if not prompter_subtitle:
                    print("提词器效果处理失败，使用标准卡拉OK流程")
                    karaoke_subtitle_path_2 = self.cache_dir / f"karaoke_prompter_{subtitle_path.stem}.ass"
                    if karaoke_subtitle_path_2.exists():
                        karaoke_subtitle_path_2.unlink()
                    prompter_subtitle = self.call_karaoke_converter(
                        calibrated_subtitle, calibration_audio, karaoke_subtitle_path_2, karaoke_effect=True
                    )
                if prompter_subtitle:
                    final_subtitles.append({
                        'language': subtitle_language,
                        'final_subtitle': prompter_subtitle,
                        'is_default': False,
                        'original_track_id': '3',
                        'effect': 'prompter'
                    })
                
                # 如果没有生成任何字幕，使用校准后的字幕
                if not final_subtitles:
                    print("所有卡拉OK效果生成失败，使用校准后的字幕")
                    final_subtitles.append({
                        'language': subtitle_language,
                        'final_subtitle': calibrated_subtitle,
                        'is_default': True,
                        'original_track_id': '1',
                        'effect': 'default'
                    })
            elif real_karaoke_effect == 1:  # 真实卡拉OK效果
                print("启用真实卡拉OK效果处理流程...")
                final_subtitle = self.process_real_karaoke(
                    calibrated_subtitle, calibration_audio, None
                )
                if not final_subtitle:
                    print("真实卡拉OK处理失败，使用标准卡拉OK流程")
                    karaoke_subtitle_path = self.cache_dir / f"karaoke_{subtitle_path.stem}.ass"
                    if karaoke_subtitle_path.exists():
                        karaoke_subtitle_path.unlink()
                    final_subtitle = self.call_karaoke_converter(
                        calibrated_subtitle, calibration_audio, karaoke_subtitle_path, karaoke_effect=True
                    )
                final_subtitles.append({
                    'language': subtitle_language,
                    'final_subtitle': final_subtitle,
                    'is_default': True,
                    'original_track_id': '1',
                    'effect': 'ktv'
                })
            elif real_karaoke_effect == 2:  # 提词器效果
                print("启用提词器效果处理流程...")
                final_subtitle = self.process_prompter_effect(
                    calibrated_subtitle, calibration_audio, None
                )
                if not final_subtitle:
                    print("提词器效果处理失败，使用标准卡拉OK流程")
                    karaoke_subtitle_path = self.cache_dir / f"karaoke_{subtitle_path.stem}.ass"
                    if karaoke_subtitle_path.exists():
                        karaoke_subtitle_path.unlink()
                    final_subtitle = self.call_karaoke_converter(
                        calibrated_subtitle, calibration_audio, karaoke_subtitle_path, karaoke_effect=True
                    )
                final_subtitles.append({
                    'language': subtitle_language,
                    'final_subtitle': final_subtitle,
                    'is_default': True,
                    'original_track_id': '1',
                    'effect': 'prompter'
                })
            else:  # 标准卡拉OK效果
                karaoke_subtitle_path = self.cache_dir / f"karaoke_{subtitle_path.stem}.ass"
                if karaoke_subtitle_path.exists():
                    karaoke_subtitle_path.unlink()
                final_subtitle = self.call_karaoke_converter(
                    calibrated_subtitle, calibration_audio, karaoke_subtitle_path, karaoke_effect=True
                )
                final_subtitles.append({
                    'language': subtitle_language,
                    'final_subtitle': final_subtitle,
                    'is_default': True,
                    'original_track_id': '1',
                    'effect': 'default'
                })
        else:
            # 不启用卡拉OK效果，只使用校准后的字幕
            final_subtitles.append({
                'language': subtitle_language,
                'final_subtitle': calibrated_subtitle,
                'is_default': True,
                'original_track_id': '1',
                'effect': 'none'
            })
        mkv_result = None
        if enable_packing:
            print("\n步骤4: MKV打包")
            print("-" * 30)
            output_mkv_path = self.process_output_video_filename(video_path, karaoke_effect, real_karaoke_effect, output_dir)
            output_mkv_path = output_dir / output_mkv_path.name
            
            # 调用字幕替换打包器，传递所有生成的字幕轨道
            mkv_result = self.call_mkv_packer_subtitles_only(
                video_path=video_path,
                subtitle_tracks=final_subtitles,
                output_path=output_mkv_path,
                enable_custom_font=enable_custom_font
            )
        result = {
            'input_video': video_path,
            'input_subtitle': subtitle_path,
            'final_subtitles': final_subtitles,
            'output_mkv': mkv_result,
            'output_dir': output_dir,
            'language': subtitle_language
        }
        print("\n" + "=" * 60)
        print("处理完成!")
        print("=" * 60)
        if mkv_result:
            print(f"输出视频: {mkv_result}")
        else:
            if final_subtitles:
                print(f"处理后的字幕轨道数量: {len(final_subtitles)}")
                for i, track in enumerate(final_subtitles):
                    print(f"  轨道{i+1}: {track['final_subtitle']}")
        return result

    def process_multilingual_subtitles(self, media_path, karaoke_effect=True, output_dir=None, enable_packing=True, enable_custom_font=True, use_vocal_separation=True, real_karaoke_effect=False):
        print("启用多语言字幕处理模式...")
        media_path = Path(media_path)
        default_output_dir = media_path.parent
        output_dir = self.validate_output_dir(output_dir, default_output_dir, media_path)
        print("\n步骤1: 提取所有字幕轨道")
        print("-" * 40)
        subtitle_tracks = self.extract_all_internal_subtitles(media_path)
        if not subtitle_tracks:
            print("未找到内置字幕轨道，尝试外部字幕...")
            return self.process_single_subtitle(media_path, karaoke_effect, output_dir, enable_packing, enable_custom_font, use_vocal_separation, real_karaoke_effect)
        print("\n步骤2: 提取音频用于字幕校准")
        print("-" * 40)
        calibration_audio = self.extract_audio_for_calibration(media_path, use_vocal_separation)
        if not calibration_audio:
            print("音频提取失败，无法进行字幕校准")
            return None
        print("\n检测到的字幕轨道:")
        for i, track in enumerate(subtitle_tracks):
            lang_name = self.get_language_name(track['language'])
            default_status = "默认" if track['default'] else "非默认"
            print(f"  {i+1}. 轨道{track['track_id']}: {lang_name} ({track['language']}), {default_status}")
        print("\n步骤3: 处理每个字幕轨道")
        print("-" * 40)
        processed_subtitles = []
        for track_info in subtitle_tracks:
            language = track_info['language']
            is_default = track_info['default']
            track_id = track_info['track_id']
            lang_name = self.get_language_name(track_info['language'])
            print(f"\n处理{lang_name}字幕轨道 (轨道{track_id}):")
            print(f"  3.1 字幕校准")
            calibrated_subtitle_path = self.cache_dir / f"calibrated_{language}_{track_id}.ass"
            if calibrated_subtitle_path.exists():
                try:
                    calibrated_subtitle_path.unlink()
                except:
                    pass
            subtitle_file_path = track_info.get('path')
            if not subtitle_file_path or not Path(subtitle_file_path).exists():
                raise FileNotFoundError(f"字幕文件不存在: {subtitle_file_path}，无法继续处理")
            calibrated_subtitle = self.call_subtitle_calibrator(
                calibration_audio, subtitle_file_path, calibrated_subtitle_path, not karaoke_effect
            )
            if not calibrated_subtitle:
                raise RuntimeError(f"{lang_name}字幕校准失败，无法继续处理")
            print(f"  3.2 卡拉OK转换")
            if karaoke_effect:
                if str(real_karaoke_effect) == 'A':  # 全选模式，生成所有效果
                    print(f"    启用全选模式，生成所有卡拉OK效果...")
                    
                    # 生成默认效果
                    print(f"    1. 生成默认效果...")
                    karaoke_subtitle_path_0 = self.cache_dir / f"karaoke_default_{language}_{track_id}.ass"
                    if karaoke_subtitle_path_0.exists():
                        karaoke_subtitle_path_0.unlink()
                    default_subtitle = self.call_karaoke_converter(
                        calibrated_subtitle, calibration_audio, karaoke_subtitle_path_0, karaoke_effect=True
                    )
                    if default_subtitle:
                        processed_subtitles.append({
                            'language': language,
                            'final_subtitle': default_subtitle,
                            'is_default': is_default,
                            'original_track_id': f'{track_id}_1',
                            'effect': 'default'
                        })
                    
                    # 生成KTV效果
                    print(f"    2. 生成KTV效果...")
                    ktv_subtitle = self.process_real_karaoke(
                        calibrated_subtitle, calibration_audio, None
                    )
                    if not ktv_subtitle:
                        print(f"    KTV效果处理失败，使用标准卡拉OK流程")
                        karaoke_subtitle_path_1 = self.cache_dir / f"karaoke_ktv_{language}_{track_id}.ass"
                        if karaoke_subtitle_path_1.exists():
                            karaoke_subtitle_path_1.unlink()
                        ktv_subtitle = self.call_karaoke_converter(
                            calibrated_subtitle, calibration_audio, karaoke_subtitle_path_1, karaoke_effect=True
                        )
                    if ktv_subtitle:
                        processed_subtitles.append({
                            'language': language,
                            'final_subtitle': ktv_subtitle,
                            'is_default': False,
                            'original_track_id': f'{track_id}_2',
                            'effect': 'ktv'
                        })
                    
                    # 生成提词器效果
                    print(f"    3. 生成提词器效果...")
                    prompter_subtitle = self.process_prompter_effect(
                        calibrated_subtitle, calibration_audio, None
                    )
                    if not prompter_subtitle:
                        print(f"    提词器效果处理失败，使用标准卡拉OK流程")
                        karaoke_subtitle_path_2 = self.cache_dir / f"karaoke_prompter_{language}_{track_id}.ass"
                        if karaoke_subtitle_path_2.exists():
                            karaoke_subtitle_path_2.unlink()
                        prompter_subtitle = self.call_karaoke_converter(
                            calibrated_subtitle, calibration_audio, karaoke_subtitle_path_2, karaoke_effect=True
                        )
                    if prompter_subtitle:
                        processed_subtitles.append({
                            'language': language,
                            'final_subtitle': prompter_subtitle,
                            'is_default': False,
                            'original_track_id': f'{track_id}_3',
                            'effect': 'prompter'
                        })
                    
                    # 如果没有生成任何字幕，使用校准后的字幕
                    if not processed_subtitles or all(track['original_track_id'].split('_')[0] != str(track_id) for track in processed_subtitles):
                        print(f"    所有卡拉OK效果生成失败，使用校准后的字幕")
                        processed_subtitles.append({
                            'language': language,
                            'final_subtitle': calibrated_subtitle,
                            'is_default': is_default,
                            'original_track_id': f'{track_id}_1',
                            'effect': 'default'
                        })
                elif real_karaoke_effect == 1:  # 真实卡拉OK效果
                    print(f"    启用真实卡拉OK效果处理流程...")
                    final_subtitle = self.process_real_karaoke(
                        calibrated_subtitle, calibration_audio, None
                    )
                    if not final_subtitle:
                        print(f"    真实卡拉OK处理失败，使用标准卡拉OK流程")
                        karaoke_subtitle_path = self.cache_dir / f"karaoke_{language}_{track_id}.ass"
                        if karaoke_subtitle_path.exists():
                            karaoke_subtitle_path.unlink()
                        final_subtitle = self.call_karaoke_converter(
                            calibrated_subtitle, calibration_audio, karaoke_subtitle_path, karaoke_effect=True
                        )
                    processed_subtitles.append({
                        'language': language,
                        'final_subtitle': final_subtitle,
                        'is_default': is_default,
                        'original_track_id': track_id,
                        'effect': 'ktv'
                    })
                elif real_karaoke_effect == 2:  # 提词器效果
                    print(f"    启用提词器效果处理流程...")
                    final_subtitle = self.process_prompter_effect(
                        calibrated_subtitle, calibration_audio, None
                    )
                    if not final_subtitle:
                        print(f"    提词器效果处理失败，使用标准卡拉OK流程")
                        karaoke_subtitle_path = self.cache_dir / f"karaoke_{language}_{track_id}.ass"
                        if karaoke_subtitle_path.exists():
                            karaoke_subtitle_path.unlink()
                        final_subtitle = self.call_karaoke_converter(
                            calibrated_subtitle, calibration_audio, karaoke_subtitle_path, karaoke_effect=True
                        )
                    processed_subtitles.append({
                        'language': language,
                        'final_subtitle': final_subtitle,
                        'is_default': is_default,
                        'original_track_id': track_id,
                        'effect': 'prompter'
                    })
                else:  # 标准卡拉OK效果
                    karaoke_subtitle_path = self.cache_dir / f"karaoke_{language}_{track_id}.ass"
                    if karaoke_subtitle_path.exists():
                        karaoke_subtitle_path.unlink()
                    final_subtitle = self.call_karaoke_converter(
                        calibrated_subtitle, calibration_audio, karaoke_subtitle_path, karaoke_effect=True
                    )
                    processed_subtitles.append({
                        'language': language,
                        'final_subtitle': final_subtitle,
                        'is_default': is_default,
                        'original_track_id': track_id,
                        'effect': 'default'
                    })
            else:
                # 不启用卡拉OK效果，只使用校准后的字幕
                processed_subtitles.append({
                    'language': language,
                    'final_subtitle': calibrated_subtitle,
                    'is_default': is_default,
                    'original_track_id': track_id,
                    'effect': 'none'
                })
        mkv_result = None
        if enable_packing:
            print("\n步骤4: MKV打包（保留原视频音频）")
            print("-" * 40)
            output_mkv_path = self.process_output_video_filename(media_path, karaoke_effect, real_karaoke_effect, output_dir)
            if output_dir != media_path.parent:
                output_mkv_path = output_dir / output_mkv_path.name
            mkv_result = self.call_mkv_packer_subtitles_only(
                video_path=media_path,
                subtitle_tracks=processed_subtitles,
                output_path=output_mkv_path,
                enable_custom_font=enable_custom_font
            )
        result = {
            'input_media': media_path,
            'processed_subtitles': processed_subtitles,
            'output_mkv': mkv_result,
            'output_dir': output_dir
        }
        print("\n" + "=" * 60)
        print("多语言字幕处理完成!")
        print("=" * 60)
        if mkv_result:
            print(f"输出视频: {mkv_result}")
        return result

    def get_language_name(self, language_code):
        language_names = {
            'zh': '中文', 'chi': '中文', 'zho': '中文', 'chinese': '中文',
            'ko': '韩语', 'kor': '韩语', 'korean': '韩语',
            'ja': '日语', 'jpn': '日语', 'japanese': '日语',
            'en': '英语', 'eng': '英语', 'english': '英语',
            'fr': '法语', 'fre': '法语', 'fra': '法语', 'french': '法语',
            'es': '西班牙语', 'spa': '西班牙语', 'spanish': '西班牙语',
            'de': '德语', 'ger': '德语', 'deu': '德语', 'german': '德语',
            'ru': '俄语', 'rus': '俄语', 'russian': '俄语',
            'ar': '阿拉伯语', 'ara': '阿拉伯语', 'arabic': '阿拉伯语',
            'pt': '葡萄牙语', 'por': '葡萄牙语', 'portuguese': '葡萄牙语',
            'it': '意大利语', 'ita': '意大利语', 'italian': '意大利语',
            'hi': '印地语', 'hin': '印地语', 'hindi': '印地语',
            'und': '未知语言'
        }
        return language_names.get(language_code.lower(), f"语言{language_code}")

    def process_single_video_file(self, video_path, karaoke_effect=True, output_dir=None, enable_packing=True, enable_custom_font=True, use_vocal_separation=True, real_karaoke_effect=False):
        video_path = Path(video_path)
        
        # 检查文件是否包含(ASS_1)标签
        has_ass1_tag = ' (ASS_1)' in video_path.name
        if has_ass1_tag:
            print("⚠️  检测到(ASS_1)标签，暂时不支持效果转换")
            # 跳过效果转换，但保留其他操作
            karaoke_effect = False
            real_karaoke_effect = 0
        
        print("检测文件字幕轨道信息...")
        subtitle_tracks = self.extract_all_internal_subtitles(video_path)
        default_output_dir = video_path.parent
        validated_output_dir = self.validate_output_dir(output_dir, default_output_dir, video_path)
        output_path = self.process_output_video_filename(video_path, karaoke_effect, real_karaoke_effect, validated_output_dir)
        if validated_output_dir != video_path.parent:
            output_path = validated_output_dir / output_path.name
        if subtitle_tracks and len(subtitle_tracks) > 1:
            print(f"检测到多字幕文件: {len(subtitle_tracks)}个字幕轨道")
            print("找到的字幕轨道:")
            for i, track in enumerate(subtitle_tracks):
                lang_name = self.get_language_name(track['language'])
                default_status = "默认" if track['default'] else "非默认"
                print(f"  {i+1}. 轨道{track['track_id']}: {lang_name} ({track['language']}), {default_status}")
            if MULTI_SUBTITLE == 1:
                print("启用多字幕处理（根据MULTI_SUBTITLE配置）")
                result = self.process_multilingual_subtitles(video_path, karaoke_effect, validated_output_dir, enable_packing, enable_custom_font, use_vocal_separation, real_karaoke_effect)
            else:
                print("禁用多字幕处理，使用单字幕处理（根据MULTI_SUBTITLE配置）")
                result = self.process_single_subtitle(video_path, karaoke_effect, validated_output_dir, enable_packing, enable_custom_font, use_vocal_separation, real_karaoke_effect)
        else:
            result = self.process_single_subtitle(video_path, karaoke_effect, validated_output_dir, enable_packing, enable_custom_font, use_vocal_separation, real_karaoke_effect)
        return result

    def process_single_subtitle(self, media_path, karaoke_effect=True, output_dir=None, enable_packing=True, enable_custom_font=True, use_vocal_separation=True, real_karaoke_effect=False):
        media_path = Path(media_path)
        default_output_dir = media_path.parent
        output_dir = self.validate_output_dir(output_dir, default_output_dir, media_path)
        workflow_text = "字幕处理工作流程：字幕校准 -> 卡拉OK生成 -> MKV打包"
        print("=" * len(workflow_text))
        print(workflow_text)
        print("=" * len(workflow_text))
        print(f"媒体文件: {media_path.name}")
        print(f"卡拉OK效果: {'开启' if karaoke_effect else '关闭'}")
        print(f"真实卡拉OK效果: {'开启' if real_karaoke_effect else '关闭'}")
        print(f"MKV打包: {'开启' if enable_packing else '关闭'}")
        print(f"自定义字体: {'启用' if enable_custom_font else '禁用'}")
        print(f"人声分离: {'启用' if use_vocal_separation else '禁用'}")
        print(f"输出目录: {output_dir}")
        print("\n步骤1: 查找字幕文件")
        print("-" * 30)
        internal_subtitles = self.extract_all_internal_subtitles(media_path)
        subtitle_files = [st['path'] for st in internal_subtitles] if internal_subtitles else []
        
        # 检查文件名是否包含 (ASS) 标签
        is_ass_a_file = '(ASS)' in media_path.name
        
        if not subtitle_files:
            for ext in ['.srt', '.ass', '.ssa', '.lrc', '.vtt', '.txt']:
                subtitle_files.extend(media_path.parent.glob(f"*{ext}"))
                subtitle_files.extend(media_path.parent.glob(f"*{ext.upper()}"))
        if not subtitle_files:
            print("未找到任何字幕文件")
            try:
                subtitle_path = input("请手动输入字幕文件路径: ").strip().strip('"')
                if not subtitle_path:
                    raise FileNotFoundError("未提供字幕文件路径")
                subtitle_path = Path(subtitle_path)
                if not subtitle_path.exists():
                    raise FileNotFoundError(f"字幕文件不存在: {subtitle_path}")
                subtitle_files = [subtitle_path]
            except EOFError:
                print("无法读取用户输入，跳过处理")
                raise FileNotFoundError("未提供字幕文件路径")
        
        # 对 (ASS) 文件特殊处理：如果有多个内置字幕，只使用默认效果的字幕
        if is_ass_a_file and len(internal_subtitles) > 1:
            print(f"\n检测到 (ASS) 文件，有 {len(internal_subtitles)} 个内置字幕轨道")
            # 查找默认效果的字幕轨道
            default_track = None
            for st in internal_subtitles:
                track_name = st.get('track_name', '').lower()
                if '默认' in track_name or 'default' in track_name or not track_name:
                    default_track = st
                    break
            if default_track:
                print(f"使用默认效果字幕轨道: {default_track['track_id']}")
                subtitle_files = [default_track['path']]
            else:
                print("未找到默认效果字幕轨道，使用第一个轨道")
                subtitle_files = [internal_subtitles[0]['path']]
        
        if len(subtitle_files) > 1:
            print("找到多个字幕文件:")
            for i, sub in enumerate(subtitle_files):
                source = "内置" if sub in [st['path'] for st in internal_subtitles] else "外部"
                print(f"  {i+1}. {sub.name} ({source})")
            choice = input("请选择字幕文件 (输入编号，回车使用第一个): ").strip()
            if choice and choice.isdigit():
                try:
                    subtitle_path = subtitle_files[int(choice) - 1]
                except (ValueError, IndexError):
                    print("无效选择，使用第一个文件")
                    subtitle_path = subtitle_files[0]
            else:
                subtitle_path = subtitle_files[0]
        else:
            subtitle_path = subtitle_files[0]
        print(f"使用字幕文件: {subtitle_path.name}")
        if internal_subtitles and subtitle_path in [st['path'] for st in internal_subtitles]:
            for st in internal_subtitles:
                if st['path'] == subtitle_path:
                    subtitle_language = st['language']
                    break
        else:
            subtitle_language = self.detect_subtitle_language(subtitle_path)
        
        # 检测文件内容格式
        content_format = self.detect_file_content_format(subtitle_path)
        print(f"检测到字幕语言: {self.get_language_name(subtitle_language)}")
        print(f"文件内容格式: {content_format}")
        print("\n步骤2: 提取音频用于字幕校准")
        print("-" * 30)
        calibration_audio = self.extract_audio_for_calibration(media_path, use_vocal_separation)
        if not calibration_audio:
            print("音频提取失败，无法进行字幕校准")
            return None
        print("\n步骤3: 字幕校准")
        print("-" * 30)
        calibrated_subtitle_path = self.cache_dir / f"calibrated_{subtitle_path.stem}.ass"
        if calibrated_subtitle_path.exists():
            try:
                calibrated_subtitle_path.unlink()
            except:
                pass
        if not subtitle_path.exists():
            raise FileNotFoundError(f"字幕文件不存在: {subtitle_path}，无法继续处理")
        calibrated_subtitle = self.call_subtitle_calibrator(
            calibration_audio, subtitle_path, calibrated_subtitle_path, not karaoke_effect
        )
        if not calibrated_subtitle:
            print("字幕校准失败，使用原始字幕")
            calibrated_subtitle = subtitle_path
        print("\n步骤4: 卡拉OK转换")
        print("-" * 30)
        # 处理卡拉OK转换
        final_subtitles = []
        if karaoke_effect:
            if str(real_karaoke_effect) == 'A':  # 全选模式，生成所有效果
                print("\n启用全选模式，生成所有卡拉OK效果...")
                
                # 生成默认效果
                print("\n1. 生成默认效果...")
                karaoke_subtitle_path_0 = self.cache_dir / f"karaoke_default_{subtitle_path.stem}.ass"
                if karaoke_subtitle_path_0.exists():
                    karaoke_subtitle_path_0.unlink()
                default_subtitle = self.call_karaoke_converter(
                    calibrated_subtitle, calibration_audio, karaoke_subtitle_path_0, karaoke_effect=True
                )
                if default_subtitle:
                    final_subtitles.append({
                        'language': subtitle_language,
                        'final_subtitle': default_subtitle,
                        'is_default': True,
                        'original_track_id': '1',
                        'effect': 'default'
                    })
                
                # 生成KTV效果
                print("\n2. 生成KTV效果...")
                ktv_subtitle = self.process_real_karaoke(
                    calibrated_subtitle, calibration_audio, None
                )
                if not ktv_subtitle:
                    print("KTV效果处理失败，使用标准卡拉OK流程")
                    karaoke_subtitle_path_1 = self.cache_dir / f"karaoke_ktv_{subtitle_path.stem}.ass"
                    if karaoke_subtitle_path_1.exists():
                        karaoke_subtitle_path_1.unlink()
                    ktv_subtitle = self.call_karaoke_converter(
                        calibrated_subtitle, calibration_audio, karaoke_subtitle_path_1, karaoke_effect=True
                    )
                if ktv_subtitle:
                    final_subtitles.append({
                        'language': subtitle_language,
                        'final_subtitle': ktv_subtitle,
                        'is_default': False,
                        'original_track_id': '2',
                        'effect': 'ktv'
                    })
                
                # 生成提词器效果
                print("\n3. 生成提词器效果...")
                prompter_subtitle = self.process_prompter_effect(
                    calibrated_subtitle, calibration_audio, None
                )
                if not prompter_subtitle:
                    print("提词器效果处理失败，使用标准卡拉OK流程")
                    karaoke_subtitle_path_2 = self.cache_dir / f"karaoke_prompter_{subtitle_path.stem}.ass"
                    if karaoke_subtitle_path_2.exists():
                        karaoke_subtitle_path_2.unlink()
                    prompter_subtitle = self.call_karaoke_converter(
                        calibrated_subtitle, calibration_audio, karaoke_subtitle_path_2, karaoke_effect=True
                    )
                if prompter_subtitle:
                    final_subtitles.append({
                        'language': subtitle_language,
                        'final_subtitle': prompter_subtitle,
                        'is_default': False,
                        'original_track_id': '3',
                        'effect': 'prompter'
                    })
                
                # 如果没有生成任何字幕，使用校准后的字幕
                if not final_subtitles:
                    print("所有卡拉OK效果生成失败，使用校准后的字幕")
                    final_subtitles.append({
                        'language': subtitle_language,
                        'final_subtitle': calibrated_subtitle,
                        'is_default': True,
                        'original_track_id': '1',
                        'effect': 'default'
                    })
            elif real_karaoke_effect == 1:  # 真实卡拉OK效果
                print("启用真实卡拉OK效果处理流程...")
                final_subtitle = self.process_real_karaoke(
                    calibrated_subtitle, calibration_audio, None
                )
                if not final_subtitle:
                    print("真实卡拉OK处理失败，使用标准卡拉OK流程")
                    karaoke_subtitle_path = self.cache_dir / f"karaoke_{subtitle_path.stem}.ass"
                    if karaoke_subtitle_path.exists():
                        karaoke_subtitle_path.unlink()
                    final_subtitle = self.call_karaoke_converter(
                        calibrated_subtitle, calibration_audio, karaoke_subtitle_path, karaoke_effect=True
                    )
                final_subtitles.append({
                    'language': subtitle_language,
                    'final_subtitle': final_subtitle,
                    'is_default': True,
                    'original_track_id': '1',
                    'effect': 'ktv'
                })
            elif real_karaoke_effect == 2:  # 提词器效果
                print("启用提词器效果处理流程...")
                final_subtitle = self.process_prompter_effect(
                    calibrated_subtitle, calibration_audio, None
                )
                if not final_subtitle:
                    print("提词器效果处理失败，使用标准卡拉OK流程")
                    karaoke_subtitle_path = self.cache_dir / f"karaoke_{subtitle_path.stem}.ass"
                    if karaoke_subtitle_path.exists():
                        karaoke_subtitle_path.unlink()
                    final_subtitle = self.call_karaoke_converter(
                        calibrated_subtitle, calibration_audio, karaoke_subtitle_path, karaoke_effect=True
                    )
                final_subtitles.append({
                    'language': subtitle_language,
                    'final_subtitle': final_subtitle,
                    'is_default': True,
                    'original_track_id': '1',
                    'effect': 'prompter'
                })
            else:  # 标准卡拉OK效果
                karaoke_subtitle_path = self.cache_dir / f"karaoke_{subtitle_path.stem}.ass"
                if karaoke_subtitle_path.exists():
                    karaoke_subtitle_path.unlink()
                final_subtitle = self.call_karaoke_converter(
                    calibrated_subtitle, calibration_audio, karaoke_subtitle_path, karaoke_effect=True
                )
                final_subtitles.append({
                    'language': subtitle_language,
                    'final_subtitle': final_subtitle,
                    'is_default': True,
                    'original_track_id': '1',
                    'effect': 'default'
                })
        else:
            # 不启用卡拉OK效果，只使用校准后的字幕
            final_subtitles.append({
                'language': subtitle_language,
                'final_subtitle': calibrated_subtitle,
                'is_default': True,
                'original_track_id': '1',
                'effect': 'none'
            })
        
        # 处理MKV打包
        mkv_result = None
        if enable_packing:
            print("\n步骤5: MKV打包（保留原视频音频）")
            print("-" * 30)
            output_mkv_path = self.process_output_video_filename(media_path, karaoke_effect, real_karaoke_effect, output_dir)
            if output_dir != media_path.parent:
                output_mkv_path = output_dir / output_mkv_path.name
            
            # 调用字幕替换打包器，传递所有生成的字幕轨道
            mkv_result = self.call_mkv_packer_subtitles_only(
                video_path=media_path,
                subtitle_tracks=final_subtitles,
                output_path=output_mkv_path,
                enable_custom_font=enable_custom_font
            )
        result = {
            'input_media': media_path,
            'input_subtitle': subtitle_path,
            'final_subtitles': final_subtitles,
            'output_mkv': mkv_result,
            'output_dir': output_dir,
            'language': subtitle_language
        }
        print("\n" + "=" * 60)
        print("字幕处理完成!")
        print("=" * 60)
        if mkv_result:
            print(f"输出视频: {mkv_result}")
        else:
            if final_subtitles:
                print(f"处理后的字幕轨道数量: {len(final_subtitles)}")
                for i, track in enumerate(final_subtitles):
                    print(f"  轨道{i+1}: {track['final_subtitle']}")
        return result

    def process_real_karaoke(self, subtitle_path, audio_path=None, output_path=None):
        print("\n" + "=" * 60)
        print("真实卡拉OK效果处理流程")
        print("=" * 60)
        print(f"字幕文件: {Path(subtitle_path).name}")
        try:
            print("\n步骤1: 使用b.py进行拖长音检测和K值生成")
            print("-" * 40)
            b_output_path = self.cache_dir / f"b_karaoke_{Path(subtitle_path).stem}.ass"
            b_result = self.call_karaoke_converter(
                subtitle_path, audio_path, b_output_path, karaoke_effect=True
            )
            if not b_result or not Path(b_result).exists():
                print("b.py处理失败，使用原始字幕")
                b_result = subtitle_path
            print(f"b.py处理完成: {Path(b_result).name}")
            print("\n步骤2: 使用k.py进行双语卡拉OK处理")
            print("-" * 40)
            k_output_path = self.cache_dir / f"k_final_{Path(subtitle_path).stem}.ass"
            k_result = self.call_karaoke_processor(b_result, k_output_path)
            if not k_result or not Path(k_result).exists():
                print("k.py处理失败，使用b.py处理结果")
                k_result = b_result
            print(f"k.py处理完成: {Path(k_result).name}")
            final_output_path = output_path
            if output_path is None:
                # 使用新的命名规则：KTV效果使用(ASS_1)标记
                stem = Path(subtitle_path).stem
                # 原文件带(ASS) 标签 将(ASS) 改成(ASS_1)
                if ' (ASS)' in stem:
                    new_stem = stem.replace(' (ASS)', ' (ASS_1)')
                else:
                    new_stem = stem + ' (ASS_1)'
                final_output_path = Path(subtitle_path).parent / f"{new_stem}.ass"
                # 与原文件重名则在后面 添加（1）序列号（）
                if final_output_path.exists():
                    counter = 1
                    while True:
                        counter += 1
                        new_path = Path(subtitle_path).parent / f"{new_stem} ({counter}).ass"
                        if not new_path.exists():
                            final_output_path = new_path
                            break
            import shutil
            shutil.copy2(k_result, final_output_path)
            print(f"\n真实卡拉OK处理完成!")
            print(f"输出文件: {final_output_path}")
            return final_output_path
        except Exception as e:
            print(f"真实卡拉OK处理失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def process_prompter_effect(self, subtitle_path, audio_path=None, output_path=None):
        """处理提词器效果"""
        print("\n" + "=" * 60)
        print("提词器效果处理流程")
        print("=" * 60)
        print(f"字幕文件: {Path(subtitle_path).name}")
        
        try:
            # 首先使用b.py进行基础卡拉OK处理
            print("\n步骤1: 使用b.py进行基础卡拉OK处理")
            print("-" * 40)
            b_output_path = self.cache_dir / f"b_karaoke_{Path(subtitle_path).stem}.ass"
            b_result = self.call_karaoke_converter(
                subtitle_path, audio_path, b_output_path, karaoke_effect=True
            )
            
            if not b_result or not Path(b_result).exists():
                print("b.py基础处理失败，尝试直接使用T.py")
                b_result = subtitle_path
            
            print(f"b.py处理完成: {Path(b_result).name}")
            
            # 然后使用T.py进行提词器转换
            print("\n步骤2: 使用T.py进行提词器转换")
            print("-" * 40)
            t_output_path = self.cache_dir / f"t_prompter_{Path(subtitle_path).stem}.ass"
            
            # 检查T.py文件是否存在
            if not Path(self.prompter_converter_path).exists():
                print(f"❌ T.py文件不存在: {self.prompter_converter_path}")
                print("请确保T.py文件与z.py在同一目录下")
                return None
            
            # 调用T.py
            cmd = [
                str(self.python_path),
                str(self.prompter_converter_path),
                str(b_result),
                '-o', str(t_output_path)
            ]
            
            print(f"调用命令: {' '.join(cmd)}")
            returncode, stdout, stderr = self.run_command_safe(cmd, timeout=300)
            
            if returncode == 0 and t_output_path.exists():
                print(f"T.py处理完成: {t_output_path.name}")
                
                final_output_path = output_path
                if output_path is None:
                    # 使用新的命名规则：提词器效果使用(ASS_1)标记
                    stem = Path(subtitle_path).stem
                    # 原文件带(ASS) 标签 将(ASS) 改成(ASS_1)
                    if ' (ASS)' in stem:
                        new_stem = stem.replace(' (ASS)', ' (ASS_1)')
                    else:
                        new_stem = stem + ' (ASS_1)'
                    final_output_path = Path(subtitle_path).parent / f"{new_stem}.ass"
                    # 与原文件重名则在后面 添加（1）序列号（）
                    if final_output_path.exists():
                        counter = 1
                        while True:
                            counter += 1
                            new_path = Path(subtitle_path).parent / f"{new_stem} ({counter}).ass"
                            if not new_path.exists():
                                final_output_path = new_path
                                break
                
                import shutil
                shutil.copy2(t_output_path, final_output_path)
                print(f"\n提词器处理完成!")
                print(f"输出文件: {final_output_path}")
                return final_output_path
            else:
                print(f"T.py处理失败，返回码: {returncode}")
                if stdout:
                    print(f"标准输出: {stdout}")
                if stderr:
                    print(f"错误输出: {stderr}")
                
                # 如果T.py处理失败，尝试直接使用b.py的结果
                print("T.py处理失败，尝试使用b.py处理结果...")
                if b_result != subtitle_path and Path(b_result).exists():
                    final_output_path = output_path
                    if output_path is None:
                        final_output_path = Path(subtitle_path).parent / f"{Path(subtitle_path).stem}_karaoke.ass"
                    shutil.copy2(b_result, final_output_path)
                    print(f"使用b.py处理结果: {final_output_path}")
                    return final_output_path
                else:
                    print("所有处理方式都失败")
                    return None
                
        except Exception as e:
            print(f"提词器处理失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def call_karaoke_converter(self, subtitle_path, audio_path=None, output_path=None, karaoke_effect=True):
        cmd = [
            str(self.python_path), str(self.karaoke_converter_path),
            '--input', str(subtitle_path),
            '--dialogue', '1'  # 启用对白字幕检测
        ]
        if audio_path and Path(audio_path).exists():
            cmd.extend(['--audio', str(audio_path)])
            print(f"  使用音频文件进行拖长音检测: {Path(audio_path).name}")
        else:
            print("  警告: 未提供音频文件，拖长音检测可能不准确")
        if output_path:
            cmd.extend(['--output', str(output_path)])
        if karaoke_effect:
            cmd.append('--karaoke')
        try:
            print("调用卡拉OK转换子程序...")
            returncode, stdout, stderr = self.run_command_safe(cmd, timeout=120)
            if returncode == 0:
                if stdout:
                    for line in stdout.split('\n'):
                        if '检测到' in line and '个独立的拖长音段' in line:
                            print(line.strip())
                        elif line.strip().startswith('段') and '-' in line:
                            print(line.strip())
                        elif '稳定性:' in line or '能量:' in line or '基频标准差:' in line:
                            print(line.strip())
                print("卡拉OK转换完成")
                if output_path and Path(output_path).exists():
                    return output_path
                else:
                    subtitle_dir = Path(subtitle_path).parent
                    subtitle_stem = Path(subtitle_path).stem
                    suffix = "_karaoke" if karaoke_effect else "_converted"
                    default_output = subtitle_dir / f"{subtitle_stem}{suffix}.ass"
                    if default_output.exists():
                        return default_output
            else:
                print(f"卡拉OK转换失败: {stderr}")
                return None
        except Exception as e:
            print(f"调用子程序失败: {e}")
            return None

    def call_karaoke_processor(self, subtitle_path, output_path=None):
        k_path = Path(__file__).parent / "k.py"
        if not k_path.exists():
            print("k.py文件未找到")
            return None
        
        # 如果没有指定输出路径，生成一个临时路径
        if output_path is None:
            output_path = Path(subtitle_path).parent / f"{Path(subtitle_path).stem}_k_processed.ass"
        
        # 使用-o参数指定输出路径，避免依赖固定的输出文件名格式
        cmd = [
            str(self.python_path), 
            str(k_path), 
            str(subtitle_path),
            "-o", str(output_path),
            "-ow"  # 自动覆盖已存在的文件
        ]
        
        try:
            print("调用k.py进行双语卡拉OK处理...")
            print(f"指定输出路径: {output_path}")
            returncode, stdout, stderr = self.run_command_safe(cmd, timeout=180)
            
            if returncode == 0:
                print("k.py处理完成")
                
                # 显示k.py的输出
                if stdout:
                    print(f"k.py输出: {stdout[:500]}")
                
                # 检查指定的输出文件是否存在
                if output_path.exists():
                    print(f"找到卡拉OK效果输出文件: {output_path}")
                    return output_path
                else:
                    # 如果指定的输出文件不存在，尝试查找其他可能的输出
                    print(f"指定的输出文件不存在，搜索其他可能的输出...")
                    
                    # 显示k.py的完整输出，以便调试
                    if stdout:
                        print(f"k.py完整输出: {stdout}")
                    if stderr:
                        print(f"k.py错误输出: {stderr}")
                    
                    # 尝试查找所有.ass文件
                    all_ass_files = list(Path(subtitle_path).parent.glob("*.ass"))
                    print(f"当前目录中的ASS文件: {[str(f) for f in all_ass_files]}")
                    
                    if len(all_ass_files) > 1:
                        # 排除原始文件，使用最新创建的文件
                        original_file = Path(subtitle_path)
                        latest_file = max(all_ass_files, key=lambda x: x.stat().st_mtime)
                        if latest_file != original_file:
                            print(f"使用最新创建的文件: {latest_file}")
                            return latest_file
                    
                    # 如果还是找不到，返回None表示失败
                    print("未找到k.py生成的输出文件")
                    return None
            else:
                print(f"k.py处理失败: {stderr}")
                return None
        except Exception as e:
            print(f"调用k.py失败: {e}")
            return None

    def call_mkv_packer_subtitles_only(self, video_path, subtitle_tracks, output_path=None, enable_custom_font=True):
        cmd = [
            str(self.python_path), str(self.mkv_packer_path),
            'pack'
        ]
        cmd.extend(['-v', str(video_path)])
        subtitle_tracks_sorted = sorted(
            subtitle_tracks,
            key=lambda x: int(x.get('original_track_id', 0)) if x.get('original_track_id') and x.get('original_track_id').isdigit() else 0
        )
        print(f"\n打包字幕轨道顺序 (按原始轨道ID排序):")
        for i, track in enumerate(subtitle_tracks_sorted):
            lang_name = self.get_language_name(track.get('language', 'und'))
            status = "默认" if track.get('is_default') else "非默认"
            effect = track.get('effect', 'default')
            # 默认字幕不显示效果名称，只显示语言信息
            effect_name = "" if effect == 'default' else "KTV效果" if effect == 'ktv' else "提词器效果" if effect == 'prompter' else ""
            if effect_name:
                print(f"  轨道{track.get('original_track_id')}: {lang_name} - {status} - {effect_name}")
            else:
                print(f"  轨道{track.get('original_track_id')}: {lang_name} - {status}")
        for track in subtitle_tracks_sorted:
            if track.get('final_subtitle') and Path(track['final_subtitle']).exists():
                cmd.extend(['-s', str(track['final_subtitle'])])
                cmd.extend(['--subtitle-language', track.get('language', 'chi')])
                original_track_id = track.get('original_track_id', '1')
                cmd.extend(['--original-track-id', original_track_id])
                if track.get('is_default'):
                    cmd.extend(['--default-subtitle', 'yes'])
                else:
                    cmd.extend(['--default-subtitle', 'no'])
                # 添加轨道名称：默认字幕不添加效果名称，只保留语言信息
                effect = track.get('effect', 'default')
                if effect == 'default':
                    track_name = ''  # 默认字幕不添加任何效果名称
                elif effect == 'ktv':
                    track_name = 'KTV效果'
                elif effect == 'prompter':
                    track_name = '提词器效果'
                else:
                    track_name = ''
                cmd.extend(['--track-name', track_name])
        if not enable_custom_font:
            cmd.append('--no-custom-font')
        if output_path:
            cmd.extend(['-o', str(output_path)])
        try:
            print("\n调用字幕替换打包器...")
            print("命令:", ' '.join(cmd))
            returncode, stdout, stderr = self.run_command_safe(cmd, timeout=300)
            if returncode == 0:
                print("字幕替换打包完成")
                return output_path if output_path else self.find_generated_mkv(video_path)
            else:
                print(f"打包失败，返回码: {returncode}")
                if stdout:
                    print(f"标准输出: {stdout}")
                if stderr:
                    print(f"错误输出: {stderr}")
                return None
        except Exception as e:
            print(f"调用打包器失败: {e}")
            return None

    def find_generated_mkv(self, video_path):
        video_dir = Path(video_path).parent
        video_stem = Path(video_path).stem
        possible_names = [
            f"{video_stem}_karaoke.mkv",
            f"{video_stem} (打包).mkv", 
            f"{video_stem}_多语言_打包.mkv"
        ]
        for name in possible_names:
            potential_file = video_dir / name
            if potential_file.exists():
                return potential_file
        return None

    def call_subtitle_calibrator(self, audio_path, subtitle_path, output_path=None, remove_karaoke=False):
        cmd = [
            str(self.python_path), str(self.subtitle_calibrator_path),
            '-a', str(audio_path), '-s', str(subtitle_path)
        ]
        # 添加移除卡拉OK标签的参数
        if remove_karaoke:
            cmd.extend(['--remove-karaoke'])
        if output_path:
            cmd.extend(['-o', str(output_path)])
        try:
            print("调用字幕校准子程序...")
            returncode, stdout, stderr = self.run_command_safe(cmd, timeout=300)
            if returncode == 0:
                print("字幕校准完成")
                if output_path and Path(output_path).exists():
                    return output_path
                else:
                    subtitle_dir = Path(subtitle_path).parent
                    subtitle_stem = Path(subtitle_path).stem
                    default_output = subtitle_dir / f"{subtitle_stem}_calibrated.ass"
                    if default_output.exists():
                        return default_output
            else:
                print(f"字幕校准失败: {stderr}")
                return None
        except Exception as e:
            print(f"调用子程序失败: {e}")
            return None

    def check_mkvtoolnix_available(self):
        try:
            returncode, stdout, stderr = self.run_command_safe([self.mkvmerge_path, '--version'])
            return returncode == 0
        except:
            return False

    def auto_detect_and_process(self, input_path, karaoke_effect=True, output_dir=None, enable_packing=True, enable_custom_font=True, use_vocal_separation=True, real_karaoke_effect=False):
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"路径不存在: {input_path}")
        if input_path.is_file() and self.is_subtitle_file(input_path):
            print(f"检测到字幕文件: {input_path.name}")
            self.setup_cache()
            try:
                video_file = self.find_video_by_subtitle(input_path)
                if video_file:
                    print(f"找到同名视频文件: {video_file.name}")
                    print("使用视频文件进行打包处理...")
                    default_output_dir = video_file.parent
                    validated_output_dir = self.validate_output_dir(output_dir, default_output_dir, video_file)
                    result = self.process_with_external_subtitle(
                        video_file, input_path, karaoke_effect, validated_output_dir, 
                        enable_packing, enable_custom_font, use_vocal_separation,
                        real_karaoke_effect
                    )
                    self.cleanup_cache()
                    return result
                else:
                    print("\n未找到同名视频文件")
                    video_path_input = input("请输入视频文件路径（留空则仅进行纯字幕转换）: ").strip().strip('"')
                    if video_path_input:
                        video_path = Path(video_path_input)
                        if video_path.exists() and video_path.is_file():
                            print(f"使用视频文件: {video_path.name}")
                            default_output_dir = video_path.parent
                            validated_output_dir = self.validate_output_dir(output_dir, default_output_dir, video_path)
                            result = self.process_with_external_subtitle(
                                video_path, input_path, karaoke_effect, validated_output_dir, 
                                enable_packing, enable_custom_font, use_vocal_separation,
                                real_karaoke_effect
                            )
                            self.cleanup_cache()
                            return result
                        else:
                            print("视频文件不存在，将仅转换字幕")
                    default_output_dir = input_path.parent
                    validated_output_dir = self.validate_output_dir(output_dir, default_output_dir, input_path)
                    result = self.convert_subtitle_only(input_path, karaoke_effect, validated_output_dir)
                    self.cleanup_cache()
                    return result
            except Exception as e:
                self.cleanup_cache()
                raise e
            finally:
                if self.cache_dir and self.cache_dir.exists():
                    self.cleanup_cache()
        elif input_path.is_dir():
            # 生成唯一的默认输出目录，如已存在则添加序列号
            base_output_dir = input_path / "ASS"
            counter = 1
            default_output_dir = base_output_dir
            while default_output_dir.exists():
                default_output_dir = input_path / f"ASS ({counter})"
                counter += 1
            validated_output_dir = self.validate_output_dir(output_dir, default_output_dir, input_path)
            video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
            video_files = []
            for f in input_path.iterdir():
                if (f.is_file() and 
                    f.suffix.lower() in video_extensions and 
                    OUTPUT_DIR_FILTER_MARKER not in f.name):
                    video_files.append(f)
            if not video_files:
                print(f"未找到视频文件（已忽略包含 {OUTPUT_DIR_FILTER_MARKER} 的文件）")
                return []
            results = []
            for i, video_file in enumerate(video_files, 1):
                print(f"\n{'='*50}")
                print(f"处理文件 [{i}/{len(video_files)}]: {video_file.name}")
                print(f"{'='*50}")
                self.setup_cache()
                try:
                    result = self.process_single_video_file(
                        video_file, karaoke_effect, validated_output_dir, 
                        enable_packing, enable_custom_font, use_vocal_separation,
                        real_karaoke_effect
                    )
                    results.append(result)
                    self.cleanup_cache()
                except Exception as e:
                    print(f"处理视频文件 {video_file.name} 时出错: {e}")
                    self.cleanup_cache()
            return results
        else:
            default_output_dir = input_path.parent
            validated_output_dir = self.validate_output_dir(output_dir, default_output_dir, input_path)
            self.setup_cache()
            try:
                print("检测文件字幕轨道信息...")
                subtitle_tracks = self.extract_all_internal_subtitles(input_path)
                if subtitle_tracks and len(subtitle_tracks) > 1:
                    print(f"检测到多字幕文件: {len(subtitle_tracks)}个字幕轨道")
                    print("找到的字幕轨道:")
                    for i, track in enumerate(subtitle_tracks):
                        lang_name = self.get_language_name(track['language'])
                        default_status = "默认" if track['default'] else "非默认"
                        print(f"  {i+1}. 轨道{track['track_id']}: {lang_name} ({track['language']}), {default_status}")
                    if MULTI_SUBTITLE == 1:
                        print("启用多字幕处理（根据MULTI_SUBTITLE配置）")
                        result = self.process_multilingual_subtitles(input_path, karaoke_effect, validated_output_dir, enable_packing, enable_custom_font, use_vocal_separation, real_karaoke_effect)
                    else:
                        print("禁用多字幕处理，使用单字幕处理（根据MULTI_SUBTITLE配置）")
                        result = self.process_single_subtitle(input_path, karaoke_effect, validated_output_dir, enable_packing, enable_custom_font, use_vocal_separation, real_karaoke_effect)
                else:
                    result = self.process_single_subtitle(input_path, karaoke_effect, validated_output_dir, enable_packing, enable_custom_font, use_vocal_separation, real_karaoke_effect)
                self.cleanup_cache()
                return result
            except Exception as e:
                self.cleanup_cache()
                raise e

class SimpleSubtitleConverter:
    @staticmethod
    def generate_incremental_filename(input_path, marker, extension, output_dir=None):
        input_path = Path(input_path)
        base_stem = input_path.stem
        clean_stem = re.sub(rf'{re.escape(marker)}\s*(\(\d+\))?\s*$', '', base_stem).strip()
        clean_stem = re.sub(r'\s+\(\d+\)\s*$', '', clean_stem).strip()
        counter = 1
        # 确定检查目录
        check_dir = Path(output_dir) if output_dir else input_path.parent
        while True:
            if counter == 1:
                new_filename = f"{clean_stem}{marker}{extension}"
            else:
                new_filename = f"{clean_stem}{marker} ({counter}){extension}"
            new_path = check_dir / new_filename
            if not new_path.exists():
                return new_path
            counter += 1
    
    def process_output_filename(self, input_path, karaoke_mode=False, is_batch=False, real_karaoke_effect=0, output_dir=None):
        input_path = Path(input_path)
        stem = input_path.stem
        
        # 根据real_karaoke_effect确定目标标记
        if real_karaoke_effect == 'A' or real_karaoke_effect == -1 or str(real_karaoke_effect) == '-1':  # 全选模式
            # 全选模式：使用 (ASS) 标记
            target_marker = ' (ASS)'
            # 替换所有标记 (SRT) 和 (SSA) 为 (ASS)
            new_stem = stem
            for replace_marker in OUTPUT_REPLACE_MARKERS:
                if replace_marker in new_stem:
                    new_stem = new_stem.replace(replace_marker, target_marker)
                    break
            if new_stem == stem:
                new_stem = stem + target_marker
        elif real_karaoke_effect == 1 or real_karaoke_effect == 2 or str(real_karaoke_effect) in ['1', '2']:  # KTV效果或提词器效果
            # 非默认效果：使用 (ASS_1) 标记
            target_marker = ' (ASS_1)'
            # 替换所有标记 (SRT) 和 (SSA) 为 (ASS_1)
            new_stem = stem
            for replace_marker in OUTPUT_REPLACE_MARKERS:
                if replace_marker in new_stem:
                    new_stem = new_stem.replace(replace_marker, target_marker)
                    break
            if new_stem == stem:
                new_stem = stem + target_marker
        else:  # 默认效果
            if karaoke_mode:
                target_marker = KARAOKE_SUFFIX
            else:
                target_marker = NO_KARAOKE_SUFFIX
            # 如果是默认效果源文件带(ASS) 则无需添加(ASS)
            if ' (ASS)' in stem and karaoke_mode:
                new_stem = stem
            else:
                new_stem = stem
                for replace_marker in OUTPUT_REPLACE_MARKERS:
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
            output_dir = input_path.parent
            output_path = output_dir / f"{new_stem}.ass"
        
        # 与原文件重名则在后面 添加（1）序列号（）
        if output_path.exists():
            return self.generate_incremental_filename(input_path, target_marker, '.ass', output_dir)
        return output_path
    
    def convert_subtitle(self, input_path, output_path=None, enable_custom_font=True, karaoke_mode=False, is_batch=False, real_karaoke_effect=0):
        try:
            from pathlib import Path
            input_path = Path(input_path)
            if output_path is None:
                output_path = self.process_output_filename(input_path, karaoke_mode, is_batch, real_karaoke_effect)
            import shutil
            shutil.copy2(input_path, output_path)
            print(f"字幕文件已转换: {output_path}")
            return output_path
        except Exception as e:
            print(f"转换失败: {e}")
            return None

def main():
    try:
        import argparse
        parser = argparse.ArgumentParser(description='字幕打包程序')
        parser.add_argument('--subtitle-mode', type=str, choices=['0', '1', '2', 'A', '-1'], help='设置字幕处理模式：0-默认，1-KTV效果，2-提词器效果，A/-1-全部效果')
        parser.add_argument('input_paths', nargs='*', help='输入文件路径')
        args = parser.parse_known_args()
        
        # 分离已知参数和未知参数
        known_args, unknown_args = args
        input_paths = known_args.input_paths + unknown_args
        
        processor = MainProcessor()
        workflow_text = "字幕处理工作流程：字幕校准 -> 卡拉OK生成 -> MKV打包"
        print("=" * len(workflow_text))
        print(workflow_text)
        print("=" * len(workflow_text))
        if input_paths:
            for i, arg in enumerate(input_paths, 1):
                print(f"\n处理参数 {i}/{len(input_paths)}: {arg}")
                input_path = Path(arg)
                if not input_path.exists():
                    print(f"警告: 路径不存在: {arg}")
                    continue
                karaoke_effect = KARAOKE_EFFECT == 1
                
                # 处理subtitle-mode参数
                if known_args.subtitle_mode is not None:
                    if known_args.subtitle_mode in ['A', '-1']:
                        real_karaoke_effect = 'A'  # 使用'A'作为内部全选标记
                    else:
                        real_karaoke_effect = int(known_args.subtitle_mode)
                else:
                    # 如果是内部值-1，转换为'A'作为内部全选标记
                    if REAL_KARAOKE_EFFECT == -1:
                        real_karaoke_effect = 'A'
                    else:
                        real_karaoke_effect = REAL_KARAOKE_EFFECT if karaoke_effect else 0
                    
                enable_custom_font = CUSTOM_FONT == 1
                use_vocal_separation = USE_VOCAL_SEPARATION
                enable_packing = ENABLE_PACKING
                if ASK_OUTPUT_DIR == 1:
                    output_dir = None
                else:
                    output_dir = None
                print(f"处理模式: 自动处理")
                print(f"卡拉OK效果: {'启用' if karaoke_effect else '禁用'}")
                if karaoke_effect:
                    if real_karaoke_effect == 1:
                        print(f"真实卡拉OK效果: 启用（真实卡拉OK式样）")
                    elif real_karaoke_effect == 2:
                        print(f"真实卡拉OK效果: 启用（提词器式样）")
                    else:
                        print(f"真实卡拉OK效果: 禁用（默认式样）")
                print(f"自定义字体: {'启用' if enable_custom_font else '禁用'}")
                print(f"人声分离: {'启用' if use_vocal_separation else '禁用'}")
                print(f"MKV打包: {'启用' if enable_packing else '禁用'}")
                try:
                    result = processor.auto_detect_and_process(
                        input_path, 
                        karaoke_effect, 
                        output_dir,
                        enable_packing,
                        enable_custom_font,
                        use_vocal_separation,
                        real_karaoke_effect
                    )
                    if result:
                        print(f"\n✓ 处理完成!")
                        if isinstance(result, list):
                            print(f"批量处理完成: {len(result)} 个文件")
                            for j, res in enumerate(result):
                                if res and res.get('output_mkv'):
                                    print(f"  文件{j+1}: {res['output_mkv'].name}")
                        elif result.get('output_mkv'):
                            print(f"输出文件: {result['output_mkv'].name}")
                        elif result.get('output_subtitle'):
                            print(f"输出字幕: {result['output_subtitle'].name}")
                        elif result.get('final_subtitle'):
                            print(f"处理后的字幕: {result['final_subtitle'].name}")
                    else:
                        print(f"\n× 处理失败!")
                except Exception as e:
                    print(f"处理 {arg} 时出错: {e}")
                    import traceback
                    traceback.print_exc()
            print("\n所有文件处理完成！")
            return
        else:
            while True:
                input_path = input("\n请输入媒体文件或字幕文件路径: ").strip().strip('"')
                if not input_path:
                    print("路径不能为空")
                    continue
                input_path = Path(input_path)
                if not input_path.exists():
                    print("路径不存在，请检查")
                    continue
                if ASK_OUTPUT_DIR == 1:
                    output_dir_input = input("请输入输出目录(直接回车使用默认目录): ").strip().strip('"')
                    if not output_dir_input:
                        output_dir = None
                    else:
                        output_dir = output_dir_input
                else:
                    output_dir = None
                    print(f"输出目录: 使用默认目录（可在配置中修改ASK_OUTPUT_DIR=1来启用询问）")
                karaoke_effect = KARAOKE_EFFECT == 1
                print(f"卡拉OK效果: {'启用' if karaoke_effect else '禁用'}（可在配置中修改KARAOKE_EFFECT）")
                real_karaoke_effect = REAL_KARAOKE_EFFECT if karaoke_effect else 0
                if karaoke_effect:
                    if real_karaoke_effect == 1:
                        print(f"真实卡拉OK效果: 启用（真实卡拉OK式样）（可在配置中修改REAL_KARAOKE_EFFECT）")
                    elif real_karaoke_effect == 2:
                        print(f"真实卡拉OK效果: 启用（提词器式样）（可在配置中修改REAL_KARAOKE_EFFECT）")
                    elif real_karaoke_effect == -1:
                        print(f"真实卡拉OK效果: 启用（全选模式）（可在配置中修改REAL_KARAOKE_EFFECT）")
                    else:
                        print(f"真实卡拉OK效果: 禁用（默认式样）（可在配置中修改REAL_KARAOKE_EFFECT）")
                enable_custom_font = CUSTOM_FONT == 1
                print(f"自定义字体: {'启用' if enable_custom_font else '禁用'}（可在配置中修改CUSTOM_FONT）")
                print(f"目录过滤标记: {OUTPUT_DIR_FILTER_MARKER}")
                use_vocal_separation = USE_VOCAL_SEPARATION
                enable_packing = ENABLE_PACKING
                print(f"人声分离: {'启用' if use_vocal_separation else '禁用'}")
                print(f"MKV打包: {'启用' if enable_packing else '禁用'}")
                result = processor.auto_detect_and_process(
                    input_path, 
                    karaoke_effect, 
                    output_dir,
                    enable_packing,
                    enable_custom_font,
                    use_vocal_separation,
                    real_karaoke_effect
                )
                if result:
                    print("\n处理完成!")
                    if isinstance(result, list):
                        print(f"批量处理完成: {len(result)} 个文件")
                        for i, res in enumerate(result):
                            if res and res.get('output_mkv'):
                                print(f"  文件{i+1}: {res['output_mkv']}")
                    elif result.get('output_mkv'):
                        print(f"输出文件: {result['output_mkv']}")
                    elif result.get('output_subtitle'):
                        print(f"输出字幕: {result['output_subtitle']}")
                    elif result.get('final_subtitle'):
                        print(f"处理后的字幕: {result['final_subtitle']}")
                else:
                    print("\n处理失败!")
                continue_choice = input("\n是否继续处理其他文件? (y=是, n=否, 默认是): ").strip().lower()
                if continue_choice == 'n':
                    print("再见!")
                    break
    except Exception as e:
        print(f"\n程序运行出错: {e}")
        import traceback
        traceback.print_exc()
    input("\n按回车键退出...")

if __name__ == "__main__":
    main()