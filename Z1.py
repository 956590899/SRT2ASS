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

import json
import subprocess
import tempfile
import re
import shutil
from pathlib import Path

# ========== 配置参数 ==========
# 多音轨多字幕默认属性:
# 0: 保持原视频的默认音频和字幕设置
# 1: 将中文音轨和字幕设为默认
DEFAULT_SETTINGS_MODE = 0  # 0或1

# 立体声转5.1声道转换开关:
# 0: 关闭，保持原始音频
# 1: 开启，将所有音频轨道转换为5.1声道
STEREO_TO_5_1 = 0  # 0或1

# 字幕处理模式开关:
# 0: 关闭，保持原始字幕
# 1: 真实卡拉OK效果，调用k.py处理字幕
# 2: 提词器效果，调用T.py处理字幕
# -1: 全选，同时处理所有效果
SUBTITLE_MODE = -1  # 0、1、2或-1（全选）
# =============================

class VideoReprocessor:
    def __init__(self):
        """初始化视频二次加工器"""
        self.python_path = sys.executable
        self.karaoke_processor_path = Path(__file__).parent / "k.py"
        self.prompter_processor_path = Path(__file__).parent / "T.py"
        self.audio_converter_path = Path(__file__).parent / "m.py"
        self.cache_dir = None
        # 初始化工具路径
        self.mkvmerge_path = self.detect_mkvmerge_path()
        self.mkvextract_path = self.detect_mkvextract_path()
        self.ffmpeg_path = self.detect_ffmpeg_path()
        
        # 应用配置
        self.default_settings_mode = DEFAULT_SETTINGS_MODE
        self.stereo_to_5_1 = STEREO_TO_5_1
        self.subtitle_mode = SUBTITLE_MODE
    
    def detect_ffmpeg_path(self):
        """检测ffmpeg路径"""
        # 项目自带的ffmpeg路径
        project_ffmpeg = Path(__file__).parent / "Python" / "ffmpeg" / "ffmpeg.exe"
        if project_ffmpeg.exists():
            return str(project_ffmpeg)
        # 系统PATH中的ffmpeg
        return "ffmpeg"
    
    def detect_mkvmerge_path(self):
        """检测MKVToolNix路径"""
        # 项目自带的MKVToolNix路径
        project_mkvmerge = Path(__file__).parent / "Python" / "MKVToolNix" / "mkvmerge.exe"
        if project_mkvmerge.exists():
            return str(project_mkvmerge)
        # 系统PATH中的mkvmerge
        return "mkvmerge"
    
    def detect_mkvextract_path(self):
        """检测mkvextract路径"""
        # 项目自带的mkvextract路径
        project_mkvextract = Path(__file__).parent / "Python" / "MKVToolNix" / "mkvextract.exe"
        if project_mkvextract.exists():
            return str(project_mkvextract)
        # 系统PATH中的mkvextract
        return "mkvextract"
        
    def setup_cache(self):
        """设置缓存目录"""
        temp_dir = tempfile.gettempdir()
        self.cache_dir = Path(temp_dir) / "video_reprocess_temp"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        print(f"缓存目录: {self.cache_dir}")
    
    def cleanup_cache(self):
        """清理缓存目录"""
        if self.cache_dir and self.cache_dir.exists():
            try:
                shutil.rmtree(self.cache_dir)
                print(f"缓存已清理: {self.cache_dir}")
            except Exception as e:
                print(f"缓存清理失败: {e}")
    
    def check_mkvtoolnix_available(self):
        """检查MKVToolNix是否可用"""
        try:
            result = subprocess.run(
                [self.mkvmerge_path, '--version'], 
                capture_output=True, text=True, encoding='utf-8', errors='ignore',
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def get_media_info_with_mkvmerge(self, video_path):
        """使用mkvmerge获取媒体信息"""
        if not self.check_mkvtoolnix_available():
            return {'subtitle_tracks': [], 'audio_tracks': []}
        
        try:
            cmd = [self.mkvmerge_path, '--identification-format', 'json', '--identify', str(video_path)]
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                encoding='utf-8', 
                errors='ignore',
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    info = json.loads(result.stdout)
                    return self.parse_mkvmerge_json_info(info)
                except json.JSONDecodeError:
                    print("mkvmerge JSON解析失败")
                    return self.parse_mkvmerge_text_info(video_path)
            else:
                return self.parse_mkvmerge_text_info(video_path)
                
        except Exception as e:
            print(f"获取媒体信息失败: {e}")
            return {'subtitle_tracks': [], 'audio_tracks': []}
    
    def parse_mkvmerge_json_info(self, info):
        """解析mkvmerge的JSON输出"""
        subtitle_tracks = []
        audio_tracks = []
        
        if 'tracks' in info:
            for track in info['tracks']:
                track_id = str(track.get('id'))
                track_type = track.get('type', '').lower()
                
                # 获取语言信息
                language = track.get('properties', {}).get('language', 'und')
                if language == 'und' and 'language_ietf' in track.get('properties', {}):
                    language = track.get('properties', {}).get('language_ietf', 'und')
                
                # 获取默认轨道状态
                is_default = track.get('properties', {}).get('default_track', False)
                
                # 获取编解码器
                codec = track.get('codec', 'unknown')
                
                # 获取声道数（仅音频轨道）
                channels = 2  # 默认立体声
                if track_type == 'audio':
                    channels = track.get('properties', {}).get('audio_channels', 2)
                
                # 获取轨道名称
                track_name = track.get('properties', {}).get('track_name', '')
                
                track_info = {
                    'track_id': track_id,
                    'language': language,
                    'default': is_default,
                    'codec': codec,
                    'channels': channels,
                    'track_name': track_name,
                    'type': track_type
                }
                
                if track_type == 'subtitles':
                    subtitle_tracks.append(track_info)
                elif track_type == 'audio':
                    audio_tracks.append(track_info)
        
        # 按轨道ID排序
        subtitle_tracks.sort(key=lambda x: int(x['track_id']) if x['track_id'].isdigit() else 0)
        audio_tracks.sort(key=lambda x: int(x['track_id']) if x['track_id'].isdigit() else 0)
        
        return {
            'subtitle_tracks': subtitle_tracks,
            'audio_tracks': audio_tracks
        }
    
    def parse_mkvmerge_text_info(self, video_path):
        """使用mkvmerge -i解析文本输出"""
        try:
            cmd = [self.mkvmerge_path, '-i', str(video_path)]
            result = subprocess.run(
                cmd,
                capture_output=True,
                encoding='utf-8',
                errors='ignore',
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            if result.returncode != 0:
                return {'subtitle_tracks': [], 'audio_tracks': []}
            
            subtitle_tracks = []
            audio_tracks = []
            lines = result.stdout.split('\n')
            
            for line in lines:
                line = line.strip()
                if 'subtitles' in line.lower():
                    # 提取轨道ID
                    track_match = re.search(r'Track ID (\d+):', line)
                    if track_match:
                        track_id = track_match.group(1)
                        
                        # 提取语言信息
                        language = 'und'
                        lang_match = re.search(r'language:([a-z]{2,3})', line, re.IGNORECASE)
                        if lang_match:
                            language = lang_match.group(1).lower()
                        
                        # 检测默认轨道
                        is_default = 'default track: yes' in line.lower()
                        
                        subtitle_tracks.append({
                            'track_id': track_id,
                            'language': language,
                            'default': is_default,
                            'type': 'subtitles'
                        })
                
                elif 'audio' in line.lower():
                    # 提取轨道ID
                    track_match = re.search(r'Track ID (\d+):', line)
                    if track_match:
                        track_id = track_match.group(1)
                        
                        # 提取语言信息
                        language = 'und'
                        lang_match = re.search(r'language:([a-z]{2,3})', line, re.IGNORECASE)
                        if lang_match:
                            language = lang_match.group(1).lower()
                        
                        # 检测默认轨道
                        is_default = 'default track: yes' in line.lower()
                        
                        # 提取轨道名称
                        track_name = ''
                        name_match = re.search(r'track name:([^,]+)', line, re.IGNORECASE)
                        if name_match:
                            track_name = name_match.group(1).strip()
                        
                        # 提取声道数
                        channels = 2  # 默认立体声
                        channels_match = re.search(r'(\d+) channels', line, re.IGNORECASE)
                        if channels_match:
                            channels = int(channels_match.group(1))
                        
                        # 提取编解码器
                        codec = 'unknown'
                        codec_match = re.search(r'codec ID:([^,]+)', line, re.IGNORECASE)
                        if codec_match:
                            codec = codec_match.group(1).strip()
                        
                        audio_tracks.append({
                            'track_id': track_id,
                            'language': language,
                            'default': is_default,
                            'track_name': track_name,
                            'channels': channels,
                            'codec': codec,
                            'type': 'audio'
                        })
            
            # 按轨道ID排序
            subtitle_tracks.sort(key=lambda x: int(x['track_id']) if x['track_id'].isdigit() else 0)
            audio_tracks.sort(key=lambda x: int(x['track_id']) if x['track_id'].isdigit() else 0)
            
            return {
                'subtitle_tracks': subtitle_tracks,
                'audio_tracks': audio_tracks
            }
            
        except Exception as e:
            print(f"mkvmerge文本解析失败: {e}")
            return {'subtitle_tracks': [], 'audio_tracks': []}
    
    def extract_subtitle_with_mkvextract(self, video_path, track_id, output_path):
        """使用mkvextract提取字幕轨道"""
        try:
            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 如果文件已存在，先删除
            if output_path.exists():
                output_path.unlink()
            
            cmd = [
                self.mkvextract_path, 'tracks', str(video_path),
                f"{track_id}:{output_path}"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                encoding='utf-8',
                errors='ignore',
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                timeout=60
            )
            
            if result.returncode == 0 and output_path.exists():
                return True
            else:
                print(f"mkvextract提取失败: {result.stderr[:200] if result.stderr else '未知错误'}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"mkvextract提取字幕轨道{track_id}超时")
            return False
        except Exception as e:
            print(f"mkvextract提取字幕轨道{track_id}失败: {e}")
            return False
    
    def extract_audio_track(self, video_path, track_index, track_info, output_path):
        """提取音频轨道，根据是否转换5.1决定使用原始编码或WAV格式"""
        try:
            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 如果文件已存在，先删除
            if output_path.exists():
                output_path.unlink()
            
            if self.stereo_to_5_1 == 1:
                # 如果需要5.1转换，提取为WAV格式（m.py需要WAV输入）
                cmd = [
                    self.ffmpeg_path, '-i', str(video_path),
                    '-map', f'0:a:{track_index}',
                    '-c:a', 'pcm_s16le',  # 转换为16位PCM WAV格式
                    '-ar', '44100',       # 44.1kHz采样率
                    '-ac', '2',           # 立体声
                    '-y',                 # 覆盖现有文件
                    str(output_path)
                ]
            else:
                # 如果不转换5.1，保持原始编码
                # 根据原始编码选择合适的容器格式
                codec = track_info.get('codec', '').lower()
                
                # 设置输出文件扩展名
                if 'aac' in codec:
                    output_path = output_path.with_suffix('.m4a')
                elif 'ac3' in codec or 'dolby' in codec:
                    output_path = output_path.with_suffix('.ac3')
                elif 'dts' in codec:
                    output_path = output_path.with_suffix('.dts')
                elif 'mp3' in codec:
                    output_path = output_path.with_suffix('.mp3')
                elif 'opus' in codec:
                    output_path = output_path.with_suffix('.opus')
                else:
                    # 默认使用mka容器（Matroska Audio）
                    output_path = output_path.with_suffix('.mka')
                
                # 使用copy参数保持原始编码
                cmd = [
                    self.ffmpeg_path, '-i', str(video_path),
                    '-map', f'0:a:{track_index}',
                    '-c:a', 'copy',  # 复制原始编码
                    '-y',
                    str(output_path)
                ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                encoding='utf-8',
                errors='ignore',
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                timeout=180
            )
            
            if result.returncode == 0 and output_path.exists():
                print(f"OK 成功提取音频轨道{track_index + 1}")
                return True, output_path
            else:
                print(f"× 提取音频轨道{track_index + 1}失败")
                if result.stderr:
                    print(f"错误信息: {result.stderr[:200]}")
                return False, None
                
        except subprocess.TimeoutExpired:
            print(f"提取音频轨道{track_index + 1}超时")
            return False, None
        except Exception as e:
            print(f"提取音频轨道{track_index + 1}失败: {e}")
            return False, None
    
    def convert_audio_to_5_1(self, audio_file_path):
        """使用m.py转换音频为5.1声道，并显示m.py的日志"""
        if not self.audio_converter_path.exists():
            print("m.py文件未找到")
            return None
        
        try:
            print(f"调用m.py转换音频: {audio_file_path.name}")
            
            # 调用m.py进行转换，并实时显示输出
            cmd = [str(self.python_path), str(self.audio_converter_path), str(audio_file_path)]
            
            # 使用Popen实时获取输出
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 将标准错误重定向到标准输出
                encoding='utf-8',
                errors='ignore',
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                bufsize=1,
                universal_newlines=True
            )
            
            # 实时读取并打印输出，处理进度条显示
            print("-" * 30 + " m.py日志开始 " + "-" * 30)
            in_progress_section = False
            progress_line = ""
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    line = output.strip()
                    
                    # 检测是否进入进度部分
                    if "分离进度:" in line:
                        in_progress_section = True
                        # 对于进度条，覆盖显示
                        print(f"\r{line}", end="", flush=True)
                        progress_line = line
                    elif in_progress_section and ("ETA:" in line or "用时:" in line):
                        # 进度部分结束
                        in_progress_section = False
                        # 如果已经有进度行，先打印换行
                        if progress_line:
                            print()  # 换行
                        print(line)
                        progress_line = ""
                    else:
                        # 如果之前有进度行，先打印换行
                        if progress_line and not in_progress_section:
                            print()  # 换行
                            progress_line = ""
                        print(line)
            
            # 确保最后有换行
            if progress_line:
                print()
            print("-" * 30 + " m.py日志结束 " + "-" * 30)
            
            returncode = process.poll()
            
            if returncode == 0:
                print("m.py转换完成")
                
                # 查找生成的5.1音频文件
                # m.py通常会在输入文件同目录生成"文件名 5.1.ac3"
                expected_file = audio_file_path.parent / f"{audio_file_path.stem} 5.1.ac3"
                
                if expected_file.exists():
                    return expected_file
                else:
                    # 查找其他可能的输出文件
                    potential_files = list(audio_file_path.parent.glob(f"*5.1*.ac3"))
                    if potential_files:
                        return potential_files[0]
                    else:
                        # 尝试查找WAV格式
                        potential_files = list(audio_file_path.parent.glob(f"*5.1*.wav"))
                        if potential_files:
                            return potential_files[0]
                        else:
                            print("未找到转换后的5.1音频文件")
                            return None
            else:
                print(f"m.py转换失败，返回码: {returncode}")
                return None
        except subprocess.TimeoutExpired:
            print("m.py转换超时")
            return None
        except Exception as e:
            print(f"调用m.py失败: {e}")
            return None
    
    def apply_default_settings(self, media_info):
        """应用多音轨多字幕默认属性"""
        if self.default_settings_mode == 0:
            # 模式0: 保持原视频的默认音频和字幕设置
            print("使用模式0: 保持原视频的默认设置")
            return media_info
        
        # 模式1: 将中文音轨和字幕设为默认
        print("使用模式1: 将中文音轨和字幕设为默认")
        
        # 处理音频轨道
        audio_tracks_modified = False
        for track in media_info.get('audio_tracks', []):
            original_default = track['default']
            
            if self.is_chinese_language(track['language']):
                track['default'] = True
                if original_default != track['default']:
                    audio_tracks_modified = True
                    print(f"  音频轨道{track['track_id']}: 设为默认 (中文)")
            else:
                track['default'] = False
                if original_default != track['default']:
                    audio_tracks_modified = True
                    print(f"  音频轨道{track['track_id']}: 设为非默认 (非中文)")
        
        if not audio_tracks_modified and media_info.get('audio_tracks'):
            print("  音频轨道默认状态无需修改")
        
        # 处理字幕轨道
        subtitle_tracks_modified = False
        for track in media_info.get('subtitle_tracks', []):
            original_default = track['default']
            
            if self.is_chinese_language(track['language']):
                track['default'] = True
                if original_default != track['default']:
                    subtitle_tracks_modified = True
                    print(f"  字幕轨道{track['track_id']}: 设为默认 (中文)")
            else:
                track['default'] = False
                if original_default != track['default']:
                    subtitle_tracks_modified = True
                    print(f"  字幕轨道{track['track_id']}: 设为非默认 (非中文)")
        
        if not subtitle_tracks_modified and media_info.get('subtitle_tracks'):
            print("  字幕轨道默认状态无需修改")
        
        return media_info
    
    def is_chinese_language(self, language_code):
        """检查是否为中文语言"""
        chinese_codes = ['chi', 'zh', 'chs', 'zho', 'chinese', 'zh-cn', 'zh-tw', 'zh-hk', 'zh-mo']
        language_code_lower = str(language_code).lower()
        
        for code in chinese_codes:
            if code in language_code_lower:
                return True
        
        if language_code_lower.startswith('zh'):
            return True
            
        return False
    
    def get_ass_title(self, ass_file_path):
        """读取ASS文件的Title信息"""
        try:
            with open(ass_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('Title:'):
                        return line.split(':', 1)[1].strip()
        except Exception as e:
            print(f"读取ASS文件Title失败: {e}")
        return ""
    
    def set_ass_title(self, ass_file_path, new_title):
        """修改ASS文件的Title信息"""
        try:
            with open(ass_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            title_found = False
            with open(ass_file_path, 'w', encoding='utf-8') as f:
                for line in lines:
                    if line.strip().startswith('Title:'):
                        f.write(f"Title: {new_title}\n")
                        title_found = True
                    elif line.strip().startswith('[Events]'):
                        # 如果在Events段前还没找到Title，添加Title
                        if not title_found:
                            f.write(f"Title: {new_title}\n")
                            title_found = True
                        f.write(line)
                    else:
                        f.write(line)
            
            # 如果整个文件都没有找到Title或[Events]，添加到文件末尾
            if not title_found:
                with open(ass_file_path, 'a', encoding='utf-8') as f:
                    f.write(f"\nTitle: {new_title}\n")
            
            return True
        except Exception as e:
            print(f"修改ASS文件Title失败: {e}")
            return False
    
    def get_language_name(self, language_code):
        """获取语言名称"""
        language_names = {
            'chi': '中文', 'zh': '中文', 'chs': '中文', 'chinese': '中文',
            'kor': '韩语', 'ko': '韩语', 'korean': '韩语',
            'jpn': '日语', 'ja': '日语', 'japanese': '日语',
            'eng': '英语', 'en': '英语', 'english': '英语',
            'und': '未知语言'
        }
        return language_names.get(language_code.lower(), f"语言{language_code}")
    
    def process_with_k_py(self, subtitle_path):
        """使用k.py处理字幕文件"""
        if not self.karaoke_processor_path.exists():
            print("k.py文件未找到")
            return None
        
        try:
            # 生成唯一的输出文件路径，不依赖固定后缀
            output_path = Path(subtitle_path).parent / f"{Path(subtitle_path).stem}_k_processed.ass"
            
            # 使用-o参数指定输出路径，避免依赖固定的输出文件名格式
            cmd = [
                str(self.python_path), 
                str(self.karaoke_processor_path), 
                str(subtitle_path),
                "-o", str(output_path),
                "-ow"  # 自动覆盖已存在的文件
            ]
            
            print(f"调用k.py处理: {Path(subtitle_path).name}")
            
            # 添加调试信息
            print(f"k.py路径: {self.karaoke_processor_path}")
            print(f"字幕文件: {subtitle_path}")
            print(f"指定输出路径: {output_path}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                encoding='utf-8',
                errors='ignore',
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                timeout=180
            )
            
            print(f"k.py返回码: {result.returncode}")
            
            if result.returncode == 0:
                print("k.py处理完成")
                
                # 显示k.py的输出
                if result.stdout:
                    print(f"k.py输出: {result.stdout[:500]}")
                
                # 检查指定的输出文件是否存在
                if output_path.exists():
                    print(f"找到卡拉OK效果输出文件: {output_path}")
                    return output_path
                else:
                    # 如果指定的输出文件不存在，尝试查找其他可能的输出
                    print(f"指定的输出文件不存在，搜索其他可能的输出...")
                    
                    # 显示k.py的完整输出，以便调试
                    if result.stdout:
                        print(f"k.py完整输出: {result.stdout}")
                    if result.stderr:
                        print(f"k.py错误输出: {result.stderr}")
                    
                    # 尝试查找所有.ass文件
                    all_ass_files = list(Path(subtitle_path).parent.glob("*.ass"))
                    print(f"找到所有ASS文件: {[str(f) for f in all_ass_files]}")
                    
                    if len(all_ass_files) > 1:
                        # 排除原始文件，使用最新创建的文件
                        original_file = Path(subtitle_path)
                        latest_file = max(all_ass_files, key=lambda x: x.stat().st_mtime)
                        if latest_file != original_file:
                            print(f"使用最新创建的文件: {latest_file}")
                            return latest_file
                    
                    print(f"未找到卡拉OK效果输出文件，使用原始文件")
                    return subtitle_path
            else:
                print(f"k.py处理失败: {result.stderr[:500] if result.stderr else '未知错误'}")
                if result.stdout:
                    print(f"k.py输出: {result.stdout}")
                return None
        except Exception as e:
            print(f"调用k.py失败: {e}")
            return None
    
    def process_with_t_py(self, subtitle_path):
        """使用T.py处理字幕文件（提词器效果）"""
        if not self.prompter_processor_path.exists():
            print("T.py文件未找到")
            return None
        
        try:
            # 生成唯一的输出文件路径，不依赖固定后缀
            output_path = Path(subtitle_path).parent / f"{Path(subtitle_path).stem}_t_processed.ass"
            
            # 使用-o参数指定输出路径，避免依赖固定的输出文件名格式
            cmd = [
                str(self.python_path), 
                str(self.prompter_processor_path), 
                str(subtitle_path),
                "-o", str(output_path)
            ]
            
            print(f"调用T.py处理提词器效果: {Path(subtitle_path).name}")
            
            # 添加调试信息
            print(f"T.py路径: {self.prompter_processor_path}")
            print(f"字幕文件: {subtitle_path}")
            print(f"指定输出路径: {output_path}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                encoding='utf-8',
                errors='ignore',
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                timeout=180
            )
            
            print(f"T.py返回码: {result.returncode}")
            
            if result.returncode == 0:
                print("T.py处理完成")
                
                # 显示T.py的输出
                if result.stdout:
                    print(f"T.py输出: {result.stdout[:500]}")
                
                # 检查指定的输出文件是否存在
                if output_path.exists():
                    print(f"找到提词器输出文件: {output_path}")
                    return output_path
                else:
                    # 如果指定的输出文件不存在，尝试查找其他可能的输出
                    print(f"指定的输出文件不存在，搜索其他可能的输出...")
                    
                    # 显示T.py的完整输出，以便调试
                    if result.stdout:
                        print(f"T.py完整输出: {result.stdout}")
                    if result.stderr:
                        print(f"T.py错误输出: {result.stderr}")
                    
                    # 尝试查找所有.ass文件
                    all_ass_files = list(Path(subtitle_path).parent.glob("*.ass"))
                    print(f"找到所有ASS文件: {[str(f) for f in all_ass_files]}")
                    
                    if len(all_ass_files) > 1:
                        # 排除原始文件，使用最新创建的文件
                        original_file = Path(subtitle_path)
                        latest_file = max(all_ass_files, key=lambda x: x.stat().st_mtime)
                        if latest_file != original_file:
                            print(f"使用最新创建的文件: {latest_file}")
                            return latest_file
                    
                    print(f"未找到提词器输出文件，使用原始文件")
                    return subtitle_path
            else:
                print(f"T.py处理失败: {result.stderr[:500] if result.stderr else '未知错误'}")
                if result.stdout:
                    print(f"T.py输出: {result.stdout}")
                return None
        except Exception as e:
            print(f"调用T.py失败: {e}")
            return None
    
    def rebuild_mkv_final(self, video_path, subtitle_tracks, audio_tracks_info, output_path=None):
        """使用mkvmerge重新打包最终MKV文件"""
        if not self.check_mkvtoolnix_available():
            print("mkvmerge不可用，无法重新打包")
            return None
        
        # 如果没有提供输出路径，生成默认输出路径
        if output_path is None:
            output_path = self.generate_output_filename(video_path)
        
        print(f"\n使用mkvmerge重新打包...")
        print(f"输出文件: {output_path}")
        
        try:
            # 构建mkvmerge命令
            cmd = [self.mkvmerge_path, '-o', str(output_path)]
            
            # 添加视频文件（移除原字幕和原始音频轨道）
            cmd.extend(['--no-subtitles', '--no-audio'])
            
            # 添加视频文件
            cmd.append(str(video_path))
            
            # 添加音频轨道（不保留原始音轨）
            for track_info in audio_tracks_info:
                audio_path = track_info.get('path')
                language = track_info.get('language', 'und')
                is_default = track_info.get('default', False)
                original_id = track_info.get('original_track_id', '1')
                
                if audio_path and Path(audio_path).exists():
                    # 添加音频轨道
                    cmd.extend(['--language', f'0:{language}'])
                    
                    # 不设置轨道名称
                    # 设置默认轨道状态
                    if is_default:
                        cmd.extend(['--default-track', '0:yes'])
                        print(f"添加音频轨道 {original_id}: 语言={language}, 默认=是")
                    else:
                        cmd.extend(['--default-track', '0:no'])
                        print(f"添加音频轨道 {original_id}: 语言={language}, 默认=否")
                    
                    cmd.append(str(audio_path))
                else:
                    print(f"× 跳过音频轨道{original_id}: 音频文件不存在")
            
            # 添加处理后的字幕轨道
            for track_info in subtitle_tracks:
                subtitle_path = track_info.get('path')
                language = track_info.get('language', 'und')
                is_default = track_info.get('is_default', False)
                original_id = track_info.get('original_track_id', '1')
                
                if subtitle_path and Path(subtitle_path).exists():
                    # 获取字幕文件的Title作为轨道名称
                    track_name = self.get_ass_title(subtitle_path)
                    if not track_name:
                        # 如果没有Title，使用默认名称（默认效果不添加说明）
                        if 'mode0' in subtitle_path.name or 'ass_0' in subtitle_path.name:
                            track_name = ""  # 默认效果不添加说明
                        elif 'mode1' in subtitle_path.name or 'ass_1' in subtitle_path.name:
                            track_name = "KTV效果"
                        elif 'mode2' in subtitle_path.name or 'ass_2' in subtitle_path.name:
                            track_name = "提词器效果"
                        else:
                            track_name = ""
                    
                    # 添加字幕轨道
                    cmd.extend(['--language', f'0:{language}'])
                    
                    # 设置轨道名称（默认效果不添加说明）
                    if track_name:
                        cmd.extend(['--track-name', f'0:{track_name}'])
                    
                    # 设置默认轨道状态
                    if is_default:
                        cmd.extend(['--default-track', '0:yes'])
                        print(f"添加字幕轨道 {original_id}: 语言={language}, 默认=是, 名称={track_name}")
                    else:
                        cmd.extend(['--default-track', f'0:no'])
                        print(f"添加字幕轨道 {original_id}: 语言={language}, 默认=否, 名称={track_name}")
                    
                    cmd.append(str(subtitle_path))
                else:
                    print(f"× 跳过字幕轨道{original_id}: 字幕文件不存在")
            
            # 注意：已移除添加字体文件的代码，不再添加字体附件
            
            # 执行mkvmerge命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                encoding='utf-8',
                errors='ignore',
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                timeout=300
            )
            
            if result.returncode == 0:
                print(f"OK MKV打包完成: {output_path}")
                return output_path
            else:
                print(f"× MKV打包命令返回非零退出码")
                if result.stderr:
                    print(f"错误信息: {result.stderr[:500]}")
                # 检查输出文件是否实际存在
                if Path(output_path).exists() and Path(output_path).stat().st_size > 0:
                    print(f"✓ 但输出文件已成功生成: {output_path}")
                    return output_path
                else:
                    print(f"× 输出文件未生成或为空")
                    return None
                
        except subprocess.TimeoutExpired:
            print("MKV打包超时")
            return None
        except Exception as e:
            print(f"MKV打包过程出错: {e}")
            return None
    
    def process_single_video(self, video_path, output_dir=None, is_batch=False):
        """处理单个视频文件"""
        video_path = Path(video_path)
        
        if not video_path.exists():
            print(f"视频文件不存在: {video_path}")
            return None
        
        # 设置缓存
        self.setup_cache()
        
        # 检查文件是否包含ASS相关标签
        has_ass1_tag = ' (ASS_1)' in video_path.name
        has_ass_k_tag = ' (ASS_K)' in video_path.name
        has_ass_t_tag = ' (ASS_T)' in video_path.name
        has_ass_tag = ' (ASS)' in video_path.name
        
        # 任何ASS相关标签都需要进一步处理
        has_any_ass_tag = has_ass1_tag or has_ass_k_tag or has_ass_t_tag or has_ass_tag
        
        original_subtitle_mode = self.subtitle_mode
        ass1_tag_detected = False
        current_title = ""
        
        if has_any_ass_tag:
            # 检测到ASS相关标签，需要进一步处理
            print("⚠️  检测到ASS相关标签，正在检查字幕式样...")
            
            # 获取媒体信息，查看字幕轨道
            media_info = self.get_media_info_with_mkvmerge(video_path)
            subtitle_tracks = media_info.get('subtitle_tracks', [])
            
            if subtitle_tracks:
                # 提取第一个字幕轨道来检查Title
                track_id = subtitle_tracks[0]['track_id']
                temp_subtitle = self.cache_dir / f"temp_check_title.ass"
                
                if self.extract_subtitle_with_mkvextract(video_path, track_id, temp_subtitle):
                    current_title = self.get_ass_title(temp_subtitle)
                    print(f"当前字幕Title: {current_title}")
                    
                    # 根据Title和当前subtitle_mode决定处理方式
                    if self.subtitle_mode == 1:  # 目标是KTV效果
                        if "KTV效果" in current_title:
                            print("✅ 已是KTV效果，无需转换")
                            self.subtitle_mode = 0  # 无需处理
                            ass1_tag_detected = True
                        elif "提词器效果" in current_title:
                            print("🔄 需要从提词器效果转换为KTV效果")
                            # 需要先用T文件还原，再用K文件转换
                            # 保持subtitle_mode为1，后面会处理
                            ass1_tag_detected = True
                    elif self.subtitle_mode == 2:  # 目标是提词器效果
                        if "提词器效果" in current_title:
                            print("✅ 已是提词器效果，无需转换")
                            self.subtitle_mode = 0  # 无需处理
                            ass1_tag_detected = True
                        elif "KTV效果" in current_title:
                            print("🔄 需要从KTV效果转换为提词器效果")
                            # 需要先用K文件还原，再用T文件转换
                            # 保持subtitle_mode为2，后面会处理
                            ass1_tag_detected = True
                else:
                    print("❌ 提取字幕失败，无法检查Title")
                    self.subtitle_mode = 0  # 跳过处理
                    ass1_tag_detected = True
            else:
                print("❌ 未找到字幕轨道，无法检查Title")
                self.subtitle_mode = 0  # 跳过处理
                ass1_tag_detected = True
        
        try:
            print("=" * 60)
            print(f"处理视频: {video_path.name}")
            print(f"多音轨多字幕默认属性: {'0-保持原样' if self.default_settings_mode == 0 else '1-中文设为默认'}")
            print(f"立体声转5.1: {'开启' if self.stereo_to_5_1 == 1 else '关闭'}")
            print(f"字幕处理模式: {self.subtitle_mode} ({self.get_subtitle_mode_name()})")
            print("=" * 60)
            
            # 检查是否有任何修改需要进行
            if self.subtitle_mode == 0 and self.stereo_to_5_1 == 0:
                # 当subtitle_mode为0且检测到ASS相关标签时，执行还原操作
                if has_any_ass_tag:
                    print("\n执行还原操作:")
                    print("-" * 30)
                    print("原因: 检测到ASS相关标签，且字幕处理模式为关闭，执行还原操作")
                    # 继续处理，执行还原
                else:
                    print("\n无需处理:")
                    print("-" * 30)
                    print("原因: 字幕处理模式为关闭，且立体声转5.1也为关闭")
                    print("没有对文件进行任何修改，因此不生成输出文件")
                    print("=" * 60)
                    return None
            
            # 获取媒体信息
            print("\n步骤1: 获取媒体信息")
            print("-" * 30)
            media_info = self.get_media_info_with_mkvmerge(video_path)
            
            # 显示原始轨道信息
            print("\n原始轨道信息:")
            print("-" * 30)
            
            if media_info.get('audio_tracks'):
                print("音频轨道:")
                for track in media_info['audio_tracks']:
                    status = "默认" if track['default'] else "非默认"
                    channels = f"{track.get('channels', 2)}声道"
                    codec = track.get('codec', '未知')
                    print(f"  轨道{track['track_id']}: {self.get_language_name(track['language'])} - {status} - {channels} - {codec}")
            
            if media_info.get('subtitle_tracks'):
                print("\n字幕轨道:")
                for track in media_info['subtitle_tracks']:
                    status = "默认" if track['default'] else "非默认"
                    print(f"  轨道{track['track_id']}: {self.get_language_name(track['language'])} - {status}")
            
            # 应用默认设置模式
            print("\n应用默认设置...")
            print("-" * 30)
            media_info = self.apply_default_settings(media_info)
            
            # 处理音频轨道
            print("\n步骤2: 处理音频轨道")
            print("-" * 30)
            
            processed_audio_tracks = []
            audio_tracks = media_info.get('audio_tracks', [])
            audio_processed = False
            
            if self.stereo_to_5_1 == 1 and audio_tracks:
                # 处理所有音频轨道为5.1声道，不保留原始音轨
                print(f"开始处理{len(audio_tracks)}个音频轨道为5.1声道（不保留原始音轨）...")
                
                for i, track_info in enumerate(audio_tracks):
                    track_id = track_info['track_id']
                    language = track_info['language']
                    language_name = self.get_language_name(language)
                    is_default = track_info['default']
                    channels = track_info.get('channels', 2)
                    
                    print(f"\n处理音频轨道{track_id}: {language_name}")
                    
                    # 检查是否已经是5.1声道
                    if channels >= 6:
                        print(f"  音频轨道{track_id}已经是{channels}声道，跳过转换")
                        # 提取音频轨道到临时文件，保持原始编码
                        audio_filename = f"audio_track_{track_id}_{language}"
                        output_audio = self.cache_dir / audio_filename
                        
                        success, extracted_audio_path = self.extract_audio_track(video_path, i, track_info, output_audio)
                        if success:
                            processed_audio_tracks.append({
                                'path': extracted_audio_path,
                                'language': language,
                                'default': is_default,
                                'track_name': track_info.get('track_name', ''),
                                'original_track_id': track_id,
                                'is_5_1': True
                            })
                            print(f"  OK 成功提取音频轨道{track_id}，保持原始编码")
                        else:
                            print(f"  × 提取音频轨道{track_id}失败，跳过此轨道")
                    else:
                        # 提取音频轨道到临时文件（WAV格式）
                        audio_filename = f"audio_track_{track_id}_{language}.wav"
                        output_audio = self.cache_dir / audio_filename
                        
                        success, extracted_audio_path = self.extract_audio_track(video_path, i, track_info, output_audio)
                        if success:
                            # 转换音频为5.1声道
                            print(f"  转换音频轨道{track_id}为5.1声道...")
                            converted_file = self.convert_audio_to_5_1(extracted_audio_path)
                            
                            if converted_file and converted_file.exists():
                                # 将转换后的文件复制到缓存目录
                                output_5_1 = self.cache_dir / f"audio_5_1_track_{track_id}_{language}{converted_file.suffix}"
                                shutil.copy2(converted_file, output_5_1)
                                
                                processed_audio_tracks.append({
                                    'path': output_5_1,
                                    'language': language,
                                    'default': is_default,
                                    'track_name': track_info.get('track_name', ''),
                                    'original_track_id': track_id,
                                    'is_5_1': True
                                })
                                print(f"  OK 成功转换为5.1声道")
                                audio_processed = True
                            else:
                                print(f"  × 转换5.1声道失败，跳过此轨道")
                        else:
                            print(f"  × 提取音频轨道{track_id}失败，跳过此轨道")
            else:
                # 不转换音频，直接使用原始音频编码
                print(f"立体声转5.1已关闭，使用原始音频编码")
                
                for i, track_info in enumerate(audio_tracks):
                    track_id = track_info['track_id']
                    language = track_info['language']
                    language_name = self.get_language_name(language)
                    is_default = track_info['default']
                    codec = track_info.get('codec', '未知')
                    
                    print(f"\n处理音频轨道{track_id}: {language_name} ({codec})")
                    
                    # 提取音频轨道到临时文件，保持原始编码
                    audio_filename = f"audio_track_{track_id}_{language}"
                    output_audio = self.cache_dir / audio_filename
                    
                    success, extracted_audio_path = self.extract_audio_track(video_path, i, track_info, output_audio)
                    if success:
                        processed_audio_tracks.append({
                            'path': extracted_audio_path,
                            'language': language,
                            'default': is_default,
                            'track_name': track_info.get('track_name', ''),
                            'original_track_id': track_id,
                            'is_5_1': False
                        })
                        print(f"OK 成功提取音频轨道{track_id}，保持原始编码")
                    else:
                        print(f"× 提取音频轨道{track_id}失败，跳过此轨道")
            
            # 处理字幕轨道
            print("\n步骤3: 处理字幕轨道")
            print("-" * 30)
            
            processed_subtitle_tracks = []
            subtitle_tracks = media_info.get('subtitle_tracks', [])
            subtitle_processed = False
            
            # 判断是否需要处理字幕：subtitle_mode>0 或 subtitle_mode=='A' 或 (subtitle_mode==0且有ASS相关标签)需要还原
            subtitle_mode_needs_processing = False
            if isinstance(self.subtitle_mode, str):
                # 字符串类型，检查是否为'A'
                subtitle_mode_needs_processing = self.subtitle_mode == 'A'
            else:
                # 数值类型，检查是否>0或==0且有ASS标签
                subtitle_mode_needs_processing = self.subtitle_mode > 0 or (self.subtitle_mode == 0 and has_any_ass_tag)
            
            # 过滤掉已经包含KTV效果或提词器效果的轨道
            processed_subtitle_tracks_info = []
            for track in subtitle_tracks:
                # 提取字幕轨道到临时文件，检查Title
                temp_subtitle = self.cache_dir / f"temp_check_title_{track['track_id']}.ass"
                if self.extract_subtitle_with_mkvextract(video_path, track['track_id'], temp_subtitle):
                    track_title = self.get_ass_title(temp_subtitle)
                    # 如果轨道已经包含KTV效果或提词器效果，跳过处理
                    if "KTV效果" in track_title or "提词器效果" in track_title:
                        print(f"  跳过字幕轨道{track['track_id']}: 已包含特效字幕")
                        continue
                # 添加到待处理列表
                processed_subtitle_tracks_info.append(track)
            
            if subtitle_mode_needs_processing and processed_subtitle_tracks_info:
                print(f"开始处理{len(processed_subtitle_tracks_info)}个字幕轨道...")
                subtitle_processed = True
                
                for i, track_info in enumerate(processed_subtitle_tracks_info):
                    track_id = track_info['track_id']
                    language = track_info['language']
                    language_name = self.get_language_name(track_info['language'])
                    is_default = track_info['default']
                    
                    print(f"\n处理字幕轨道{track_id}: {language_name}")
                    
                    # 提取字幕轨道到临时文件
                    subtitle_filename = f"subtitle_track_{track_id}_{language}.ass"
                    output_subtitle = self.cache_dir / subtitle_filename
                    
                    if self.extract_subtitle_with_mkvextract(video_path, track_id, output_subtitle):
                        # 根据字幕处理模式选择处理方式
                        if self.subtitle_mode == 'A':
                            # 模式A: 全部效果打包，为每个轨道应用所有效果
                            print(f"  开始应用全部效果到字幕轨道{track_id}...")
                            
                            # 处理模式0: 默认原始效果
                            print(f"  1. 处理模式0（默认原始效果）...")
                            if has_any_ass_tag:
                                # 检测到ASS相关标签，需要还原字幕
                                print(f"    正在还原字幕...")
                                restore_output_path = self.cache_dir / f"{Path(output_subtitle).stem}_restored_mode0.ass"
                                
                                if "KTV效果" in current_title:
                                    # 使用k.py还原KTV效果
                                    print(f"    用k.py还原KTV效果字幕...")
                                    cmd = [
                                        str(self.python_path), 
                                        str(self.karaoke_processor_path), 
                                        str(output_subtitle),
                                        "-o", str(restore_output_path),
                                        "-ow",  # 自动覆盖已存在的文件
                                        "-r"   # 还原模式
                                    ]
                                    result = subprocess.run(
                                        cmd,
                                        capture_output=True,
                                        encoding='utf-8',
                                        errors='ignore',
                                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                                        timeout=180
                                    )
                                    if result.returncode == 0 and restore_output_path.exists():
                                        print(f"    ✓ KTV效果还原成功")
                                        mode0_output = restore_output_path
                                        mode0_processed = True
                                    else:
                                        print(f"    ❌ KTV效果还原失败，使用原始字幕")
                                        mode0_output = output_subtitle
                                        mode0_processed = False
                                elif "提词器效果" in current_title:
                                    # 使用T.py还原提词器效果
                                    print(f"    用T.py还原提词器效果字幕...")
                                    cmd = [
                                        str(self.python_path), 
                                        str(self.prompter_processor_path), 
                                        str(output_subtitle),
                                        "-o", str(restore_output_path),
                                        "-r"   # 还原模式
                                    ]
                                    result = subprocess.run(
                                        cmd,
                                        capture_output=True,
                                        encoding='utf-8',
                                        errors='ignore',
                                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                                        timeout=180
                                    )
                                    if result.returncode == 0 and restore_output_path.exists():
                                        print(f"    ✓ 提词器效果还原成功")
                                        mode0_output = restore_output_path
                                        mode0_processed = True
                                    else:
                                        print(f"    ❌ 提词器效果还原失败，使用原始字幕")
                                        mode0_output = output_subtitle
                                        mode0_processed = False
                                else:
                                    # 未知效果，使用原始字幕
                                    print(f"    未知效果类型，使用原始字幕")
                                    mode0_output = output_subtitle
                                    mode0_processed = False
                            else:
                                # 没有ASS相关标签，使用原始字幕
                                mode0_output = output_subtitle
                                mode0_processed = False
                                print(f"    字幕处理模式0，使用原始字幕")
                            
                            # 处理模式1: 真实卡拉OK效果
                            print(f"  2. 处理模式1（真实卡拉OK效果）...")
                            if has_any_ass_tag and "提词器效果" in current_title:
                                # 需要从提词器效果转换为KTV效果：先用T.py还原，再用k.py转换
                                print(f"    正在从提词器效果转换为KTV效果...")
                                print(f"    1. 先用T.py还原提词器效果字幕...")
                                # 生成唯一的输出文件路径用于还原
                                restore_output_path = self.cache_dir / f"{Path(output_subtitle).stem}_restored_mode1.ass"
                                # 使用T.py的还原模式
                                cmd = [
                                    str(self.python_path), 
                                    str(self.prompter_processor_path), 
                                    str(output_subtitle),
                                    "-o", str(restore_output_path),
                                    "-r"   # 还原模式
                                ]
                                result = subprocess.run(
                                    cmd,
                                    capture_output=True,
                                    encoding='utf-8',
                                    errors='ignore',
                                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                                    timeout=180
                                )
                                if result.returncode == 0 and restore_output_path.exists():
                                    print(f"    ✓ 提词器效果还原成功")
                                    print(f"    2. 再用k.py转换为KTV效果...")
                                    mode1_output = self.process_with_k_py(restore_output_path)
                                    mode1_processed = True
                                else:
                                    print(f"    ❌ 提词器效果还原失败，直接使用k.py处理")
                                    mode1_output = self.process_with_k_py(output_subtitle)
                                    mode1_processed = True
                            else:
                                # 直接使用k.py处理
                                mode1_output = self.process_with_k_py(output_subtitle)
                                mode1_processed = True
                            
                            # 处理模式2: 提词器效果
                            print(f"  3. 处理模式2（提词器效果）...")
                            if has_any_ass_tag and "KTV效果" in current_title:
                                # 需要从KTV效果转换为提词器效果：先用K文件还原，再用T文件转换
                                print(f"    正在从KTV效果转换为提词器效果...")
                                print(f"    1. 先用k.py还原KTV效果字幕...")
                                # 生成唯一的输出文件路径用于还原
                                restore_output_path = self.cache_dir / f"{Path(output_subtitle).stem}_restored_mode2.ass"
                                # 使用k.py的还原模式
                                cmd = [
                                    str(self.python_path), 
                                    str(self.karaoke_processor_path), 
                                    str(output_subtitle),
                                    "-o", str(restore_output_path),
                                    "-ow",  # 自动覆盖已存在的文件
                                    "-r"   # 还原模式
                                ]
                                result = subprocess.run(
                                    cmd,
                                    capture_output=True,
                                    encoding='utf-8',
                                    errors='ignore',
                                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                                    timeout=180
                                )
                                if result.returncode == 0 and restore_output_path.exists():
                                    print(f"    ✓ KTV效果还原成功")
                                    print(f"    2. 再用T.py转换为提词器效果...")
                                    mode2_output = self.process_with_t_py(restore_output_path)
                                    mode2_processed = True
                                else:
                                    print(f"    ❌ KTV效果还原失败，直接使用T.py处理")
                                    mode2_output = self.process_with_t_py(output_subtitle)
                                    mode2_processed = True
                            else:
                                # 直接使用T.py处理
                                mode2_output = self.process_with_t_py(output_subtitle)
                                mode2_processed = True
                            
                            # 将所有处理后的字幕轨道添加到列表中
                            for mode, output, is_processed in [(0, mode0_output, mode0_processed), (1, mode1_output, mode1_processed), (2, mode2_output, mode2_processed)]:
                                if output and Path(output).exists():
                                    # 检查文件大小，确保不是空文件
                                    file_size = Path(output).stat().st_size
                                    if file_size > 100:  # 至少100字节
                                        # 将处理后的文件复制到缓存目录
                                        suffix = f"_ass_{mode}" if is_processed else f"_mode{mode}"
                                        output_processed = self.cache_dir / f"subtitle{suffix}_{track_id}_{language}.ass"
                                        shutil.copy2(output, output_processed)
                                        
                                        # 根据模式设置不同的Title（默认效果不添加说明）
                                        if mode == 0:
                                            title = ""  # 默认效果不添加说明
                                        elif mode == 1:
                                            title = "KTV效果"
                                        elif mode == 2:
                                            title = "提词器效果"
                                        
                                        # 修改ASS文件的Title（默认效果不添加说明）
                                        if title:
                                            self.set_ass_title(output_processed, title)
                                        
                                        processed_subtitle_tracks.append({
                                            'path': output_processed,
                                            'language': language,
                                            'is_default': is_default if mode == 0 else False,  # 只有模式0设为默认
                                            'original_track_id': track_id,
                                            'is_processed': is_processed
                                        })
                                        print(f"    OK 成功处理字幕轨道（模式{mode}，大小: {file_size} 字节，Title: {title}）")
                                    else:
                                        print(f"    × 处理后的字幕文件太小（模式{mode}，{file_size} 字节），可能处理失败")
                                        processed_subtitle_tracks.append({
                                            'path': output_subtitle,
                                            'language': language,
                                            'is_default': is_default if mode == 0 else False,
                                            'original_track_id': track_id,
                                            'is_processed': False
                                        })
                                else:
                                    print(f"    × 字幕处理失败（模式{mode}），使用原始字幕")
                                    processed_subtitle_tracks.append({
                                        'path': output_subtitle,
                                        'language': language,
                                        'is_default': is_default if mode == 0 else False,
                                        'original_track_id': track_id,
                                        'is_processed': False
                                    })
                        elif self.subtitle_mode == 1:
                            # 模式1: 真实卡拉OK效果
                            if has_any_ass_tag and "提词器效果" in current_title:
                                # 需要从提词器效果转换为KTV效果：先用T.py还原，再用k.py转换
                                print(f"  正在从提词器效果转换为KTV效果...")
                                print(f"  1. 先用T.py还原提词器效果字幕...")
                                # 生成唯一的输出文件路径用于还原
                                restore_output_path = self.cache_dir / f"{Path(output_subtitle).stem}_restored.ass"
                                # 使用T.py的还原模式
                                cmd = [
                                    str(self.python_path), 
                                    str(self.prompter_processor_path), 
                                    str(output_subtitle),
                                    "-o", str(restore_output_path),
                                    "-r"   # 还原模式
                                ]
                                result = subprocess.run(
                                    cmd,
                                    capture_output=True,
                                    encoding='utf-8',
                                    errors='ignore',
                                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                                    timeout=180
                                )
                                if result.returncode == 0 and restore_output_path.exists():
                                    print(f"  ✓ 提词器效果还原成功")
                                    print(f"  2. 再用k.py转换为KTV效果...")
                                    k_output = self.process_with_k_py(restore_output_path)
                                    is_processed = True
                                else:
                                    print(f"  ❌ 提词器效果还原失败，直接使用k.py处理")
                                    k_output = self.process_with_k_py(output_subtitle)
                                    is_processed = True
                            else:
                                # 直接使用k.py处理
                                print(f"  使用k.py处理字幕轨道{track_id}（真实卡拉OK效果）...")
                                k_output = self.process_with_k_py(output_subtitle)
                                is_processed = True
                        elif self.subtitle_mode == 2:
                            # 模式2: 提词器效果
                            if has_any_ass_tag and "KTV效果" in current_title:
                                # 需要从KTV效果转换为提词器效果：先用K文件还原，再用T文件转换
                                print(f"  正在从KTV效果转换为提词器效果...")
                                print(f"  1. 先用k.py还原KTV效果字幕...")
                                # 生成唯一的输出文件路径用于还原
                                restore_output_path = self.cache_dir / f"{Path(output_subtitle).stem}_restored.ass"
                                # 使用k.py的还原模式
                                cmd = [
                                    str(self.python_path), 
                                    str(self.karaoke_processor_path), 
                                    str(output_subtitle),
                                    "-o", str(restore_output_path),
                                    "-ow",  # 自动覆盖已存在的文件
                                    "-r"   # 还原模式
                                ]
                                result = subprocess.run(
                                    cmd,
                                    capture_output=True,
                                    encoding='utf-8',
                                    errors='ignore',
                                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                                    timeout=180
                                )
                                if result.returncode == 0 and restore_output_path.exists():
                                    print(f"  ✓ KTV效果还原成功")
                                    print(f"  2. 再用T.py转换为提词器效果...")
                                    k_output = self.process_with_t_py(restore_output_path)
                                    is_processed = True
                                else:
                                    print(f"  ❌ KTV效果还原失败，直接使用T.py处理")
                                    k_output = self.process_with_t_py(output_subtitle)
                                    is_processed = True
                            else:
                                # 直接使用T.py处理
                                print(f"  使用T.py处理字幕轨道{track_id}（提词器效果）...")
                                k_output = self.process_with_t_py(output_subtitle)
                                is_processed = True
                        elif self.subtitle_mode == 0:
                            # 模式0: 关闭，视为还原操作
                            if has_any_ass_tag:
                                # 检测到ASS相关标签，需要还原字幕
                                print(f"  正在还原字幕...")
                                restore_output_path = self.cache_dir / f"{Path(output_subtitle).stem}_restored.ass"
                                
                                if "KTV效果" in current_title:
                                    # 使用k.py还原KTV效果
                                    print(f"  1. 用k.py还原KTV效果字幕...")
                                    cmd = [
                                        str(self.python_path), 
                                        str(self.karaoke_processor_path), 
                                        str(output_subtitle),
                                        "-o", str(restore_output_path),
                                        "-ow",  # 自动覆盖已存在的文件
                                        "-r"   # 还原模式
                                    ]
                                    result = subprocess.run(
                                        cmd,
                                        capture_output=True,
                                        encoding='utf-8',
                                        errors='ignore',
                                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                                        timeout=180
                                    )
                                    if result.returncode == 0 and restore_output_path.exists():
                                        print(f"  ✓ KTV效果还原成功")
                                        k_output = restore_output_path
                                        is_processed = True
                                    else:
                                        print(f"  ❌ KTV效果还原失败，使用原始字幕")
                                        k_output = output_subtitle
                                        is_processed = False
                                elif "提词器效果" in current_title:
                                    # 使用T.py还原提词器效果
                                    print(f"  1. 用T.py还原提词器效果字幕...")
                                    cmd = [
                                        str(self.python_path), 
                                        str(self.prompter_processor_path), 
                                        str(output_subtitle),
                                        "-o", str(restore_output_path),
                                        "-r"   # 还原模式
                                    ]
                                    result = subprocess.run(
                                        cmd,
                                        capture_output=True,
                                        encoding='utf-8',
                                        errors='ignore',
                                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                                        timeout=180
                                    )
                                    if result.returncode == 0 and restore_output_path.exists():
                                        print(f"  ✓ 提词器效果还原成功")
                                        k_output = restore_output_path
                                        is_processed = True
                                    else:
                                        print(f"  ❌ 提词器效果还原失败，使用原始字幕")
                                        k_output = output_subtitle
                                        is_processed = False
                                else:
                                    # 未知效果，使用原始字幕
                                    print(f"  未知效果类型，使用原始字幕")
                                    k_output = output_subtitle
                                    is_processed = False
                            else:
                                # 没有ASS相关标签，使用原始字幕
                                k_output = output_subtitle
                                is_processed = False
                                print(f"  字幕处理模式{self.subtitle_mode}，使用原始字幕")
                        else:
                            # 其他模式，使用原始字幕
                            k_output = output_subtitle
                            is_processed = False
                            print(f"  字幕处理模式{self.subtitle_mode}，使用原始字幕")
                        
                        if self.subtitle_mode != 'A' and k_output and Path(k_output).exists():
                            # 检查文件大小，确保不是空文件
                            file_size = Path(k_output).stat().st_size
                            if file_size > 100:  # 至少100字节
                                # 将处理后的文件复制到缓存目录
                                suffix = "_ass_1" if is_processed else ""
                                output_processed = self.cache_dir / f"subtitle{suffix}_{track_id}_{language}.ass"
                                shutil.copy2(k_output, output_processed)
                                
                                # 根据模式设置不同的Title（默认效果不添加说明）
                                if self.subtitle_mode == 0:
                                    title = ""  # 默认效果不添加说明
                                elif self.subtitle_mode == 1:
                                    title = "KTV效果"
                                elif self.subtitle_mode == 2:
                                    title = "提词器效果"
                                
                                # 修改ASS文件的Title（默认效果不添加说明）
                                if title:
                                    self.set_ass_title(output_processed, title)
                                
                                processed_subtitle_tracks.append({
                                    'path': output_processed,
                                    'language': language,
                                    'is_default': is_default,
                                    'original_track_id': track_id,
                                    'is_processed': is_processed
                                })
                                print(f"  OK 成功处理字幕轨道 (大小: {file_size} 字节，Title: {title})")
                            else:
                                print(f"  × 处理后的字幕文件太小 ({file_size} 字节)，可能处理失败")
                                processed_subtitle_tracks.append({
                                    'path': output_subtitle,
                                    'language': language,
                                    'is_default': is_default,
                                    'original_track_id': track_id,
                                    'is_processed': False
                                })
                        elif self.subtitle_mode != 'A':
                            print(f"  × 字幕处理失败，使用原始字幕")
                            processed_subtitle_tracks.append({
                                'path': output_subtitle,
                                'language': language,
                                'is_default': is_default,
                                'original_track_id': track_id,
                                'is_processed': False
                            })
                    else:
                        print(f"  × 提取字幕轨道{track_id}失败")
            else:
                # 不处理字幕，直接使用原始字幕轨道信息
                print(f"字幕处理模式已关闭，保留原始字幕轨道")
                for i, track_info in enumerate(subtitle_tracks):
                    track_id = track_info['track_id']
                    language = track_info['language']
                    is_default = track_info['default']
                    
                    # 提取字幕轨道到临时文件
                    subtitle_filename = f"subtitle_track_{track_id}_{language}.ass"
                    output_subtitle = self.cache_dir / subtitle_filename
                    
                    if self.extract_subtitle_with_mkvextract(video_path, track_id, output_subtitle):
                        processed_subtitle_tracks.append({
                            'path': output_subtitle,
                            'language': language,
                            'is_default': is_default,
                            'original_track_id': track_id,
                            'is_processed': False
                        })
                        print(f"OK 提取字幕轨道{track_id}用于重新打包")
                    else:
                        print(f"× 提取字幕轨道{track_id}失败")
            
            # 检查是否有任何实际修改
            any_modifications = audio_processed or subtitle_processed
            
            # 检查是否有任何轨道被成功处理
            has_processed_tracks = len(processed_audio_tracks) > 0 or len(processed_subtitle_tracks) > 0
            
            # 检查是否真的有必要重新打包
            # 如果没有任何修改，且字幕模式为0（关闭），且音频处理失败，不生成新文件
            if not any_modifications and self.subtitle_mode == 0 and len(processed_audio_tracks) == 0:
                print("\n无需处理:")
                print("-" * 30)
                print("原因: 没有对文件进行任何修改")
                print("- 音频轨道已经是5.1声道，跳过转换")
                print("- 音频轨道提取失败")
                if ass1_tag_detected:
                    print("- 检测到(ASS_1)标签，暂时不支持效果转换")
                else:
                    print("- 字幕处理模式已关闭")
                print("因此不生成输出文件")
                print("=" * 60)
                return None
            
            # 如果没有任何修改且没有成功处理的轨道，不生成新文件
            if not any_modifications and not has_processed_tracks:
                print("\n无需处理:")
                print("-" * 30)
                print("原因: 没有对文件进行任何修改，且没有成功处理的轨道")
                print("因此不生成输出文件")
                print("=" * 60)
                return None
            
            # 重新打包MKV
            print("\n步骤4: 重新打包MKV")
            print("-" * 30)
            
            # 生成输出文件名
            output_filename = self.generate_output_filename(video_path, output_dir, is_batch)
            
            if output_dir:
                # 如果是批量处理，使用指定的输出目录
                output_dir_path = Path(output_dir)
                output_dir_path.mkdir(parents=True, exist_ok=True)
                output_path = output_dir_path / output_filename
                print(f"输出目录: {output_dir_path}")
                print(f"输出文件: {output_path}")
            else:
                # 如果是单文件处理，使用原目录
                output_path = video_path.parent / output_filename
                print(f"输出文件: {output_path}")
            
            # 重新打包MKV
            mkv_result = self.rebuild_mkv_final(
                video_path=video_path,
                subtitle_tracks=processed_subtitle_tracks,
                audio_tracks_info=processed_audio_tracks,
                output_path=output_path
            )
            
            if mkv_result:
                print(f"\nOK 处理完成!")
                print(f"输出文件: {mkv_result}")
                
                # 验证最终文件的轨道设置
                self.verify_final_tracks(mkv_result)
                
                return mkv_result
            else:
                print(f"\n× 打包失败")
                return None
                
        except Exception as e:
            print(f"处理过程中出错: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            # 恢复原始字幕模式
            if ass1_tag_detected:
                self.subtitle_mode = original_subtitle_mode
            # 清理缓存
            self.cleanup_cache()
    
    def get_subtitle_mode_name(self):
        """获取字幕处理模式的名称"""
        mode_names = {
            0: "关闭",
            1: "真实卡拉OK",
            2: "提词器"
        }
        return mode_names.get(self.subtitle_mode, f"模式{self.subtitle_mode}")
    
    def verify_final_tracks(self, mkv_path):
        """验证最终文件的轨道设置"""
        try:
            print("\n验证最终文件轨道设置...")
            print("-" * 30)
            
            final_info = self.get_media_info_with_mkvmerge(mkv_path)
            
            if final_info.get('audio_tracks'):
                print("音频轨道状态:")
                for track in final_info['audio_tracks']:
                    status = "默认" if track['default'] else "非默认"
                    channels = f"{track.get('channels', 2)}声道"
                    language_name = self.get_language_name(track['language'])
                    track_name = track.get('track_name', '')
                    codec = track.get('codec', '未知')
                    if track_name:
                        print(f"  轨道{track['track_id']}: {language_name} - {status} - {channels} - {codec} - 名称: {track_name}")
                    else:
                        print(f"  轨道{track['track_id']}: {language_name} - {status} - {channels} - {codec}")
            
            if final_info.get('subtitle_tracks'):
                print("\n字幕轨道状态:")
                for track in final_info['subtitle_tracks']:
                    status = "默认" if track['default'] else "非默认"
                    language_name = self.get_language_name(track['language'])
                    track_name = track.get('track_name', '')
                    if track_name:
                        print(f"  轨道{track['track_id']}: {language_name} - {status} - 名称: {track_name}")
                    else:
                        print(f"  轨道{track['track_id']}: {language_name} - {status}")
            
        except Exception as e:
            print(f"验证轨道设置时出错: {e}")
    
    def generate_output_filename(self, video_path, output_dir=None, is_batch=False):
        """生成输出文件名"""
        video_stem = video_path.stem
        
        # 初始化tags变量，确保在所有代码路径中都有定义
        tags = []
        
        # 检查原文件是否包含ASS相关标签
        has_ass1_tag = ' (ASS_1)' in video_stem
        has_ass_tag = ' (ASS)' in video_stem
        has_ass_k_tag = ' (ASS_K)' in video_stem
        has_ass_t_tag = ' (ASS_T)' in video_stem
        # 检查原文件是否包含(5.1)标签
        has_51_tag = ' (5.1)' in video_stem
        
        # 保留原始文件名结构，只替换ASS标签内容，保持位置不变
        base_filename = video_stem
        
        # 根据subtitle_mode确定要使用的ASS标签
        new_ass_tag = ''
        if self.subtitle_mode == 0:
            new_ass_tag = ' (ASS)'
        elif self.subtitle_mode == 1:
            new_ass_tag = ' (ASS_K)'
        elif self.subtitle_mode == 2:
            new_ass_tag = ' (ASS_T)'
        elif self.subtitle_mode == 'A':
            new_ass_tag = ' (ASS)'
        
        # 替换原文件中的ASS标签，保持位置不变
        if has_ass1_tag:
            base_filename = base_filename.replace(' (ASS_1)', new_ass_tag)
        elif has_ass_tag:
            base_filename = base_filename.replace(' (ASS)', new_ass_tag)
        elif has_ass_k_tag:
            base_filename = base_filename.replace(' (ASS_K)', new_ass_tag)
        elif has_ass_t_tag:
            base_filename = base_filename.replace(' (ASS_T)', new_ass_tag)
        else:
            # 如果原文件没有ASS标签，添加到文件名末尾
            if base_filename.endswith(')'):
                # 如果末尾有标签，在标签前添加
                base_filename = base_filename.rsplit('(', 1)[0].strip() + new_ass_tag + ' (' + base_filename.rsplit('(', 1)[1]
            else:
                # 如果末尾没有标签，直接添加
                base_filename += new_ass_tag
        
        # 处理5.1标签
        if self.stereo_to_5_1 == 1:
            if not has_51_tag:
                # 如果原文件没有5.1标签，但启用了5.1转换，添加5.1标签
                # 检查文件名末尾是否已经有标签
                if base_filename.endswith(')'):
                    # 如果末尾有标签，在标签前添加
                    base_filename = base_filename.rsplit('(', 1)[0].strip() + ' (5.1) (' + base_filename.rsplit('(', 1)[1]
                else:
                    # 如果末尾没有标签，直接添加
                    base_filename = base_filename + ' (5.1)'
        
        # 构建输出文件名
        output_filename = f"{base_filename}.mkv"
        
        # 检查文件是否与原文件重名
        if output_dir:
            target_path = Path(output_dir) / output_filename
        else:
            target_path = video_path.parent / output_filename
        
        # 获取原文件的完整路径（用于比较）
        original_file_path = video_path.resolve()
        
        # 如果是目录批量处理，直接返回该文件名，不添加序列号
        # 因为目录已经处理过重名问题
        if is_batch:
            return output_filename
        
        # 如果生成的文件名与原文件不同名，直接返回该文件名（即使与其他文件重名，也直接覆盖）
        if target_path.resolve() != original_file_path:
            return output_filename
        
        # 如果与原文件重名，添加编号防止覆盖
        counter = 1
        
        while True:
            # 构建带编号的完整文件名
            # 直接在原始文件名后添加序列号，保留原始结构
            if base_filename.endswith(')'):
                # 如果末尾有标签，在标签后添加
                numbered_output_filename = base_filename + f" ({counter}).mkv"
            else:
                # 如果末尾没有标签，直接添加
                numbered_output_filename = base_filename + f" ({counter}).mkv"
            
            # 检查带编号的文件是否存在
            if output_dir:
                numbered_target_path = Path(output_dir) / numbered_output_filename
            else:
                numbered_target_path = video_path.parent / numbered_output_filename
            
            if not numbered_target_path.exists():
                return numbered_output_filename
            
            # 递增编号
            counter += 1
            
            # 防止无限循环
            if counter > 999:
                print("警告: 文件名编号超过999，可能存在命名冲突")
                break
    
    def generate_incremental_directory(self, base_dir):
        """生成递增的目录名"""
        if not base_dir.exists():
            return base_dir
        
        counter = 1
        while True:
            numbered_dir = base_dir.parent / f"{base_dir.name} ({counter})"
            if not numbered_dir.exists():
                return numbered_dir
            counter += 1
            if counter > 999:
                break
        return base_dir
    
    def batch_process_directory(self, directory_path, output_dir=None):
        """批量处理目录下的所有视频文件（按文件名排序）"""
        directory_path = Path(directory_path)
        
        if not directory_path.exists() or not directory_path.is_dir():
            print(f"目录不存在: {directory_path}")
            return []
        
        # 处理输出目录：如果存在，添加序列号
        if output_dir:
            output_dir_path = Path(output_dir)
            output_dir_path = self.generate_incremental_directory(output_dir_path)
            output_dir = str(output_dir_path)
        
        # 支持的视频格式（小写）
        video_extensions = {'.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
        
        # 使用集合来避免重复，通过文件路径的字符串形式去重
        video_files_set = set()
        
        # 查找所有视频文件（不区分大小写）
        for file_path in directory_path.iterdir():
            if file_path.is_file():
                # 获取文件扩展名并转换为小写
                ext = file_path.suffix.lower()
                if ext in video_extensions:
                    # 使用文件的绝对路径作为键来去重
                    video_files_set.add(file_path.resolve())
        
        # 转换回Path对象列表，并按文件名排序
        video_files = sorted([Path(file_path) for file_path in video_files_set], key=lambda x: x.name)
        
        if not video_files:
            print("未找到可处理的视频文件")
            return []
        
        print(f"找到{len(video_files)}个视频文件（按文件名排序）:")
        for i, video_file in enumerate(video_files, 1):
            print(f"  {i:2d}. {video_file.name}")
        
        # 如果用户没有指定输出目录，创建输出子目录
        if output_dir is None:
            dir_tags = []
            if self.subtitle_mode == 1:
                dir_tags.append("ASS_K")
            elif self.subtitle_mode == 2:
                dir_tags.append("ASS_T")
            elif self.subtitle_mode == 0:
                dir_tags.append("ASS")
            if self.stereo_to_5_1 == 1:
                dir_tags.append("5.1")
            
            if dir_tags:
                dir_name = "已处理 (" + " ".join(dir_tags) + ")"
            else:
                dir_name = "已处理"
            
            output_dir = directory_path / dir_name
            output_dir.mkdir(parents=True, exist_ok=True)
            print(f"\n输出目录: {output_dir}")
        
        results = []
        for i, video_file in enumerate(video_files, 1):
            print(f"\n{'='*60}")
            print(f"处理文件 [{i}/{len(video_files)}]: {video_file.name}")
            print(f"{'='*60}")
            
            result = self.process_single_video(video_file, output_dir, is_batch=True)
            if result:
                results.append(result)
            
            print(f"{'='*60}")
        
        print(f"\n批量处理完成: {len(results)}/{len(video_files)}个文件成功")
        print(f"输出目录: {output_dir}")
        if results:
            print("\n生成的文件:")
            for i, result in enumerate(results, 1):
                print(f"  {i:2d}. {Path(result).name}")
        return results

def main():
    """主函数"""
    try:
        processor = VideoReprocessor()
        
        # 解析命令行参数，支持设置subtitle_mode
        import argparse
        parser = argparse.ArgumentParser(description='视频二次加工工具')
        parser.add_argument('--subtitle-mode', type=str, choices=['0', '1', '2', 'A', '-1'], help='设置字幕处理模式：0-默认原始效果，1-KTV效果，2-提词器效果，A/-1-全部效果打包')
        args, remaining_args = parser.parse_known_args()
        
        # 更新sys.argv，移除已解析的参数，保留剩余参数供后续处理
        sys.argv = [sys.argv[0]] + remaining_args
        
        # 如果指定了subtitle_mode，更新processor的subtitle_mode
        if args.subtitle_mode is not None:
            if args.subtitle_mode in ['A', '-1']:
                processor.subtitle_mode = 'A'  # 使用'A'作为内部全选标记
                print(f"通过命令行设置字幕处理模式: 全部效果打包 (ASS)")
            else:
                processor.subtitle_mode = int(args.subtitle_mode)
                print(f"通过命令行设置字幕处理模式: {processor.subtitle_mode} ({processor.get_subtitle_mode_name()})")
        
        print("=" * 60)
        print("视频二次加工工具")
        print("功能: 提取音频/字幕 -> 音频5.1转换/字幕处理 -> mkvmerge打包")
        print(f"多音轨多字幕默认属性: {'0-保持原样' if processor.default_settings_mode == 0 else '1-中文设为默认'}")
        print(f"立体声转5.1: {'开启' if processor.stereo_to_5_1 == 1 else '关闭'}")
        print(f"字幕处理模式: {processor.subtitle_mode} ({processor.get_subtitle_mode_name()})")
        print("注意:")
        print("  - 单文件处理: 输出到原视频所在目录")
        print("  - 目录批量处理: 按文件名排序，输出到独立目录")
        print("  - 文件名规则: LE SSERAFIM - EASY 60fps  (ASS_K) (5.1).mkv 或 (ASS_T) (5.1).mkv")
        print("  - 重名规则: LE SSERAFIM - EASY 60fps  (ASS_K) (5.1) (1).mkv")
        print("  - 5.1转换: 不保留原始音轨，只保留转换后的5.1音轨")
        print("  - 字幕轨道名称: 根据模式显示为 (ASS), (ASS_K) 或 (ASS_T)")
        print("  - 不添加字体附件")
        print("=" * 60)
        
        # 检查命令行参数
        if len(sys.argv) > 1:
            # 命令行模式：直接处理拖放的文件/文件夹
            print(f"检测到{len(sys.argv)-1}个拖放的文件/文件夹")
            
            successful_files = []
            failed_files = []
            
            for i, arg in enumerate(sys.argv[1:], 1):
                print(f"\n处理参数 {i}/{len(sys.argv)-1}: {arg}")
                
                input_path = Path(arg)
                if not input_path.exists():
                    print(f"× 路径不存在: {arg}")
                    failed_files.append(arg)
                    continue
                
                if input_path.is_file():
                    # 单文件处理，不指定输出目录，让process_single_video决定输出路径
                    result = processor.process_single_video(input_path, None)
                    if result:
                        print(f"OK 处理完成: {Path(result).name}")
                        successful_files.append(str(result))
                    else:
                        print("× 处理失败")
                        failed_files.append(arg)
                else:
                    # 目录处理，不指定输出目录，让batch_process_directory创建独立子目录
                    print(f"批量处理目录: {arg}")
                    print("将按文件名排序处理，并输出到独立目录")
                    results = processor.batch_process_directory(input_path, None)
                    if results:
                        print(f"OK 批量处理完成: {len(results)}个文件")
                        for j, result in enumerate(results, 1):
                            print(f"  {j}. {Path(result).name}")
                            successful_files.append(str(result))
                    else:
                        print("× 批量处理失败")
                        failed_files.append(arg)
            
            # 显示处理结果总结
            print(f"\n" + "=" * 60)
            print("处理结果总结:")
            print(f"成功处理: {len(successful_files)} 个文件")
            print(f"处理失败: {len(failed_files)} 个文件")
            
            if failed_files:
                print("\n失败的文件列表:")
                for failed in failed_files:
                    print(f"  {failed}")
            
            return
            
        else:
            # 交互模式：没有命令行参数，进入原来的交互流程
            while True:
                # 获取输入路径
                input_path = input("\n请输入视频文件或目录路径 (输入q退出): ").strip().strip('"')
                
                if input_path.lower() in ['q', 'quit', 'exit']:
                    print("退出程序")
                    break
                
                if not input_path:
                    print("路径不能为空")
                    continue
                
                input_path = Path(input_path)
                if not input_path.exists():
                    print("路径不存在，请检查")
                    continue
                
                # 处理文件
                if input_path.is_file():
                    # 单文件处理，不指定输出目录，让process_single_video决定输出路径
                    result = processor.process_single_video(input_path, None)
                    if result:
                        print(f"\nOK 处理完成: {result}")
                    else:
                        print("\n× 处理失败")
                else:
                    # 目录处理，不指定输出目录，让batch_process_directory创建独立子目录
                    print("将按文件名排序处理，并输出到独立目录")
                    results = processor.batch_process_directory(input_path, None)
                    if results:
                        print(f"\nOK 批量处理完成: {len(results)}个文件")
                        # 显示输出目录
                        dir_tags = []
                        if processor.subtitle_mode == 1 or processor.subtitle_mode == 2:
                            dir_tags.append("ASS_1")
                        if processor.stereo_to_5_1 == 1:
                            dir_tags.append("5.1")
                        
                        if dir_tags:
                            dir_name = "已处理 (" + " ".join(dir_tags) + ")"
                        else:
                            dir_name = "已处理"
                        
                        print(f"输出目录: {input_path / dir_name}")
                        print("生成的文件:")
                        for i, result in enumerate(results, 1):
                            print(f"  {i:2d}. {Path(result).name}")
                    else:
                        print("\n× 批量处理失败")
                
                # 询问是否继续
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