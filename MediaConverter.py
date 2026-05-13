import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import os
import threading
import json

# 自动安装缺失的依赖
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    TKINTERDND_AVAILABLE = True
except ImportError:
    print("tkinterdnd2 未安装，正在安装...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tkinterdnd2", "--no-cache-dir"])
    from tkinterdnd2 import TkinterDnD, DND_FILES
    TKINTERDND_AVAILABLE = True

# ============================================
# 配置区 - 用于保存MediaConverter相关配置
# ============================================

# MEDIA_CONVERTER_CONFIG_START - 唯一配置开始标记
MEDIA_CONVERTER_CONFIG = {
  "enable_subtitle": False,
  "subtitle_style": "none",
  "resolution": "original",
  "delete_original": True,
  "codec": "自动",
  "preset": "medium",
  "bitrate": "自动",
  "max_bitrate": "自动",
  "crf": "自动",
  "fps": "默认",
  "audio_format": "mp3",
  "audio_quality": "auto",
  "audio_bitrate": "自动",
  "flac_compression": "best"
}
# MEDIA_CONVERTER_CONFIG_END

class TS2MP4Converter:
    # 类变量，用于存储全局状态
    global_state = {
        'video_input_files': [],
        'audio_input_files': [],
        'subtitle_files': [],
        'subtitle_style': 'default',  # default, ktv, prompter
        'is_converting': False,
        'is_format_conversion': False,
        'progress': 0,
        'status': '就绪',
        'success_count': 0,
        'failed_count': 0,
        'failed_files': []
    }
    
    def __init__(self, parent=None, font_config=None):
        # 判断是否独立运行
        self.is_standalone = parent is None
        
        if self.is_standalone:
            # 独立运行，创建自己的根窗口
            if TKINTERDND_AVAILABLE:
                self.parent = TkinterDnD.Tk()
            else:
                self.parent = tk.Tk()
            self.parent.title("TS转MP4转换器")
            self.parent.geometry("600x600")
            self.parent.resizable(False, False)
        else:
            # 内嵌运行，使用父窗口
            self.parent = parent
        
        # 获取字体配置
        self.font_config = font_config or {}
        self.font_name = self.font_config.get("ui_font", "微软雅黑")
        self.font_size = int(self.font_config.get("ui_font_size", 16))
        self.font_weight = "bold" if self.font_config.get("ui_bold", False) else "normal"
        
        # 获取FFmpeg路径
        # 使用灵活的路径查找方式，确保能正确找到ffmpeg.exe
        # 尝试多种可能的路径
        possible_paths = [
            # 当从SRT目录运行时
            os.path.join("Python", "ffmpeg", "ffmpeg.exe"),
            # 当从SRT2ASS根目录运行时
            os.path.join("SRT", "Python", "ffmpeg", "ffmpeg.exe"),
            # 当从其他目录运行时，尝试向上查找
            os.path.join("..", "Python", "ffmpeg", "ffmpeg.exe"),
            os.path.join("..", "..", "Python", "ffmpeg", "ffmpeg.exe")
        ]
        
        self.ffmpeg_path = None
        for path in possible_paths:
            if os.path.exists(path):
                self.ffmpeg_path = path
                break
        
        if not self.ffmpeg_path:
            messagebox.showerror("错误", "找不到FFmpeg可执行文件！请确保FFmpeg位于SRT\\Python\\ffmpeg目录中")
            return
        
        # 从全局状态恢复
        self.video_input_files = self.global_state.get('video_input_files', [])
        self.audio_input_files = self.global_state.get('audio_input_files', [])
        self.subtitle_files = self.global_state.get('subtitle_files', [])
        self.subtitle_style = self.global_state.get('subtitle_style', 'default')
        self.is_converting = self.global_state.get('is_converting', False)
        self.is_format_conversion = self.global_state.get('is_format_conversion', False)
        
        # 从配置区加载配置
        self.load_config()
        
        self.create_widgets()
        
        # 恢复UI状态
        self.progress_var.set(self.global_state['progress'])
        self.status_var.set(self.global_state['status'])
        
        # 恢复文件列表
        # 暂时注释掉，因为widgets还未创建
        # for file_path in self.input_files:
        #     self.input_listbox.insert(tk.END, os.path.basename(file_path))
        
        # 如果正在转换，更新按钮状态
        if self.is_converting:
            try:
                self.convert_button.config(state=tk.DISABLED, text="转换中...")
                self.add_button.config(state=tk.DISABLED)
                self.add_folder_button.config(state=tk.DISABLED)
                self.remove_button.config(state=tk.DISABLED)
                self.clear_button.config(state=tk.DISABLED)
            except:
                pass
        
        # 如果是独立运行，启动主循环
        if self.is_standalone:
            self.parent.mainloop()
    
    def load_config(self):
        """从配置区加载配置"""
        global MEDIA_CONVERTER_CONFIG
        self.enable_subtitle = MEDIA_CONVERTER_CONFIG.get("enable_subtitle", True)
        self.subtitle_style = MEDIA_CONVERTER_CONFIG.get("subtitle_style", "ktv")
        self.resolution = MEDIA_CONVERTER_CONFIG.get("resolution", "original")
        self.delete_original = MEDIA_CONVERTER_CONFIG.get("delete_original", False)
        # 加载高级设置
        self.codec = MEDIA_CONVERTER_CONFIG.get("codec", "h264_nvenc")
        self.preset = MEDIA_CONVERTER_CONFIG.get("preset", "medium")
        self.bitrate = MEDIA_CONVERTER_CONFIG.get("bitrate", "8M")
        self.max_bitrate = MEDIA_CONVERTER_CONFIG.get("max_bitrate", "16M")
        self.crf = MEDIA_CONVERTER_CONFIG.get("crf", "18")
        self.fps = MEDIA_CONVERTER_CONFIG.get("fps", "默认")
        # 加载音频设置
        self.audio_format = MEDIA_CONVERTER_CONFIG.get("audio_format", "mp3")
        self.audio_quality = MEDIA_CONVERTER_CONFIG.get("audio_quality", "high")
        self.audio_bitrate = MEDIA_CONVERTER_CONFIG.get("audio_bitrate", "自动")
        self.flac_compression = MEDIA_CONVERTER_CONFIG.get("flac_compression", "medium")
    
    def save_config(self):
        """保存配置到配置区"""
        global MEDIA_CONVERTER_CONFIG
        try:
            with open(__file__, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 找到配置开始和结束标记
            start_tag = '# MEDIA_CONVERTER_CONFIG_START - 唯一配置开始标记'
            end_tag = '# MEDIA_CONVERTER_CONFIG_END'
            start_pos = content.find(start_tag)
            end_pos = content.find(end_tag)
            
            if start_pos != -1 and end_pos != -1:
                start_pos += len(start_tag)
                # 构建新的配置字符串
                config_str = json.dumps(MEDIA_CONVERTER_CONFIG, ensure_ascii=False, indent=2)
                # 将JSON布尔值转换为Python布尔值
                config_str = config_str.replace('true', 'True').replace('false', 'False')
                # 生成新的文件内容
                new_content = content[:start_pos] + '\nMEDIA_CONVERTER_CONFIG = ' + config_str + '\n' + content[end_pos:]
                
                # 写入文件
                with open(__file__, 'w', encoding='utf-8') as f:
                    f.write(new_content)
        except Exception as e:
            print(f"保存MediaConverter配置失败: {e}")
    
    def get_subtitle_tracks(self, input_file):
        """获取视频文件中的字幕轨道信息"""
        try:
            # 使用ffprobe获取视频文件信息
            cmd = [
                self.ffmpeg_path.replace('ffmpeg.exe', 'ffprobe.exe'),
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_streams',
                input_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            import json
            data = json.loads(result.stdout)
            
            # 提取字幕轨道信息
            subtitle_tracks = []
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'subtitle':
                    track_info = {
                        'index': stream.get('index'),
                        'language': stream.get('tags', {}).get('language', ''),
                        'title': stream.get('tags', {}).get('title', ''),
                        'codec_name': stream.get('codec_name')
                    }
                    subtitle_tracks.append(track_info)
            
            return subtitle_tracks
        except Exception as e:
            print(f"获取字幕轨道信息失败: {e}")
            return []
    
    def get_video_resolution(self, input_file):
        """获取视频文件的原始分辨率"""
        try:
            # 使用ffprobe获取视频文件信息
            cmd = [
                self.ffmpeg_path.replace('ffmpeg.exe', 'ffprobe.exe'),
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_streams',
                input_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            import json
            data = json.loads(result.stdout)
            
            # 提取视频轨道信息
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    width = stream.get('width', 0)
                    height = stream.get('height', 0)
                    return width, height
            
            return 0, 0
        except Exception as e:
            print(f"获取视频分辨率失败: {e}")
            return 0, 0
    
    def get_video_info(self, input_file):
        """获取视频文件的详细信息，包括分辨率、编码格式、比特率和帧率"""
        try:
            # 尝试使用ffprobe获取视频文件信息
            ffprobe_path = self.ffmpeg_path.replace('ffmpeg.exe', 'ffprobe.exe')
            
            # 首先检查ffprobe是否存在
            if not os.path.exists(ffprobe_path):
                print(f"ffprobe不存在: {ffprobe_path}")
                return {
                    'resolution': 'Unknown',
                    'codec': 'Unknown',
                    'bitrate': 'Unknown',
                    'fps': 'Unknown'
                }
            
            # 使用更详细的命令获取视频信息
            cmd = [
                ffprobe_path,
                '-v', 'error',
                '-show_format',
                '-show_streams',
                '-print_format', 'json',
                input_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            
            # 检查命令是否执行成功
            if result.returncode != 0:
                print(f"ffprobe命令执行失败: {result.stderr}")
                return {
                    'resolution': 'Unknown',
                    'codec': 'Unknown',
                    'bitrate': 'Unknown',
                    'fps': 'Unknown'
                }
            
            import json
            data = json.loads(result.stdout)
            
            video_info = {
                'resolution': 'Unknown',
                'codec': 'Unknown',
                'bitrate': 'Unknown',
                'fps': 'Unknown',
                'audio_bitrate': 'Unknown'
            }
            
            # 提取视频轨道信息
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    width = stream.get('width', 0)
                    height = stream.get('height', 0)
                    if width and height:
                        video_info['resolution'] = f'{width}x{height}'
                    
                    codec_name = stream.get('codec_name', 'Unknown')
                    video_info['codec'] = codec_name
                    
                    # 尝试从视频流获取比特率
                    bitrate = stream.get('bit_rate')
                    if not bitrate:
                        # 如果视频流中没有比特率，尝试从格式信息中获取
                        bitrate = data.get('format', {}).get('bit_rate')
                    
                    if bitrate:
                        try:
                            bitrate_kbps = int(bitrate) // 1000
                            if bitrate_kbps >= 1000:
                                video_info['bitrate'] = f'{bitrate_kbps // 1000}M'
                            else:
                                video_info['bitrate'] = f'{bitrate_kbps}K'
                        except:
                            pass
                    
                    # 获取帧率
                    fps = stream.get('r_frame_rate')
                    if fps:
                        try:
                            # 处理分数形式的帧率，如 30/1, 29.97/1 等
                            if '/' in fps:
                                num, den = fps.split('/')
                                fps_value = float(num) / float(den)
                                video_info['fps'] = f'{fps_value:.2f}'
                            else:
                                video_info['fps'] = fps
                        except:
                            video_info['fps'] = fps
                    break
            
            # 提取音频轨道信息
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    bitrate = stream.get('bit_rate')
                    if bitrate:
                        try:
                            bitrate_kbps = int(bitrate) // 1000
                            video_info['audio_bitrate'] = f'{bitrate_kbps}k'
                        except:
                            pass
                    break
            
            return video_info
        except Exception as e:
            print(f"获取视频信息失败: {e}")
            return {
                'resolution': 'Unknown',
                'codec': 'Unknown',
                'bitrate': 'Unknown',
                'fps': 'Unknown'
            }
    
    def enable_file_drop(self):
        """启用文件拖拽功能"""
        # 为文件列表添加拖拽功能
        try:
            # 启用列表框的多选功能
            self.video_listbox.config(selectmode=tk.MULTIPLE)
            if hasattr(self, 'audio_listbox'):
                self.audio_listbox.config(selectmode=tk.MULTIPLE)
            
            # 绑定右键菜单
            self.video_listbox.bind('<Button-3>', self.show_video_context_menu)
            if hasattr(self, 'audio_listbox'):
                self.audio_listbox.bind('<Button-3>', self.show_audio_context_menu)
            
            # 使用tkinterdnd2绑定文件拖拽事件
            if TKINTERDND_AVAILABLE:
                # 为文件列表框绑定拖拽事件
                self.video_listbox.drop_target_register(DND_FILES)
                self.video_listbox.dnd_bind('<<Drop>>', self.on_drop)
                
                if hasattr(self, 'audio_listbox'):
                    self.audio_listbox.drop_target_register(DND_FILES)
                    self.audio_listbox.dnd_bind('<<Drop>>', self.on_drop)
            else:
                pass
            
        except Exception as e:
            pass
    
    def on_drop(self, event):
        """处理文件拖放事件"""
        try:
            # 处理文件路径格式
            data = event.data
            
            # 处理多个文件的情况（花括号分隔）
            if '} {' in data:
                # 多个文件，按照 } { 分割
                file_paths = data.split('} {')
                # 处理第一个和最后一个文件的花括号
                file_paths[0] = file_paths[0].strip('{')
                file_paths[-1] = file_paths[-1].strip('}')
            else:
                # 单个文件，移除花括号
                data = data.strip('{}')
                file_paths = [data]
            
            # 确定当前活动的选项卡
            current_tab = self.notebook.select()
            is_audio_tab = hasattr(self, 'audio_conversion_frame') and current_tab == str(self.audio_conversion_frame)
            
            if is_audio_tab:
                # 音频转换页面：支持音频和视频文件
                media_extensions = ['.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg', '.mp4', '.mkv', '.avi', '.mov', '.ts']
            else:
                # 视频转换页面或TS转MP4页面：支持视频文件
                media_extensions = ['.ts', '.mp4', '.avi', '.mov', '.mkv']
            
            valid_files = []
            
            for file_path in file_paths:
                # 移除路径中的引号和空格
                file_path = file_path.strip().strip('"')
                
                # 检查文件是否存在
                if not os.path.exists(file_path):
                    continue
                
                # 检查是否是文件夹
                if os.path.isdir(file_path):
                    # 遍历文件夹中的所有文件
                    for root, dirs, files in os.walk(file_path):
                        for file in files:
                            file_full_path = os.path.join(root, file)
                            # 检查是否是支持的文件
                            ext = os.path.splitext(file_full_path)[1].lower()
                            if ext in media_extensions:
                                valid_files.append(file_full_path)
                else:
                    # 检查是否是支持的文件
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in media_extensions:
                        valid_files.append(file_path)
            
            # 添加文件到列表
            if valid_files:
                for file_path in valid_files:
                    if is_audio_tab:
                        # 音频转换页面
                        if file_path not in self.audio_input_files:
                            self.audio_input_files.append(file_path)
                            # 更新全局状态
                            self.global_state['audio_input_files'] = self.audio_input_files
                            
                            try:
                                audio_info = self.get_audio_info(file_path)
                                display_text = f"{os.path.basename(file_path)} [{audio_info.get('codec', 'Unknown')} | {audio_info.get('bitrate', 'Unknown')}]"
                                if hasattr(self, 'audio_listbox'):
                                    self.audio_listbox.insert(tk.END, display_text)
                            except Exception as e:
                                if hasattr(self, 'audio_listbox'):
                                    self.audio_listbox.insert(tk.END, os.path.basename(file_path))
                    else:
                        # 视频转换页面或TS转MP4页面
                        if file_path not in self.video_input_files:
                            self.video_input_files.append(file_path)
                            # 更新全局状态
                            self.global_state['video_input_files'] = self.video_input_files
                            
                            try:
                                video_info = self.get_video_info(file_path)
                                display_text = f"{os.path.basename(file_path)} [{video_info['resolution']} | {video_info['codec']} | {video_info['bitrate']}]"
                                if hasattr(self, 'input_listbox'):
                                    self.input_listbox.insert(tk.END, display_text)
                                if hasattr(self, 'video_listbox'):
                                    self.video_listbox.insert(tk.END, display_text)
                            except Exception as e:
                                pass
        except Exception as e:
            pass
    
    def create_widgets(self):
        # 设置样式
        style = ttk.Style()
        # 设置选项卡为暗色主题（使用与主GUI相同的配色）
        style.configure(
            "TNotebook",
            background="#2c2c2c",
            foreground="#ffffff"
        )
        style.configure(
            "TNotebook.Tab",
            background="#3a3a3a",
            foreground="#cccccc",  # 未选中时使用稍暗的文字颜色
            padding=[12, 6],
            font=(self.font_name, int(self.font_size * 0.9))  # 未选中时使用正常大小字体
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#4a90e2")],  # 选中时使用蓝色背景
            foreground=[("selected", "#ffffff")],  # 选中时使用白色文字
            font=[("selected", (self.font_name, int(self.font_size * 1.1), "bold"))],  # 选中时使用更大更粗的字体
            relief=[("selected", "raised")]  # 选中时添加凸起效果
        )
        
        # 自定义组合框样式
        style.configure(
            "Custom.TCombobox",
            background="#3a3a3a",
            foreground="#ffffff",
            fieldbackground="#3a3a3a",
            font=(self.font_name, int(self.font_size * 0.9))
        )
        style.map(
            "Custom.TCombobox",
            background=[("active", "#4a4a4a")],
            fieldbackground=[("active", "#4a4a4a")],
            font=[("focus", (self.font_name, int(self.font_size * 0.9), "bold"))]  # 选中时使用加粗字体
        )
        
        # 自定义复选框样式
        style.configure(
            "MediaConverter.TCheckbutton",
            background="#2c2c2c",
            foreground="#ffffff",
            font=(self.font_name, int(self.font_size * 0.9))
        )
        style.map(
            "MediaConverter.TCheckbutton",
            background=[("active", "#3a3a3a")],
            foreground=[("active", "#ffffff")]
        )
        
        # 创建主框架
        self.main_frame = ttk.Frame(self.parent, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_font_size = int(self.font_size * 1.2)
        title_label = ttk.Label(self.main_frame, text="媒体格式转换工具", font=(self.font_name, title_font_size, "bold"))
        title_label.pack(pady=10)
        
        # 创建选项卡
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 视频转换页面
        self.format_conversion_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.format_conversion_frame, text="视频转换")
        
        # 音频转换页面
        self.audio_conversion_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.audio_conversion_frame, text="音频转换")
        
        # 初始化格式转换页面
        self.init_format_conversion_page()
        
        # 初始化音频转换页面
        self.init_audio_conversion_page()
        
        # 进度条和状态标签（全局）
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.main_frame, variable=self.progress_var, maximum=100, length=400)
        self.progress_bar.pack(pady=10)
        
        # 进度条文本标签
        self.status_var = tk.StringVar(value="就绪")
        self.status_label = ttk.Label(self.main_frame, textvariable=self.status_var)
        self.status_label.pack(pady=5)
        
        # 启用文件拖拽功能
        self.enable_file_drop()
    

    
    def init_format_conversion_page(self):
        """初始化格式转换页面"""
        frame = self.format_conversion_frame
        
        # 输入文件选择区域
        input_frame = ttk.Frame(frame)
        input_frame.pack(pady=10, padx=20, fill=tk.X)
        
        label_font_size = int(self.font_size * 0.8)
        ttk.Label(input_frame, text="视频文件:", font=(self.font_name, label_font_size, self.font_weight)).pack(anchor=tk.W)
        
        listbox_font_size = int(self.font_size * 0.75)
        self.video_listbox = tk.Listbox(input_frame, height=10, selectmode=tk.MULTIPLE, font=(self.font_name, listbox_font_size, self.font_weight))
        self.video_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # 启用列表框的多选功能
        self.video_listbox.config(selectmode=tk.MULTIPLE)
        
        # 绑定右键菜单
        self.video_listbox.bind('<Button-3>', self.show_video_context_menu)
        
        # 确保区域选择功能正常工作
        self.video_listbox.bind('<ButtonPress-1>', lambda e: self.video_listbox.selection_clear(0, tk.END))
        self.video_listbox.bind('<B1-Motion>', lambda e: self.video_listbox.selection_set(self.video_listbox.nearest(e.y)))
        
        input_scrollbar = ttk.Scrollbar(input_frame, orient=tk.VERTICAL, command=self.video_listbox.yview)
        input_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.video_listbox.config(yscrollcommand=input_scrollbar.set)
        
        # 创建右键菜单
        self.video_context_menu = tk.Menu(self.parent, tearoff=0)
        self.video_context_menu.add_command(label="移除", command=self.remove_video_files)
        self.video_context_menu.add_separator()
        # 动态添加音频和字幕轨道选项
        self.video_context_menu.add_cascade(label="选择音频轨道", menu=self.create_audio_track_menu())
        self.video_context_menu.add_cascade(label="选择字幕轨道", menu=self.create_subtitle_track_menu())
        
        # 按钮区域
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=10)
        
        self.add_video_button = ttk.Button(button_frame, text="添加视频文件", command=self.add_video_files, width=12)
        self.add_video_button.pack(side=tk.LEFT, padx=5)
        
        self.add_video_folder_button = ttk.Button(button_frame, text="打开文件夹", command=self.add_video_folder_files, width=12)
        self.add_video_folder_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_video_button = ttk.Button(button_frame, text="清空列表", command=self.clear_video_files, width=12)
        self.clear_video_button.pack(side=tk.LEFT, padx=5)
        
        # 转换按钮（放到最右边）
        self.format_conversion_button = ttk.Button(button_frame, text="开始处理", command=self.start_format_conversion, width=15)
        self.format_conversion_button.pack(side=tk.RIGHT, padx=5)
        
        # 处理状态标志
        self.is_processing = False
        self.process_thread = None
        
        # 字幕效果和分辨率预设
        options_frame = ttk.Frame(frame)
        options_frame.pack(pady=10, padx=20, fill=tk.X)
        
        # 字幕效果部分
        style_part = ttk.Frame(options_frame)
        style_part.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(style_part, text="字幕效果:", font=(self.font_name, label_font_size, self.font_weight)).pack(side=tk.LEFT, padx=5)
        # 创建中文选项和英文值的映射
        self.style_options = {
            "禁用字幕": "none",
            "默认效果": "default",
            "KTV效果": "ktv",
            "提词器效果": "prompter"
        }
        # 设置默认值为禁用字幕，不读取配置
        self.subtitle_style_var = tk.StringVar(value="禁用字幕")
        # 创建暗色主题的下拉框，使用中文选项
        self.style_combobox = ttk.Combobox(
            style_part, 
            textvariable=self.subtitle_style_var, 
            values=list(self.style_options.keys()), 
            width=15, 
            state="readonly",
            style="Custom.TCombobox"
        )
        self.style_combobox.bind("<<ComboboxSelected>>", self.on_subtitle_style_changed)
        self.style_combobox.pack(side=tk.LEFT, padx=5)
        
        # 分辨率预设部分
        resolution_part = ttk.Frame(options_frame)
        resolution_part.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(resolution_part, text="分辨率预设:", font=(self.font_name, label_font_size, self.font_weight)).pack(side=tk.LEFT, padx=5)
        # 分辨率选项
        self.resolution_options = {
            "原始": "original",
            "480P": "480",
            "720P": "720",
            "1080P": "1080"
        }
        # 设置默认值
        resolution_name = "原始"  # 默认值
        for name, value in self.resolution_options.items():
            if value == self.resolution:
                resolution_name = name
                break
        self.resolution_var = tk.StringVar(value=resolution_name)
        # 创建暗色主题的下拉框
        self.resolution_combobox = ttk.Combobox(
            resolution_part, 
            textvariable=self.resolution_var, 
            values=list(self.resolution_options.keys()), 
            width=10, 
            state="readonly",
            style="Custom.TCombobox"
        )
        self.resolution_combobox.bind("<<ComboboxSelected>>", self.on_resolution_changed)
        self.resolution_combobox.pack(side=tk.LEFT, padx=5)
        
        # 编码和比特率设置区域
        settings_frame = ttk.LabelFrame(frame, text="编码设置")
        settings_frame.pack(fill=tk.X, pady=10, padx=20)
        
        # 第一行：编码器和预设
        row1 = ttk.Frame(settings_frame)
        row1.pack(fill=tk.X, pady=5, padx=10)
        
        # 编码器选择
        ttk.Label(row1, text="编码器:", width=10).pack(side=tk.LEFT, padx=5)
        self.codec_var = tk.StringVar(value=self.codec)
        codec_combobox = ttk.Combobox(
            row1, 
            textvariable=self.codec_var, 
            values=["自动", "h264_nvenc", "hevc_nvenc", "libx264", "libx265"], 
            state="readonly",
            width=15,
            style="Custom.TCombobox"
        )
        codec_combobox.pack(side=tk.LEFT, padx=10)
        
        # 预设选择
        ttk.Label(row1, text="预设:", width=10).pack(side=tk.LEFT, padx=5)
        self.preset_var = tk.StringVar(value=self.preset)
        preset_combobox = ttk.Combobox(
            row1, 
            textvariable=self.preset_var, 
            values=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"], 
            state="readonly",
            width=15,
            style="Custom.TCombobox"
        )
        preset_combobox.pack(side=tk.LEFT, padx=10)
        
        # 第二行：比特率设置
        row2 = ttk.Frame(settings_frame)
        row2.pack(fill=tk.X, pady=5, padx=10)
        
        # 目标比特率
        ttk.Label(row2, text="目标比特率:", width=10).pack(side=tk.LEFT, padx=5)
        self.bitrate_var = tk.StringVar(value=self.bitrate)
        bitrate_combobox = ttk.Combobox(
            row2, 
            textvariable=self.bitrate_var, 
            values=["自动", "1M", "2M", "4M", "6M", "8M", "10M", "12M", "16M", "20M", "24M"], 
            state="readonly",
            width=15,
            style="Custom.TCombobox"
        )
        bitrate_combobox.pack(side=tk.LEFT, padx=10)
        
        # 最大比特率
        ttk.Label(row2, text="最大比特率:", width=10).pack(side=tk.LEFT, padx=5)
        self.max_bitrate_var = tk.StringVar(value=self.max_bitrate)
        max_bitrate_combobox = ttk.Combobox(
            row2, 
            textvariable=self.max_bitrate_var, 
            values=["自动", "2M", "4M", "8M", "12M", "16M", "24M", "32M", "40M"], 
            state="readonly",
            width=15,
            style="Custom.TCombobox"
        )
        max_bitrate_combobox.pack(side=tk.LEFT, padx=10)
        
        # 第三行：帧率和CRF值设置
        row3 = ttk.Frame(settings_frame)
        row3.pack(fill=tk.X, pady=5, padx=10)
        
        # 帧率设置
        ttk.Label(row3, text="帧率:", width=10).pack(side=tk.LEFT, padx=5)
        self.fps_var = tk.StringVar(value="默认")
        fps_combobox = ttk.Combobox(
            row3, 
            textvariable=self.fps_var, 
            values=["默认", "24", "30", "60"], 
            state="readonly",
            width=15,
            style="Custom.TCombobox"
        )
        fps_combobox.pack(side=tk.LEFT, padx=10)
        
        # CRF值设置
        ttk.Label(row3, text="CRF值:", width=10).pack(side=tk.LEFT, padx=5)
        self.crf_var = tk.StringVar(value=self.crf)
        crf_combobox = ttk.Combobox(
            row3, 
            textvariable=self.crf_var, 
            values=["自动", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24"], 
            state="readonly",
            width=15,
            style="Custom.TCombobox"
        )
        crf_combobox.pack(side=tk.LEFT, padx=10)
        ttk.Label(row3, text="越小质量越高", foreground="#808080").pack(side=tk.LEFT, padx=5)

        
        # 绑定分辨率变化事件
        self.resolution_combobox.bind("<<ComboboxSelected>>", self.on_resolution_changed)
        
        # 移除已成功文件选项
        option_frame = ttk.Frame(frame)
        option_frame.pack(pady=10, padx=20, fill=tk.X)
        
        self.remove_success_var = tk.BooleanVar(value=True)  # 默认勾选
        self.remove_success_checkbox = ttk.Checkbutton(
            option_frame, 
            text="转换完成后移除已成功文件", 
            variable=self.remove_success_var,
            style="MediaConverter.TCheckbutton"
        )
        self.remove_success_checkbox.pack(anchor=tk.W, pady=5)
    
    def init_audio_conversion_page(self):
        """初始化音频转换页面"""
        frame = self.audio_conversion_frame
        
        # 输入文件选择区域
        input_frame = ttk.Frame(frame)
        input_frame.pack(pady=10, padx=20, fill=tk.X)
        
        label_font_size = int(self.font_size * 0.8)
        ttk.Label(input_frame, text="音频/视频文件:", font=(self.font_name, label_font_size, self.font_weight)).pack(anchor=tk.W)
        
        listbox_font_size = int(self.font_size * 0.75)
        self.audio_listbox = tk.Listbox(input_frame, height=10, selectmode=tk.MULTIPLE, font=(self.font_name, listbox_font_size, self.font_weight))
        self.audio_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # 启用列表框的多选功能
        self.audio_listbox.config(selectmode=tk.MULTIPLE)
        
        # 绑定右键菜单
        self.audio_listbox.bind('<Button-3>', self.show_audio_context_menu)
        
        # 确保区域选择功能正常工作
        self.audio_listbox.bind('<ButtonPress-1>', lambda e: self.audio_listbox.selection_clear(0, tk.END))
        self.audio_listbox.bind('<B1-Motion>', lambda e: self.audio_listbox.selection_set(self.audio_listbox.nearest(e.y)))
        
        input_scrollbar = ttk.Scrollbar(input_frame, orient=tk.VERTICAL, command=self.audio_listbox.yview)
        input_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.audio_listbox.config(yscrollcommand=input_scrollbar.set)
        
        # 创建右键菜单（初始创建）
        self.audio_context_menu = tk.Menu(self.parent, tearoff=0)
        self.audio_context_menu.add_command(label="移除", command=self.remove_audio_files)
        
        # 按钮区域
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=10)
        
        self.add_audio_button = ttk.Button(button_frame, text="添加文件", command=self.add_audio_files, width=12)
        self.add_audio_button.pack(side=tk.LEFT, padx=5)
        
        self.add_audio_folder_button = ttk.Button(button_frame, text="打开文件夹", command=self.add_audio_folder_files, width=12)
        self.add_audio_folder_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_audio_button = ttk.Button(button_frame, text="清空列表", command=self.clear_audio_files, width=12)
        self.clear_audio_button.pack(side=tk.LEFT, padx=5)
        
        # 转换按钮（放到最右边）
        self.audio_conversion_button = ttk.Button(button_frame, text="开始转换", command=self.start_audio_conversion, width=15)
        self.audio_conversion_button.pack(side=tk.RIGHT, padx=5)
        
        # 处理状态标志
        self.audio_conversion_processing = False
        
        # 音频设置区域
        settings_frame = ttk.LabelFrame(frame, text="音频设置")
        settings_frame.pack(fill=tk.X, pady=10, padx=20)
        
        # 第一行：输出格式
        row1 = ttk.Frame(settings_frame)
        row1.pack(fill=tk.X, pady=5, padx=10)
        
        ttk.Label(row1, text="输出格式:", width=10).pack(side=tk.LEFT, padx=5)
        self.audio_format_var = tk.StringVar(value=self.audio_format)
        audio_format_combobox = ttk.Combobox(
            row1, 
            textvariable=self.audio_format_var, 
            values=["mp3", "flac"], 
            state="readonly",
            width=15,
            style="Custom.TCombobox"
        )
        audio_format_combobox.pack(side=tk.LEFT, padx=10)
        audio_format_combobox.bind("<<ComboboxSelected>>", self.on_audio_format_changed)
        
        # 第二行：MP3质量设置（仅MP3时显示）
        self.mp3_quality_frame = ttk.Frame(settings_frame)
        self.mp3_quality_frame.pack(fill=tk.X, pady=5, padx=10)
        
        ttk.Label(self.mp3_quality_frame, text="MP3质量:", width=10).pack(side=tk.LEFT, padx=5)
        # 固定默认值为自动，不读取配置
        self.audio_quality_var = tk.StringVar(value="auto")
        self.audio_quality_display_var = tk.StringVar(value="自动")
        self.mp3_quality_combobox = ttk.Combobox(
            self.mp3_quality_frame, 
            textvariable=self.audio_quality_display_var, 
            values=["自动", "低质量", "中等质量", "高质量"], 
            state="readonly",
            width=15,
            style="Custom.TCombobox"
        )
        self.mp3_quality_combobox.pack(side=tk.LEFT, padx=10)
        self.mp3_quality_combobox.bind("<<ComboboxSelected>>", self.on_audio_quality_changed)
        
        # 第三行：MP3比特率设置（仅MP3时显示）
        self.mp3_bitrate_frame = ttk.Frame(settings_frame)
        self.mp3_bitrate_frame.pack(fill=tk.X, pady=5, padx=10)
        
        ttk.Label(self.mp3_bitrate_frame, text="比特率:", width=10).pack(side=tk.LEFT, padx=5)
        self.audio_bitrate_var = tk.StringVar(value=self.audio_bitrate)
        self.mp3_bitrate_combobox = ttk.Combobox(
            self.mp3_bitrate_frame, 
            textvariable=self.audio_bitrate_var, 
            values=["自动", "64k", "96k", "128k", "160k", "192k", "256k", "320k"], 
            state="readonly",
            width=15,
            style="Custom.TCombobox"
        )
        self.mp3_bitrate_combobox.pack(side=tk.LEFT, padx=10)
        self.mp3_bitrate_combobox.bind("<<ComboboxSelected>>", self.on_audio_bitrate_changed)
        
        # 第四行：FLAC压缩等级设置（仅FLAC时显示）
        self.flac_compression_frame = ttk.Frame(settings_frame)
        self.flac_compression_frame.pack(fill=tk.X, pady=5, padx=10)
        
        ttk.Label(self.flac_compression_frame, text="压缩等级:", width=10).pack(side=tk.LEFT, padx=5)
        # 固定默认值为中等压缩，不读取配置
        self.flac_compression_var = tk.StringVar(value="中等压缩 (5)")
        self.flac_compression_combobox = ttk.Combobox(
            self.flac_compression_frame, 
            textvariable=self.flac_compression_var, 
            values=["最高压缩 (0)", "中等压缩 (5)", "快速压缩 (8)"], 
            state="readonly",
            width=15,
            style="Custom.TCombobox"
        )
        self.flac_compression_combobox.pack(side=tk.LEFT, padx=10)
        self.flac_compression_combobox.bind("<<ComboboxSelected>>", self.on_flac_compression_changed)
        
        # 根据当前格式显示/隐藏相应的选项
        self.update_audio_options_visibility()
        
        # 移除已成功文件选项
        option_frame = ttk.Frame(frame)
        option_frame.pack(pady=10, padx=20, fill=tk.X)
        
        self.remove_audio_success_var = tk.BooleanVar(value=True)
        self.remove_audio_success_checkbox = ttk.Checkbutton(
            option_frame, 
            text="转换完成后移除已成功文件", 
            variable=self.remove_audio_success_var,
            style="MediaConverter.TCheckbutton"
        )
        self.remove_audio_success_checkbox.pack(anchor=tk.W, pady=5)
    
    def update_audio_options_visibility(self):
        """根据输出格式显示/隐藏相应的选项"""
        current_format = self.audio_format_var.get()
        if current_format == "flac":
            self.mp3_quality_frame.pack_forget()
            self.mp3_bitrate_frame.pack_forget()
            self.flac_compression_frame.pack(fill=tk.X, pady=5, padx=10)
        else:
            self.flac_compression_frame.pack_forget()
            self.mp3_quality_frame.pack(fill=tk.X, pady=5, padx=10)
            self.mp3_bitrate_frame.pack(fill=tk.X, pady=5, padx=10)
    
    def on_audio_format_changed(self, event):
        """音频格式选项变化时的处理"""
        global MEDIA_CONVERTER_CONFIG
        MEDIA_CONVERTER_CONFIG["audio_format"] = self.audio_format_var.get()
        self.update_audio_options_visibility()
        self.save_config()
    
    def on_audio_quality_changed(self, event):
        """MP3质量选项变化时的处理"""
        # 不同步保存配置
        # 同步更新比特率显示
        bitrate_map = {
            "自动": "自动",
            "低质量": "128k",
            "中等质量": "192k",
            "高质量": "320k"
        }
        selected = self.audio_quality_display_var.get()
        bitrate = bitrate_map.get(selected, "自动")
        self.audio_bitrate_var.set(bitrate)
    
    def on_flac_compression_changed(self, event):
        """FLAC压缩等级选项变化时的处理"""
        # 不同步保存配置
    
    def on_audio_bitrate_changed(self, event):
        """MP3比特率选项变化时的处理"""
        # 不同步保存配置
    
    def add_audio_files(self):
        """添加音频文件"""
        files = filedialog.askopenfilenames(
            title="选择音频/视频文件",
            filetypes=[("音频/视频文件", "*.mp3;*.flac;*.wav;*.m4a;*.aac;*.ogg;*.mp4;*.mkv;*.avi;*.mov;*.ts"), ("所有文件", "*.*")],
            initialdir=os.getcwd()
        )
        
        for file in files:
            if file not in self.audio_input_files:
                self.audio_input_files.append(file)
                # 更新全局状态
                self.global_state['audio_input_files'] = self.audio_input_files
                try:
                    # 获取音频信息
                    audio_info = self.get_audio_info(file)
                    # 构建显示文本
                    display_text = f"{os.path.basename(file)} [{audio_info.get('codec', 'Unknown')} | {audio_info.get('bitrate', 'Unknown')}]"
                    self.audio_listbox.insert(tk.END, display_text)
                except:
                    self.audio_listbox.insert(tk.END, os.path.basename(file))
    
    def add_audio_folder_files(self):
        """添加音频文件夹"""
        folder = filedialog.askdirectory(title="选择包含音频/视频文件的文件夹", initialdir=os.getcwd())
        if folder:
            # 遍历文件夹中的所有音频文件
            audio_extensions = [".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg", ".mp4", ".mkv", ".avi", ".mov", ".ts"]
            for root, dirs, files in os.walk(folder):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in audio_extensions:
                        file_path = os.path.join(root, file)
                        if file_path not in self.audio_input_files:
                            self.audio_input_files.append(file_path)
                            # 更新全局状态
                            self.global_state['audio_input_files'] = self.audio_input_files
                            try:
                                # 获取音频信息
                                audio_info = self.get_audio_info(file_path)
                                # 构建显示文本
                                display_text = f"{os.path.basename(file)} [{audio_info.get('codec', 'Unknown')} | {audio_info.get('bitrate', 'Unknown')}]"
                                self.audio_listbox.insert(tk.END, display_text)
                            except:
                                self.audio_listbox.insert(tk.END, os.path.basename(file))
    
    def remove_audio_files(self):
        """移除选中的音频文件"""
        try:
            selected_indices = self.audio_listbox.curselection()[::-1]
            for index in selected_indices:
                self.audio_listbox.delete(index)
                del self.audio_input_files[index]
            # 更新全局状态
            self.global_state['audio_input_files'] = self.audio_input_files
        except:
            pass
    
    def clear_audio_files(self):
        """清空音频文件列表"""
        try:
            self.audio_listbox.delete(0, tk.END)
        except:
            pass
        self.audio_input_files.clear()
        # 更新全局状态
        self.global_state['audio_input_files'] = self.audio_input_files
    
    def show_audio_context_menu(self, event):
        """显示音频文件的右键菜单"""
        # 获取右键点击的文件索引
        index = self.audio_listbox.nearest(event.y)
        # 选择点击的文件
        self.audio_listbox.selection_clear(0, tk.END)
        self.audio_listbox.selection_set(index)
        # 保存当前选中的文件索引，供子菜单使用
        self.current_selected_file = self.audio_input_files[index]
        # 重新创建右键菜单，确保子菜单能够获取到选中的文件
        self.audio_context_menu = tk.Menu(self.parent, tearoff=0)
        self.audio_context_menu.add_command(label="移除", command=self.remove_audio_files)
        self.audio_context_menu.add_separator()
        # 音频转换页面只需要音频轨道选择，不需要字幕选择
        self.audio_context_menu.add_cascade(label="选择音频轨道", menu=self.create_audio_track_menu())
        # 显示右键菜单
        self.audio_context_menu.post(event.x_root, event.y_root)
    
    def get_audio_info(self, input_file):
        """获取音频文件的详细信息"""
        try:
            # 使用ffprobe获取音频信息
            ffprobe_path = self.ffmpeg_path.replace('ffmpeg.exe', 'ffprobe.exe')
            
            # 首先检查ffprobe是否存在
            if not os.path.exists(ffprobe_path):
                return {'codec': 'Unknown', 'bitrate': 'Unknown'}
            
            # 构建命令
            cmd = [
                ffprobe_path,
                '-v', 'error',
                '-show_format',
                '-show_streams',
                '-print_format', 'json',
                input_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            
            # 检查命令是否执行成功
            if result.returncode != 0:
                return {'codec': 'Unknown', 'bitrate': 'Unknown'}
            
            import json
            data = json.loads(result.stdout)
            
            audio_info = {
                'codec': 'Unknown',
                'bitrate': 'Unknown'
            }
            
            # 提取音频流信息
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    audio_info['codec'] = stream.get('codec_name', 'Unknown')
                    break
            
            # 提取比特率
            bitrate = data.get('format', {}).get('bit_rate')
            if bitrate:
                try:
                    bitrate_kbps = int(bitrate) // 1000
                    if bitrate_kbps >= 1000:
                        audio_info['bitrate'] = f"{bitrate_kbps // 1000}M"
                    else:
                        audio_info['bitrate'] = f"{bitrate_kbps}k"
                except:
                    pass
            
            return audio_info
        except Exception as e:
            return {'codec': 'Unknown', 'bitrate': 'Unknown'}
    
    def get_original_audio_bitrate(self, input_file):
        """获取原始音频的比特率（kbps），用于MP3转换时保持原比特率"""
        try:
            ffprobe_path = self.ffmpeg_path.replace('ffmpeg.exe', 'ffprobe.exe')
            if not os.path.exists(ffprobe_path):
                return 0
            
            cmd = [
                ffprobe_path,
                '-v', 'error',
                '-show_format',
                '-show_streams',
                '-print_format', 'json',
                input_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            if result.returncode != 0:
                return 0
            
            import json
            data = json.loads(result.stdout)
            
            # 只从音频流获取比特率，不回退到整体格式（避免获取到视频比特率）
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    bitrate = stream.get('bit_rate')
                    if bitrate:
                        audio_bitrate = int(bitrate) // 1000
                        # 检查比特率是否合理（一般不会超过512kbps）
                        if audio_bitrate > 0 and audio_bitrate <= 512:
                            return audio_bitrate
            
            return 0
        except:
            return 0
    
    def start_audio_conversion(self):
        """开始音频转换"""
        if not self.audio_input_files:
            messagebox.showwarning("警告", "请添加至少一个音频/视频文件！")
            return
        
        if self.audio_conversion_processing:
            # 如果正在处理，停止处理
            self.stop_audio_conversion()
            return
        
        self.audio_conversion_processing = True
        self.global_state['status'] = "开始音频转换..."
        self.global_state['progress'] = 0
        
        try:
            self.audio_conversion_button.config(text="停止处理", command=self.stop_audio_conversion)
            self.add_audio_button.config(state=tk.DISABLED)
            self.add_audio_folder_button.config(state=tk.DISABLED)
            self.clear_audio_button.config(state=tk.DISABLED)
            self.status_var.set("处理中 0%")
            self.progress_var.set(0)
        except:
            pass
        
        # 启动转换线程
        self.audio_thread = threading.Thread(target=self.convert_audio_files, daemon=False)
        self.audio_thread.start()
    
    def stop_audio_conversion(self):
        """停止音频转换"""
        self.audio_conversion_processing = False
        self.global_state['status'] = "已停止"
        
        try:
            self.audio_conversion_button.config(text="开始转换", command=self.start_audio_conversion)
            self.add_audio_button.config(state=tk.NORMAL)
            self.add_audio_folder_button.config(state=tk.NORMAL)
            self.clear_audio_button.config(state=tk.NORMAL)
            self.status_var.set("已停止")
        except:
            pass
    
    def convert_audio_files(self):
        """执行音频文件转换"""
        total_files = len(self.audio_input_files)
        success_count = 0
        failed_count = 0
        failed_files = []
        
        for i, input_file in enumerate(self.audio_input_files):
            # 检查是否需要停止处理
            if not self.audio_conversion_processing:
                break
            
            filename = os.path.basename(input_file)
            
            # 更新全局状态
            current_progress = (i / total_files) * 100
            self.global_state['progress'] = current_progress
            self.global_state['status'] = f"正在处理 {i+1}/{total_files} - {filename} 成功: {success_count} 失败: {failed_count}"
            # 更新UI
            try:
                self.status_var.set(f"处理中 {current_progress:.1f}% - 正在处理 {i+1}/{total_files} - {filename}")
                self.progress_var.set(current_progress)
            except:
                pass
            
            try:
                # 获取文件中的所有音频轨道
                audio_tracks = self.get_audio_tracks(input_file)
                print(f"[{filename}] 发现 {len(audio_tracks)} 个音频轨道")
                
                # 检查用户是否手动选择了特定的音频轨道
                user_selected_track = getattr(self, 'selected_audio_track', None)
                
                # 要转换的轨道索引列表
                if user_selected_track is not None:
                    # 用户手动选择了特定轨道，只转换那一个
                    tracks_to_convert = [(user_selected_track, audio_tracks[user_selected_track])]
                else:
                    # 用户没有手动选择，转换所有音频轨道
                    tracks_to_convert = list(enumerate(audio_tracks))
                
                # 遍历要转换的音频轨道
                for track_idx, track_info in tracks_to_convert:
                    # 检查是否需要停止处理
                    if not self.audio_conversion_processing:
                        break
                    
                    # 生成输出路径
                    input_dir = os.path.dirname(input_file)
                    output_dir = os.path.join(input_dir, "已转换")
                    os.makedirs(output_dir, exist_ok=True)
                    
                    # 获取输出格式
                    output_format = self.audio_format_var.get()
                    
                    # 生成音频轨道标识（语言或标题）
                    track_label = ""
                    if track_info.get('language'):
                        track_label = track_info['language']
                    elif track_info.get('title'):
                        track_label = track_info['title']
                    elif track_info.get('codec'):
                        track_label = track_info['codec'].upper()
                    else:
                        track_label = f"Track{track_idx}"
                    
                    # 生成输出文件名
                    base_name = os.path.splitext(os.path.basename(input_file))[0]
                    if len(tracks_to_convert) > 1:
                        # 多个轨道时添加轨道标识
                        output_filename = f"{base_name} [{track_label}].{output_format}"
                    else:
                        # 单个轨道时直接使用原名
                        output_filename = f"{base_name}.{output_format}"
                    
                    # 获取唯一文件名
                    output_filename = self.get_unique_filename(output_dir, output_filename)
                    output_file = os.path.join(output_dir, output_filename)
                    
                    print(f"[{filename}] 转换音频轨道 {track_idx}: {track_label}")
                    
                    # 构建FFmpeg命令
                    cmd = [
                        self.ffmpeg_path,
                        '-i', input_file,
                        '-map_metadata', '0',
                        '-map', f'0:a:{track_idx}',
                        '-id3v2_version', '3',
                        '-write_id3v1', '1',
                        '-y'
                    ]
                    
                    # 根据输出格式和质量设置添加参数
                    if output_format == 'mp3':
                        cmd.extend(['-c:a', 'libmp3lame'])
                        selected_bitrate = self.audio_bitrate_var.get()
                        
                        if selected_bitrate == "自动":
                            # 获取该轨道的比特率
                            track_bitrate = self.get_audio_track_bitrate(input_file, track_idx)
                            if track_bitrate > 0:
                                bitrate = f"{track_bitrate}k"
                            else:
                                quality = self.audio_quality_display_var.get()
                                if quality == '低质量':
                                    bitrate = '128k'
                                elif quality == '高质量':
                                    bitrate = '320k'
                                else:
                                    bitrate = '192k'
                        else:
                            bitrate = selected_bitrate
                        
                        cmd.extend(['-b:a', bitrate])
                    elif output_format == 'flac':
                        cmd.extend(['-c:a', 'flac'])
                        compression_map = {
                            "快速压缩 (8)": "8",
                            "中等压缩 (5)": "5",
                            "最高压缩 (0)": "0"
                        }
                        selected = self.flac_compression_var.get()
                        compression_level = compression_map.get(selected, "5")
                        cmd.extend(['-compression_level', compression_level])
                    
                    # 添加输出文件
                    cmd.append(output_file)
                    
                    # 执行转换
                    print(f"执行命令: {' '.join(cmd)}")
                    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
                    
                    if result.returncode == 0:
                        print(f"转换成功: {filename} [{track_label}] -> {output_filename}")
                        success_count += 1
                    else:
                        # 转换失败，清理已生成的部分文件
                        if os.path.exists(output_file):
                            try:
                                os.remove(output_file)
                                print(f"已清理失败文件: {output_file}")
                            except:
                                pass
                        error_msg = f"转换失败: {filename} [{track_label}] - {result.stderr if result.stderr else '未知错误'}"
                        print(error_msg)
                        failed_count += 1
                        failed_files.append(f"{filename} [{track_label}]: {result.stderr if result.stderr else '未知错误'}")
                
            except Exception as e:
                error_msg = f"转换失败: {filename} - {str(e)}"
                print(error_msg)
                failed_count += 1
                failed_files.append(f"{filename}: {str(e)}")
                continue
        
        # 转换完成
        self.audio_conversion_processing = False
        self.global_state['is_converting'] = False
        self.global_state['progress'] = 100
        self.global_state['status'] = f"音频转换完成！成功: {success_count} 失败: {failed_count}"
        self.global_state['success_count'] = success_count
        self.global_state['failed_count'] = failed_count
        self.global_state['failed_files'] = failed_files
        
        # 检查是否需要移除已成功文件
        try:
            if self.remove_audio_success_var.get() and success_count > 0:
                # 收集失败文件的文件名
                failed_file_names = []
                for fail_info in failed_files:
                    if ': ' in fail_info:
                        filename = fail_info.split(': ')[0]
                        failed_file_names.append(filename)
                    else:
                        failed_file_names.append(os.path.basename(fail_info))
                # 过滤掉已成功的文件，只保留失败的文件
                self.audio_input_files = [file for file in self.audio_input_files if os.path.basename(file) in failed_file_names]
                # 更新全局状态
                self.global_state['audio_input_files'] = self.audio_input_files
                # 刷新文件列表显示
                self.update_audio_listbox()
                print(f"已移除 {success_count} 个成功文件，保留 {len(self.audio_input_files)} 个失败文件")
        except Exception as e:
            print(f"移除已成功文件时出错: {e}")
        
        # 尝试重置UI
        try:
            self.reset_audio_conversion_ui()
            self.status_var.set(f"处理完成 100% - 成功: {success_count} 失败: {failed_count}")
            self.progress_var.set(100)
            # 显示转换结果
            result_message = f"音频转换完成！\n成功: {success_count} 个文件\n失败: {failed_count} 个文件"
            if failed_files:
                result_message += "\n\n失败文件:\n" + "\n".join(failed_files)
            print(result_message)
        except:
            pass
    
    def update_audio_listbox(self):
        """更新音频文件列表显示"""
        try:
            self.audio_listbox.delete(0, tk.END)
            for file_path in self.audio_input_files:
                try:
                    audio_info = self.get_audio_info(file_path)
                    display_text = f"{os.path.basename(file_path)} [{audio_info.get('codec', 'Unknown')} | {audio_info.get('bitrate', 'Unknown')}]"
                    self.audio_listbox.insert(tk.END, display_text)
                except:
                    self.audio_listbox.insert(tk.END, os.path.basename(file_path))
        except Exception as e:
            print(f"更新音频列表时出错: {e}")
    
    def reset_audio_conversion_ui(self):
        """重置音频转换页面UI"""
        try:
            self.audio_conversion_button.config(text="开始转换", command=self.start_audio_conversion)
            self.add_audio_button.config(state=tk.NORMAL)
            self.add_audio_folder_button.config(state=tk.NORMAL)
            self.clear_audio_button.config(state=tk.NORMAL)
        except:
            pass
    

    
    def on_subtitle_style_changed(self, event):
        """字幕效果选项变化时的处理"""
        selected_style_name = self.subtitle_style_var.get()
        selected_style = self.style_options.get(selected_style_name, "none")
        
        # 如果选择了禁用字幕，设置enable_subtitle为False
        if selected_style == "none":
            if hasattr(self, 'enable_subtitle_var'):
                self.enable_subtitle_var.set(False)
        else:
            # 否则设置enable_subtitle为True
            if hasattr(self, 'enable_subtitle_var'):
                self.enable_subtitle_var.set(True)
    
    def on_resolution_changed(self, event):
        """分辨率选项变化时的处理"""
        global MEDIA_CONVERTER_CONFIG
        selected_resolution_name = self.resolution_var.get()
        selected_resolution = self.resolution_options.get(selected_resolution_name, "original")
        MEDIA_CONVERTER_CONFIG["resolution"] = selected_resolution
        
        # 根据分辨率预设更新编码信息（预设优先）
        if selected_resolution == "480":
            self.codec_var.set("h264_nvenc")
            self.preset_var.set("medium")
            self.bitrate_var.set("2M")
            self.max_bitrate_var.set("4M")
            self.crf_var.set("18")
            self.fps_var.set("默认")
        elif selected_resolution == "720":
            self.codec_var.set("h264_nvenc")
            self.preset_var.set("medium")
            self.bitrate_var.set("4M")
            self.max_bitrate_var.set("8M")
            self.crf_var.set("18")
            self.fps_var.set("默认")
        elif selected_resolution == "1080":
            self.codec_var.set("h264_nvenc")
            self.preset_var.set("medium")
            self.bitrate_var.set("6M")
            self.max_bitrate_var.set("12M")
            self.crf_var.set("18")
            self.fps_var.set("默认")
        else:  # original
            # 原始分辨率显示自动
            self.codec_var.set("自动")
            self.preset_var.set("medium")
            self.bitrate_var.set("自动")
            self.max_bitrate_var.set("自动")
            self.crf_var.set("自动")
            self.fps_var.set("默认")
        
        # 更新配置
        MEDIA_CONVERTER_CONFIG["codec"] = self.codec_var.get()
        MEDIA_CONVERTER_CONFIG["preset"] = self.preset_var.get()
        MEDIA_CONVERTER_CONFIG["bitrate"] = self.bitrate_var.get()
        MEDIA_CONVERTER_CONFIG["max_bitrate"] = self.max_bitrate_var.get()
        MEDIA_CONVERTER_CONFIG["crf"] = self.crf_var.get()
        MEDIA_CONVERTER_CONFIG["fps"] = self.fps_var.get()
        
        self.save_config()
    
    def show_advanced_settings(self):
        """显示高级设置窗口"""
        # 创建高级设置窗口
        self.advanced_window = tk.Toplevel(self.parent)
        self.advanced_window.title("高级设置")
        self.advanced_window.geometry("400x400")
        self.advanced_window.resizable(False, False)
        
        # 设置窗口背景
        self.advanced_window.configure(bg="#1e1e1e")
        
        # 创建主框架
        main_frame = ttk.Frame(self.advanced_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 编码格式设置
        codec_frame = ttk.LabelFrame(main_frame, text="编码设置")
        codec_frame.pack(fill=tk.X, pady=10)
        
        # 编码器选择
        codec_row = ttk.Frame(codec_frame)
        codec_row.pack(fill=tk.X, pady=5, padx=10)
        ttk.Label(codec_row, text="编码器:", width=10).pack(side=tk.LEFT, padx=5)
        
        self.codec_var = tk.StringVar(value="h264_nvenc")
        codec_combobox = ttk.Combobox(
            codec_row, 
            textvariable=self.codec_var, 
            values=["h264_nvenc", "hevc_nvenc", "libx264", "libx265"], 
            state="readonly",
            width=15
        )
        codec_combobox.pack(side=tk.LEFT, padx=5)
        
        # 预设选择
        preset_row = ttk.Frame(codec_frame)
        preset_row.pack(fill=tk.X, pady=5, padx=10)
        ttk.Label(preset_row, text="预设:", width=10).pack(side=tk.LEFT, padx=5)
        
        self.preset_var = tk.StringVar(value="medium")
        preset_combobox = ttk.Combobox(
            preset_row, 
            textvariable=self.preset_var, 
            values=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"], 
            state="readonly",
            width=15
        )
        preset_combobox.pack(side=tk.LEFT, padx=5)
        
        # 比特率设置
        bitrate_frame = ttk.LabelFrame(main_frame, text="比特率设置")
        bitrate_frame.pack(fill=tk.X, pady=10)
        
        # 目标比特率
        bitrate_row = ttk.Frame(bitrate_frame)
        bitrate_row.pack(fill=tk.X, pady=5, padx=10)
        ttk.Label(bitrate_row, text="目标比特率:", width=10).pack(side=tk.LEFT, padx=5)
        
        self.bitrate_var = tk.StringVar(value="8M")
        bitrate_combobox = ttk.Combobox(
            bitrate_row, 
            textvariable=self.bitrate_var, 
            values=["1M", "2M", "4M", "6M", "8M", "10M", "12M", "16M", "24M"], 
            state="readonly",
            width=10
        )
        bitrate_combobox.pack(side=tk.LEFT, padx=5)
        
        # 最大比特率
        max_bitrate_row = ttk.Frame(bitrate_frame)
        max_bitrate_row.pack(fill=tk.X, pady=5, padx=10)
        ttk.Label(max_bitrate_row, text="最大比特率:", width=10).pack(side=tk.LEFT, padx=5)
        
        self.max_bitrate_var = tk.StringVar(value="16M")
        max_bitrate_combobox = ttk.Combobox(
            max_bitrate_row, 
            textvariable=self.max_bitrate_var, 
            values=["2M", "4M", "8M", "12M", "16M", "24M", "32M", "48M"], 
            state="readonly",
            width=10
        )
        max_bitrate_combobox.pack(side=tk.LEFT, padx=5)
        
        # CRF值设置
        crf_frame = ttk.LabelFrame(main_frame, text="质量设置")
        crf_frame.pack(fill=tk.X, pady=10)
        
        crf_row = ttk.Frame(crf_frame)
        crf_row.pack(fill=tk.X, pady=5, padx=10)
        ttk.Label(crf_row, text="CRF值:", width=10).pack(side=tk.LEFT, padx=5)
        
        self.crf_var = tk.StringVar(value="18")
        crf_entry = ttk.Entry(crf_row, textvariable=self.crf_var, width=5)
        crf_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(crf_row, text="(0-51, 值越小质量越高)", foreground="#808080").pack(side=tk.LEFT, padx=5)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        save_button = ttk.Button(button_frame, text="保存", command=self.save_advanced_settings, width=10)
        save_button.pack(side=tk.RIGHT, padx=5)
        
        cancel_button = ttk.Button(button_frame, text="取消", command=self.advanced_window.destroy, width=10)
        cancel_button.pack(side=tk.RIGHT, padx=5)
    
    def save_advanced_settings(self):
        """保存高级设置"""
        # 保存设置到配置
        global MEDIA_CONVERTER_CONFIG
        
        # 检查并保存设置
        try:
            # 保存编码器设置
            MEDIA_CONVERTER_CONFIG["codec"] = self.codec_var.get()
            MEDIA_CONVERTER_CONFIG["preset"] = self.preset_var.get()
            MEDIA_CONVERTER_CONFIG["bitrate"] = self.bitrate_var.get()
            MEDIA_CONVERTER_CONFIG["max_bitrate"] = self.max_bitrate_var.get()
            MEDIA_CONVERTER_CONFIG["crf"] = self.crf_var.get()
            
            # 保存配置
            self.save_config()
            
            # 关闭窗口
            self.advanced_window.destroy()
            
            # 显示成功信息
            messagebox.showinfo("成功", "高级设置已保存")
        except Exception as e:
            messagebox.showerror("错误", f"保存设置失败: {e}")
    

    

    
    def remove_files(self):
        try:
            # 检查input_listbox是否存在
            if hasattr(self, 'input_listbox'):
                selected_indices = self.input_listbox.curselection()[::-1]
                for index in selected_indices:
                    self.input_listbox.delete(index)
                    del self.video_input_files[index]
                # 更新全局状态
                self.global_state['video_input_files'] = self.video_input_files
        except:
            pass
    




    def add_video_files(self):
        """添加视频文件"""
        files = filedialog.askopenfilenames(
            title="选择视频文件",
            filetypes=[("视频文件", "*.mp4;*.ts;*.avi;*.mov;*.mkv"), ("所有文件", "*.*")],
            initialdir=os.getcwd()
        )
        
        for file in files:
            if file not in self.video_input_files:
                self.video_input_files.append(file)
                # 更新全局状态
                self.global_state['video_input_files'] = self.video_input_files
                try:
                    # 获取视频信息
                    video_info = self.get_video_info(file)
                    # 构建显示文本
                    display_text = f"{os.path.basename(file)} [{video_info['resolution']} | {video_info['codec']} | {video_info['bitrate']}]"
                    self.video_listbox.insert(tk.END, display_text)
                except:
                    pass
    
    def add_video_folder_files(self):
        """添加视频文件夹"""
        folder = filedialog.askdirectory(title="选择包含视频文件的文件夹", initialdir=os.getcwd())
        if folder:
            # 遍历文件夹中的所有视频文件
            for root, dirs, files in os.walk(folder):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in [".mp4", ".ts", ".avi", ".mov", ".mkv"]:
                        file_path = os.path.join(root, file)
                        if file_path not in self.video_input_files:
                            self.video_input_files.append(file_path)
                            # 更新全局状态
                            self.global_state['video_input_files'] = self.video_input_files
                            try:
                                # 获取视频信息
                                video_info = self.get_video_info(file_path)
                                # 构建显示文本
                                display_text = f"{os.path.basename(file)} [{video_info['resolution']} | {video_info['codec']} | {video_info['bitrate']}]"
                                self.video_listbox.insert(tk.END, display_text)
                            except:
                                pass
    
    def remove_video_files(self):
        """移除选中的视频文件"""
        try:
            selected_indices = self.video_listbox.curselection()[::-1]
            for index in selected_indices:
                self.video_listbox.delete(index)
                del self.video_input_files[index]
            # 更新全局状态
            self.global_state['video_input_files'] = self.video_input_files
        except:
            pass
    
    def clear_video_files(self):
        """清空视频文件列表"""
        try:
            self.video_listbox.delete(0, tk.END)
        except:
            pass
        self.video_input_files.clear()
        # 更新全局状态
        self.global_state['video_input_files'] = self.video_input_files
    
    def update_file_listbox(self):
        """更新文件列表显示"""
        try:
            # 清空视频列表
            if hasattr(self, 'video_listbox'):
                self.video_listbox.delete(0, tk.END)
                # 重新添加剩余的文件
                for file_path in self.video_input_files:
                    try:
                        # 获取视频信息
                        video_info = self.get_video_info(file_path)
                        # 构建显示文本
                        display_text = f"{os.path.basename(file_path)} [{video_info['resolution']} | {video_info['codec']} | {video_info['bitrate']}]"
                        self.video_listbox.insert(tk.END, display_text)
                    except:
                        pass
            # 清空TS文件列表（向后兼容）
            if hasattr(self, 'input_listbox'):
                self.input_listbox.delete(0, tk.END)
                # 重新添加剩余的文件
                for file_path in self.video_input_files:
                    try:
                        # 获取视频信息
                        video_info = self.get_video_info(file_path)
                        # 构建显示文本
                        display_text = f"{os.path.basename(file_path)} [{video_info['resolution']} | {video_info['codec']} | {video_info['bitrate']}]"
                        self.input_listbox.insert(tk.END, display_text)
                    except:
                        pass
        except Exception as e:
            print(f"更新文件列表时出错: {e}")
    

    
    def show_video_context_menu(self, event):
        """显示视频文件的右键菜单"""
        # 获取右键点击的文件索引
        index = self.video_listbox.nearest(event.y)
        # 选择点击的文件
        self.video_listbox.selection_clear(0, tk.END)
        self.video_listbox.selection_set(index)
        # 保存当前选中的文件索引，供子菜单使用
        self.current_selected_file = self.video_input_files[index]
        # 重新创建右键菜单，确保子菜单能够获取到选中的文件
        self.video_context_menu = tk.Menu(self.parent, tearoff=0)
        self.video_context_menu.add_command(label="移除", command=self.remove_video_files)
        self.video_context_menu.add_separator()
        # 动态添加音频和字幕轨道选项
        self.video_context_menu.add_cascade(label="选择音频轨道", menu=self.create_audio_track_menu())
        self.video_context_menu.add_cascade(label="选择字幕轨道", menu=self.create_subtitle_track_menu())
        # 显示右键菜单
        self.video_context_menu.post(event.x_root, event.y_root)
    

    

    
    def create_audio_track_menu(self):
        """创建音频轨道选择子菜单"""
        # 创建子菜单
        audio_menu = tk.Menu(self.parent, tearoff=0)
        
        try:
            # 检查是否存在必要的属性
            if not hasattr(self, 'notebook'):
                audio_menu.add_command(label="功能未就绪", state=tk.DISABLED)
                return audio_menu
            
            # 确定当前活动页面
            current_tab = self.notebook.select()
            
            # 检查是否存在对应的listbox
            listbox = None
            files = None
            
            if hasattr(self, 'video_listbox') and current_tab == str(self.format_conversion_frame):
                # 格式转换页面
                listbox = self.video_listbox
                files = self.video_input_files
            elif hasattr(self, 'audio_listbox') and current_tab == str(self.audio_conversion_frame):
                # 音频转换页面
                listbox = self.audio_listbox
                files = self.audio_input_files
            else:
                audio_menu.add_command(label="列表未就绪", state=tk.DISABLED)
                return audio_menu
            
            # 获取选中的文件
            selected_indices = listbox.curselection()
            if not selected_indices:
                audio_menu.add_command(label="请先选择一个文件", state=tk.DISABLED)
                return audio_menu
            
            # 获取第一个选中的文件
            input_file = files[selected_indices[0]]
            
            # 获取文件的音频轨道信息
            audio_tracks = self.get_audio_tracks(input_file)
            if not audio_tracks:
                audio_menu.add_command(label="未找到音频轨道", state=tk.DISABLED)
                return audio_menu
            
            # 添加音频轨道选项
            for i, track in enumerate(audio_tracks):
                track_info = f"轨道 {i}: {track.get('language', '未知')} - {track.get('title', '无标题')}"
                audio_menu.add_command(label=track_info, command=lambda idx=i: self.set_audio_track(idx))
                
        except Exception as e:
            print(f"创建音频轨道菜单失败: {e}")
            audio_menu.add_command(label="获取音频轨道失败", state=tk.DISABLED)
        
        return audio_menu
    
    def create_subtitle_track_menu(self):
        """创建字幕轨道选择子菜单"""
        # 创建子菜单
        subtitle_menu = tk.Menu(self.parent, tearoff=0)
        
        try:
            # 检查是否存在必要的属性
            if not hasattr(self, 'notebook'):
                subtitle_menu.add_command(label="功能未就绪", state=tk.DISABLED)
                return subtitle_menu
            
            # 确定当前活动页面
            current_tab = self.notebook.select()
            
            # 检查是否存在对应的listbox
            listbox = None
            files = None
            
            if hasattr(self, 'video_listbox') and current_tab == str(self.format_conversion_frame):
                # 格式转换页面
                listbox = self.video_listbox
                files = self.video_input_files
            elif hasattr(self, 'audio_listbox') and current_tab == str(self.audio_conversion_frame):
                # 音频转换页面
                listbox = self.audio_listbox
                files = self.audio_input_files
            else:
                subtitle_menu.add_command(label="列表未就绪", state=tk.DISABLED)
                return subtitle_menu
            
            # 获取选中的文件
            selected_indices = listbox.curselection()
            if not selected_indices:
                subtitle_menu.add_command(label="请先选择一个文件", state=tk.DISABLED)
                return subtitle_menu
            
            # 获取第一个选中的文件
            input_file = files[selected_indices[0]]
            
            # 获取文件的字幕轨道信息
            subtitle_tracks = self.get_subtitle_tracks(input_file)
            if not subtitle_tracks:
                subtitle_menu.add_command(label="未找到字幕轨道", state=tk.DISABLED)
                return subtitle_menu
            
            # 添加字幕轨道选项
            for i, track in enumerate(subtitle_tracks):
                track_info = f"轨道 {i}: {track.get('language', '未知')} - {track.get('title', '无标题')}"
                subtitle_menu.add_command(label=track_info, command=lambda idx=i: self.set_subtitle_track(idx))
                
        except Exception as e:
            print(f"创建字幕轨道菜单失败: {e}")
            subtitle_menu.add_command(label="获取字幕轨道失败", state=tk.DISABLED)
        
        return subtitle_menu
    
    def set_audio_track(self, track_index):
        """设置音频轨道"""
        self.selected_audio_track = track_index
        filename = os.path.basename(self.current_selected_file) if hasattr(self, 'current_selected_file') else '未知文件'
        print(f"[{filename}] 已选择音频轨道: {track_index}")
    
    def set_subtitle_track(self, track_index):
        """设置字幕轨道"""
        self.selected_subtitle_track = track_index
        filename = os.path.basename(self.current_selected_file) if hasattr(self, 'current_selected_file') else '未知文件'
        print(f"[{filename}] 已选择字幕轨道: {track_index}")
    
    def get_audio_tracks(self, input_file):
        """获取视频文件中的音频轨道信息"""
        try:
            # 使用ffprobe获取视频文件信息
            cmd = [
                self.ffmpeg_path.replace('ffmpeg.exe', 'ffprobe.exe'),
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_streams',
                input_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            import json
            data = json.loads(result.stdout)
            
            # 提取音频轨道信息
            audio_tracks = []
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    track_info = {
                        'index': stream.get('index'),
                        'language': stream.get('tags', {}).get('language', ''),
                        'title': stream.get('tags', {}).get('title', ''),
                        'codec_name': stream.get('codec_name')
                    }
                    audio_tracks.append(track_info)
            
            return audio_tracks
        except Exception as e:
            print(f"获取音频轨道信息失败: {e}")
            return []
    
    def get_audio_track_bitrate(self, input_file, track_index):
        """获取特定音频轨道的比特率"""
        try:
            ffprobe_path = self.ffmpeg_path.replace('ffmpeg.exe', 'ffprobe.exe')
            if not os.path.exists(ffprobe_path):
                return 0
            
            cmd = [
                ffprobe_path,
                '-v', 'error',
                '-show_streams',
                '-select_streams', f'a:{track_index}',
                '-print_format', 'json',
                input_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            if result.returncode != 0:
                return 0
            
            import json
            data = json.loads(result.stdout)
            
            # 从音频流获取比特率
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    bitrate = stream.get('bit_rate')
                    if bitrate:
                        return int(bitrate) // 1000
                    # 如果没有bit_rate，尝试从format获取
                    format_data = stream.get('tags', {}).get('BPS')
                    if format_data:
                        return int(format_data) // 1000
            
            return 0
        except Exception as e:
            print(f"获取音频轨道比特率失败: {e}")
            return 0
    
    def add_subtitle_files(self):
        """添加字幕文件"""
        files = filedialog.askopenfilenames(
            title="选择字幕文件",
            filetypes=[("字幕文件", "*.ass;*.srt;*.ssa"), ("所有文件", "*.*")],
            initialdir=os.getcwd()
        )
        
        for file in files:
            if file not in self.subtitle_files:
                self.subtitle_files.append(file)
                # 更新全局状态
                self.global_state['subtitle_files'] = self.subtitle_files
                try:
                    self.subtitle_listbox.insert(tk.END, os.path.basename(file))
                except:
                    pass
    
    def update_global_state(self):
        """更新全局状态"""
        self.global_state['video_input_files'] = self.video_input_files
        self.global_state['subtitle_files'] = self.subtitle_files
        # 将中文选项转换为对应的英文值
        if hasattr(self, 'style_options') and self.subtitle_style_var.get() in self.style_options:
            self.global_state['subtitle_style'] = self.style_options[self.subtitle_style_var.get()]
        else:
            self.global_state['subtitle_style'] = 'ktv'  # 默认KTV式样
        self.global_state['is_converting'] = self.is_converting
    
    def browse_output(self):
        directory = filedialog.askdirectory(title="选择输出目录", initialdir=os.getcwd())
        if directory:
            self.output_path_var.set(directory)
    

    
    def start_format_conversion(self):
        """格式转换"""
        if not self.video_input_files:
            messagebox.showwarning("警告", "请添加至少一个视频文件！")
            return
        
        if self.is_processing:
            # 如果正在处理，停止处理
            self.stop_format_conversion()
            return
        
        # 更新全局状态
        self.update_global_state()
        self.is_converting = True
        self.is_processing = True
        self.global_state['is_converting'] = True
        self.global_state['status'] = "开始视频转换..."
        self.global_state['progress'] = 0
        
        try:
            self.format_conversion_button.config(text="停止处理", command=self.stop_format_conversion)
            self.add_video_button.config(state=tk.DISABLED)
            self.add_video_folder_button.config(state=tk.DISABLED)
            self.remove_video_button.config(state=tk.DISABLED)
            self.clear_video_button.config(state=tk.DISABLED)
            self.status_var.set("处理中 0%")
            self.progress_var.set(0)
        except:
            # 如果UI控件已被销毁，忽略错误
            pass
        
        # 启动转换线程，设置daemon=False，确保线程在UI销毁后仍能继续运行
        self.process_thread = threading.Thread(target=self.convert_format_conversion, daemon=False)
        self.process_thread.start()
    
    def stop_format_conversion(self):
        """停止格式转换"""
        # 设置停止标志
        self.is_converting = False
        self.is_processing = False
        self.global_state['is_converting'] = False
        self.global_state['status'] = "已停止"
        
        try:
            # 恢复按钮状态
            self.format_conversion_button.config(text="开始处理", command=self.start_format_conversion)
            self.add_video_button.config(state=tk.NORMAL)
            self.add_video_folder_button.config(state=tk.NORMAL)
            self.remove_video_button.config(state=tk.NORMAL)
            self.clear_video_button.config(state=tk.NORMAL)
            self.status_var.set("已停止")
        except:
            # 如果UI控件已被销毁，忽略错误
            pass
    

    
    def get_matching_subtitle(self, video_file):
        """为视频文件找到匹配的字幕文件"""
        video_name = os.path.basename(video_file)
        video_base = os.path.splitext(video_name)[0]
        
        # 优先匹配同名字幕文件
        for subtitle_file in self.subtitle_files:
            subtitle_name = os.path.basename(subtitle_file)
            subtitle_base = os.path.splitext(subtitle_name)[0]
            
            if video_base == subtitle_base:
                return subtitle_file
        
        # 如果没有同名字幕，返回第一个字幕文件
        if self.subtitle_files:
            return self.subtitle_files[0]
        
        return None
    
    def get_unique_filename(self, directory, filename):
        """获取唯一的文件名，避免重复"""
        base_name = os.path.splitext(filename)[0]
        ext = os.path.splitext(filename)[1]
        counter = 1
        unique_filename = filename
        
        while os.path.exists(os.path.join(directory, unique_filename)):
            unique_filename = f"{base_name}（{counter}）{ext}"
            counter += 1
        
        return unique_filename
    

    
    def convert_format_conversion(self):
        """格式转换"""
        total_files = len(self.video_input_files)
        success_count = 0
        failed_count = 0
        failed_files = []
        
        for i, input_file in enumerate(self.video_input_files):
            # 检查是否需要停止处理
            if not self.is_converting:
                break
            
            # 记录原始文件名
            original_file = input_file
            # 失败次数计数
            fail_count = 0
            # 是否重命名过文件
            renamed = False
            # 重命名后的临时文件
            temp_file = None
                
            # 更新全局状态
            current_progress = (i / total_files) * 100
            self.global_state['progress'] = current_progress
            self.global_state['status'] = f"正在处理 {i+1}/{total_files} - {os.path.basename(input_file)} 成功: {success_count} 失败: {failed_count}"
            # 更新UI
            try:
                self.status_var.set(f"处理中 {current_progress:.1f}% - 正在处理 {i+1}/{total_files} - {os.path.basename(input_file)}")
                self.progress_var.set(current_progress)
            except:
                pass
            
            while True:
                try:
                    # 生成输出路径：输入文件所在目录的"已转换"子目录
                    input_dir = os.path.dirname(input_file)
                    output_dir = os.path.join(input_dir, "已转换")
                    # 确保输出目录存在
                    os.makedirs(output_dir, exist_ok=True)
                    
                    # 生成输出文件名
                    # 获取选择的字幕效果
                    subtitle_style = self.style_options.get(self.subtitle_style_var.get(), "default")
                    # 映射字幕效果到中文名称
                    style_name_map = {
                        "default": "默认效果",
                        "ktv": "KTV效果",
                        "prompter": "提词器效果"
                    }
                    style_name = style_name_map.get(subtitle_style, "默认效果")
                    # 生成输出文件名，使用原始文件的名称
                    original_basename = os.path.splitext(os.path.basename(original_file))[0]
                    
                    # 安全地清理文件名以用于输出，移除所有(ASS)标签
                    clean_basename = original_basename.replace(" (ASS)", "").replace("(ASS)", "")
                    
                    # 获取选择的分辨率
                    resolution = self.resolution_options.get(self.resolution_var.get(), "original")
                    
                    # 检查是否禁用字幕 - 如果用户手动选择了字幕轨道，则不禁用
                    is_subtitle_disabled = not (hasattr(self, 'selected_subtitle_track') and self.selected_subtitle_track is not None) and \
                                          (subtitle_style == "none" or (hasattr(self, 'enable_subtitle_var') and not self.enable_subtitle_var.get()))
                    
                    # 根据是否启用字幕和分辨率决定输出文件名
                    if is_subtitle_disabled:
                        # 未启用字幕，不添加字幕效果名称
                        if resolution == "original":
                            # 原始分辨率，不添加后缀
                            output_filename = clean_basename + ".mp4"
                        else:
                            # 非原始分辨率，添加分辨率后缀
                            output_filename = clean_basename + f" {resolution}P.mp4"
                    else:
                        # 启用字幕，添加字幕效果名称
                        if resolution == "original":
                            # 原始分辨率，不添加分辨率后缀
                            output_filename = clean_basename + f" {style_name}.mp4"
                        else:
                            # 非原始分辨率，添加分辨率后缀
                            output_filename = clean_basename + f" {style_name} {resolution}P.mp4"
                    
                    # 获取唯一文件名
                    output_filename = self.get_unique_filename(output_dir, output_filename)
                    output_file = os.path.join(output_dir, output_filename)
                    
                    # 构建FFmpeg命令，使用视频内嵌的字幕
                    # 根据选择的字幕效果选择对应的字幕轨道
                    if hasattr(self, 'style_options') and self.subtitle_style_var.get() in self.style_options:
                        subtitle_style = self.style_options[self.subtitle_style_var.get()]
                    else:
                        subtitle_style = 'ktv'  # 默认KTV效果
                    
                    # 初始化变量
                    selected_track = None
                    subtitle_tracks = []
                    filename = os.path.basename(input_file)
                    
                    # 检查是否禁用字幕 - 优先检查用户是否手动选择了字幕轨道
                    if hasattr(self, 'selected_subtitle_track') and self.selected_subtitle_track is not None:
                        # 构建硬压滤镜路径 (关键：处理 Windows 路径转义)
                        # FFmpeg subtitles 滤镜路径要求：反斜杠转斜杠，冒号要转义
                        # 示例: C:/Users/Admin/Desktop/STAYC - BEBE.mkv -> C\:/Users/Admin/Desktop/STAYC - BEBE.mkv
                        safe_input_path = input_file
                        # 进行路径转义
                        safe_input_path = safe_input_path.replace("\\", "/").replace(":", "\\:")
                        
                        # 获取视频文件中的字幕轨道信息
                        subtitle_tracks = self.get_subtitle_tracks(input_file)
                    elif subtitle_style == 'none':
                        print(f"[{filename}] 禁用字幕")
                        # 不添加字幕滤镜
                        video_filter = ""
                    else:
                        # 映射字幕效果到轨道索引
                        track_map = {
                            'default': 2,
                            'ktv': 3,
                            'prompter': 4
                        }
                        
                        # 尝试选择的字幕轨道
                        subtitle_index = track_map.get(subtitle_style, 3)  # 默认KTV轨道
                        print(f"[{filename}] 选择字幕式样: {subtitle_style}, 对应轨道: {subtitle_index}")
                        
                        # 构建硬压滤镜路径 (关键：处理 Windows 路径转义)
                        # FFmpeg subtitles 滤镜路径要求：反斜杠转斜杠，冒号要转义
                        # 示例: C:/Users/Admin/Desktop/STAYC - BEBE.mkv -> C\:/Users/Admin/Desktop/STAYC - BEBE.mkv
                        safe_input_path = input_file
                        # 进行路径转义
                        safe_input_path = safe_input_path.replace("\\", "/").replace(":", "\\:")
                        
                        # 获取视频文件中的字幕轨道信息
                        subtitle_tracks = self.get_subtitle_tracks(input_file)
                        print(f"[{filename}] 找到字幕轨道: {subtitle_tracks}")
                        
                        # 根据字幕式样和轨道title属性选择合适的字幕轨道
                        for track in subtitle_tracks:
                            title = track.get('title', '').lower()
                            if subtitle_style == 'ktv' and 'ktv' in title:
                                selected_track = track
                                break
                            elif subtitle_style == 'prompter' and '提词器' in title:
                                selected_track = track
                                break
                            elif subtitle_style == 'default' and not title:
                                selected_track = track
                                break
                    
                    # 如果用户手动选择了字幕轨道，使用用户选择的
                    if hasattr(self, 'selected_subtitle_track') and self.selected_subtitle_track is not None and subtitle_tracks:
                        # 确保用户选择的轨道索引在范围内
                        if self.selected_subtitle_track < len(subtitle_tracks):
                            selected_track = subtitle_tracks[self.selected_subtitle_track]
                        else:
                            # 如果索引超出范围，使用第一个字幕轨道
                            selected_track = subtitle_tracks[0]
                            print(f"[{filename}] 用户选择的字幕轨道索引超出范围，使用第一个字幕轨道")
                    # 如果没有找到匹配的轨道，使用第一个字幕轨道
                    elif not selected_track and subtitle_tracks:
                        selected_track = subtitle_tracks[0]
                        print(f"[{filename}] 未找到匹配的字幕轨道，使用第一个字幕轨道")
                    
                    # 检查是否为TS文件（使用TS转MP4的无损转换）
                    input_ext = os.path.splitext(input_file)[1].lower()
                    if input_ext == '.ts':
                        print("检测到TS文件，使用无损转换")
                        
                        # 获取视频总时长
                        total_duration_ms = self.get_video_duration(input_file)
                        total_duration_sec = total_duration_ms / 1000000
                        minutes = int(total_duration_sec // 60)
                        seconds = total_duration_sec % 60
                        print(f"视频总时长: {minutes}分{seconds:.2f}秒")
                        
                        cmd = [
                            self.ffmpeg_path,
                            "-i", input_file,
                            "-c:v", "copy",
                            "-c:a", "copy",
                            "-y",
                            output_file
                        ]
                        print(f"执行命令: {' '.join(cmd)}")
                        
                        # 添加进度输出参数
                        cmd_with_progress = cmd.copy()
                        cmd_with_progress.insert(1, '-progress')
                        cmd_with_progress.insert(2, 'pipe:1')
                        
                        try:
                            # 使用Popen以便实时读取输出
                            process = subprocess.Popen(
                                cmd_with_progress,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                text=True,
                                encoding='utf-8',
                                errors='ignore'
                            )
                            
                            # 实时读取输出并更新进度
                            for line in iter(process.stdout.readline, ''):
                                # 检查是否需要停止处理
                                if not self.is_converting:
                                    process.terminate()
                                    break
                                
                                # 解析进度信息
                                if 'out_time_ms' in line:
                                    try:
                                        # 提取时间信息
                                        time_ms = int(line.split('=')[1].strip())
                                        # 计算进度（使用实际的视频总时长）
                                        progress = min((time_ms / total_duration_ms) * 100, 100)
                                        # 更新全局状态
                                        self.global_state['progress'] = progress
                                        # 更新UI
                                        try:
                                            self.progress_var.set(progress)
                                            self.status_var.set(f"处理中 {progress:.1f}% - 正在处理 {i+1}/{total_files} - {os.path.basename(input_file)}")
                                        except:
                                            pass
                                    except:
                                        pass
                            
                            # 等待进程结束
                            process.wait()
                            
                            if process.returncode == 0:
                                print(f"TS文件转换成功!")
                                success = True
                            else:
                                raise Exception(f"TS文件转换失败，返回码: {process.returncode}")
                        except Exception as e:
                            print(f"TS文件转换失败: {e}")
                            success = False
                    # 对于非TS文件，即使禁用字幕也进行转码
                    else:
                        # 初始化success变量
                        success = False
                        
                        # 检查是否启用字幕 - 优先使用用户手动选择的字幕轨道
                        is_subtitle_enabled = (hasattr(self, 'selected_subtitle_track') and self.selected_subtitle_track is not None) or \
                                             (subtitle_style != 'none' and (not hasattr(self, 'enable_subtitle_var') or self.enable_subtitle_var.get()))
                        
                        # 获取视频原始分辨率
                        width, height = self.get_video_resolution(input_file)
                        print(f"视频原始分辨率: {width}x{height}")
                        
                        # 获取视频详细信息
                        video_info = self.get_video_info(input_file)
                        print(f"原始视频编码: {video_info.get('codec', 'Unknown')}")
                        print(f"原始视频比特率: {video_info.get('bitrate', 'Unknown')}")
                        print(f"原始视频帧率: {video_info.get('fps', 'Unknown')} FPS")
                        
                        # 获取视频总时长
                        total_duration_ms = self.get_video_duration(input_file)
                        total_duration_sec = total_duration_ms / 1000000
                        minutes = int(total_duration_sec // 60)
                        seconds = total_duration_sec % 60
                        print(f"视频总时长: {minutes}分{seconds:.2f}秒")
                        
                        # 根据选择的分辨率预设和视频原始分辨率决定编码和画质
                        resolution = self.resolution_options.get(self.resolution_var.get(), "original")
                        print(f"选择的分辨率预设: {resolution}")
                        
                        # 构建视频滤镜
                        video_filter = ""
                        
                        # 如果启用字幕，添加字幕滤镜
                        if is_subtitle_enabled:
                            # 优先使用用户选择的字幕轨道
                            if hasattr(self, 'selected_subtitle_track') and self.selected_subtitle_track is not None:
                                # 使用用户选择的字幕轨道
                                si_index = self.selected_subtitle_track
                            elif selected_track:
                                # 计算si参数（从0开始的字幕轨道索引）
                                # 找到该轨道在所有字幕轨道中的索引
                                si_index = subtitle_tracks.index(selected_track)
                                print(f"[{filename}] 选择字幕式样: {subtitle_style}, 对应轨道: {selected_track['index']}, si索引: {si_index}")
                            else:
                                # 没有找到字幕轨道
                                print(f"[{filename}] 未找到字幕轨道，跳过文件: {input_file}")
                                failed_files.append(input_file)
                                break
                            
                            # 确保路径中的单引号被正确转义
                            safe_input_path = safe_input_path.replace("'", "\\'")
                            video_filter = f"subtitles='{safe_input_path}':si={si_index}"
                        
                        # 添加分辨率缩放滤镜（如果不是原始分辨率）
                        if resolution != "original":
                            target_height = int(resolution)
                            # 保持宽高比
                            if width and height:
                                aspect_ratio = width / height
                                target_width = int(target_height * aspect_ratio)
                                # 确保宽度是偶数
                                target_width = target_width + 1 if target_width % 2 != 0 else target_width
                                if video_filter:
                                    video_filter += f",scale={target_width}:{target_height}"
                                else:
                                    video_filter = f"scale={target_width}:{target_height}"
                            print(f"缩放分辨率: {target_width}x{target_height}")
                        
                        # 使用主界面上的编码设置
                        codec = self.codec_var.get()
                        preset = self.preset_var.get()
                        bitrate = self.bitrate_var.get()
                        max_bitrate = self.max_bitrate_var.get()
                        crf = self.crf_var.get()
                        bufsize = max_bitrate  # 缓冲区大小设置为最大比特率
                        
                        # 初始化编码配置文件
                        if height > 1080:
                            codec_profile = "main10"
                        else:
                            codec_profile = "main"
                        
                        # 检查是否是原始分辨率
                        if resolution == "original":
                            # 解析原始比特率
                            original_bitrate = video_info.get('bitrate', '8M')
                            print(f"解析原始比特率: {original_bitrate}")
                            
                            try:
                                if 'M' in original_bitrate:
                                    bitrate_value = float(original_bitrate.replace('M', ''))
                                elif 'K' in original_bitrate:
                                    bitrate_value = float(original_bitrate.replace('K', '')) / 1000
                                else:
                                    bitrate_value = 8.0
                            except:
                                bitrate_value = 8.0
                            
                            print(f"解析后的比特率值: {bitrate_value}M")
                            
                            # 使用原始比特率
                            print(f"使用原始比特率: {bitrate_value}M")
                            
                            # 根据视频高度设置最高比特率限制
                            if height > 4320:  # 8K以上
                                max_bitrate_limit = 60.0
                                print("识别为8K以上视频")
                            elif height >= 2160:  # 4K
                                max_bitrate_limit = 30.0  # 提高4K视频的最大比特率限制
                                print("识别为4K视频")
                            elif height > 1080:  # 1440P
                                max_bitrate_limit = 16.0
                                print("识别为1440P视频")
                            elif height > 720:  # 1080P
                                max_bitrate_limit = 12.0
                                print("识别为1080P视频")
                            elif height > 480:  # 720P
                                max_bitrate_limit = 8.0
                                print("识别为720P视频")
                            else:  # 480P以下
                                max_bitrate_limit = 5.0
                                print("识别为480P以下视频")
                            
                            print(f"最大比特率限制: {max_bitrate_limit}M")
                            
                            # 限制目标比特率不超过最高限制
                            bitrate_value = min(bitrate_value, max_bitrate_limit)
                            bitrate = f"{int(bitrate_value)}M"
                            print(f"最终目标比特率: {bitrate}")
                            
                            # 设置最大比特率为目标比特率的1.5倍，不超过最高限制的1.5倍
                            max_bitrate_value = min(bitrate_value * 1.5, max_bitrate_limit * 1.5)
                            max_bitrate = f"{int(max_bitrate_value)}M"
                            bufsize = max_bitrate
                            print(f"最终最大比特率: {max_bitrate}")
                            
                            # 根据视频高度选择编码格式和CRF值
                            if height > 1080:
                                # 1080P以上使用H.265编码
                                codec = "hevc_nvenc"
                                preset = "slow"
                                if crf == "自动":
                                    crf = "15"
                                # 1080P以上使用main10编码配置
                                codec_profile = "main10"
                                print(f"使用编码配置文件: {codec_profile}")
                            else:
                                # 1080P以下使用H.264编码
                                codec = "h264_nvenc"
                                preset = "medium"
                                if crf == "自动":
                                    crf = "18"
                                codec_profile = "main"
                                print(f"使用编码配置文件: {codec_profile}")
                        
                        print(f"使用编码: {codec}, 预设: {preset}, CRF: {crf}, 比特率: {bitrate}")
                        
                        # 构建FFmpeg命令
                        # 获取用户选择的音频轨道，默认为0
                        audio_track_index = getattr(self, 'selected_audio_track', 0)
                        
                        cmd = [
                            self.ffmpeg_path,
                            "-hwaccel", "auto",  # 自动选择硬件加速
                            "-y",
                            "-i", input_file,
                            "-map", "0:v:0",  # 明确指定使用第一个视频流
                            "-map", f"0:a:{audio_track_index}",  # 使用用户选择的音频流
                        ]
                        
                        # 添加视频滤镜（如果有）
                        if video_filter:
                            cmd.extend(["-vf", video_filter])
                        
                        # 添加编码参数
                        cmd.extend([
                            "-c:v", codec,
                            "-preset", preset,
                            "-crf", crf,
                            "-profile:v", codec_profile,  # 设置编码配置文件
                            "-rc:v", "vbr",  # 使用可变比特率
                            "-maxrate:v", max_bitrate,  # 设置最大比特率
                            "-b:v", bitrate,  # 设置目标比特率
                            "-bufsize:v", bufsize,  # 设置缓冲区大小
                        ])
                        
                        # 处理帧率设置
                        framerate = ""
                        fps = self.fps_var.get()
                        if fps != "默认":
                            # 获取原始视频帧率
                            video_info = self.get_video_info(input_file)
                            original_fps = video_info.get('fps', 'Unknown')
                            
                            # 检查用户选择的帧率是否小于原始帧率
                            try:
                                if original_fps != 'Unknown':
                                    original_fps_value = float(original_fps)
                                    selected_fps_value = float(fps)
                                    
                                    if selected_fps_value < original_fps_value:
                                        # 只在帧率小于原始帧率时应用
                                        cmd.extend(["-r", fps])
                                        framerate = fps
                                else:
                                    # 如果无法获取原始帧率，使用用户选择的帧率
                                    cmd.extend(["-r", fps])
                                    framerate = fps
                            except:
                                # 解析失败时，使用用户选择的帧率
                                cmd.extend(["-r", fps])
                                framerate = fps
                        
                        # 音频转码为aac，使用原始音频码率
                        audio_bitrate = video_info.get('audio_bitrate', '192k')
                        if audio_bitrate == 'Unknown':
                            audio_bitrate = '192k'
                        print(f"原始音频比特率: {audio_bitrate}")
                        
                        cmd.extend([
                            "-c:a", "aac",
                            "-b:a", audio_bitrate,
                            "-y",
                            output_file
                        ])
                        
                        # 初始化success变量
                        success = False
                        # 执行转换，使用utf-8编码避免编码错误
                        print(f"执行命令: {' '.join(cmd)}")
                        # 添加进度输出参数
                        cmd_with_progress = cmd.copy()
                        cmd_with_progress.insert(1, '-progress')
                        cmd_with_progress.insert(2, 'pipe:1')
                        
                        try:
                            # 使用Popen以便实时读取输出
                            process = subprocess.Popen(
                                cmd_with_progress,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                text=True,
                                encoding='utf-8',
                                errors='ignore'
                            )
                            
                            # 实时读取输出并更新进度
                            for line in iter(process.stdout.readline, ''):
                                # 检查是否需要停止处理
                                if not self.is_converting:
                                    process.terminate()
                                    break
                                
                                # 解析进度信息
                                if 'out_time_ms' in line:
                                    try:
                                        # 提取时间信息
                                        time_ms = int(line.split('=')[1].strip())
                                        # 计算进度（使用实际的视频总时长）
                                        progress = min((time_ms / total_duration_ms) * 100, 100)
                                        # 更新全局状态
                                        self.global_state['progress'] = progress
                                        # 更新UI
                                        try:
                                            self.progress_var.set(progress)
                                            self.status_var.set(f"处理中 {progress:.1f}% - 正在处理 {i+1}/{total_files} - {os.path.basename(input_file)}")
                                        except:
                                            pass
                                    except:
                                        pass
                                
                            # 等待进程结束
                            process.wait()
                            
                            if process.returncode == 0:
                                if is_subtitle_enabled:
                                    print(f"使用字幕轨道 {si_index} 转换成功!")
                                else:
                                    print(f"转换成功!")
                                success = True
                            else:
                                raise Exception(f"转换失败，返回码: {process.returncode}")
                        except Exception as e:
                            if is_subtitle_enabled:
                                print(f"使用字幕轨道 {si_index} 转换失败: {e}")
                            else:
                                print(f"转换失败: {e}")
                        
                        # 失败后尝试使用CPU编码
                        if not success:
                            print("GPU编码失败，尝试使用CPU编码")
                            # 构建使用CPU编码的命令
                            # 获取用户选择的音频轨道，默认为0
                            audio_track_index = getattr(self, 'selected_audio_track', 0)
                            
                            cmd = [
                                self.ffmpeg_path,
                                "-hwaccel", "auto",  # 自动选择硬件加速
                                "-y",
                                "-i", input_file,
                                "-map", "0:v:0",  # 明确指定使用第一个视频流
                                "-map", f"0:a:{audio_track_index}",  # 使用用户选择的音频流
                            ]
                            
                            # 添加视频滤镜（如果有）
                            if video_filter:
                                cmd.extend(["-vf", video_filter])
                            
                            # 使用CPU编码
                            cmd.extend([
                                "-c:v", "libx264",  # CPU编码
                                "-preset", preset,
                                "-crf", crf,
                                "-rc:v", "vbr",
                                "-maxrate:v", max_bitrate,
                                "-b:v", bitrate,
                                "-bufsize:v", max_bitrate,
                            ])
                            
                            # 添加帧率设置（如果用户选择了非默认帧率）
                            if framerate:
                                cmd.extend(["-r", framerate])
                            
                            # 音频转码为aac，使用原始音频码率
                            audio_bitrate = video_info.get('audio_bitrate', '192k')
                            if audio_bitrate == 'Unknown':
                                audio_bitrate = '192k'
                            
                            cmd.extend([
                                "-c:a", "aac",
                                "-b:a", audio_bitrate,
                                "-y",
                                output_file
                            ])
                            
                            print(f"执行CPU编码命令: {' '.join(cmd)}")
                            # 添加进度输出参数
                            cmd_with_progress = cmd.copy()
                            cmd_with_progress.insert(1, '-progress')
                            cmd_with_progress.insert(2, 'pipe:1')
                            
                            try:
                                # 使用Popen以便实时读取输出
                                process = subprocess.Popen(
                                    cmd_with_progress,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    text=True,
                                    encoding='utf-8',
                                    errors='ignore'
                                )
                                
                                # 实时读取输出并更新进度
                                for line in iter(process.stdout.readline, ''):
                                    # 检查是否需要停止处理
                                    if not self.is_converting:
                                        process.terminate()
                                        break
                                    
                                    # 解析进度信息
                                    if 'out_time_ms' in line:
                                        try:
                                            # 提取时间信息
                                            time_ms = int(line.split('=')[1].strip())
                                            # 计算进度（使用实际的视频总时长）
                                            progress = min((time_ms / total_duration_ms) * 100, 100)
                                            # 更新全局状态
                                            self.global_state['progress'] = progress
                                            # 更新UI
                                            try:
                                                self.progress_var.set(progress)
                                                self.status_var.set(f"处理中 {progress:.1f}% - 正在处理 {i+1}/{total_files} - {os.path.basename(input_file)}")
                                            except:
                                                pass
                                        except:
                                            pass
                                    
                                # 等待进程结束
                                process.wait()
                                
                                if process.returncode == 0:
                                    print("使用CPU编码转换成功!")
                                    success = True
                                else:
                                    raise Exception(f"CPU编码失败，返回码: {process.returncode}")
                            except Exception as e:
                                print(f"使用CPU编码转换失败: {e}")
                                # 如果CPU编码也失败，清理已生成的部分文件
                                if os.path.exists(output_file):
                                    try:
                                        os.remove(output_file)
                                        print(f"已清理失败文件: {output_file}")
                                    except:
                                        pass
                                # 如果CPU编码也失败，直接跳过
                                print("CPU编码也失败，跳过此文件")
                                raise

                        

                    if success:
                        print(f"格式转换成功: {os.path.basename(input_file)} -> {output_filename}")
                        success_count += 1
                        break
                    else:
                        raise Exception("转换失败")
                except subprocess.CalledProcessError as e:
                    # 转换失败，记录失败信息并继续下一个文件
                    error_msg = f"格式转换失败: {os.path.basename(input_file)} - {e.stderr if e.stderr else str(e)}"
                    print(error_msg)
                    fail_count += 1
                    
                    # 如果失败两次且文件包含特殊字符，尝试重命名文件
                    if fail_count >= 2 and ("'" in input_file or "\"" in input_file):
                        print("文件包含特殊字符，尝试重命名文件后重试")
                        try:
                            # 生成临时文件名（移除特殊字符）
                            import re
                            temp_basename = re.sub(r"[\\'\"<>|:*?]", "", os.path.basename(original_file))
                            temp_dir = os.path.dirname(original_file)
                            temp_file = os.path.join(temp_dir, temp_basename)
                            
                            # 重命名文件
                            os.rename(original_file, temp_file)
                            renamed = True
                            print(f"文件已重命名为: {temp_basename}")
                            
                            # 更新input_file为临时文件
                            input_file = temp_file
                            # 重置失败计数
                            fail_count = 0
                            # 继续循环，使用重命名后的文件重试
                            continue
                        except Exception as rename_error:
                            print(f"重命名文件失败: {rename_error}")
                            # 重命名失败，直接记录失败信息
                            failed_count += 1
                            failed_files.append(f"{os.path.basename(original_file)}: {error_msg}")
                            break
                    elif fail_count < 2:
                        # 失败次数不足，继续循环尝试其他编码方式
                        continue
                    else:
                        # 失败次数足够但文件不包含特殊字符，直接记录失败信息
                        failed_count += 1
                        failed_files.append(f"{os.path.basename(original_file)}: {error_msg}")
                        break
                except Exception as e:
                    # 其他错误，记录并继续
                    error_msg = f"格式转换失败: {os.path.basename(input_file)} - {str(e)}"
                    print(error_msg)
                    fail_count += 1
                    
                    # 如果失败两次且文件包含特殊字符，尝试重命名文件
                    if fail_count >= 2 and ("'" in input_file or "\"" in input_file):
                        print("文件包含特殊字符，尝试重命名文件后重试")
                        try:
                            # 生成临时文件名（移除特殊字符）
                            import re
                            temp_basename = re.sub(r"[\\'\"<>|:*?]", "", os.path.basename(original_file))
                            temp_dir = os.path.dirname(original_file)
                            temp_file = os.path.join(temp_dir, temp_basename)
                            
                            # 重命名文件
                            os.rename(original_file, temp_file)
                            renamed = True
                            print(f"文件已重命名为: {temp_basename}")
                            
                            # 更新input_file为临时文件
                            input_file = temp_file
                            # 重置失败计数
                            fail_count = 0
                            # 继续循环，使用重命名后的文件重试
                            continue
                        except Exception as rename_error:
                            print(f"重命名文件失败: {rename_error}")
                            # 重命名失败，直接记录失败信息
                            failed_count += 1
                            failed_files.append(f"{os.path.basename(original_file)}: {error_msg}")
                            break
                    elif fail_count < 2:
                        # 失败次数不足，继续循环尝试其他编码方式
                        continue
                    else:
                        # 失败次数足够但文件不包含特殊字符，直接记录失败信息
                        failed_count += 1
                        failed_files.append(f"{os.path.basename(original_file)}: {error_msg}")
                        break
            
            # 如果重命名过文件，改回原名称
            if renamed and temp_file and os.path.exists(temp_file):
                try:
                    os.rename(temp_file, original_file)
                    print(f"文件已改回原名称: {os.path.basename(original_file)}")
                except Exception as rename_back_error:
                    print(f"改回原名称失败: {rename_back_error}")
        
        # 转换完成
        self.is_converting = False
        self.is_processing = False
        # 更新全局状态
        self.global_state['is_converting'] = False
        self.global_state['progress'] = 100
        self.global_state['status'] = f"格式转换完成！成功：{success_count} 个文件 失败：{failed_count} 个文件"
        self.global_state['success_count'] = success_count
        self.global_state['failed_count'] = failed_count
        self.global_state['failed_files'] = failed_files
        
        # 检查是否需要移除已成功文件
        try:
            if self.remove_success_var.get() and success_count > 0:
                # 收集失败文件的文件名（从错误信息中提取）
                failed_file_names = []
                for fail_info in failed_files:
                    # 提取文件名部分（冒号前的内容）
                    if ': ' in fail_info:
                        filename = fail_info.split(': ')[0]
                        failed_file_names.append(filename)
                    else:
                        # 对于直接添加的文件路径
                        failed_file_names.append(os.path.basename(fail_info))
                # 过滤掉已成功的文件，只保留失败的文件
                original_files = self.video_input_files.copy()
                self.video_input_files = [file for file in self.video_input_files if os.path.basename(file) in failed_file_names]
                # 更新全局状态
                self.global_state['video_input_files'] = self.video_input_files
                # 刷新文件列表显示
                self.update_file_listbox()
                print(f"已移除 {success_count} 个成功文件，保留 {len(self.video_input_files)} 个失败文件")
        except Exception as e:
            print(f"移除已成功文件时出错: {e}")
        
        # 尝试重置UI，如果UI已销毁，忽略错误
        try:
            self.reset_format_conversion_ui()
            self.status_var.set(f"处理完成 100% - 成功：{success_count} 个文件 失败：{failed_count} 个文件")
            self.progress_var.set(100)
            # 显示转换结果
            result_message = f"格式转换完成！\n成功：{success_count} 个文件\n失败：{failed_count} 个文件"
            if failed_files:
                result_message += "\n\n失败文件：\n" + "\n".join(failed_files)
            print(result_message)
        except:
            pass
    

    
    def reset_format_conversion_ui(self):
        """重置格式转换页面UI"""
        try:
            self.format_conversion_button.config(state=tk.NORMAL, text="开始处理", command=self.start_format_conversion)
            self.add_video_button.config(state=tk.NORMAL)
            self.add_video_folder_button.config(state=tk.NORMAL)
            self.remove_video_button.config(state=tk.NORMAL)
            self.clear_video_button.config(state=tk.NORMAL)
        except:
            # 如果UI控件已被销毁，忽略错误
            pass
    
    def get_video_duration(self, input_file):
        """获取视频文件的总时长（毫秒）"""
        try:
            # 使用ffprobe获取视频时长
            ffprobe_path = self.ffmpeg_path.replace('ffmpeg.exe', 'ffprobe.exe')
            
            # 首先检查ffprobe是否存在
            if not os.path.exists(ffprobe_path):
                print(f"ffprobe不存在: {ffprobe_path}")
                return 60 * 1000000  # 默认60秒
            
            # 构建命令
            cmd = [
                ffprobe_path,
                '-v', 'error',
                '-show_format',
                '-print_format', 'json',
                input_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            
            # 检查命令是否执行成功
            if result.returncode != 0:
                print(f"ffprobe命令执行失败: {result.stderr}")
                return 60 * 1000000  # 默认60秒
            
            import json
            data = json.loads(result.stdout)
            
            # 提取时长信息
            duration = data.get('format', {}).get('duration')
            if duration:
                try:
                    # 转换为毫秒
                    duration_ms = float(duration) * 1000000
                    return int(duration_ms)
                except:
                    pass
            
            return 60 * 1000000  # 默认60秒
        except Exception as e:
            print(f"获取视频时长失败: {e}")
            return 60 * 1000000  # 默认60秒

if __name__ == "__main__":
    app = TS2MP4Converter()