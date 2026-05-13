import os
import sys
import subprocess

# 自动安装缺失的依赖
try:
    import mutagen
except ImportError:
    print("mutagen 未安装，正在安装...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mutagen", "--no-cache-dir"])
    import mutagen

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
except ImportError:
    print("tkinterdnd2 未安装，正在安装...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tkinterdnd2", "--no-cache-dir"])
    from tkinterdnd2 import TkinterDnD, DND_FILES

import tkinter as tk
import threading
from tkinter import ttk, messagebox, filedialog
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError
from mutagen.mp3 import MP3

# 支持的音频文件扩展名
audio_extensions = ['.mp3', '.wav', '.flac', '.ogg', '.m4a']

class AudioRenamerApp:
    # 类变量，用于存储全局状态
    global_state = {
        'files_to_process': [],
        'is_renaming': False,
        'log_messages': [],
        'success_count': 0,
        'error_count': 0,
        'skipped_count': 0,
        'failed_files': []
    }
    
    def __init__(self, parent=None, font_config=None):
        # 判断是否独立运行
        self.is_standalone = parent is None
        
        if self.is_standalone:
            # 独立运行，创建自己的根窗口（使用TkinterDnD以支持拖放）
            self.parent = TkinterDnD.Tk()
            self.parent.title("音频文件重命名工具")
            self.parent.geometry("600x600")
            self.parent.resizable(True, True)
        else:
            # 内嵌运行，使用父窗口
            self.parent = parent
        
        # 获取字体配置
        self.font_config = font_config or {}
        self.font_name = self.font_config.get("ui_font", "微软雅黑")
        self.font_size = int(self.font_config.get("ui_font_size", 16))
        self.font_weight = "bold" if self.font_config.get("ui_bold", False) else "normal"
        
        # 从全局状态恢复
        self.files_to_process = self.global_state['files_to_process']
        self.is_renaming = self.global_state['is_renaming']
        
        # 创建主框架
        self.main_frame = ttk.Frame(parent, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建标题
        title_font_size = int(self.font_size * 1.2)
        self.title_label = ttk.Label(self.main_frame, text="音频文件重命名工具", font=(self.font_name, title_font_size, "bold"))
        self.title_label.pack(pady=10)
        
        # 创建说明文本
        info_font_size = int(self.font_size * 0.8)
        self.info_label = ttk.Label(self.main_frame, text="将音频文件拖放到下方区域，或点击按钮选择文件/文件夹", font=(self.font_name, info_font_size, self.font_weight))
        self.info_label.pack(pady=10)
        
        # 创建文件列表区域
        self.file_list_frame = ttk.LabelFrame(self.main_frame, text="文件列表", padding="10")
        self.file_list_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 创建排序按钮框架
        self.sort_frame = ttk.Frame(self.file_list_frame)
        self.sort_frame.pack(fill=tk.X, pady=5)
        
        # 添加排序按钮
        self.sort_by_name_btn = ttk.Button(self.sort_frame, text="按文件名排序", command=self.sort_files_by_name)
        self.sort_by_name_btn.pack(side=tk.LEFT, padx=5)
        
        self.sort_by_artist_btn = ttk.Button(self.sort_frame, text="按歌手排序", command=self.sort_files_by_artist)
        self.sort_by_artist_btn.pack(side=tk.LEFT, padx=5)
        
        self.sort_by_title_btn = ttk.Button(self.sort_frame, text="按歌曲排序", command=self.sort_files_by_title)
        self.sort_by_title_btn.pack(side=tk.LEFT, padx=5)
        
        self.sort_by_album_art_btn = ttk.Button(self.sort_frame, text="按专辑图分辨率排序", command=self.sort_files_by_album_art)
        self.sort_by_album_art_btn.pack(side=tk.LEFT, padx=5)
        
        # 创建文件列表
        listbox_font_size = int(self.font_size * 0.75)
        self.file_list = tk.Listbox(self.file_list_frame, selectmode=tk.EXTENDED, font=(self.font_name, listbox_font_size, self.font_weight))
        self.file_list.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        # 滚动条
        self.file_list_scrollbar = ttk.Scrollbar(self.file_list_frame, command=self.file_list.yview)
        self.file_list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_list.config(yscrollcommand=self.file_list_scrollbar.set)
        
        # 绑定鼠标事件
        self.file_list_frame.bind("<Enter>", self.on_enter)
        self.file_list_frame.bind("<Leave>", self.on_leave)
        
        # 添加文件拖拽支持
        self.file_list_frame.drop_target_register(DND_FILES)
        self.file_list_frame.dnd_bind("<<Drop>>", self.on_drop)
        
        # 让文件列表本身也支持拖放
        self.file_list.drop_target_register(DND_FILES)
        self.file_list.dnd_bind("<<Drop>>", self.on_drop)
        
        # 创建右键菜单
        self.context_menu = tk.Menu(self.file_list, tearoff=0)
        self.context_menu.add_command(label="移动文件", command=self.move_selected_files)
        self.context_menu.add_command(label="移除文件", command=self.remove_files)
        self.context_menu.add_command(label="定位到此文件", command=self.locate_file)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="修改内置歌手名", command=self.modify_artist)
        self.context_menu.add_command(label="修改内置歌曲名", command=self.modify_title)
        
        # 绑定右键菜单到文件列表
        self.file_list.bind("<Button-3>", self.show_context_menu)
        
        # 创建选项框架
        self.options_frame = ttk.LabelFrame(self.main_frame, text="重命名选项", padding="10")
        self.options_frame.pack(fill=tk.X, pady=10)
        
        # 删除文件名中歌曲部分的括号内容选项
        self.remove_song_brackets_var = tk.BooleanVar(value=True)
        self.remove_song_brackets_check = ttk.Checkbutton(self.options_frame, text="删除文件名中歌曲部分的括号内容", variable=self.remove_song_brackets_var)
        self.remove_song_brackets_check.pack(side=tk.LEFT, padx=10)
        
        # 创建按钮框架
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, pady=10)
        
        # 选择文件按钮
        self.select_files_btn = ttk.Button(self.button_frame, text="选择文件", command=self.select_files)
        self.select_files_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 选择文件夹按钮
        self.select_folder_btn = ttk.Button(self.button_frame, text="选择文件夹", command=self.select_folder)
        self.select_folder_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 开始重命名按钮
        self.start_btn = ttk.Button(self.button_frame, text="开始重命名", command=self.start_renaming)
        self.start_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 清空列表按钮
        self.clear_list_btn = ttk.Button(self.button_frame, text="清空列表", command=self.clear_list)
        self.clear_list_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 创建日志文本框
        self.log_frame = ttk.LabelFrame(self.main_frame, text="操作日志", padding="10")
        self.log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 创建日志文本框
        log_font_size = int(self.font_size * 0.75)
        self.log_text = tk.Text(self.log_frame, wrap=tk.WORD, height=8, font=(self.font_name, log_font_size, self.font_weight))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 滚动条
        self.scrollbar = ttk.Scrollbar(self.log_text, command=self.log_text.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=self.scrollbar.set)
        
        # 让日志区也支持拖放
        self.log_frame.drop_target_register(DND_FILES)
        self.log_frame.dnd_bind("<<Drop>>", self.on_drop)
        
        self.log_text.drop_target_register(DND_FILES)
        self.log_text.dnd_bind("<<Drop>>", self.on_drop)
        
        # 恢复文件列表
        for file_path in self.files_to_process:
            self.file_list.insert(tk.END, os.path.basename(file_path))
        
        # 恢复日志
        for message in self.global_state['log_messages']:
            try:
                self.log_text.insert(tk.END, message + "\n")
            except:
                pass
        
        # 如果正在重命名，更新按钮状态
        if self.is_renaming:
            try:
                self.start_btn.config(state=tk.DISABLED, text="重命名中...")
                self.select_files_btn.config(state=tk.DISABLED)
                self.select_folder_btn.config(state=tk.DISABLED)
                self.clear_list_btn.config(state=tk.DISABLED)
            except:
                pass
        
        # 如果是独立运行，启动主循环
        if self.is_standalone:
            self.parent.mainloop()
        

        

    
    def on_enter(self, event):
        """鼠标进入事件"""
        self.file_list_frame.config(relief=tk.SUNKEN)
    
    def on_leave(self, event):
        """鼠标离开事件"""
        self.file_list_frame.config(relief=tk.GROOVE)
    
    def on_click(self, event):
        """鼠标点击事件"""
        # 打开文件选择对话框
        file_types = [
            ("音频文件", "*.mp3 *.wav *.flac *.ogg *.m4a"),
            ("所有文件", "*.*")
        ]
        files = filedialog.askopenfilenames(title="选择音频文件", filetypes=file_types)
        if files:
            self.add_files(files)
    
    def on_drop(self, event):
        """文件拖拽事件"""
        # 获取拖拽的文件路径
        self.log(f"拖拽原始数据: {event.data}")
        
        data = event.data
        file_paths = []
        
        if data:
            # 处理多个文件的情况，每个文件都被大括号包围
            if '} {' in data:
                # 分割多个文件
                raw_paths = data.split('} {')
                for i, raw_path in enumerate(raw_paths):
                    # 清理每个路径
                    path = raw_path.strip('{}')
                    file_paths.append(path)
            # 处理单个文件的情况
            elif data.startswith('{') and data.endswith('}'):
                # 移除大括号
                path = data[1:-1]
                file_paths = [path]
            # 处理其他格式的路径
            else:
                # 分割路径，处理包含空格的情况
                import shlex
                try:
                    file_paths = shlex.split(data)
                except:
                    # 如果shlex分割失败，使用简单分割
                    file_paths = data.split()
            
            # 清理路径
            cleaned_paths = []
            for path in file_paths:
                # 移除引号
                path = path.strip('"')
                # 移除可能的file:前缀
                if path.startswith('file:'):
                    path = path[5:]
                # 处理Windows路径格式
                if path.startswith('/'):
                    path = path.replace('/', '\\')
                cleaned_paths.append(path)
            
            file_paths = cleaned_paths
        
        self.log(f"解析后的文件路径: {file_paths}")
        self.add_files(file_paths)
    
    def select_files(self):
        """选择文件"""
        file_types = [
            ("音频文件", "*.mp3 *.wav *.flac *.ogg *.m4a"),
            ("所有文件", "*.*")
        ]
        files = filedialog.askopenfilenames(title="选择音频文件", filetypes=file_types)
        if files:
            self.add_files(files)
    
    def select_folder(self):
        """选择文件夹"""
        folder = filedialog.askdirectory(title="选择文件夹")
        if folder:
            self.add_files([folder])
    
    def add_files(self, paths):
        """添加文件到处理列表"""
        self.log(f"开始添加文件，路径数量: {len(paths)}")
        for path in paths:
            self.log(f"处理路径: {path}")
            if os.path.exists(path):
                if os.path.isfile(path):
                    ext = os.path.splitext(path)[1].lower()
                    self.log(f"文件扩展名: {ext}")
                    if ext in audio_extensions:
                        if path not in self.files_to_process:
                            self.files_to_process.append(path)
                            # 更新全局状态
                            self.global_state['files_to_process'] = self.files_to_process
                            try:
                                self.file_list.insert(tk.END, os.path.basename(path))
                            except:
                                pass
                            self.log(f"已添加文件: {os.path.basename(path)}")
                        else:
                            self.log(f"文件已存在: {os.path.basename(path)}")
                    else:
                        self.log(f"跳过非音频文件: {os.path.basename(path)}")
                elif os.path.isdir(path):
                    # 遍历文件夹中的所有音频文件
                    self.log(f"处理文件夹: {path}")
                    for root_dir, _, files in os.walk(path):
                        for file in files:
                            file_path = os.path.join(root_dir, file)
                            ext = os.path.splitext(file_path)[1].lower()
                            if ext in audio_extensions:
                                if file_path not in self.files_to_process:
                                    self.files_to_process.append(file_path)
                                    # 更新全局状态
                                    self.global_state['files_to_process'] = self.files_to_process
                                    try:
                                        self.file_list.insert(tk.END, os.path.basename(file_path))
                                    except:
                                        pass
                                    self.log(f"已添加文件: {os.path.basename(file_path)}")
                    self.log(f"已添加文件夹: {path}")
            else:
                self.log(f"路径不存在: {path}")
        
        self.log(f"当前待处理文件数量: {len(self.files_to_process)}")
    
    def get_audio_metadata(self, file_path):
        """获取音频文件的元数据"""
        try:
            audio = EasyID3(file_path)
            artist = audio.get('artist', ['Unknown Artist'])[0]
            title = audio.get('title', ['Unknown Title'])[0]
            return artist, title
        except ID3NoHeaderError:
            # 如果没有 ID3 标签，尝试使用 MP3 模块
            try:
                audio = MP3(file_path)
                artist = audio.get('TPE1', ['Unknown Artist'])[0] if hasattr(audio, 'get') else 'Unknown Artist'
                title = audio.get('TIT2', ['Unknown Title'])[0] if hasattr(audio, 'get') else 'Unknown Title'
                return artist, title
            except Exception as e:
                self.log(f"错误: 读取 {os.path.basename(file_path)} 的元数据失败: {e}")
                return 'Unknown Artist', 'Unknown Title'
        except Exception as e:
            self.log(f"错误: 读取 {os.path.basename(file_path)} 的元数据失败: {e}")
            return 'Unknown Artist', 'Unknown Title'
    
    def get_album_art_info(self, file_path):
        """获取音频文件的专辑图信息"""
        try:
            from mutagen.id3 import ID3
            audio = ID3(file_path)
            for tag in audio.values():
                if tag.FrameID == 'APIC':
                    # 检查是否有图片数据
                    if hasattr(tag, 'data') and tag.data:
                        # 尝试解析图片数据获取分辨率
                        import io
                        try:
                            from PIL import Image
                            try:
                                image = Image.open(io.BytesIO(tag.data))
                                width, height = image.size
                                return f"{width}x{height}"
                            except Exception:
                                return "Unknown"
                        except ImportError:
                            return "No PIL"
            return "No Art"
        except Exception as e:
            # 只在调试模式下显示详细错误
            # self.log(f"错误: 读取 {os.path.basename(file_path)} 的专辑图失败: {e}")
            return "Error"
    
    def clean_filename(self, s):
        """清理文件名，移除非法字符"""
        illegal_chars = '<>"/\\|?*'
        for char in illegal_chars:
            s = s.replace(char, '')
        return s.strip()
    
    def remove_files(self):
        """移除选中的文件"""
        try:
            selected_indices = self.file_list.curselection()
            if not selected_indices:
                messagebox.showinfo("提示", "请先选择要移除的文件")
                return
            
            # 从后往前删除，避免索引混乱
            for index in sorted(selected_indices, reverse=True):
                # 从文件列表中删除
                self.file_list.delete(index)
                # 从待处理列表中删除
                removed_file = self.files_to_process.pop(index)
                self.log(f"已移除文件: {os.path.basename(removed_file)}")
            
            # 更新全局状态
            self.global_state['files_to_process'] = self.files_to_process
            
            self.log(f"当前待处理文件数量: {len(self.files_to_process)}")
        except:
            pass
    
    def start_renaming(self):
        """开始重命名文件"""
        if not self.files_to_process:
            messagebox.showinfo("提示", "请先添加音频文件")
            return
        
        self.is_renaming = True
        # 更新全局状态
        self.global_state['is_renaming'] = True
        
        # 更新按钮状态
        try:
            self.start_btn.config(state=tk.DISABLED, text="重命名中...")
            self.select_files_btn.config(state=tk.DISABLED)
            self.select_folder_btn.config(state=tk.DISABLED)
            self.clear_list_btn.config(state=tk.DISABLED)
        except:
            pass
        
        # 启动重命名线程，设置daemon=False，确保线程在UI销毁后仍能继续运行
        threading.Thread(target=self.rename_files, daemon=False).start()
    
    def rename_files(self):
        """在后台线程中执行重命名操作"""
        success_count = 0
        error_count = 0
        skipped_count = 0
        failed_files = []
        
        # 复制文件列表，确保即使UI被销毁也能继续处理
        files_to_process = self.files_to_process.copy()
        
        for file_path in files_to_process:
            try:
                original_filename = os.path.basename(file_path)
                # 尝试记录日志，如果UI已销毁，忽略错误
                try:
                    self.log(f"处理: {original_filename}")
                except:
                    pass
                
                artist, title = self.get_audio_metadata(file_path)
                
                # 清理文件名
                artist = self.clean_filename(artist)
                title = self.clean_filename(title)
                
                # 额外清理冒号等Windows非法字符
                artist = artist.replace(':', '')
                title = title.replace(':', '')
                
                # 同步唱片艺术家（专辑艺术家）
                try:
                    audio = EasyID3(file_path)
                    # 检查是否已有专辑艺术家信息
                    if 'albumartist' not in audio or not audio.get('albumartist'):
                        # 同步艺术家到专辑艺术家
                        audio['albumartist'] = artist
                        audio.save()
                        # 尝试记录日志
                        try:
                            self.log(f"同步唱片艺术家成功: {artist}")
                        except:
                            pass
                except Exception as e:
                    # 尝试记录日志
                    try:
                        self.log(f"同步唱片艺术家失败: {e}")
                    except:
                        pass
                
                # 生成新文件名
                ext = os.path.splitext(file_path)[1]
                
                # 删除歌曲部分的括号内容
                if self.remove_song_brackets_var.get():
                    import re
                    title = re.sub(r'\s*[\(\[][^\)\]]*[\)\]]\s*', '', title)
                
                new_filename = f"{artist} - {title}{ext}"
                
                # 确保目标路径包含完整的目录
                # 规范化路径，处理混合斜杠问题
                file_path = os.path.normpath(file_path)
                directory = os.path.dirname(file_path)
                new_file_path = os.path.join(directory, new_filename)
                
                # 检查新文件名是否与原文件名相同
                if new_filename == original_filename:
                    # 尝试记录日志
                    try:
                        self.log(f"跳过: 文件名未变更")
                    except:
                        pass
                    skipped_count += 1
                    continue
                
                # 处理文件名冲突
                counter = 1
                while os.path.exists(new_file_path):
                    new_filename = f"{artist} - {title} ({counter}){ext}"
                    new_file_path = os.path.join(os.path.dirname(file_path), new_filename)
                    counter += 1
                
                os.rename(file_path, new_file_path)
                # 尝试记录日志
                try:
                    self.log(f"重命名成功: {new_filename}")
                except:
                    pass
                success_count += 1
            except Exception as e:
                error_msg = f"重命名 {original_filename} 失败: {e}"
                # 尝试记录日志
                try:
                    self.log(f"错误: {error_msg}")
                except:
                    pass
                failed_files.append(error_msg)
                error_count += 1
        
        # 尝试记录日志
        try:
            # 显示失败文件列表
            if failed_files:
                self.log("\n失败文件列表:")
                for failed_file in failed_files:
                    self.log(f"- {failed_file}")
            
            self.log(f"\n处理完成! 成功: {success_count}, 失败: {error_count}, 跳过: {skipped_count}")
        except:
            pass
        
        # 更新全局状态
        self.global_state['is_renaming'] = False
        self.global_state['success_count'] = success_count
        self.global_state['error_count'] = error_count
        self.global_state['skipped_count'] = skipped_count
        self.global_state['failed_files'] = failed_files
        self.global_state['files_to_process'] = []
        
        # 尝试清空待处理列表和文件列表
        try:
            self.files_to_process = []
            self.file_list.delete(0, tk.END)
            # 恢复按钮状态
            self.start_btn.config(state=tk.NORMAL, text="开始重命名")
            self.select_files_btn.config(state=tk.NORMAL)
            self.select_folder_btn.config(state=tk.NORMAL)
            self.clear_list_btn.config(state=tk.NORMAL)
            # 显示完成消息
            messagebox.showinfo("完成", f"重命名完成!\n成功: {success_count}\n失败: {error_count}\n跳过: {skipped_count}")
        except:
            pass
    
    def log(self, message):
        """添加日志信息"""
        # 更新全局状态
        self.global_state['log_messages'].append(message)
        # 限制日志条数，避免内存占用过大
        if len(self.global_state['log_messages']) > 1000:
            self.global_state['log_messages'] = self.global_state['log_messages'][-1000:]
        
        try:
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
        except:
            # 如果UI控件已被销毁，忽略错误
            pass
    
    def sort_files_by_name(self):
        """按文件名排序文件列表"""
        if not self.files_to_process:
            return
        
        # 按文件名排序
        sorted_files = sorted(self.files_to_process, key=lambda x: os.path.basename(x).lower())
        
        # 更新文件列表
        self.files_to_process = sorted_files
        
        # 清空并重新填充文件列表
        self.file_list.delete(0, tk.END)
        for file_path in self.files_to_process:
            self.file_list.insert(tk.END, os.path.basename(file_path))
        
        self.log("文件列表已按文件名排序")
    
    def sort_files_by_artist(self):
        """按歌手排序文件列表"""
        if not self.files_to_process:
            return
        
        # 获取每个文件的歌手信息
        def get_artist_key(file_path):
            artist, _ = self.get_audio_metadata(file_path)
            return artist.lower()  # 按歌手名小写排序
        
        # 按歌手排序
        sorted_files = sorted(self.files_to_process, key=get_artist_key)
        
        # 更新文件列表
        self.files_to_process = sorted_files
        
        # 清空并重新填充文件列表
        self.file_list.delete(0, tk.END)
        for file_path in self.files_to_process:
            artist, _ = self.get_audio_metadata(file_path)
            self.file_list.insert(tk.END, f"{os.path.basename(file_path)} ({artist})")
        
        self.log("文件列表已按歌手排序")
    
    def sort_files_by_title(self):
        """按歌曲排序文件列表"""
        if not self.files_to_process:
            return
        
        # 获取每个文件的歌曲信息
        def get_title_key(file_path):
            _, title = self.get_audio_metadata(file_path)
            return title.lower()  # 按歌曲名小写排序
        
        # 按歌曲排序
        sorted_files = sorted(self.files_to_process, key=get_title_key)
        
        # 更新文件列表
        self.files_to_process = sorted_files
        
        # 清空并重新填充文件列表
        self.file_list.delete(0, tk.END)
        for file_path in self.files_to_process:
            _, title = self.get_audio_metadata(file_path)
            self.file_list.insert(tk.END, f"{os.path.basename(file_path)} ({title})")
        
        self.log("文件列表已按歌曲排序")
    
    def sort_files_by_album_art(self):
        """按专辑图分辨率排序文件列表"""
        if not self.files_to_process:
            return
        
        # 获取每个文件的专辑图分辨率信息
        def get_resolution_key(file_path):
            album_art_info = self.get_album_art_info(file_path)
            try:
                if 'x' in album_art_info:
                    width, height = album_art_info.split('x')
                    return int(width) * int(height)  # 按像素总数排序
                else:
                    return 0  # 没有专辑图的排在前面
            except:
                return 0
        
        # 按专辑图分辨率排序
        sorted_files = sorted(self.files_to_process, key=get_resolution_key, reverse=True)
        
        # 更新文件列表
        self.files_to_process = sorted_files
        
        # 清空并重新填充文件列表
        self.file_list.delete(0, tk.END)
        for file_path in self.files_to_process:
            album_art_info = self.get_album_art_info(file_path)
            self.file_list.insert(tk.END, f"{os.path.basename(file_path)} ({album_art_info})")
        
        self.log("文件列表已按专辑图分辨率排序")
    
    def show_context_menu(self, event):
        """显示右键菜单"""
        # 检查是否有选中的文件
        selected_indices = self.file_list.curselection()
        if selected_indices:
            # 显示右键菜单
            self.context_menu.post(event.x_root, event.y_root)
    
    def move_selected_files(self):
        """移动选中的文件到指定位置"""
        selected_indices = self.file_list.curselection()
        if not selected_indices:
            messagebox.showinfo("提示", "请先选择要移动的文件")
            return
        
        # 选择目标文件夹
        target_folder = filedialog.askdirectory(title="选择目标文件夹")
        if not target_folder:
            return
        
        # 移动选中的文件
        moved_count = 0
        failed_count = 0
        failed_files = []
        
        # 从后往前处理，避免索引混乱
        for index in sorted(selected_indices, reverse=True):
            file_path = self.files_to_process[index]
            file_name = os.path.basename(file_path)
            new_file_path = os.path.join(target_folder, file_name)
            
            # 处理文件名冲突
            counter = 1
            while os.path.exists(new_file_path):
                base_name, ext = os.path.splitext(file_name)
                new_file_name = f"{base_name} ({counter}){ext}"
                new_file_path = os.path.join(target_folder, new_file_name)
                counter += 1
            
            try:
                # 检查是否跨磁盘移动
                import shutil
                if os.path.splitdrive(file_path)[0] != os.path.splitdrive(new_file_path)[0]:
                    # 跨磁盘移动，使用shutil.move
                    shutil.move(file_path, new_file_path)
                else:
                    # 同磁盘移动，使用os.rename
                    os.rename(file_path, new_file_path)
                # 从文件列表中移除
                self.file_list.delete(index)
                self.files_to_process.pop(index)
                self.log(f"已移动文件: {file_name}")
                moved_count += 1
            except Exception as e:
                error_msg = f"移动 {file_name} 失败: {e}"
                self.log(f"错误: {error_msg}")
                failed_files.append(error_msg)
                failed_count += 1
        
        self.log(f"移动完成! 成功: {moved_count}, 失败: {failed_count}")
        messagebox.showinfo("完成", f"移动完成!\n成功: {moved_count}\n失败: {failed_count}")
        
        self.log(f"当前待处理文件数量: {len(self.files_to_process)}")
    
    def clear_list(self):
        """清空文件列表"""
        try:
            if not self.files_to_process:
                return
            
            # 清空待处理列表
            self.files_to_process = []
            # 清空文件列表
            self.file_list.delete(0, tk.END)
            # 更新全局状态
            self.global_state['files_to_process'] = self.files_to_process
            
            self.log("文件列表已清空")
        except:
            pass
    
    def locate_file(self):
        """定位到选中的文件（在资源管理器中打开并选中）"""
        selected_indices = self.file_list.curselection()
        if not selected_indices:
            return
        
        # 只处理第一个选中的文件
        index = selected_indices[0]
        file_path = self.files_to_process[index]
        file_name = os.path.basename(file_path)
        
        try:
            # 标准化路径格式，确保使用Windows风格的反斜杠
            file_path = os.path.normpath(file_path)
            # 使用Windows资源管理器打开并选中文件
            import subprocess
            # 对于Windows系统，使用explorer.exe /select,命令
            # 使用shell=True来处理包含空格和非ASCII字符的路径
            # 移除check=True，因为explorer.exe可能返回非零状态码但操作成功
            subprocess.run(f'explorer.exe /select,"{file_path}"', shell=True)
            self.log(f"已定位文件: {file_name}")
        except Exception as e:
            # 即使有异常，也可能已经成功打开了资源管理器
            # 只记录异常信息，不显示失败
            self.log(f"定位文件时出现信息: {e}")
    
    def modify_artist(self):
        """修改选中文件的内置歌手名"""
        selected_indices = self.file_list.curselection()
        if not selected_indices:
            messagebox.showinfo("提示", "请先选择要修改的文件")
            return
        
        # 只处理第一个选中的文件
        index = selected_indices[0]
        file_path = self.files_to_process[index]
        file_name = os.path.basename(file_path)
        
        # 获取当前歌手名
        current_artist, _ = self.get_audio_metadata(file_path)
        
        # 创建输入对话框
        from tkinter.simpledialog import askstring
        new_artist = askstring("修改歌手名", f"请输入新的歌手名\n当前歌手名: {current_artist}", initialvalue=current_artist)
        
        if new_artist is not None and new_artist.strip():
            try:
                # 清理歌手名
                new_artist = self.clean_filename(new_artist.strip())
                
                # 更新歌手信息
                audio = EasyID3(file_path)
                audio['artist'] = new_artist
                # 同时更新专辑艺术家
                audio['albumartist'] = new_artist
                audio.save()
                
                self.log(f"已修改 {file_name} 的歌手名为: {new_artist}")
                messagebox.showinfo("成功", f"已成功修改 {file_name} 的歌手名为: {new_artist}")
            except Exception as e:
                error_msg = f"修改歌手名失败: {e}"
                self.log(f"错误: {error_msg}")
                messagebox.showerror("错误", error_msg)
    
    def modify_title(self):
        """修改选中文件的内置歌曲名"""
        selected_indices = self.file_list.curselection()
        if not selected_indices:
            messagebox.showinfo("提示", "请先选择要修改的文件")
            return
        
        # 只处理第一个选中的文件
        index = selected_indices[0]
        file_path = self.files_to_process[index]
        file_name = os.path.basename(file_path)
        
        # 获取当前歌曲名
        _, current_title = self.get_audio_metadata(file_path)
        
        # 创建输入对话框
        from tkinter.simpledialog import askstring
        new_title = askstring("修改歌曲名", f"请输入新的歌曲名\n当前歌曲名: {current_title}", initialvalue=current_title)
        
        if new_title is not None and new_title.strip():
            try:
                # 清理歌曲名
                new_title = self.clean_filename(new_title.strip())
                
                # 更新歌曲信息
                audio = EasyID3(file_path)
                audio['title'] = new_title
                audio.save()
                
                self.log(f"已修改 {file_name} 的歌曲名为: {new_title}")
                messagebox.showinfo("成功", f"已成功修改 {file_name} 的歌曲名为: {new_title}")
            except Exception as e:
                error_msg = f"修改歌曲名失败: {e}"
                self.log(f"错误: {error_msg}")
                messagebox.showerror("错误", error_msg)

if __name__ == "__main__":
    app = AudioRenamerApp()