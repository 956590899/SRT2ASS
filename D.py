import os
import sys

# 设置环境变量，确保Python使用UTF-8编码
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LANG'] = 'zh_CN.UTF-8'
os.environ['LC_ALL'] = 'zh_CN.UTF-8'

# 设置标准输出编码为UTF-8，解决中文乱码问题
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import re
import json
import subprocess
import tempfile
import shutil
from pathlib import Path

# ====== D.py自己的字体配置 ======
FONT_CONFIG = {
    "simplified_chinese": {
        "font_name": "方正准圆简体",
        "font_file": "方正准圆简体.ttf"
    },
    "japanese_traditional": {
        "font_name": "夏花绚烂前程似锦",
        "font_file": "夏花绚烂前程似锦.ttf"
    },
    "enable_font_attachment": 1,
    "set_unknown_to_chinese": 1,
    "use_system_font": 0,
    "system_font_name": "Microsoft YaHei"
}

class MKVFontReplacer:
    """MKV字体替换工具"""
    
    def __init__(self):
        """初始化"""
        # 字体目录路径：SRT/TTF/
        self.fonts_dir = Path("SRT") / "TTF"
        self.enable_font_attachment = FONT_CONFIG['enable_font_attachment']
        self.set_unknown_to_chinese = FONT_CONFIG['set_unknown_to_chinese']  # 新增
        self.use_system_font = FONT_CONFIG.get('use_system_font', 0)
        self.system_font_name = FONT_CONFIG.get('system_font_name', 'Microsoft YaHei')
        
        # 检查两个字体文件是否存在
        self.simplified_font_file = None
        self.japanese_traditional_font_file = None
        
        # 检查简体中文字体
        simplified_config = FONT_CONFIG['simplified_chinese']
        if simplified_config['font_file']:
            simplified_font = self.fonts_dir / simplified_config['font_file']
            if simplified_font.exists():
                self.simplified_font_file = simplified_font
            else:
                print(f"警告: 简体中文字体文件不存在: {simplified_font}")
        
        # 检查日语/繁体中文字体
        jt_config = FONT_CONFIG['japanese_traditional']
        if jt_config['font_file']:
            jt_font = self.fonts_dir / jt_config['font_file']
            if jt_font.exists():
                self.japanese_traditional_font_file = jt_font
            else:
                print(f"警告: 日语/繁体中文字体文件不存在: {jt_font}")
        
        print(f"字体附件: {'启用' if self.enable_font_attachment else '禁用'}")
        print(f"使用系统字体: {'是' if self.use_system_font == 1 else '否'}")
        if self.use_system_font == 1:
            print(f"系统字体: {self.system_font_name}")
        else:
            print(f"简体中文字体: {simplified_config['font_name']}")
            print(f"日语/繁体中文字体: {jt_config['font_name']}")
        set_unknown_mode = "开启" if self.set_unknown_to_chinese == 1 else "关闭"
        print(f"未知语言设为中文: {set_unknown_mode} (仅当字幕唯一时)")
    
    def detect_language_from_content(self, content):
        """
        从内容检测语言类型
        返回: 'japanese', 'traditional_chinese', 'simplified_chinese'
        """
        if not content:
            return 'simplified_chinese'  # 默认简体中文
        
        # 清理内容：移除ASS标签和特殊字符
        clean_content = re.sub(r'\{[^}]*\}', '', content)  # 移除ASS标签
        clean_content = re.sub(r'[^\u4e00-\u9fff\u3040-\u30ff\u31f0-\u31ff\uff00-\uffef]', '', clean_content)
        
        if not clean_content:
            return 'simplified_chinese'  # 默认简体中文
        
        # 检测是否包含日文字符（平假名、片假名）
        if self.contains_japanese_text(clean_content):
            return 'japanese'
        
        # 检测是否包含繁体中文
        if self.contains_traditional_chinese_text(clean_content):
            return 'traditional_chinese'
        
        # 如果只包含中文字符，则为简体中文
        chinese_pattern = re.compile(r'[\u4e00-\u9fff]')
        if chinese_pattern.search(clean_content):
            return 'simplified_chinese'
        
        return 'simplified_chinese'  # 默认简体中文
    
    def contains_japanese_text(self, text):
        """检测文本是否包含日文字符（平假名、片假名）"""
        if not text:
            return False
        
        # 日文字符范围
        japanese_ranges = [
            (0x3040, 0x309F),  # 平假名 (Hiragana)
            (0x30A0, 0x30FF),  # 片假名 (Katakana)
            (0x31F0, 0x31FF),  # 片假名音标扩展
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
        """检测文本是否包含繁体中文"""
        if not text:
            return False
        
        # 繁体中文特有字符
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
        
        # 基于字符使用频率的简单检测
        traditional_indicators = ['麼', '為', '於', '裡', '後', '個', '體', '國', '學', '與']
        traditional_count = sum(1 for char in text if char in traditional_indicators)
        
        # 显示关键识别逻辑（无论是否满足阈值）
        if traditional_count > 0:
            print(f"      识别逻辑: 检测到 {traditional_count} 个繁体特征字符，占比 {traditional_count/len(text)*100:.1f}%")
        
        # 如果包含繁体特征字符，无论数量多少，都认为是繁体中文
        if traditional_count > 0:
            return True
        
        return False
    
    def get_font_config_by_language(self, language_type):
        """根据语言类型获取字体配置"""
        if self.use_system_font == 1:
            # 使用系统字体
            system_font_config = {
                'font_name': self.system_font_name,
                'font_file': None  # 系统字体不需要文件
            }
            return system_font_config, None
        else:
            # 使用自定义字体
            if language_type in ['japanese', 'traditional_chinese']:
                return FONT_CONFIG['japanese_traditional'], self.japanese_traditional_font_file
            else:
                return FONT_CONFIG['simplified_chinese'], self.simplified_font_file
    
    def run_command(self, cmd_parts):
        """运行命令"""
        try:
            # 检查是否是mkvmerge或mkvextract命令
            if cmd_parts and cmd_parts[0] in ['mkvmerge', 'mkvextract']:
                # 使用本地MKVToolNix目录中的可执行文件
                # 正确路径：SRT/Python/MKVToolNix/
                mkvtoolnix_dir = os.path.join(os.path.dirname(__file__), 'Python', 'MKVToolNix')
                tool_path = os.path.join(mkvtoolnix_dir, cmd_parts[0] + '.exe')
                # 检查工具文件是否存在
                if os.path.exists(tool_path):
                    cmd_parts[0] = tool_path
                else:
                    print(f"警告: 工具文件不存在: {tool_path}")
                    # 尝试使用系统PATH中的工具
                    pass
            
            # 打印命令执行信息
            print(f"执行命令: {cmd_parts[0]}...")
            
            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                check=False,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            return result
        except Exception as e:
            print(f"命令执行失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_mkv_info(self, mkv_path):
        """获取MKV信息"""
        cmd_parts = ['mkvmerge', '-J', str(mkv_path)]
        result = self.run_command(cmd_parts)
        
        if not result or result.returncode != 0:
            print(f"获取MKV信息失败: {result.stderr if result else '未知错误'}")
            return None
        
        try:
            return json.loads(result.stdout)
        except Exception as e:
            print(f"解析MKV信息失败: {e}")
            return None
    
    def extract_and_process_subtitles(self, mkv_path, temp_dir):
        """提取并处理字幕"""
        info = self.get_mkv_info(mkv_path)
        if not info:
            print("  NO 无法获取MKV信息")
            return []
        
        subtitle_tracks = []
        
        for track in info.get('tracks', []):
            if track.get('type', '').lower() == 'subtitles':
                props = track.get('properties', {})
                
                track_info = {
                    'id': str(track.get('id', '')),
                    'codec': track.get('codec', ''),
                    'language': props.get('language', 'und'),
                    'default_track': bool(props.get('default_track', False)),
                }
                
                # 只处理ASS/SSA
                codec_lower = track_info['codec'].lower()
                if any(x in codec_lower for x in ['ass', 'ssa', 'substationalpha']):
                    # 提取字幕
                    temp_file = Path(temp_dir) / f"track_{track_info['id']}.ass"
                    cmd_parts = ['mkvextract', 'tracks', str(mkv_path), f"{track_info['id']}:{temp_file}"]
                    result = self.run_command(cmd_parts)
                    
                    if result and result.returncode == 0 and temp_file.exists():
                        track_info['extracted_file'] = temp_file
                        subtitle_tracks.append(track_info)
                        print(f"    OK 轨道{track_info['id']}: {track_info['language'].upper()} ({track_info['codec']})")
                    else:
                        print(f"    NO 提取失败轨道{track_info['id']}: {result.stderr if result else '未知错误'}")
        
        return subtitle_tracks
    
    def analyze_language_from_ass_content(self, ass_file_path):
        """从ASS文件内容分析语言类型"""
        try:
            with open(ass_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(50000)  # 读取前50000字符进行分析
            
            # 提取所有字幕文本（排除样式行）
            text_lines = []
            in_events_section = False
            
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('[Events]'):
                    in_events_section = True
                    continue
                elif line.startswith('[') and in_events_section:
                    break
                
                if in_events_section and line.startswith('Dialogue:'):
                    # 提取字幕文本（第10个逗号之后的内容）
                    parts = line.split(',', 9)
                    if len(parts) >= 10:
                        text = parts[9]
                        # 移除特效标签
                        text = re.sub(r'\{[^}]*\}', '', text)
                        if text.strip():
                            text_lines.append(text)
            
            # 合并文本进行分析
            combined_text = ''.join(text_lines)
            
            # 检测语言类型
            language_type = self.detect_language_from_content(combined_text)
            
            # 语言名称映射
            language_names = {
                'japanese': '日文',
                'traditional_chinese': '繁体中文', 
                'simplified_chinese': '简体中文'
            }
            
            lang_name = language_names.get(language_type, '简体中文')
            return language_type, lang_name
            
        except Exception as e:
            print(f"      语言分析失败: {e}")
            return 'simplified_chinese', '简体中文'
    
    def replace_ass_fonts_by_language(self, ass_file, track_id):
        """根据语言类型替换字体"""
        try:
            # 分析ASS文件的语言
            language_type, lang_name = self.analyze_language_from_ass_content(ass_file)
            print(f"      检测语言: {lang_name}")
            
            # 根据语言类型获取字体配置
            font_config, font_file = self.get_font_config_by_language(language_type)
            target_font_name = font_config['font_name']
            
            with open(ass_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            lines = content.split('\n')
            new_lines = []
            replaced = False
            
            for line in lines:
                original_line = line
                
                # 只处理Style行
                if line.strip().startswith('Style:'):
                    parts = line.split(',')
                    if len(parts) >= 3:
                        old_font = parts[1].strip()
                        if old_font and old_font != target_font_name:
                            parts[1] = target_font_name
                            line = ','.join(parts)
                            replaced = True
                            print(f"      字体替换 ({lang_name}): {old_font} -> {target_font_name}")
                        else:
                            print(f"      字体未更改 ({lang_name}): {old_font}")
                
                new_lines.append(line)
            
            new_file = ass_file.parent / f"new_{track_id}_{language_type}.ass"
            with open(new_file, 'w', encoding='utf-8', errors='ignore') as f:
                f.write('\n'.join(new_lines))
            
            # 返回处理后的文件信息和语言类型
            return new_file, language_type, font_config, font_file
            
        except Exception as e:
            print(f"      NO 字体替换失败: {e}")
            return ass_file, 'simplified_chinese', FONT_CONFIG['simplified_chinese'], None
    
    def process_subtitles(self, subtitle_tracks, temp_dir):
        """处理字幕"""
        processed_tracks = []
        font_files_to_attach = set()  # 收集需要附加的字体文件
        
        # 检查是否是唯一的字幕轨道且为未知语言
        is_only_subtitle_track = len(subtitle_tracks) == 1
        
        for track in subtitle_tracks:
            if 'extracted_file' in track:
                # 根据内容分析语言并替换字体
                processed_file, language_type, font_config, font_file = self.replace_ass_fonts_by_language(
                    track['extracted_file'], track['id']
                )
                
                if processed_file:
                    track['processed_file'] = processed_file
                    track['language_type'] = language_type
                    track['font_config'] = font_config
                    
                    # 如果需要附加字体且字体文件存在，添加到集合
                    # 只有在不使用系统字体时才添加字体文件
                    if self.enable_font_attachment and not self.use_system_font and font_file and font_file.exists():
                        font_files_to_attach.add(font_file)
                    
                    # 只有当配置开启时，才处理未知语言的情况
                    if self.set_unknown_to_chinese == 1:
                        # 只有当字幕轨道唯一且语言为未知时，才设为中文
                        if is_only_subtitle_track and track['language'] == 'und':
                            # 根据语言类型设置标准语言代码
                            if language_type == 'japanese':
                                track['language'] = 'jpn'
                            elif language_type == 'traditional_chinese':
                                track['language'] = 'chi'
                            else:
                                track['language'] = 'chi'
                            print(f"      OK 将唯一未知语言字幕设为中文标签: {track['language']}")
                    else:
                        print(f"      ℹ 保持原语言标签: {track['language']}")
                    
                    processed_tracks.append(track)
                    
                    lang = track['language'].upper()
                    default = " [默认]" if track['default_track'] else ""
                    print(f"    轨道{track['id']}: {lang}{default} (字体: {font_config['font_name']})")
        
        return processed_tracks, list(font_files_to_attach)
    
    def direct_mkvmerge_pack_with_font_cleanup(self, mkv_path, processed_tracks, font_files, output_file):
        """直接使用mkvmerge打包，并清理原字体"""
        print("  使用mkvmerge打包...")
        
        try:
            # 第一步：从原文件提取视频和音频（排除原字幕和附件）
            cmd_parts = ['mkvmerge', '-o', str(output_file)]
            
            # 添加原文件的视频和音频轨道（排除原字幕）
            cmd_parts.extend(['--no-subtitles', '--no-attachments', str(mkv_path)])
            
            # 添加处理后的字幕轨道
            for track in processed_tracks:
                if 'processed_file' in track and Path(track['processed_file']).exists():
                    language = track.get('language', 'und')
                    is_default = track.get('default_track', False)
                    
                    # 设置语言（保持原语言代码）
                    cmd_parts.extend(['--language', f'0:{language}'])
                    
                    # 不添加轨道名称
                    # 保持原来的轨道名称，不修改
                    
                    # 设置默认轨道标志
                    if is_default:
                        cmd_parts.extend(['--default-track', '0:yes'])
                    else:
                        cmd_parts.extend(['--default-track', '0:no'])
                    
                    # 添加字幕文件
                    cmd_parts.append(str(track['processed_file']))
                    
                    # 获取使用的字体信息
                    font_name = track.get('font_config', {}).get('font_name', '未知')
                    print(f"    OK 添加字幕轨道: 语言={language.upper()} (字体: {font_name}) {'(默认)' if is_default else ''}")
            
            # 添加字体文件（如果启用字体附件且有字体文件）
            if self.enable_font_attachment and font_files:
                for font_file in font_files:
                    if font_file and font_file.exists():
                        cmd_parts.extend(['--attachment-mime-type', 'application/x-truetype-font'])
                        cmd_parts.extend(['--attach-file', str(font_file)])
                        print(f"    OK 添加字体附件: {font_file.name}")
            
            # 执行打包命令
            print(f"  执行命令: {' '.join(cmd_parts[:5])}...")  # 显示前几个参数
            
            result = self.run_command(cmd_parts)
            
            if result and result.returncode == 0:
                print(f"  OK 打包成功: {output_file.name}")
                if result.stdout:
                    print(f"  输出: {result.stdout[:200]}")
                return output_file
            else:
                print(f"  NO 打包失败")
                if result:
                    print(f"  返回码: {result.returncode}")
                    if result.stderr:
                        print(f"  错误: {result.stderr[:500]}")
                return None
                
        except Exception as e:
            print(f"  NO 打包异常: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def verify_output(self, mkv_path):
        """验证输出文件"""
        info = self.get_mkv_info(mkv_path)
        if not info:
            return
        
        # 检查轨道
        tracks = info.get('tracks', [])
        print(f"    视频轨道: {len([t for t in tracks if t.get('type') == 'video'])} 个")
        print(f"    音频轨道: {len([t for t in tracks if t.get('type') == 'audio'])} 个")
        
        subtitle_tracks = [t for t in tracks if t.get('type') == 'subtitles']
        print(f"    字幕轨道: {len(subtitle_tracks)} 个")
        
        # 显示每个字幕轨道的详细信息
        for track in subtitle_tracks:
            props = track.get('properties', {})
            track_id = track.get('id', '')
            language = props.get('language', 'und').upper()
            name = props.get('track_name', '')
            default = " (默认)" if props.get('default_track', False) else ""
            print(f"      轨道{track_id}: {language} - {name}{default}")
        
        # 检查字体附件
        attachments = info.get('attachments', [])
        font_attachments = [a for a in attachments if a.get('content_type', '') == 'application/x-truetype-font']
        
        if font_attachments:
            print(f"    字体附件: {len(font_attachments)} 个")
            for font in font_attachments:
                font_name = font.get('file_name', '未知')
                font_size = font.get('size', 0)
                print(f"      - {font_name} ({font_size:,} 字节)")
        else:
            print("    字体附件: 无")
    
    def process_single_mkv(self, mkv_path, output_dir=None):
        """处理单个MKV文件"""
        print(f"\n处理文件: {mkv_path.name}")
        print("-" * 40)
        
        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix="mkv_")
        
        try:
            print("1. 提取字幕...")
            subtitle_tracks = self.extract_and_process_subtitles(mkv_path, temp_dir)
            
            if not subtitle_tracks:
                print("  ℹ 未找到ASS字幕，跳过")
                return None
            
            print(f"  找到 {len(subtitle_tracks)} 个字幕轨道")
            
            print("\n2. 分析语言并替换字体...")
            processed_tracks, font_files = self.process_subtitles(subtitle_tracks, temp_dir)
            
            if not processed_tracks:
                print("  ℹ 无字幕需要处理，跳过")
                return None
            
            print(f"\n3. 打包MKV (字体附件: {'启用' if self.enable_font_attachment else '禁用'})...")
            print(f"  使用字体: {len(font_files)} 个")
            
            # 确定输出文件路径
            if output_dir:
                # 文件夹模式：在输出目录中创建相同结构的路径
                output_file = output_dir / mkv_path.name
            else:
                # 单文件模式：在原目录下
                output_file = mkv_path.parent / f"{mkv_path.stem}_newfont.mkv"
            
            # 使用mkvmerge打包
            result = self.direct_mkvmerge_pack_with_font_cleanup(mkv_path, processed_tracks, font_files, output_file)
            
            if result and result.exists():
                # 验证输出
                print("\n4. 验证输出文件...")
                self.verify_output(result)
                print(f"\n  OK 完成: {result.name}")
                return result
            else:
                return None
                
        finally:
            # 清理临时目录
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
    
    def find_video_files(self, path):
        """查找视频文件"""
        video_extensions = {'.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
        video_files = []
        
        path = Path(path)
        
        if path.is_file():
            if path.suffix.lower() in video_extensions:
                video_files.append(path)
        elif path.is_dir():
            for ext in video_extensions:
                video_files.extend(path.rglob(f"*{ext}"))
        
        # 过滤掉已经处理过的文件（包含_newfont的）
        filtered_files = []
        for file in video_files:
            if '_newfont' not in file.stem and not file.name.startswith('processed_'):
                filtered_files.append(file)
        
        return filtered_files
    
    def process_folder(self, input_path, output_path=None):
        """批量处理文件夹"""
        print(f"\n批量处理模式启动...")
        print(f"输入路径: {input_path}")
        
        # 查找视频文件
        video_files = self.find_video_files(input_path)
        
        if not video_files:
            print("未找到支持的视频文件")
            return []
        
        print(f"找到 {len(video_files)} 个视频文件")
        
        # 创建输出目录
        if output_path:
            output_dir = Path(output_path)
        else:
            # 默认输出目录：输入目录下的 processed 文件夹
            input_path_obj = Path(input_path)
            if input_path_obj.is_file():
                output_dir = input_path_obj.parent / "processed"
            else:
                output_dir = input_path_obj / "processed"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"输出目录: {output_dir}")
        
        # 处理每个文件
        successful_files = []
        failed_files = []
        
        for i, video_file in enumerate(video_files, 1):
            print(f"\n{'='*60}")
            print(f"处理文件 {i}/{len(video_files)}")
            print(f"{'='*60}")
            
            try:
                # 对于文件夹模式，保持相对路径结构
                if Path(input_path).is_dir():
                    # 计算相对路径
                    rel_path = video_file.relative_to(input_path)
                    file_output_dir = output_dir / rel_path.parent
                    file_output_dir.mkdir(parents=True, exist_ok=True)
                    output_file = file_output_dir / video_file.name
                else:
                    # 单文件模式
                    output_file = output_dir / video_file.name
                
                result = self.process_single_mkv(video_file, output_dir)
                
                if result:
                    successful_files.append(result)
                    print(f"OK 成功处理: {video_file.name}")
                else:
                    failed_files.append(video_file)
                    print(f"NO 处理失败: {video_file.name}")
                    
            except Exception as e:
                failed_files.append(video_file)
                print(f"NO 处理异常 {video_file.name}: {e}")
                import traceback
                traceback.print_exc()
        
        # 输出统计信息
        print(f"\n{'='*60}")
        print("批量处理完成!")
        print(f"{'='*60}")
        print(f"总计文件: {len(video_files)}")
        print(f"成功处理: {len(successful_files)}")
        print(f"处理失败: {len(failed_files)}")
        
        if successful_files:
            print(f"\n成功文件保存在: {output_dir}")
        
        if failed_files:
            print(f"\n失败的文件:")
            for file in failed_files[:10]:  # 只显示前10个失败文件
                print(f"  {file.name}")
            if len(failed_files) > 10:
                print(f"  ... 还有 {len(failed_files) - 10} 个失败文件")
        
        return successful_files
    
    def main(self, input_path):
        """主处理函数"""
        input_path = Path(input_path)
        
        print("=" * 60)
        print("MKV字体替换工具 - D.py批量版")
        print("=" * 60)
        
        # 显示字体配置
        simplified_config = FONT_CONFIG['simplified_chinese']
        jt_config = FONT_CONFIG['japanese_traditional']
        
        print(f"使用系统字体: {'是' if self.use_system_font == 1 else '否'}")
        if self.use_system_font == 1:
            print(f"系统字体: {self.system_font_name}")
        else:
            print(f"简体中文字体: {simplified_config['font_name']}")
            if self.simplified_font_file and self.simplified_font_file.exists():
                print(f"  字体文件: {self.simplified_font_file.name} (OK 存在)")
            else:
                print(f"  字体文件: {simplified_config.get('font_file', '未配置')} (NO 不存在)")
            
            print(f"日语/繁体中文字体: {jt_config['font_name']}")
            if self.japanese_traditional_font_file and self.japanese_traditional_font_file.exists():
                print(f"  字体文件: {self.japanese_traditional_font_file.name} (OK 存在)")
            else:
                print(f"  字体文件: {jt_config.get('font_file', '未配置')} (NO 不存在)")
        
        print(f"字体附件: {'启用' if self.enable_font_attachment else '禁用'}")
        
        # 显示新配置
        set_unknown_mode = "开启" if self.set_unknown_to_chinese == 1 else "关闭"
        print(f"未知语言设为中文: {set_unknown_mode} (仅当字幕唯一时)")
        
        print("-" * 60)
        
        if not input_path.exists():
            print(f"错误: 路径不存在: {input_path}")
            return False
        
        # 检查是文件还是文件夹
        if input_path.is_file():
            print(f"单文件模式: {input_path.name}")
            result = self.process_single_mkv(input_path)
            if result:
                print("\n" + "=" * 60)
                print("OK 处理完成!")
                print(f"输出文件: {result}")
                print("=" * 60)
                return True
            else:
                print("\n" + "=" * 60)
                print("NO 处理失败")
                print("=" * 60)
                return False
        else:
            print(f"文件夹模式: {input_path}")
            # 询问输出目录
            default_output = input_path / "newfont"
            
            # 尝试获取用户输入，如果失败（非交互式环境）则使用默认值
            try:
                output_input = input(f"请输入输出目录（直接回车使用默认: {default_output}）: ").strip()
                output_path = output_input if output_input else default_output
            except EOFError:
                # 非交互式环境，直接使用默认输出路径
                print(f"使用默认输出目录: {default_output}")
                output_path = default_output
            
            successful_files = self.process_folder(input_path, output_path)
            return len(successful_files) > 0

def main():
    """程序入口"""
    # 解析命令行参数
    input_path = None
    
    # 解析参数 - 只保留输入路径
    for arg in sys.argv[1:]:
        if os.path.exists(arg):
            input_path = arg
            break
    
    if not input_path:
        # 交互模式
        print("MKV字体替换工具 - D.py批量版")
        print("支持文件和文件夹拖放")
        print("=" * 60)
        
        input_path = input("请拖放文件或文件夹: ").strip().strip('"')
        if not input_path:
            print("路径不能为空")
            return
    
    # 创建并运行替换器
    replacer = MKVFontReplacer()
    success = replacer.main(input_path)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()