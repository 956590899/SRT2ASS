import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinterdnd2 import TkinterDnD, DND_FILES
import subprocess
import os
import sys
import threading
import re
import json

# ============================================
# 配置区 - 用于保存GUI字体配置
# ============================================

# GUI_CONFIG_START - 唯一配置开始标记
GUI_CONFIG = {
  "ui_font": "微软雅黑",
  "ui_font_size": 15.0,
  "ui_bold": True,
  "remember_window_position": True,
  "window_x": 1297,
  "window_y": 562,
  "window_width": 1150,
  "window_height": 800
}
# GUI_CONFIG_END

class MainGUI:
    def __init__(self, root):
        self.root = root
        # 添加版本号
        self.version = "1.5.0 Summerキッス "
        self.root.title(f"字幕制作工具 - {self.version}")
        
        # 加载并应用窗口位置和大小设置
        self.load_window_position()
        
        # 绑定窗口关闭事件，保存位置
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # 绑定窗口大小和位置变化事件
        self.root.bind("<Configure>", self.on_window_configure)
        
        # 设置主题为暗黑模式
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # 优化字体渲染质量 - 提高显示效果
        try:
            # 针对不同DPI屏幕的缩放设置
            self.root.call("tk", "scaling", 1.0)
            
            # 设置全局默认字体，确保所有组件都继承这个字体
            global GUI_CONFIG
            selected_font = GUI_CONFIG.get("ui_font", "微软雅黑")
            font_size = GUI_CONFIG.get("ui_font_size", 16.0)
            font_size_int = int(round(font_size))
            font_weight = "bold" if GUI_CONFIG.get("ui_bold", False) else "normal"
            
            # 设置所有tkinter组件的默认字体
            self.root.option_add("*Font", f"{selected_font} {font_size_int} {font_weight}")
            
            # 设置所有ttk组件的默认字体
            self.style.configure(".", font=(selected_font, font_size_int, font_weight))
        except Exception as e:
            # 如果设置失败，忽略错误
            pass
        
        # 现代暗黑主题颜色配置
        self.bg_color = "#1e1e1e"
        self.fg_color = "#cccccc"
        self.accent_color = "#0078d4"
        self.border_color = "#333333"
        self.hover_color = "#252526"
        self.card_bg = "#252526"
        self.shadow_color = "#000000"
        
        # 创建局部变量以便在当前方法中使用
        bg_color = self.bg_color
        fg_color = self.fg_color
        accent_color = self.accent_color
        border_color = self.border_color
        hover_color = self.hover_color
        card_bg = self.card_bg
        shadow_color = self.shadow_color
        
        # 设置根窗口背景
        self.root.configure(bg=bg_color)
        
        # 配置ttk样式
        self.style.configure(
            ".",
            background=bg_color,
            foreground=fg_color,
            fieldbackground=card_bg,
            bordercolor=border_color,
            darkcolor=border_color,
            lightcolor=border_color
        )
        
        # 配置框架样式
        self.style.configure(
            "TLabelframe",
            background=bg_color,
            foreground=fg_color,
            bordercolor=border_color
        )
        
        self.style.configure(
            "TLabelframe.Label",
            background=bg_color,
            foreground=fg_color
        )
        
        # 配置按钮样式
        self.style.configure(
            "TButton",
            background=card_bg,
            foreground=fg_color,
            bordercolor=border_color,
            padding=5,
            borderradius=8
        )
        
        self.style.map(
            "TButton",
            background=[("active", hover_color), ("disabled", card_bg)],
            foreground=[("disabled", "#808080")],
            bordercolor=[("active", accent_color)]
        )
        
        # 配置高亮按钮样式（当前选中的功能）
        # 计算增大20%的字体大小
        highlighted_font_size = int(round(font_size * 1.2))
        self.style.configure(
            "Highlight.TButton",
            background=accent_color,
            foreground="#ffffff",
            bordercolor=accent_color,
            padding=8,
            borderradius=8,
            font=(selected_font, highlighted_font_size, font_weight)  # 字体增大20%
        )
        
        self.style.map(
            "Highlight.TButton",
            background=[("active", "#005a9e"), ("disabled", card_bg)],
            foreground=[("disabled", "#808080")],
            bordercolor=[("active", "#005a9e")]
        )
        
        # 配置标签样式
        self.style.configure(
            "TLabel",
            background=bg_color,
            foreground=fg_color
        )
        
        # 配置文本框样式
        self.style.configure(
            "TEntry",
            background=card_bg,
            foreground=fg_color,
            bordercolor=border_color,
            borderradius=8
        )
        
        self.style.map(
            "TEntry",
            bordercolor=[("focus", accent_color)]
        )
        
        # 配置Combobox样式
        # 为Windows系统创建一个专门的Combobox样式
        self.style.configure(
            "Custom.TCombobox",
            background=card_bg,
            foreground=fg_color,
            bordercolor=border_color,
            selectbackground=accent_color,
            selectforeground="#ffffff",
            fieldbackground=card_bg,
            darkcolor=card_bg,
            lightcolor=card_bg,
            borderradius=8
        )
        
        self.style.map(
            "Custom.TCombobox",
            background=[("active", hover_color), ("disabled", card_bg)],
            foreground=[("disabled", "#808080")],
            bordercolor=[("focus", accent_color)],
            fieldbackground=[("disabled", card_bg)]
        )
        
        # 配置Combobox下拉列表样式
        self.style.configure(
            "Custom.TCombobox.Popup",
            background=card_bg,
            foreground=fg_color,
            bordercolor=border_color
        )
        
        # 配置Combobox列表项样式
        self.style.configure(
            "Custom.TCombobox.Listbox",
            background=card_bg,
            foreground=fg_color,
            fieldbackground=card_bg
        )
        
        self.style.map(
            "Custom.TCombobox.Listbox",
            background=[("active", hover_color)],
            foreground=[("active", fg_color)]
        )
        
        # 针对Windows系统，可能需要额外配置Combobox的Entry样式
        self.style.configure(
            "Custom.TCombobox.Entry",
            background=card_bg,
            foreground=fg_color,
            fieldbackground=card_bg
        )
        
        # 配置单选按钮样式
        self.style.configure(
            "TRadiobutton",
            background=bg_color,
            foreground=fg_color,
            bordercolor=border_color
        )
        
        self.style.map(
            "TRadiobutton",
            background=[("active", bg_color), ("disabled", bg_color), ("selected", bg_color)],
            foreground=[("active", fg_color), ("disabled", "#808080"), ("selected", accent_color)],
            bordercolor=[("active", accent_color), ("disabled", border_color), ("selected", accent_color)]
        )
        
        # 配置滚动条样式
        self.style.configure(
            "Vertical.TScrollbar",
            background=card_bg,
            troughcolor=bg_color,
            bordercolor=border_color,
            arrowcolor=fg_color,
            width=10
        )
        
        self.style.map(
            "Vertical.TScrollbar",
            background=[("active", hover_color)]
        )
        
        # 加载并应用字体配置（在所有其他样式配置完成后）
        self.load_and_apply_font_config()
        
        # 创建主框架
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)
        
        # 创建左侧功能栏
        self.left_frame = ttk.LabelFrame(self.main_frame, text="功能选项", width=180)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=2)
        
        # 创建右侧工作区
        self.right_frame = ttk.LabelFrame(self.main_frame, text="工作界面")
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=4, pady=2)
        

        
        # 创建功能按钮
        self.create_function_buttons()
        
        # 初始化右侧工作区
        self.init_right_frame()
        
        # 设置窗口关闭协议
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def create_function_buttons(self):
        """创建左侧功能按钮，支持高亮效果，包括设置选项作为第七个大类"""
        self.buttons = []
        functions = [
            ("字幕校对打包程序", lambda: self.run_program("Z.py")),
            ("字幕式样打包替换", lambda: self.run_program("Z1.py")),
            ("字幕字体打包替换", lambda: self.run_program("D.py")),
            ("字幕文件独立修改", lambda: self.show_subtitle_independent_modification()),  # 添加字幕文件独立修改作为第四个大类，使用独立处理函数
            ("立体声转5.1声道", lambda: self.run_program("M.py")),  # 添加立体声转5.1声道作为第五个大类
            ("人声分离", lambda: self.run_program("x.py")),  # 添加人声分离作为第六个大类
            ("歌词适配", lambda: self.run_program("V.py")),  # 将歌词适配移到人声分离下面作为第七个大类
            ("设置选项", lambda: self.show_settings())  # 添加设置选项作为第八个大类
        ]
        
        for text, command in functions:
            btn = ttk.Button(self.left_frame, text=text, command=command, width=18)
            btn.pack(pady=4, padx=4)
            self.buttons.append(btn)
        
        # 默认高亮第一个按钮
        if self.buttons:
            self.highlight_button(self.buttons[0])
    
    def load_window_position(self):
        """从配置中加载窗口位置和大小，并确保窗口不超出屏幕范围"""
        global GUI_CONFIG
        # 从配置中获取窗口大小，默认使用1200x800
        width = GUI_CONFIG.get("window_width", 1200)
        height = GUI_CONFIG.get("window_height", 800)
        
        if GUI_CONFIG.get("remember_window_position", False):
            # 从配置中获取窗口位置
            x = GUI_CONFIG.get("window_x", 100)
            y = GUI_CONFIG.get("window_y", 100)
            
            # 获取屏幕尺寸
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # 确保窗口不超出屏幕范围
            # 左边界检查
            if x < 0:
                x = 0
            # 上边界检查
            if y < 0:
                y = 0
            # 右边界检查
            if x + width > screen_width:
                x = screen_width - width
            # 下边界检查
            if y + height > screen_height:
                y = screen_height - height
            
            # 应用调整后的窗口位置和大小
            self.root.geometry(f"{width}x{height}+{x}+{y}")
        else:
            # 使用默认大小和位置
            self.root.geometry("1200x800")
    
    def save_window_position(self):
        """只保存当前窗口位置到配置，不保存大小"""
        global GUI_CONFIG
        if GUI_CONFIG.get("remember_window_position", False):
            # 只获取当前窗口位置，不获取大小
            x = self.root.winfo_x()
            y = self.root.winfo_y()
            
            # 只更新位置配置，不更新大小
            GUI_CONFIG["window_x"] = x
            GUI_CONFIG["window_y"] = y
            
            # 保存配置到文件
            self.save_gui_config()
    
    def on_close(self):
        """窗口关闭时保存配置"""
        self.root.destroy()
    
    def on_window_configure(self, event):
        """窗口大小或位置变化时保存配置（延迟保存，避免频繁写入）"""
        # 仅在窗口已经映射到屏幕上时保存位置
        if self.root.winfo_exists() and self.root.winfo_ismapped():
            # 使用after延迟保存，避免频繁写入
            try:
                self.root.after_cancel(self.save_position_after_id)
            except AttributeError:
                pass
            self.save_position_after_id = self.root.after(1000, self.save_window_position)
    
    def save_gui_config(self):
        """保存GUI配置到文件"""
        global GUI_CONFIG
        try:
            with open(__file__, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 找到配置开始和结束标记
            start_tag = '# GUI_CONFIG_START - 唯一配置开始标记'
            end_tag = '# GUI_CONFIG_END'
            start_pos = content.find(start_tag)
            end_pos = content.find(end_tag)
            
            if start_pos != -1 and end_pos != -1:
                start_pos += len(start_tag)
                # 构建新的配置字符串
                config_str = json.dumps(GUI_CONFIG, ensure_ascii=False, indent=2)
                # 将JSON布尔值转换为Python布尔值
                config_str = config_str.replace('true', 'True').replace('false', 'False')
                # 生成新的文件内容
                new_content = content[:start_pos] + '\nGUI_CONFIG = ' + config_str + '\n' + content[end_pos:]
                
                # 写入文件
                with open(__file__, 'w', encoding='utf-8') as f:
                    f.write(new_content)
        except Exception as e:
            print(f"保存GUI配置失败: {e}")
    
    def on_remember_window_changed(self, *args):
        """记住窗口位置选项变化时的处理"""
        global GUI_CONFIG
        # 更新配置
        GUI_CONFIG["remember_window_position"] = self.remember_window_var.get()
        # 保存配置到文件
        self.save_gui_config()
        # 如果开启了记住窗口位置，立即保存当前位置
        if GUI_CONFIG["remember_window_position"]:
            self.save_window_position()
    
    def show_settings(self):
        """显示设置选项，作为一个独立的大类"""
        # 声明全局变量
        global GUI_CONFIG
        
        self.clear_right_frame()
        
        # 创建设置选项区域
        settings_frame = ttk.LabelFrame(self.right_frame, text="设置选项")
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)
        
        # 创建窗口设置框架
        window_frame = ttk.LabelFrame(settings_frame, text="窗口设置")
        window_frame.pack(fill=tk.X, padx=4, pady=2)
        
        # 记住窗口位置选项
        remember_window_frame = ttk.Frame(window_frame)
        remember_window_frame.pack(fill=tk.X, padx=4, pady=2)
        
        ttk.Label(remember_window_frame, text="记住窗口位置: " ).pack(side=tk.LEFT, padx=4, pady=2)
        
        # 加载保存的设置
        saved_remember_window = GUI_CONFIG.get("remember_window_position", False)
        self.remember_window_var = tk.BooleanVar(value=saved_remember_window)
        
        ttk.Radiobutton(remember_window_frame, text="关闭", variable=self.remember_window_var, value=False).pack(side=tk.LEFT, padx=4, pady=2)
        ttk.Radiobutton(remember_window_frame, text="开启", variable=self.remember_window_var, value=True).pack(side=tk.LEFT, padx=4, pady=2)
        
        # 添加提示信息
        # 获取当前字体配置，使用相对字体大小
        selected_font = GUI_CONFIG.get("ui_font", "微软雅黑")
        font_size = GUI_CONFIG.get("ui_font_size", 16.0)
        # 使用相对字体大小，比主文本小约20%
        small_font_size = max(6, int(round(font_size * 0.8)))
        font_weight = "bold" if GUI_CONFIG.get("ui_bold", False) else "normal"
        ttk.Label(remember_window_frame, text="(开启后下次启动将记住当前窗口位置)", foreground="#808080", font=(selected_font, small_font_size, font_weight)).pack(side=tk.LEFT, padx=4, pady=2)
        
        # 绑定状态变化事件
        self.remember_window_var.trace_add("write", self.on_remember_window_changed)
        
        # 创建UI字体设置框架
        ui_font_frame = ttk.LabelFrame(settings_frame, text="UI字体设置")
        ui_font_frame.pack(fill=tk.X, padx=4, pady=2)
        
        # 字体选择
        font_choice_frame = ttk.Frame(ui_font_frame)
        font_choice_frame.pack(fill=tk.X, padx=4, pady=2)
        
        ttk.Label(font_choice_frame, text="字体选择: " ).pack(side=tk.LEFT, padx=4, pady=2)
        
        # 常用系统字体列表
        system_fonts = ["微软雅黑", "等线", "仿宋", "黑体", "楷体", "新宋体"]
        # 加载保存的字体配置
        saved_font = GUI_CONFIG.get("ui_font", "微软雅黑")
        self.ui_font_var = tk.StringVar(value=saved_font)
        
        font_combobox = ttk.Combobox(font_choice_frame, textvariable=self.ui_font_var, values=system_fonts, width=20, state="readonly", style="Custom.TCombobox")
        font_combobox.pack(side=tk.LEFT, padx=4, pady=2)
        
        # 字体加粗选项
        bold_frame = ttk.Frame(ui_font_frame)
        bold_frame.pack(fill=tk.X, padx=4, pady=2)
        
        ttk.Label(bold_frame, text="字体加粗: " ).pack(side=tk.LEFT, padx=4, pady=2)
        
        saved_bold = 1 if GUI_CONFIG.get("ui_bold", False) else 0
        self.ui_bold_var = tk.IntVar(value=saved_bold)
        
        # 创建自定义复选框样式
        self.style.configure(
            "Custom.TCheckbutton",
            indicatoron=True,
            indicatorbackground=self.border_color,
            indicatorforeground=self.accent_color,
            background=self.bg_color,
            foreground=self.fg_color
            # 不设置硬编码字体，继承全局字体设置
        )
        
        # 配置复选框选中状态的样式
        self.style.map(
            "Custom.TCheckbutton",
            indicatorbackground=[("selected", self.accent_color)],
            indicatorforeground=[("selected", "#ffffff")]
        )
        
        # 使用tk.Checkbutton，确保显示对勾
        # 获取当前字体配置
        selected_font = GUI_CONFIG.get("ui_font", "微软雅黑")
        font_size = GUI_CONFIG.get("ui_font_size", 16.0)
        font_weight = "bold" if GUI_CONFIG.get("ui_bold", False) else "normal"
        font_size_int = int(round(font_size))
        
        self.font_bold_checkbox = tk.Checkbutton(
            bold_frame, 
            variable=self.ui_bold_var, 
            text="字体加粗",
            bg=self.bg_color,
            fg=self.fg_color,
            selectcolor=self.accent_color,
            activebackground=self.hover_color,
            activeforeground=self.fg_color,
            font=(selected_font, font_size_int, font_weight),
            relief="flat"
        )
        self.font_bold_checkbox.pack(side=tk.LEFT, padx=4, pady=2)
        
        # 字体大小调节
        font_size_frame = ttk.Frame(ui_font_frame)
        font_size_frame.pack(fill=tk.X, padx=4, pady=2)
        
        ttk.Label(font_size_frame, text="字体大小: " ).pack(side=tk.LEFT, padx=4, pady=2)
        
        saved_font_size = float(GUI_CONFIG.get("ui_font_size", 10.0))
        self.ui_font_size_var = tk.DoubleVar(value=saved_font_size)
        font_size_label = ttk.Label(font_size_frame, text="", width=5)
        font_size_label.pack(side=tk.LEFT, padx=4, pady=2)
        
        # 更新字体大小标签的函数
        def update_font_size_label():
            size = self.ui_font_size_var.get()
            font_size_label.config(text=f"{size:.1f}")
        
        # 初始更新
        update_font_size_label()
        
        # 绑定变量变化事件
        self.ui_font_size_var.trace_add("write", lambda *args: update_font_size_label())
        
        # 字体大小调节按钮
        ttk.Button(font_size_frame, text="-0.5", command=lambda: self.adjust_font_size(-0.5)).pack(side=tk.LEFT, padx=4, pady=2)
        ttk.Button(font_size_frame, text="+0.5", command=lambda: self.adjust_font_size(0.5)).pack(side=tk.LEFT, padx=4, pady=2)
        
        # 添加提示信息
        # 获取当前字体配置，保持较小字号但应用加粗设置
        selected_font = GUI_CONFIG.get("ui_font", "微软雅黑")
        font_weight = "bold" if GUI_CONFIG.get("ui_bold", False) else "normal"
        # 获取当前字体配置，使用相对字体大小
        small_font_size = max(6, int(round(font_size * 0.8)))
        ttk.Label(font_size_frame, text="(调整单位: 0.5，范围: 5.0-30.0)", foreground="#808080", font=(selected_font, small_font_size, font_weight)).pack(side=tk.LEFT, padx=4, pady=2)
        
        # 应用按钮
        apply_frame = ttk.Frame(ui_font_frame)
        apply_frame.pack(fill=tk.X, padx=4, pady=10)
        
        ttk.Button(apply_frame, text="应用字体设置", command=self.apply_ui_font_settings).pack(side=tk.LEFT, padx=4, pady=2)
        
        # 初始化进程为None
        self.process = None
        
        # 高亮对应的功能按钮
        for i, btn in enumerate(self.buttons):
            if i == 7:  # 设置选项是第八个大类
                self.highlight_button(btn)
                break
    
    def init_right_frame(self):
        """初始化右侧工作区，默认选择第一个功能"""
        # 默认运行第一个功能：字幕打包程序
        self.run_program("Z.py")
    
    def clear_right_frame(self):
        """清空右侧工作区"""
        for widget in self.right_frame.winfo_children():
            widget.destroy()
    
    def highlight_button(self, button):
        """高亮指定的按钮，取消其他按钮的高亮"""
        for btn in self.buttons:
            if btn == button:
                # 高亮当前按钮
                btn.configure(style="Highlight.TButton")
            else:
                # 恢复其他按钮的默认样式
                btn.configure(style="TButton")
    
    def read_z1_config(self):
        """读取Z1.py的配置"""
        z1_path = os.path.join(os.path.dirname(__file__), "Z1.py")
        config = {}
        
        try:
            with open(z1_path, "r", encoding="utf-8") as f:
                content = f.read()
                
                # 提取DEFAULT_SETTINGS_MODE，支持带有注释的情况
                match = re.search(r'DEFAULT_SETTINGS_MODE\s*=\s*(\d+)\s*(#.*)?', content)
                if match:
                    config["DEFAULT_SETTINGS_MODE"] = int(match.group(1))
                else:
                    config["DEFAULT_SETTINGS_MODE"] = 1
                
                # 提取STEREO_TO_5_1，支持带有注释的情况
                match = re.search(r'STEREO_TO_5_1\s*=\s*(\d+)\s*(#.*)?', content)
                if match:
                    config["STEREO_TO_5_1"] = int(match.group(1))
                else:
                    config["STEREO_TO_5_1"] = 0
                
                # 提取SUBTITLE_MODE，支持带有注释的情况
                match = re.search(r'SUBTITLE_MODE\s*=\s*(-?\d+)\s*(#.*)?', content)
                if match:
                    subtitle_mode = int(match.group(1))
                    config["SUBTITLE_MODE"] = subtitle_mode
                else:
                    config["SUBTITLE_MODE"] = 2
                    
        except Exception as e:
            print(f"读取Z1.py配置失败: {e}")
            config = {
                "DEFAULT_SETTINGS_MODE": 1,
                "STEREO_TO_5_1": 0,
                "SUBTITLE_MODE": 2
            }
        
        return config
    
    def read_d_config(self):
        """读取D.py的配置"""
        d_path = os.path.join(os.path.dirname(__file__), "D.py")
        # 默认配置，包含所有必要的配置项
        config = {
            "simplified_chinese": {
                "font_name": "方正准圆简体",
                "font_file": "方正准圆简体.ttf"
            },
            "japanese_traditional": {
                "font_name": "夏花绚烂前程似锦",
                "font_file": "夏花绚烂前程似锦.ttf"
            },
            "enable_font_attachment": 1,
            "set_unknown_to_chinese": 1
        }
        
        try:
            with open(d_path, "r", encoding="utf-8") as f:
                content = f.read()
                
                # 提取FONT_CONFIG字典
                # 查找FONT_CONFIG的开始位置
                start_pos = content.find('FONT_CONFIG = {')
                if start_pos != -1:
                    # 从开始位置开始，计算大括号的平衡
                    brace_count = 0
                    end_pos = start_pos
                    found_opening = False
                    
                    for i in range(start_pos, len(content)):
                        if content[i] == '{':
                            brace_count += 1
                            found_opening = True
                        elif content[i] == '}':
                            brace_count -= 1
                            if found_opening and brace_count == 0:
                                end_pos = i + 1
                                break
                    
                    if end_pos > start_pos:
                        font_config_str = content[start_pos:end_pos]
                        # 执行字符串来获取完整的FONT_CONFIG字典
                        local_vars = {}
                        exec(font_config_str, globals(), local_vars)
                        if 'FONT_CONFIG' in local_vars:
                            font_config = local_vars['FONT_CONFIG']
                            # 更新所有配置项，而不仅仅是字体相关的
                            for key, value in font_config.items():
                                config[key] = value
                            # 确保必要的配置项存在
                            if 'enable_font_attachment' not in config:
                                config['enable_font_attachment'] = 1
                            if 'set_unknown_to_chinese' not in config:
                                config['set_unknown_to_chinese'] = 1
                            
        except Exception as e:
            print(f"读取D.py配置失败: {e}")
        
        return config
    
    def save_d_settings(self):
        """保存D.py的设置"""
        d_path = os.path.join(os.path.dirname(__file__), "D.py")
        
        try:
            # 读取D.py文件的所有行
            with open(d_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 提取完整的FONT_CONFIG字典
            start_pos = content.find('FONT_CONFIG = {')
            if start_pos != -1:
                # 计算大括号的平衡
                brace_count = 0
                end_pos = start_pos
                found_opening = False
                
                for i in range(start_pos, len(content)):
                    if content[i] == '{':
                        brace_count += 1
                        found_opening = True
                    elif content[i] == '}':
                        brace_count -= 1
                        if found_opening and brace_count == 0:
                            end_pos = i + 1
                            break
                
                if end_pos > start_pos:
                    font_config_str = content[start_pos:end_pos]
                    # 执行字符串来获取完整的FONT_CONFIG字典
                    local_vars = {}
                    exec(font_config_str, globals(), local_vars)
                    if 'FONT_CONFIG' in local_vars:
                        d_config = local_vars['FONT_CONFIG']
                    else:
                        # 如果执行失败，使用默认配置
                        d_config = {
                            "simplified_chinese": {
                                "font_name": "方正准圆简体",
                                "font_file": "方正准圆简体.ttf"
                            },
                            "japanese_traditional": {
                                "font_name": "夏花绚烂前程似锦",
                                "font_file": "夏花绚烂前程似锦.ttf"
                            },
                            "enable_font_attachment": 1,
                            "set_unknown_to_chinese": 1
                        }
                else:
                    # 如果找不到完整的FONT_CONFIG，使用默认配置
                    d_config = {
                        "simplified_chinese": {
                            "font_name": "方正准圆简体",
                            "font_file": "方正准圆简体.ttf"
                        },
                        "japanese_traditional": {
                            "font_name": "夏花绚烂前程似锦",
                            "font_file": "夏花绚烂前程似锦.ttf"
                        },
                        "enable_font_attachment": 1,
                        "set_unknown_to_chinese": 1
                    }
            else:
                # 如果找不到FONT_CONFIG，使用默认配置
                d_config = {
                    "simplified_chinese": {
                        "font_name": "方正准圆简体",
                        "font_file": "方正准圆简体.ttf"
                    },
                    "japanese_traditional": {
                        "font_name": "夏花绚烂前程似锦",
                        "font_file": "夏花绚烂前程似锦.ttf"
                    },
                    "enable_font_attachment": 1,
                    "set_unknown_to_chinese": 1
                }
            
            # 更新字体配置
            # 简体中文字体：同步更新font_name和font_file
            if hasattr(self, 'sc_font_var'):
                sc_font_name = self.sc_font_var.get()
                d_config['simplified_chinese']['font_name'] = sc_font_name
                d_config['simplified_chinese']['font_file'] = f'{sc_font_name}.ttf'  # 自动同步font_file
            
            # 日语繁体字体：同步更新font_name和font_file
            if hasattr(self, 'jt_font_var'):
                jt_font_name = self.jt_font_var.get()
                d_config['japanese_traditional']['font_name'] = jt_font_name
                d_config['japanese_traditional']['font_file'] = f'{jt_font_name}.ttf'  # 自动同步font_file
            
            # 更新系统字体设置
            if hasattr(self, 'use_system_font_var'):
                d_config['use_system_font'] = self.use_system_font_var.get()
            
            if hasattr(self, 'system_font_var'):
                d_config['system_font_name'] = self.system_font_var.get()
            
            # 生成新的FONT_CONFIG代码
            font_config_str = json.dumps(d_config, ensure_ascii=False, indent=4)
            # 将JSON布尔值转换为Python布尔值
            font_config_str = font_config_str.replace('true', 'True').replace('false', 'False')
            font_config_code = f'FONT_CONFIG = {font_config_str}'
            
            # 找到FONT_CONFIG的开始和结束位置
            start_pos = content.find('FONT_CONFIG = {')
            if start_pos != -1:
                # 计算大括号的平衡
                brace_count = 0
                end_pos = start_pos
                found_opening = False
                
                for i in range(start_pos, len(content)):
                    if content[i] == '{':
                        brace_count += 1
                        found_opening = True
                    elif content[i] == '}':
                        brace_count -= 1
                        if found_opening and brace_count == 0:
                            end_pos = i + 1
                            break
                
                if end_pos > start_pos:
                    # 跳过FONT_CONFIG块结束后的所有空行
                    remaining_content = content[end_pos:]
                    # 找到第一个非空行的位置
                    next_content_start = 0
                    for i, char in enumerate(remaining_content):
                        if char not in '\n\r\t ':  # 不是空白字符，找到下一个有内容的位置
                            next_content_start = i
                            break
                    # 替换整个FONT_CONFIG块，只保留必要的换行
                    new_content = content[:start_pos] + font_config_code + '\n\n' + remaining_content[next_content_start:]
                    
                    # 写入更新后的内容
                    with open(d_path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                else:
                    # 如果找不到完整的FONT_CONFIG，使用默认方法
                    print("未找到完整的FONT_CONFIG，使用默认方法保存")
                    with open(d_path, "w", encoding="utf-8") as f:
                        f.write('import os\nimport sys\nimport re\nimport json\nimport subprocess\nimport tempfile\nimport shutil\nfrom pathlib import Path\n\n# ====== D.py自己的字体配置 ======\n' + font_config_code + '\n\nclass MKVFontReplacer:\n')
            else:
                # 如果没有找到FONT_CONFIG，创建新的配置
                print("未找到FONT_CONFIG，创建新的配置")
                with open(d_path, "w", encoding="utf-8") as f:
                    f.write('import os\nimport sys\nimport re\nimport json\nimport subprocess\nimport tempfile\nimport shutil\nfrom pathlib import Path\n\n# ====== D.py自己的字体配置 ======\n' + font_config_code + '\n\nclass MKVFontReplacer:\n')
                    
        except Exception as e:
            print(f"保存D.py设置失败: {e}")
    
    def get_available_fonts(self):
        """获取SRT/TTF目录中的可用字体文件"""
        fonts_dir = os.path.join(os.path.dirname(__file__), "TTF")
        available_fonts = []
        
        try:
            if os.path.exists(fonts_dir):
                for file in os.listdir(fonts_dir):
                    if file.lower().endswith('.ttf'):
                        # 获取字体名称（去除.ttf扩展名）
                        font_name = os.path.splitext(file)[0]
                        available_fonts.append((font_name, file))
        except Exception as e:
            print(f"读取字体目录失败: {e}")
        
        return available_fonts
    
    def get_font_file_by_name(self, font_name):
        """根据字体名称获取对应的字体文件名"""
        available_fonts = self.get_available_fonts()
        for name, file in available_fonts:
            if name == font_name:
                return file
        return font_name + '.ttf'
    
    def save_z1_settings(self):
        """保存Z1.py的设置"""
        z1_path = os.path.join(os.path.dirname(__file__), "Z1.py")
        
        try:
            with open(z1_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 更新DEFAULT_SETTINGS_MODE
            if hasattr(self, 'default_settings_mode_var'):
                mode = self.default_settings_mode_var.get()
                # 确保能匹配带有注释的情况
                content = re.sub(r'DEFAULT_SETTINGS_MODE\s*=\s*\d+\s*#.*', f'DEFAULT_SETTINGS_MODE = {mode}  # 0或1', content)
                content = re.sub(r'DEFAULT_SETTINGS_MODE\s*=\s*\d+', f'DEFAULT_SETTINGS_MODE = {mode}', content)
            
            # 更新STEREO_TO_5_1
            if hasattr(self, 'stereo_to_5_1_var'):
                mode = self.stereo_to_5_1_var.get()
                # 确保能匹配带有注释的情况
                content = re.sub(r'STEREO_TO_5_1\s*=\s*\d+\s*#.*', f'STEREO_TO_5_1 = {mode}  # 0或1', content)
                content = re.sub(r'STEREO_TO_5_1\s*=\s*\d+', f'STEREO_TO_5_1 = {mode}', content)
            
            # 更新SUBTITLE_MODE
            if hasattr(self, 'subtitle_mode_var'):
                mode = self.subtitle_mode_var.get()
                # 确保能匹配带有注释的情况
                content = re.sub(r'SUBTITLE_MODE\s*=\s*-?\d+\s*#.*', f'SUBTITLE_MODE = {mode}  # 0、1、2或-1（全选）', content)
                content = re.sub(r'SUBTITLE_MODE\s*=\s*-?\d+', f'SUBTITLE_MODE = {mode}', content)
            
            with open(z1_path, "w", encoding="utf-8") as f:
                f.write(content)
                
        except Exception as e:
            print(f"保存Z1.py设置失败: {e}")
    
    def on_subtitle_radio_click(self, clicked_value):
        """处理字幕单选按钮的点击事件，实现纯粹的单选逻辑：
        - 正常情况下只能选择一个选项
        - 移除全选模式，使用简单的单选逻辑
        """
        # 简单的单选逻辑，直接设置选中值即可
        # Tkinter的Radiobutton会自动处理其他选项的取消选中
        self.subtitle_mode_var.set(clicked_value)
        # 重置全选模式标志
        self.is_all_selected = False
    
    def on_karaoke_effect_radio_click(self, clicked_value):
        """处理卡拉OK效果单选按钮的点击事件，实现纯粹的单选逻辑：
        - 只能选择一个选项
        - 取消全选模式，恢复正常单选行为
        """
        # 添加调试信息
        # print(f"DEBUG: on_karaoke_effect_radio_click 被调用，clicked_value = {clicked_value}")
        # print(f"DEBUG: real_karaoke_var.get() = {self.real_karaoke_var.get()}")
        
        # 重置所有选项状态
        if hasattr(self, 'all_effects_radio'):
            self.all_effects_radio.state(['!selected'])
        for radio in [self.default_effect_radio, self.ktv_effect_radio, self.prompter_effect_radio]:
            radio.state(['!selected'])
        
        # 只选择当前点击的选项
        self.real_karaoke_var.set(clicked_value)
        
        # 设置当前点击的选项为选中状态
        if clicked_value == -1:
            if hasattr(self, 'all_effects_radio'):
                self.all_effects_radio.state(['selected'])
        else:
            for radio in [self.default_effect_radio, self.ktv_effect_radio, self.prompter_effect_radio]:
                if int(radio.cget('value')) == clicked_value:
                    radio.state(['selected'])
        
        # 确保全选模式标记为False
        if hasattr(self, 'z_all_selected'):
            self.z_all_selected = False
        if hasattr(self, 'is_all_selected'):
            self.is_all_selected = False
        
        # 打印最终状态
        # print(f"DEBUG: 操作完成后，z_all_selected = {getattr(self, 'z_all_selected', False)}, is_all_selected = {getattr(self, 'is_all_selected', False)}")
        # print(f"DEBUG: real_karaoke_var.get() = {self.real_karaoke_var.get()}")
    
    def read_v_config(self):
        """读取V.py的配置"""
        v_path = os.path.join(os.path.dirname(__file__), "V.py")
        config = {}
        
        try:
            with open(v_path, "r", encoding="utf-8") as f:
                content = f.read()
                
                # 提取ENABLE_Z_PACKAGING
                match = re.search(r'ENABLE_Z_PACKAGING\s*=\s*(\d+)', content)
                if match:
                    config["ENABLE_Z_PACKAGING"] = int(match.group(1))
                else:
                    config["ENABLE_Z_PACKAGING"] = 1
                
                # 提取SAVE_ORIGINAL_LRC
                match = re.search(r'SAVE_ORIGINAL_LRC\s*=\s*(\d+)', content)
                if match:
                    config["SAVE_ORIGINAL_LRC"] = int(match.group(1))
                else:
                    config["SAVE_ORIGINAL_LRC"] = 0
                
        except Exception as e:
            print(f"读取V.py配置失败: {e}")
            config = {
                "ENABLE_Z_PACKAGING": 1,
                "SAVE_ORIGINAL_LRC": 0
            }
        
        return config
    
    def save_v_settings(self):
        """保存V.py的设置"""
        v_path = os.path.join(os.path.dirname(__file__), "V.py")
        
        try:
            with open(v_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 更新ENABLE_Z_PACKAGING
            if hasattr(self, 'enable_z_packaging_var'):
                mode = self.enable_z_packaging_var.get()
                content = re.sub(r'ENABLE_Z_PACKAGING\s*=\s*\d+', f'ENABLE_Z_PACKAGING = {mode}', content)
            
            # 更新SAVE_ORIGINAL_LRC
            if hasattr(self, 'save_original_lrc_var'):
                mode = self.save_original_lrc_var.get()
                content = re.sub(r'SAVE_ORIGINAL_LRC\s*=\s*\d+', f'SAVE_ORIGINAL_LRC = {mode}', content)
            
            with open(v_path, "w", encoding="utf-8") as f:
                f.write(content)
                
        except Exception as e:
            print(f"保存V.py设置失败: {e}")
    
    def read_x_config(self):
        """读取x.py的配置"""
        x_path = os.path.join(os.path.dirname(__file__), "x.py")
        config = {}
        
        try:
            with open(x_path, "r", encoding="utf-8") as f:
                content = f.read()
                
                # 提取DEFAULT_OUTPUT_MODE_ID
                match = re.search(r'DEFAULT_OUTPUT_MODE_ID\s*=\s*(\d+)', content)
                if match:
                    config["DEFAULT_OUTPUT_MODE_ID"] = int(match.group(1))
                else:
                    config["DEFAULT_OUTPUT_MODE_ID"] = 1
                
        except Exception as e:
            print(f"读取x.py配置失败: {e}")
            config = {
                "DEFAULT_OUTPUT_MODE_ID": 1
            }
        
        return config
    
    def save_x_settings(self):
        """保存x.py的设置"""
        x_path = os.path.join(os.path.dirname(__file__), "x.py")
        
        try:
            with open(x_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 更新DEFAULT_OUTPUT_MODE_ID
            if hasattr(self, 'default_output_mode_id_var'):
                mode_id = self.default_output_mode_id_var.get()
                content = re.sub(r'DEFAULT_OUTPUT_MODE_ID\s*=\s*\d+', f'DEFAULT_OUTPUT_MODE_ID = {mode_id}', content)
            
            with open(x_path, "w", encoding="utf-8") as f:
                f.write(content)
                
        except Exception as e:
            print(f"保存x.py设置失败: {e}")
    
    def read_m_config(self):
        """读取M.py的配置"""
        m_path = os.path.join(os.path.dirname(__file__), "M.py")
        config = {}
        
        try:
            with open(m_path, "r", encoding="utf-8") as f:
                content = f.read()
                
                # 提取DEFAULT_OUTPUT_FORMAT_ID
                match = re.search(r'DEFAULT_OUTPUT_FORMAT_ID\s*=\s*(\d+)', content)
                if match:
                    config["DEFAULT_OUTPUT_FORMAT_ID"] = int(match.group(1))
                else:
                    config["DEFAULT_OUTPUT_FORMAT_ID"] = 1
                
        except Exception as e:
            print(f"读取M.py配置失败: {e}")
            config = {
                "DEFAULT_OUTPUT_FORMAT_ID": 1
            }
        
        return config
    
    def save_m_settings(self):
        """保存M.py的设置"""
        m_path = os.path.join(os.path.dirname(__file__), "M.py")
        
        try:
            with open(m_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 更新DEFAULT_OUTPUT_FORMAT_ID
            if hasattr(self, 'default_output_format_id_var'):
                format_id = self.default_output_format_id_var.get()
                content = re.sub(r'DEFAULT_OUTPUT_FORMAT_ID\s*=\s*\d+', f'DEFAULT_OUTPUT_FORMAT_ID = {format_id}', content)
            
            with open(m_path, "w", encoding="utf-8") as f:
                f.write(content)
                
        except Exception as e:
            print(f"保存M.py设置失败: {e}")
    
    def run_program(self, program_name):
        """运行指定的程序，显示功能说明信息"""
        global GUI_CONFIG
        # 获取当前目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 构建程序路径
        program_path = os.path.join(current_dir, program_name)
        
        # 更新右侧工作区显示
        self.clear_right_frame()
        
        # 获取功能名称和描述
        program_info = {
            "Z.py": {"name": "字幕打包程序", "description": [
                "==================================",
                "字幕处理工作流程：字幕校准 -> 卡拉OK生成 -> MKV打包",
                "==================================",

                "本程序工作目录为输入目录和系统下载目录",
                "（输入字幕自动查找同名视频文件进行处理）",
                "",
                "字幕校对打包程序 - 你需要准备：",
                "1. 字幕文件+视频文件（同名）",
                "2. 或者内嵌字幕的视频文件",
                "",
                "可选功能：",
                "1. 是否启用自定义字体",
                "2. 是否使用卡拉OK扫字特效",
                "",
                "技术说明：",
                "- 将使用人声分离技术进行字幕校对",
                "",
                "使用方法：",
                "1. 点击'选择文件'按钮选择字幕文件",
                "2. 点击'执行'按钮开始任务",
                "3. 开始任务后将显示实际输出"
            ]},
            "Z1.py": {"name": "视频字幕式样替换", "description": [
                "================",
                "字幕式样替换功能使用说明：",
                "================",
                "",
                "功能说明：",
                "- 替换内嵌字幕视频文件中的样式信息",
                "- 支持批量处理多个字幕文件",
                "- 可以自定义替换规则",
                "",
                "使用方法：",
                "1. 点击'选择文件'按钮选择视频文件",
                "2. 点击'执行'按钮开始处理",
                "3. 处理完成后查看输出结果"
            ]},
            "D.py": {"name": "视频字幕字体替换", "description": [
                "================",
                "字幕字体替换功能使用说明：",
                "================",
                "",
                "功能说明：",
                "- 自动识别字体文件夹SRT2ASS\SRT\TTF",
                "- 启用系统自带字体模式不打包字体文件",
                "- 替换内嵌字幕视频文件中的字体设置",
                "- 支持批量替换多个内嵌字幕视频文件",
                "- 可以指定新的字体名称和样式",
                "",
                "使用方法：",
                "1. 点击'选择文件'按钮选择视频文件",
                "2. 点击'执行'按钮开始处理",
                "3. 处理完成后查看输出结果"
            ]},
            "C.py": {"name": "", "description": [
                
            ]},
            "M.py": {"name": "立体声转5.1声道", "description": [
                "=================",
                "立体声转5.1声道功能使用说明：",
                "=================",
                "",
                "功能说明：",
                "- 将立体声音频转换为5.1声道音频",
                "- 支持处理音频文件和视频文件中的音频",
                "- 可以提升音频的空间感和环绕声效果",
                "",
                "使用方法：",
                "1. 点击'选择文件'按钮选择音频文件或视频文件",
                "2. 点击'执行'按钮开始处理",
                "3. 处理完成后查看输出结果"
            ]},
            "x.py": {"name": "人声分离", "description": [
                "=============",
                "人声分离功能使用说明：",
                "=============",
                "",
                "功能说明：",
                "- 使用Demucs技术分离音频中的人声和伴奏",
                "- 支持多种输出模式：仅人声、仅伴奏、人声和伴奏、全部分离",
                "- 可以处理音频文件和视频文件中的音频",
                "",
                "使用方法：",
                "1. 点击'选择文件'按钮选择音频文件或视频文件",
                "2. 点击'执行'按钮开始处理",
                "3. 处理完成后查看输出结果"
            ]},
            "V.py": {"name": "歌词适配", "description": [
                "=============",
                "歌词适配功能使用说明：",
                "=============",
                "",
                "功能说明：",
                "- 支持输入视频文件或字幕文件",
                "- 输入文件用于获取歌曲名（需清理文件名为 歌手- 歌曲 格式防止干扰）",
                "- 根据提取到歌曲信息生成MP3文件调用第三方程序匹配歌词",
                "- 匹配过程会接管你的鼠标操作 ",
                "- 当出现歌词预览后发现歌词不满意可手动接管",
                "- 当输入为字幕文件时 会将目标歌词时间进行对其计算总持续时间",
                "- 误差在合理范围内可选是否进行一键打包整合",
                "- 时间误差过大需自行校对时间轴",
                "- 内嵌字幕视频也支持时间轴对比（用于不满意当前歌词翻译情况进行一键替换）",
                "",
                "使用方法：",
                "1. 点击'选择文件'按钮选择歌词文件和视频文件",
                "2. 点击'执行'按钮开始处理",
                "3. 处理完成后查看输出结果"
            ]}
        }
        
        # 获取当前功能的信息
        current_program = program_info.get(program_name, {"name": program_name, "description": [f"功能：{program_name}"]})
        
        # 仅为非C.py的功能创建输入参数和控制按钮区域
        if program_name != "C.py":
            # 创建输入区域 - 放到最上面
            input_frame = ttk.LabelFrame(self.right_frame, text="输入参数")
            input_frame.pack(fill=tk.X, padx=4, pady=2)
            
            # 简化布局，直接使用Grid布局实现精确对齐
            # 第一行：文件路径标签和输入框
            ttk.Label(input_frame, text="文件路径: ", anchor="w").grid(row=0, column=0, padx=8, pady=2, sticky="w")
            
            self.input_entry = ttk.Entry(input_frame, width=60)
            self.input_entry.grid(row=0, column=1, padx=4, pady=2, sticky="we")
            
            # 为输入框添加拖放支持
            self.input_entry.drop_target_register(DND_FILES)
            self.input_entry.dnd_bind("<<Drop>>", self.on_drop)
            
            # 第二行：所有按钮，全部靠右排列
            button_frame = ttk.Frame(input_frame)
            button_frame.grid(row=1, column=0, columnspan=2, padx=8, pady=2, sticky="e")
            
            # 执行/停止共用按钮，初始显示为"开始处理"
            self.execute_stop_btn = ttk.Button(
                button_frame, 
                text="开始处理", 
                command=lambda: self.toggle_execute(program_path, current_dir),
                width=12
            )
            self.execute_stop_btn.pack(side=tk.RIGHT, padx=4, pady=1)
            
            # 清空日志按钮
            ttk.Button(button_frame, text="清空日志", command=self.clear_output, width=12).pack(side=tk.RIGHT, padx=4, pady=1)
            
            # 如果不是歌词适配功能，添加选择目录按钮
            if program_name != "V.py":
                # 添加选择目录按钮（原选择文件夹）
                browse_folder_btn = ttk.Button(
                    button_frame, 
                    text="选择目录", 
                    command=self.browse_folder, 
                    width=10
                )
                browse_folder_btn.pack(side=tk.RIGHT, padx=4, pady=1)
            
            # 添加选择文件按钮
            browse_btn = ttk.Button(
                button_frame, 
                text="选择文件", 
                command=self.browse_files, 
                width=10
            )
            browse_btn.pack(side=tk.RIGHT, padx=4, pady=1)
            
            # 配置Grid列权重，使输入框能够自动扩展
            input_frame.columnconfigure(1, weight=1)
        
        # 创建设置选项区域
        if program_name == "Z.py":
            settings_frame = ttk.LabelFrame(self.right_frame, text="设置选项")
            settings_frame.pack(fill=tk.X, padx=4, pady=2)
            
            # 读取配置
            z_config = self.read_z_config()
            c_config = self.read_c_config()
            
            # 横向排列的设置框架
            horizontal_frame = ttk.Frame(settings_frame)
            horizontal_frame.pack(fill=tk.X, padx=4, pady=1)
            
            # 字幕式样设置 - 左侧
            style_frame = ttk.LabelFrame(horizontal_frame, text="字幕式样")
            style_frame.pack(side=tk.LEFT, padx=4, pady=1, fill=tk.BOTH, expand=True)
            
            # 卡拉OK开关
            karaoke_frame = ttk.Frame(style_frame)
            karaoke_frame.pack(fill=tk.X, padx=4, pady=1)
            
            ttk.Label(karaoke_frame, text="卡拉OK开关: " ).pack(side=tk.LEFT, padx=4, pady=1)
            
            self.karaoke_var = tk.IntVar(value=z_config.get("KARAOKE_EFFECT", 1))
            
            ttk.Radiobutton(karaoke_frame, text="关闭", variable=self.karaoke_var, value=0).pack(side=tk.LEFT, padx=4, pady=1)
            ttk.Radiobutton(karaoke_frame, text="开启", variable=self.karaoke_var, value=1).pack(side=tk.LEFT, padx=4, pady=1)
            
            # 卡拉OK效果
            real_karaoke_frame = ttk.Frame(style_frame)
            real_karaoke_frame.pack(fill=tk.X, padx=4, pady=1)
            
            ttk.Label(real_karaoke_frame, text="卡拉OK效果: " ).pack(side=tk.LEFT, padx=4, pady=1)
            
            real_effect = z_config.get("REAL_KARAOKE_EFFECT", 0)
            # 初始化变量 - 如果是'A'（全选），转换为全选选项值-1
            # 确保传递给IntVar的是整数
            if real_effect == 'A':
                real_karaoke_var_value = -1
            else:
                # 确保real_effect是整数
                real_karaoke_var_value = int(real_effect) if isinstance(real_effect, str) and (real_effect.isdigit() or real_effect == '-1') else real_effect
            self.real_karaoke_var = tk.IntVar(value=real_karaoke_var_value)
            self.is_all_selected = False  # 取消全选模式
            
            # 保存单选按钮为实例变量，并添加命令
            self.all_effects_radio = ttk.Radiobutton(real_karaoke_frame, text="全选", variable=self.real_karaoke_var, value=-1, command=lambda: self.on_karaoke_effect_radio_click(-1))
            self.all_effects_radio.pack(side=tk.LEFT, padx=4, pady=1)
            
            self.default_effect_radio = ttk.Radiobutton(real_karaoke_frame, text="默认", variable=self.real_karaoke_var, value=0, command=lambda: self.on_karaoke_effect_radio_click(0))
            self.default_effect_radio.pack(side=tk.LEFT, padx=4, pady=1)
            
            self.ktv_effect_radio = ttk.Radiobutton(real_karaoke_frame, text="KTV", variable=self.real_karaoke_var, value=1, command=lambda: self.on_karaoke_effect_radio_click(1))
            self.ktv_effect_radio.pack(side=tk.LEFT, padx=4, pady=1)
            
            self.prompter_effect_radio = ttk.Radiobutton(real_karaoke_frame, text="提词器", variable=self.real_karaoke_var, value=2, command=lambda: self.on_karaoke_effect_radio_click(2))
            self.prompter_effect_radio.pack(side=tk.LEFT, padx=4, pady=1)
            
            # 设置按钮状态 - 纯粹单选，只高亮当前选项
            # 重置所有选项状态
            for radio in [self.all_effects_radio, self.default_effect_radio, self.ktv_effect_radio, self.prompter_effect_radio]:
                radio.state(['!selected'])
            
            # 高亮当前选中的选项
            if self.real_karaoke_var.get() == -1:
                # 如果是全选选项，高亮全选按钮
                self.all_effects_radio.state(['selected'])
            else:
                # 否则高亮对应的效果选项
                for radio in [self.default_effect_radio, self.ktv_effect_radio, self.prompter_effect_radio]:
                    if int(radio.cget('value')) == self.real_karaoke_var.get():
                        radio.state(['selected'])
            
            # 拖长音检测开关
            sustain_detection_frame = ttk.Frame(style_frame)
            sustain_detection_frame.pack(fill=tk.X, padx=4, pady=1)
            
            # 检查是否是第一次初始化延长音检测设置
            if not hasattr(self, 'sustain_detection_initialized'):
                # 第一次启动GUI时强制将延长音检测设为关闭
                self.beginning_sustain_detection_var = tk.IntVar(value=0)
                self.ending_sustain_detection_var = tk.IntVar(value=0)
                # 同时更新B.py中的配置为关闭状态
                self.save_b_settings()
                # 标记已初始化
                self.sustain_detection_initialized = True
            else:
                # 后续切换时读取B.py中的实际配置
                b_config = self.read_b_config()
                self.beginning_sustain_detection_var = tk.IntVar(value=b_config.get("ENABLE_BEGINNING_SUSTAIN_DETECTION", 0))
                self.ending_sustain_detection_var = tk.IntVar(value=b_config.get("ENABLE_ENDING_SUSTAIN_DETECTION", 0))
            
            # 句首延长音开关
            beginning_sustain_frame = ttk.Frame(sustain_detection_frame)
            beginning_sustain_frame.pack(fill=tk.X, padx=4, pady=1)
            ttk.Label(beginning_sustain_frame, text="句首延长音: " ).pack(side=tk.LEFT, padx=4, pady=1)
            self.beginning_sustain_off_radio = ttk.Radiobutton(beginning_sustain_frame, text="关闭", variable=self.beginning_sustain_detection_var, value=0)
            self.beginning_sustain_off_radio.pack(side=tk.LEFT, padx=4, pady=1)
            self.beginning_sustain_on_radio = ttk.Radiobutton(beginning_sustain_frame, text="开启", variable=self.beginning_sustain_detection_var, value=1)
            self.beginning_sustain_on_radio.pack(side=tk.LEFT, padx=4, pady=1)
            # 获取当前字体配置，使用相对字体大小
            selected_font = GUI_CONFIG.get("ui_font", "微软雅黑")
            font_size = GUI_CONFIG.get("ui_font_size", 16.0)
            # 使用相对字体大小，比主文本小约20%
            small_font_size = max(6, int(round(font_size * 0.8)))
            font_weight = "bold" if GUI_CONFIG.get("ui_bold", False) else "normal"
            ttk.Label(beginning_sustain_frame, text="(测试功能，不建议开启)", foreground="#808080", font=(selected_font, small_font_size, font_weight)).pack(side=tk.LEFT, padx=4, pady=1)
            
            # 句末延长音开关
            ending_sustain_frame = ttk.Frame(sustain_detection_frame)
            ending_sustain_frame.pack(fill=tk.X, padx=4, pady=1)
            ttk.Label(ending_sustain_frame, text="句末延长音: " ).pack(side=tk.LEFT, padx=4, pady=1)
            self.ending_sustain_off_radio = ttk.Radiobutton(ending_sustain_frame, text="关闭", variable=self.ending_sustain_detection_var, value=0)
            self.ending_sustain_off_radio.pack(side=tk.LEFT, padx=4, pady=1)
            self.ending_sustain_on_radio = ttk.Radiobutton(ending_sustain_frame, text="开启", variable=self.ending_sustain_detection_var, value=1)
            self.ending_sustain_on_radio.pack(side=tk.LEFT, padx=4, pady=1)
            # 获取当前字体配置，使用相对字体大小
            selected_font = GUI_CONFIG.get("ui_font", "微软雅黑")
            font_size = GUI_CONFIG.get("ui_font_size", 16.0)
            # 使用相对字体大小，比主文本小约20%
            small_font_size = max(6, int(round(font_size * 0.8)))
            font_weight = "bold" if GUI_CONFIG.get("ui_bold", False) else "normal"
            ttk.Label(ending_sustain_frame, text="(测试功能，不建议开启)", foreground="#808080", font=(selected_font, small_font_size, font_weight)).pack(side=tk.LEFT, padx=4, pady=1)
            
            # 绑定卡拉OK开关状态变化事件
            self.karaoke_var.trace("w", self.on_karaoke_toggled)
            
            # 绑定拖长音检测开关状态变化事件
            self.beginning_sustain_detection_var.trace("w", self.auto_save_settings)
            self.ending_sustain_detection_var.trace("w", self.auto_save_settings)
            
            # 初始化时根据卡拉OK开关状态设置下方选项的初始状态
            self.on_karaoke_toggled()
            
            # 字体设置 - 右侧
            font_frame = ttk.LabelFrame(horizontal_frame, text="字体设置")
            font_frame.pack(side=tk.RIGHT, padx=4, pady=1, fill=tk.BOTH, expand=True)
            
            # 自定义字体开关
            custom_font_frame = ttk.Frame(font_frame)
            custom_font_frame.pack(fill=tk.X, padx=4, pady=1)
            
            ttk.Label(custom_font_frame, text="自定义字体: " ).pack(side=tk.LEFT, padx=4, pady=1)
            
            self.custom_font_var = tk.IntVar(value=z_config.get("CUSTOM_FONT", 1))
            
            ttk.Radiobutton(custom_font_frame, text="不启用", variable=self.custom_font_var, value=0).pack(side=tk.LEFT, padx=4, pady=1)
            ttk.Radiobutton(custom_font_frame, text="启用", variable=self.custom_font_var, value=1).pack(side=tk.LEFT, padx=4, pady=1)
            
            # 系统自带字体选项
            system_font_frame = ttk.Frame(font_frame)
            system_font_frame.pack(fill=tk.X, padx=4, pady=1)
            
            ttk.Label(system_font_frame, text="系统自带字体: " ).pack(side=tk.LEFT, padx=4, pady=1)
            
            # 常用系统字体列表
            system_fonts_display = ["微软雅黑", "等线", "仿宋", "黑体", "楷体", "新宋体"]
            system_fonts_values = ["Microsoft YaHei", "DengXian", "FangSong", "SimHei", "KaiTi", "NSimSun"]
            # 创建字体映射字典
            self.font_map = dict(zip(system_fonts_display, system_fonts_values))
            # 反向映射
            self.font_map_reverse = dict(zip(system_fonts_values, system_fonts_display))
            
            # 读取默认字体
            default_font_value = c_config.get('simplified_chinese', {}).get('default_font_name', 'Microsoft YaHei')
            # 获取对应的中文显示值
            default_font_display = self.font_map_reverse.get(default_font_value, default_font_value)
            self.default_font_var = tk.StringVar(value=default_font_display)
            
            # 根据CUSTOM_FONT的值决定系统字体选择框的状态
            system_font_combobox_state = "readonly" if self.custom_font_var.get() == 0 else "disabled"
            self.system_font_combobox = ttk.Combobox(system_font_frame, textvariable=self.default_font_var, values=system_fonts_display, width=18, state=system_font_combobox_state, style="Custom.TCombobox")
            
            self.system_font_combobox.pack(side=tk.LEFT, padx=4, pady=1)
            # 获取当前字体配置，使用相对字体大小
            selected_font = GUI_CONFIG.get("ui_font", "微软雅黑")
            font_size = GUI_CONFIG.get("ui_font_size", 16.0)
            # 使用相对字体大小，比主文本小约20%
            small_font_size = max(6, int(round(font_size * 0.8)))
            font_weight = "bold" if GUI_CONFIG.get("ui_bold", False) else "normal"
            
            # 获取TTF目录下的字体文件列表
            def get_font_files():
                ttf_dir = os.path.join(os.path.dirname(__file__), "TTF")
                font_files = []
                if os.path.exists(ttf_dir):
                    for file in os.listdir(ttf_dir):
                        if file.lower().endswith(".ttf"):
                            font_name = os.path.splitext(file)[0]
                            font_files.append(font_name)
                return font_files

            # 创建系统字体状态说明标签
            system_font_label = ttk.Label(system_font_frame, text="(不启用时使用)", foreground="#808080", font=(selected_font, small_font_size, font_weight))
            
            # 根据初始状态决定是否显示系统字体标签
            if self.custom_font_var.get() == 1:
                system_font_label.pack(side=tk.LEFT, padx=4, pady=1)

            # 简体中文字体
            sc_font_frame = ttk.Frame(font_frame)
            sc_font_frame.pack(fill=tk.X, padx=4, pady=1)
            
            ttk.Label(sc_font_frame, text="简体中文字体: " ).pack(side=tk.LEFT, padx=4, pady=1)
            
            # 获取字体列表
            font_list = get_font_files()
            sc_font = c_config.get('simplified_chinese', {}).get('font_name', '方正准圆简体')
            self.sc_font_var = tk.StringVar(value=sc_font)
            
            # 根据CUSTOM_FONT的值决定字体选择框的状态
            sc_combobox_state = "readonly" if self.custom_font_var.get() == 1 else "disabled"
            self.sc_combobox = ttk.Combobox(sc_font_frame, textvariable=self.sc_font_var, values=font_list, width=18, state=sc_combobox_state, style="Custom.TCombobox")
            
            self.sc_combobox.pack(side=tk.LEFT, padx=4, pady=1)
            
            # 添加状态说明
            if self.custom_font_var.get() == 0:
                # 获取当前字体配置，使用相对字体大小
                selected_font = GUI_CONFIG.get("ui_font", "微软雅黑")
                font_size = GUI_CONFIG.get("ui_font_size", 16.0)
                # 使用相对字体大小，比主文本小约20%
                small_font_size = max(6, int(round(font_size * 0.8)))
                font_weight = "bold" if GUI_CONFIG.get("ui_bold", False) else "normal"
                ttk.Label(sc_font_frame, text="(需开启自定义)", foreground="#808080", font=(selected_font, small_font_size, font_weight)).pack(side=tk.LEFT, padx=4, pady=1)
            
            # 日语繁体字体
            jt_font_frame = ttk.Frame(font_frame)
            jt_font_frame.pack(fill=tk.X, padx=4, pady=1)
            
            ttk.Label(jt_font_frame, text="日语繁体字体: " ).pack(side=tk.LEFT, padx=4, pady=1)
            
            jt_font = c_config.get('japanese_traditional', {}).get('font_name', '夏花绚烂前程似锦')
            self.jt_font_var = tk.StringVar(value=jt_font)
            
            # 禁用日语和繁体字体的修改，但使用下拉框保持界面一致性
            # 创建只包含当前字体的列表作为下拉选项
            jt_font_list = [jt_font]
            jt_combobox = ttk.Combobox(jt_font_frame, textvariable=self.jt_font_var, values=jt_font_list, width=18, state="disabled", style="Custom.TCombobox")
            jt_combobox.pack(side=tk.LEFT, padx=4, pady=1)
            # 获取当前字体配置，使用相对字体大小
            selected_font = GUI_CONFIG.get("ui_font", "微软雅黑")
            font_size = GUI_CONFIG.get("ui_font_size", 16.0)
            # 使用相对字体大小，比主文本小约20%
            small_font_size = max(6, int(round(font_size * 0.8)))
            font_weight = "bold" if GUI_CONFIG.get("ui_bold", False) else "normal"
            ttk.Label(jt_font_frame, text="(暂不开放修改)", foreground="#808080", font=(selected_font, small_font_size, font_weight)).pack(side=tk.LEFT, padx=4, pady=1)
            
            # 绑定自定义字体开关的事件
            self.custom_font_var.trace("w", self.on_custom_font_changed)
            
            # 添加自动保存功能
            self.karaoke_var.trace("w", self.auto_save_settings)
            self.real_karaoke_var.trace("w", self.auto_save_settings)
            self.custom_font_var.trace("w", self.auto_save_settings)
            self.sc_font_var.trace("w", self.auto_save_settings)
            self.default_font_var.trace("w", self.auto_save_settings)
            

        
        elif program_name == "Z1.py":
            settings_frame = ttk.LabelFrame(self.right_frame, text="设置选项")
            settings_frame.pack(fill=tk.X, padx=4, pady=2)
            
            # 读取Z1.py的配置
            z1_config = self.read_z1_config()
            
            # 横向排列的设置框架
            horizontal_frame = ttk.Frame(settings_frame)
            horizontal_frame.pack(fill=tk.X, padx=4, pady=2)
            
            # 多音轨多字幕默认属性 - 横向
            mode_frame = ttk.LabelFrame(horizontal_frame, text="多音轨多字幕默认属性")
            mode_frame.pack(side=tk.LEFT, padx=4, pady=2, fill=tk.Y)
            # 设置固定大小 - 减小宽度以适应横向排列
            mode_frame.configure(width=260, height=150)
            mode_frame.pack_propagate(0)  # 禁用自动调整大小
            
            self.default_settings_mode_var = tk.IntVar(value=z1_config.get("DEFAULT_SETTINGS_MODE", 1))
            
            ttk.Radiobutton(mode_frame, text="0: 保持原样", variable=self.default_settings_mode_var, value=0).pack(anchor=tk.W, padx=4, pady=2)
            ttk.Radiobutton(mode_frame, text="1: 默认中文", variable=self.default_settings_mode_var, value=1).pack(anchor=tk.W, padx=4, pady=2)
            
            # 立体声转5.1声道 - 横向
            stereo_frame = ttk.LabelFrame(horizontal_frame, text="立体声转5.1声道")
            stereo_frame.pack(side=tk.LEFT, padx=4, pady=2, fill=tk.Y)
            # 设置固定大小 - 减小宽度以适应横向排列
            stereo_frame.configure(width=260, height=150)
            stereo_frame.pack_propagate(0)  # 禁用自动调整大小
            
            self.stereo_to_5_1_var = tk.IntVar(value=z1_config.get("STEREO_TO_5_1", 0))
            
            ttk.Radiobutton(stereo_frame, text="0: 关闭", variable=self.stereo_to_5_1_var, value=0).pack(anchor=tk.W, padx=4, pady=2)
            ttk.Radiobutton(stereo_frame, text="1: 开启", variable=self.stereo_to_5_1_var, value=1).pack(anchor=tk.W, padx=4, pady=2)
            
            # 字幕处理模式 - 横向
            subtitle_frame = ttk.LabelFrame(horizontal_frame, text="字幕显示效果")
            subtitle_frame.pack(side=tk.LEFT, padx=4, pady=2, fill=tk.Y)
            # 设置固定大小 - 与其他框架保持一致
            subtitle_frame.configure(width=260, height=150)
            subtitle_frame.pack_propagate(0)  # 禁用自动调整大小
            
            # 使用单选按钮实现特殊逻辑：正常单选，点击全选选项进入全选模式
            # 初始化单选按钮变量和全选状态变量
            self.subtitle_mode_var = tk.IntVar(value=z1_config.get("SUBTITLE_MODE", 2))
            self.is_all_selected = False  # 跟踪是否处于全选模式
            
            # 创建单选按钮，添加全选选项
            # 直接在subtitle_frame中排列，不使用额外的行框架
            ttk.Radiobutton(subtitle_frame, text="全选", variable=self.subtitle_mode_var, value=-1, command=lambda: self.on_subtitle_radio_click(-1)).pack(anchor=tk.W, padx=4, pady=2)
            ttk.Radiobutton(subtitle_frame, text="0: 默认效果", variable=self.subtitle_mode_var, value=0, command=lambda: self.on_subtitle_radio_click(0)).pack(anchor=tk.W, padx=4, pady=2)
            ttk.Radiobutton(subtitle_frame, text="1: KTV效果", variable=self.subtitle_mode_var, value=1, command=lambda: self.on_subtitle_radio_click(1)).pack(anchor=tk.W, padx=4, pady=2)
            ttk.Radiobutton(subtitle_frame, text="2: 提词器效果", variable=self.subtitle_mode_var, value=2, command=lambda: self.on_subtitle_radio_click(2)).pack(anchor=tk.W, padx=4, pady=2)
            
            # 添加自动保存功能
            self.default_settings_mode_var.trace("w", lambda *args: self.save_z1_settings())
            self.stereo_to_5_1_var.trace("w", lambda *args: self.save_z1_settings())
            self.subtitle_mode_var.trace("w", lambda *args: self.save_z1_settings())
            
        elif program_name == "D.py":
            settings_frame = ttk.LabelFrame(self.right_frame, text="字体设置选项")
            settings_frame.pack(fill=tk.X, padx=4, pady=2)
            
            # 读取D.py的配置
            d_config = self.read_d_config()
            
            # 字体使用模式设置
            font_mode_frame = ttk.LabelFrame(settings_frame, text="字体使用模式")
            font_mode_frame.pack(fill=tk.X, padx=4, pady=2)
            
            # 使用系统自带字体选项
            use_system_font_frame = ttk.Frame(font_mode_frame)
            use_system_font_frame.pack(fill=tk.X, padx=4, pady=2)
            
            ttk.Label(use_system_font_frame, text="自定义字体: " ).pack(side=tk.LEFT, padx=4, pady=2)
            
            # 当前设置
            use_system_font = d_config.get('use_system_font', 0)
            self.use_system_font_var = tk.IntVar(value=use_system_font)
            
            ttk.Radiobutton(use_system_font_frame, text="不启用", variable=self.use_system_font_var, value=1).pack(side=tk.LEFT, padx=4, pady=2)
            ttk.Radiobutton(use_system_font_frame, text="启用", variable=self.use_system_font_var, value=0).pack(side=tk.LEFT, padx=4, pady=2)
            
            # 字体设置框架
            font_frame = ttk.LabelFrame(settings_frame, text="字体设置")
            font_frame.pack(fill=tk.X, padx=4, pady=2)
            
            # 系统自带字体选择
            system_font_frame = ttk.Frame(font_frame)
            system_font_frame.pack(fill=tk.X, padx=4, pady=2)
            
            ttk.Label(system_font_frame, text="系统自带字体: " ).pack(side=tk.LEFT, padx=4, pady=2)
            
            # 系统字体列表 - 中文显示
            system_fonts_display = ["微软雅黑", "等线", "仿宋", "黑体", "楷体", "新宋体"]
            # 系统字体列表 - 英文存储
            system_fonts_value = ["Microsoft YaHei", "DengXian", "FangSong", "SimHei", "KaiTi", "NSimSun"]
            
            # 当前系统字体
            current_system_font = d_config.get('system_font_name', 'Microsoft YaHei')
            # 找到当前字体在英文列表中的索引，用于在中文列表中显示
            current_font_index = system_fonts_value.index(current_system_font) if current_system_font in system_fonts_value else 0
            self.system_font_display_var = tk.StringVar(value=system_fonts_display[current_font_index])
            # 存储实际的英文字体名称
            self.system_font_var = tk.StringVar(value=current_system_font)
            
            # 创建系统字体下拉菜单
            self.system_font_combobox = ttk.Combobox(
                system_font_frame, 
                textvariable=self.system_font_display_var, 
                values=system_fonts_display,
                state="readonly",
                width=20,
                style="Custom.TCombobox"
            )
            self.system_font_combobox.pack(side=tk.LEFT, padx=4, pady=2)
            
            # 添加系统字体状态说明标签
            # 获取当前字体配置，使用相对字体大小
            selected_font = GUI_CONFIG.get("ui_font", "微软雅黑")
            font_size = GUI_CONFIG.get("ui_font_size", 16.0)
            # 使用相对字体大小，比主文本小约20%
            small_font_size = max(6, int(round(font_size * 0.8)))
            font_weight = "bold" if GUI_CONFIG.get("ui_bold", False) else "normal"
            
            # 创建并显示系统字体标签
            system_font_label = ttk.Label(system_font_frame, text="(不启用时使用)", foreground="#808080", font=(selected_font, small_font_size, font_weight))
            if self.use_system_font_var.get() == 0:  # 自定义字体启用时显示
                system_font_label.pack(side=tk.LEFT, padx=4, pady=2)
            
            # 绑定下拉菜单选择事件，同步更新实际的英文字体名称
            def on_system_font_select(event):
                selected_index = self.system_font_combobox.current()
                if selected_index >= 0:
                    self.system_font_var.set(system_fonts_value[selected_index])
                    self.save_d_settings()
            
            self.system_font_combobox.bind("<<ComboboxSelected>>", on_system_font_select)
            
            # 简体中文字体选择
            sc_font_frame = ttk.Frame(font_frame)
            sc_font_frame.pack(fill=tk.X, padx=4, pady=2)
            
            ttk.Label(sc_font_frame, text="简体中文字体: " ).pack(side=tk.LEFT, padx=4, pady=2)
            
            # 获取可用字体列表
            available_fonts = self.get_available_fonts()
            font_names = [font[0] for font in available_fonts]
            
            # 当前字体
            current_font = d_config['simplified_chinese']['font_name']
            self.sc_font_var = tk.StringVar(value=current_font)
            
            # 创建字体下拉菜单
            self.sc_combobox = ttk.Combobox(
                sc_font_frame, 
                textvariable=self.sc_font_var, 
                values=font_names,
                state="readonly",
                width=20,
                style="Custom.TCombobox"
            )
            self.sc_combobox.pack(side=tk.LEFT, padx=4, pady=2)
            
            # 日语和繁体中文字体（暂不开放修改）
            jt_font_frame = ttk.Frame(font_frame)
            jt_font_frame.pack(fill=tk.X, padx=4, pady=2)
            
            ttk.Label(jt_font_frame, text="日语繁体字体: " ).pack(side=tk.LEFT, padx=4, pady=2)
            
            jt_font = d_config['japanese_traditional']['font_name']
            self.jt_font_var = tk.StringVar(value=jt_font)
            
            # 使用下拉选择框保持界面一致性
            self.jt_combobox = ttk.Combobox(
                jt_font_frame, 
                textvariable=self.jt_font_var, 
                values=[jt_font],  # 只包含当前字体，不可修改
                state="disabled",
                width=20,
                style="Custom.TCombobox"
            )
            self.jt_combobox.pack(side=tk.LEFT, padx=4, pady=2)
            # 获取当前字体配置，使用相对字体大小
            selected_font = GUI_CONFIG.get("ui_font", "微软雅黑")
            font_size = GUI_CONFIG.get("ui_font_size", 16.0)
            # 使用相对字体大小，比主文本小约20%
            small_font_size = max(6, int(round(font_size * 0.8)))
            font_weight = "bold" if GUI_CONFIG.get("ui_bold", False) else "normal"
            ttk.Label(jt_font_frame, text="(暂不开放修改)", foreground="#808080", font=(selected_font, small_font_size, font_weight)).pack(side=tk.LEFT, padx=4, pady=2)
            
            # 初始化字体选择框状态
            if self.use_system_font_var.get() == 1:
                self.sc_combobox.configure(state="disabled")
                self.system_font_combobox.configure(state="readonly")
                # 添加状态说明
                has_label = False
                for widget in sc_font_frame.winfo_children():
                    if isinstance(widget, ttk.Label) and widget.cget("text") == "(需开启自定义)":
                        has_label = True
                        break
                if not has_label:
                    # 获取当前字体配置，使用相对字体大小
                    selected_font = GUI_CONFIG.get("ui_font", "微软雅黑")
                    font_size = GUI_CONFIG.get("ui_font_size", 16.0)
                    # 使用相对字体大小，比主文本小约20%
                    small_font_size = max(6, int(round(font_size * 0.8)))
                    font_weight = "bold" if GUI_CONFIG.get("ui_bold", False) else "normal"
                    ttk.Label(sc_font_frame, text="(需开启自定义)", foreground="#808080", font=(selected_font, small_font_size, font_weight)).pack(side=tk.LEFT, padx=4, pady=2)
            else:
                self.sc_combobox.configure(state="readonly")
                self.system_font_combobox.configure(state="disabled")
                # 移除状态说明
                for widget in sc_font_frame.winfo_children():
                    if isinstance(widget, ttk.Label) and widget.cget("text") == "(需开启自定义)":
                        widget.destroy()
            
            # 添加自动保存功能
            self.sc_font_var.trace("w", lambda *args: self.save_d_settings())
            self.use_system_font_var.trace("w", lambda *args: self.on_d_system_font_changed())
            self.system_font_var.trace("w", lambda *args: self.save_d_settings())
        
        elif program_name == "V.py":
            settings_frame = ttk.LabelFrame(self.right_frame, text="设置选项")
            settings_frame.pack(fill=tk.X, padx=4, pady=2)
            
            # 读取V.py的配置
            v_config = self.read_v_config()
            
            # Z打包功能设置
            z_packaging_frame = ttk.LabelFrame(settings_frame, text="打包功能")
            z_packaging_frame.pack(fill=tk.X, padx=4, pady=2)
            
            # 启用Z打包功能
            z_packaging_enable_frame = ttk.Frame(z_packaging_frame)
            z_packaging_enable_frame.pack(fill=tk.X, padx=4, pady=2)
            
            ttk.Label(z_packaging_enable_frame, text="是否启用打包同名视频文件功能: " ).pack(side=tk.LEFT, padx=4, pady=2)
            
            self.enable_z_packaging_var = tk.IntVar(value=v_config.get("ENABLE_Z_PACKAGING", 1))
            
            ttk.Radiobutton(z_packaging_enable_frame, text="不启用", variable=self.enable_z_packaging_var, value=0).pack(side=tk.LEFT, padx=4, pady=2)
            ttk.Radiobutton(z_packaging_enable_frame, text="启用", variable=self.enable_z_packaging_var, value=1).pack(side=tk.LEFT, padx=4, pady=2)
            
            # 原始歌词文件保存设置
            original_lrc_frame = ttk.LabelFrame(settings_frame, text="原始歌词文件")
            original_lrc_frame.pack(fill=tk.X, padx=4, pady=2)
            
            # 启用保存原始LRC文件
            original_lrc_enable_frame = ttk.Frame(original_lrc_frame)
            original_lrc_enable_frame.pack(fill=tk.X, padx=4, pady=2)
            
            ttk.Label(original_lrc_enable_frame, text="是否保留原始歌词文件: " ).pack(side=tk.LEFT, padx=4, pady=2)
            
            self.save_original_lrc_var = tk.IntVar(value=v_config.get("SAVE_ORIGINAL_LRC", 0))
            
            ttk.Radiobutton(original_lrc_enable_frame, text="不保留", variable=self.save_original_lrc_var, value=0).pack(side=tk.LEFT, padx=4, pady=2)
            ttk.Radiobutton(original_lrc_enable_frame, text="保留", variable=self.save_original_lrc_var, value=1).pack(side=tk.LEFT, padx=4, pady=2)
            
            # 添加自动保存功能
            self.enable_z_packaging_var.trace("w", lambda *args: self.save_v_settings())
            self.save_original_lrc_var.trace("w", lambda *args: self.save_v_settings())
        
        elif program_name == "C.py":
            # 创建子功能按钮区域
            sub_functions_frame = ttk.LabelFrame(self.right_frame, text="子功能选项")
            sub_functions_frame.pack(fill=tk.X, padx=4, pady=2)
            
            # 创建竖向排列的子功能项目
            sub_functions = [
                ("《字幕校对》 - 先选择字幕文件后选择纯人声音频文件", "A.py", "subtitle_proofreading_entry"),
                ("《卡拉OK自动打轴》 - 选择ASS字幕后自动执行", "B.py", "karaoke_timing_entry"),
                ("《卡拉OK转KTV效果》 - 选择ASS字幕后自动执行", "K.py", "karaoke_to_ktv_entry"),
                ("《卡拉OK转提词器效果》 - 选择ASS字幕后自动执行", "T.py", "karaoke_to_prompter_entry")
            ]
            
            # 读取B.py的配置
            b_config = self.read_b_config()
            
            # 为每个子功能创建独立的输入框、选择文件按钮和执行按钮
            for func_name, script_name, entry_name in sub_functions:
                # 创建子功能框架
                func_frame = ttk.LabelFrame(sub_functions_frame, text=func_name)
                func_frame.pack(fill=tk.X, padx=4, pady=2)
                
                # 创建输入框和按钮框架
                input_frame = ttk.Frame(func_frame)
                input_frame.pack(fill=tk.X, padx=4, pady=2)
                
                # 创建输入框
                entry = ttk.Entry(input_frame, width=60)
                entry.pack(side=tk.LEFT, padx=4, pady=2, fill=tk.X, expand=True)
                # 保存输入框引用
                setattr(self, entry_name, entry)
                
                # 为输入框添加拖拽功能
                entry.drop_target_register(DND_FILES)
                entry.dnd_bind("<<Drop>>", lambda e, script=script_name, entry=entry: self.on_sub_function_drop(e, script, entry))
                
                # 创建按钮容器
                button_frame = ttk.Frame(input_frame)
                button_frame.pack(side=tk.RIGHT, padx=4, pady=2)
                
                # 创建选择文件按钮（选择后自动执行）
                browse_btn = ttk.Button(
                    button_frame, 
                    text="选择文件", 
                    command=lambda script=script_name, entry=entry: self.browse_sub_function_file(script, entry)
                )
                browse_btn.pack(side=tk.LEFT, padx=4, pady=2)
                
                # 为卡拉OK自动打轴功能添加延长音检测开关
                if script_name == "B.py":
                    # 创建延长音检测开关框架
                    sustain_frame = ttk.Frame(func_frame)
                    sustain_frame.pack(fill=tk.X, padx=4, pady=2)
                    
                    # 读取B.py中的配置
                    b_config = self.read_b_config()
                    
                    # 句首延长音开关
                    beginning_sustain_frame = ttk.Frame(sustain_frame)
                    beginning_sustain_frame.pack(fill=tk.X, padx=4, pady=1)
                    ttk.Label(beginning_sustain_frame, text="句首延长音: " ).pack(side=tk.LEFT, padx=4, pady=1)
                    self.beginning_sustain_detection_var = tk.IntVar(value=b_config.get("ENABLE_BEGINNING_SUSTAIN_DETECTION", 0))
                    ttk.Radiobutton(beginning_sustain_frame, text="关闭", variable=self.beginning_sustain_detection_var, value=0).pack(side=tk.LEFT, padx=4, pady=1)
                    ttk.Radiobutton(beginning_sustain_frame, text="开启", variable=self.beginning_sustain_detection_var, value=1).pack(side=tk.LEFT, padx=4, pady=1)
                    ttk.Label(beginning_sustain_frame, text="(关闭则只需要ASS文件，开启则需要ASS文件+音频文件)", foreground="#808080").pack(side=tk.LEFT, padx=4, pady=1)
                    
                    # 句末延长音开关
                    ending_sustain_frame = ttk.Frame(sustain_frame)
                    ending_sustain_frame.pack(fill=tk.X, padx=4, pady=1)
                    ttk.Label(ending_sustain_frame, text="句末延长音: " ).pack(side=tk.LEFT, padx=4, pady=1)
                    self.ending_sustain_detection_var = tk.IntVar(value=b_config.get("ENABLE_ENDING_SUSTAIN_DETECTION", 0))
                    ttk.Radiobutton(ending_sustain_frame, text="关闭", variable=self.ending_sustain_detection_var, value=0).pack(side=tk.LEFT, padx=4, pady=1)
                    ttk.Radiobutton(ending_sustain_frame, text="开启", variable=self.ending_sustain_detection_var, value=1).pack(side=tk.LEFT, padx=4, pady=1)
                    ttk.Label(ending_sustain_frame, text="(关闭则只需要ASS文件，开启则需要ASS文件+音频文件)", foreground="#808080").pack(side=tk.LEFT, padx=4, pady=1)
                    
                    # 绑定状态变化事件
                    self.beginning_sustain_detection_var.trace("w", lambda *args: self.save_b_settings())
                    self.ending_sustain_detection_var.trace("w", lambda *args: self.save_b_settings())
            
            # 为A.py(字幕校对)创建音频文件输入框引用（不显示在UI上）
            if "A.py" in [script for _, script, _ in sub_functions]:
                # 创建一个隐藏的音频输入框引用
                # 这样在选择字幕后仍然可以自动弹出音频文件选择对话框
                # 但不在UI上显示音频输入框
                class HiddenEntry:
                    def __init__(self):
                        self.value = ""
                    def delete(self, *args):
                        self.value = ""
                    def insert(self, *args):
                        # 使用最后一个参数作为value值
                        if args:
                            self.value = args[-1]
                    def get(self):
                        return self.value
                
                # 保存隐藏的音频输入框引用
                setattr(self, "subtitle_proofreading_audio_entry", HiddenEntry())
        
        elif program_name == "M.py":
            settings_frame = ttk.LabelFrame(self.right_frame, text="设置选项")
            settings_frame.pack(fill=tk.X, padx=4, pady=2)
            
            # 读取M.py的配置
            m_config = self.read_m_config()
            
            # 输出格式设置
            output_format_frame = ttk.LabelFrame(settings_frame, text="输出格式设置")
            output_format_frame.pack(fill=tk.X, padx=4, pady=2)
            
            # 输出格式选择
            output_format_select_frame = ttk.Frame(output_format_frame)
            output_format_select_frame.pack(fill=tk.X, padx=4, pady=2)
            
            ttk.Label(output_format_select_frame, text="输出格式: " ).pack(side=tk.LEFT, padx=4, pady=2)
            
            # 输出格式配置
            OUTPUT_FORMAT_CONFIGS = [
                (1, "ac3", "AC3 (有损压缩)"),
                (2, "wav", "WAV (无损格式)")
            ]
            
            # 获取当前输出格式
            current_format_id = m_config.get("DEFAULT_OUTPUT_FORMAT_ID", 1)
            self.default_output_format_id_var = tk.IntVar(value=current_format_id)
            
            # 创建输出格式选择下拉菜单
            output_format_values = [config[2] for config in OUTPUT_FORMAT_CONFIGS]
            output_format_ids = [config[0] for config in OUTPUT_FORMAT_CONFIGS]
            
            # 创建一个从格式名称到ID的映射
            format_name_to_id = {config[2]: config[0] for config in OUTPUT_FORMAT_CONFIGS}
            format_id_to_name = {config[0]: config[2] for config in OUTPUT_FORMAT_CONFIGS}
            
            # 获取当前格式的显示名称
            current_format_name = format_id_to_name.get(current_format_id, output_format_values[0])
            self.output_format_var = tk.StringVar(value=current_format_name)
            
            # 创建下拉菜单
            self.output_format_combobox = ttk.Combobox(
                output_format_select_frame, 
                textvariable=self.output_format_var, 
                values=output_format_values,
                state="readonly",
                width=20,
                style="Custom.TCombobox"
            )
            self.output_format_combobox.pack(side=tk.LEFT, padx=4, pady=2)
            
            # 添加自动保存功能
            def on_output_format_changed(*args):
                # 获取选择的格式名称
                selected_format_name = self.output_format_var.get()
                # 获取对应的格式ID
                selected_format_id = format_name_to_id.get(selected_format_name, 1)
                # 更新格式ID变量
                self.default_output_format_id_var.set(selected_format_id)
                # 保存设置
                self.save_m_settings()
            
            self.output_format_var.trace("w", on_output_format_changed)
        
        elif program_name == "x.py":
            settings_frame = ttk.LabelFrame(self.right_frame, text="设置选项")
            settings_frame.pack(fill=tk.X, padx=4, pady=2)
            
            # 读取x.py的配置
            x_config = self.read_x_config()
            
            # 输出模式设置
            output_mode_frame = ttk.LabelFrame(settings_frame, text="输出模式设置")
            output_mode_frame.pack(fill=tk.X, padx=4, pady=2)
            
            # 输出模式选择
            output_mode_select_frame = ttk.Frame(output_mode_frame)
            output_mode_select_frame.pack(fill=tk.X, padx=4, pady=2)
            
            ttk.Label(output_mode_select_frame, text="输出模式: " ).pack(side=tk.LEFT, padx=4, pady=2)
            
            # 输出模式配置
            OUTPUT_MODE_CONFIGS = [
                (1, "vocals", "仅人声"),
                (2, "accompaniment", "仅伴奏"),
                (3, "both", "人声和伴奏"),
                (4, "all", "全部分离 (人声、鼓、贝斯、其他)")
            ]
            
            # 获取当前输出模式
            current_output_mode_id = x_config.get("DEFAULT_OUTPUT_MODE_ID", 1)
            self.default_output_mode_id_var = tk.IntVar(value=current_output_mode_id)
            
            # 创建输出模式选择下拉菜单
            output_mode_values = [config[2] for config in OUTPUT_MODE_CONFIGS]
            output_mode_ids = [config[0] for config in OUTPUT_MODE_CONFIGS]
            
            # 创建一个从模式名称到ID的映射
            mode_name_to_id = {config[2]: config[0] for config in OUTPUT_MODE_CONFIGS}
            mode_id_to_name = {config[0]: config[2] for config in OUTPUT_MODE_CONFIGS}
            
            # 获取当前模式的显示名称
            current_mode_name = mode_id_to_name.get(current_output_mode_id, output_mode_values[0])
            self.output_mode_var = tk.StringVar(value=current_mode_name)
            
            # 创建下拉菜单
            self.output_mode_combobox = ttk.Combobox(
                output_mode_select_frame, 
                textvariable=self.output_mode_var, 
                values=output_mode_values,
                state="readonly",
                width=30,
                style="Custom.TCombobox"
            )
            self.output_mode_combobox.pack(side=tk.LEFT, padx=4, pady=2)
            
            # 添加自动保存功能
            def on_output_mode_changed(*args):
                # 获取选择的模式名称
                selected_mode_name = self.output_mode_var.get()
                # 获取对应的模式ID
                selected_mode_id = mode_name_to_id.get(selected_mode_name, 1)
                # 更新模式ID变量
                self.default_output_mode_id_var.set(selected_mode_id)
                # 保存设置
                self.save_x_settings()
            
            self.output_mode_var.trace("w", on_output_mode_changed)
        
        # 创建输出显示区域 - 放到最下面
        output_frame = ttk.LabelFrame(self.right_frame, text="程序输出")
        output_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)
        
        # 创建滚动条和文本框
        scrollbar = ttk.Scrollbar(output_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 为文本框设置暗黑主题样式和字体
        selected_font = GUI_CONFIG.get("ui_font", "微软雅黑")
        font_size = GUI_CONFIG.get("ui_font_size", 16.0)
        font_weight = "bold" if GUI_CONFIG.get("ui_bold", False) else "normal"
        # 日志文本使用90%的全局字体大小
        font_size_int = int(round(font_size * 0.9))
        
        self.output_text = tk.Text(
            output_frame, 
            wrap=tk.WORD, 
            yscrollcommand=scrollbar.set, 
            height=18,
            bg=self.bg_color,
            fg=self.fg_color,
            insertbackground=self.fg_color,
            selectbackground=self.accent_color,
            selectforeground="#ffffff",
            borderwidth=1,
            relief="solid",
            highlightbackground=self.border_color,
            highlightcolor=self.accent_color,
            font=(selected_font, font_size_int, font_weight)
        )
        # 添加拖放功能
        # 启用拖放
        self.output_text.bind("<Enter>", self.on_enter)
        self.output_text.bind("<Leave>", self.on_leave)
        # 绑定粘贴事件，支持从剪贴板粘贴文件路径
        self.output_text.bind("<Control-v>", self.on_paste)
        
        # 只对非C.py的功能启用日志页的拖拽功能
        if program_name != "C.py":
            # 启用文件拖放功能
            # 使用tkinterdnd2为日志栏添加拖放支持
            self.output_text.drop_target_register(DND_FILES)
            self.output_text.dnd_bind("<<Drop>>", self.on_drop)
            # 对于Windows系统，使用正确的拖放实现
            if sys.platform == 'win32':
                try:
                    # 使用tkinterdnd2库的替代方案
                    # 启用窗口接受文件
                    self.root.bind('<Button-1>', self.on_root_click)
                except:
                    pass
        
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)
        scrollbar.config(command=self.output_text.yview)
        
        # 在输出框中显示功能说明
        for line in current_program['description']:
            self.output_text.insert(tk.END, line + "\n")
        
        # 初始化进程为None
        self.process = None
        
        # 高亮对应的功能按钮
        for i, btn in enumerate(self.buttons):
            if i < len(list(program_info.keys())) and list(program_info.keys())[i] == program_name:
                self.highlight_button(btn)
                break
    
    def browse_files(self):
        """打开文件选择对话框，支持选择单个文件"""
        # 打开文件选择对话框
        file_path = filedialog.askopenfilename(
            title="选择文件",
            filetypes=[
                ("所有文件", "*.*"),
                ("字幕文件", "*.srt *.ass *.ssa"),
                ("视频文件", "*.mp4 *.mkv *.avi *.mov"),
                ("Python文件", "*.py")
            ],
            initialdir="",
            defaultextension=""
        )
        
        if file_path:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, file_path)
            
            # 检查当前是否为字幕文件独立修改功能
            current_program = None
            for i, btn in enumerate(self.buttons):
                if btn.cget("style") == "Highlight.TButton":
                    if i == 3:  # 字幕文件独立修改是第4个功能
                        current_program = "C.py"
                        break
            
            # 如果是字幕文件独立修改功能，自动执行所有子功能
            if current_program == "C.py":
                self.output_text.insert(tk.END, f"\n文件选择: {file_path}\n")
                self.output_text.insert(tk.END, "开始自动执行子功能...\n")
                self.output_text.see(tk.END)
                
                # 自动执行所有子功能
                self.run_all_sub_functions(file_path)
    
    def browse_folder(self):
        """打开文件夹选择对话框，支持选择文件夹"""
        # 打开文件夹选择对话框
        folder_path = filedialog.askdirectory(
            title="选择文件夹",
            initialdir=""
        )
        
        if folder_path:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, folder_path)
            
            # 检查当前是否为字幕文件独立修改功能
            current_program = None
            for i, btn in enumerate(self.buttons):
                if btn.cget("style") == "Highlight.TButton":
                    if i == 3:  # 字幕文件独立修改是第4个功能
                        current_program = "C.py"
                        break
            
            # 如果是字幕文件独立修改功能，自动执行所有子功能
            if current_program == "C.py":
                self.output_text.insert(tk.END, f"\n文件夹选择: {folder_path}\n")
                self.output_text.insert(tk.END, "开始自动执行子功能...\n")
                self.output_text.see(tk.END)
                
                # 自动执行所有子功能
                self.run_all_sub_functions(folder_path)
    
    def toggle_execute(self, program_path, current_dir):
        """切换执行/停止状态，共用一个按钮"""
        if self.process is None:
            # 当前没有运行中的进程，执行程序
            self.execute_program(program_path, current_dir)
        else:
            # 当前有运行中的进程，停止程序
            self.stop_program()
    
    def execute_program(self, program_path, current_dir):
        """执行程序并传递输入参数"""
        # 获取用户输入的文件路径
        input_path = self.input_entry.get().strip()
        
        if not input_path:
            self.output_text.insert(tk.END, "请输入文件路径！\n")
            return
        
        # 开始任务前清除日志
        self.clear_output()
        
        self.output_text.insert(tk.END, f"正在执行: {os.path.basename(program_path)}\n")
        self.output_text.insert(tk.END, f"输入路径: {input_path}\n\n")
        
        # 启动程序并传递输入参数
        threading.Thread(
            target=self._run_program_with_input, 
            args=(program_path, current_dir, input_path), 
            daemon=True
        ).start()
        
        # 更改按钮文本为"停止处理"
        self.execute_stop_btn.configure(text="停止处理")
    
    def _run_program_with_input(self, program_path, current_dir, input_path):
        """运行指定的程序并传递输入参数，模拟批处理脚本的运行方式"""
        try:
            import os
            import subprocess
            import time
            import queue
            import threading
            
            # 清理输入路径，移除可能的引号和空格
            input_path = input_path.strip().strip('"').strip("'")
            
            # 验证输入路径是否存在
            if not input_path:
                self.output_text.insert(tk.END, f"\n错误: 路径不能为空\n")
                if hasattr(self, 'execute_stop_btn'):
                    self.root.after(0, self.safe_configure_execute_stop_btn)
                return
            
            # 处理包含"|"分隔符的特殊格式（ASS文件路径|音频文件路径）
            if "|" in input_path:
                ass_path = input_path.split("|", 1)[0]
                if not os.path.exists(ass_path):
                    self.output_text.insert(tk.END, f"\n错误: ASS文件路径不存在 - {ass_path}\n")
                    if hasattr(self, 'execute_stop_btn'):
                        self.root.after(0, self.safe_configure_execute_stop_btn)
                    return
            else:
                # 普通路径格式
                if not os.path.exists(input_path):
                    self.output_text.insert(tk.END, f"\n错误: 路径不存在 - {input_path}\n")
                    if hasattr(self, 'execute_stop_btn'):
                        self.root.after(0, self.safe_configure_execute_stop_btn)
                    return
            
            # 模拟批处理脚本的运行方式
            # 1. 设置环境变量
            original_path = os.environ.get('PATH', '')
            new_path = f"{os.path.join(current_dir, '..', 'Python')};{os.path.join(current_dir, '..', 'Python', 'Scripts')};{os.path.join(current_dir, '..', 'Python', 'ffmpeg')};{os.path.join(current_dir, '..', 'Python', 'MKVToolNix')};{original_path}"
            
            # 2. 使用项目的Python环境
            python_exe = os.path.join(current_dir, "..", "Python", "python.exe")
            
            # 3. 构建命令行参数
            cmd = None
            if os.path.basename(program_path) == "A.py":
                # 对于A.py，使用命令行参数模式
                # 优先使用用户手动选择的音频文件
                audio_path = ""
                if hasattr(self, "subtitle_proofreading_audio_entry"):
                    audio_entry = getattr(self, "subtitle_proofreading_audio_entry")
                    audio_path = audio_entry.get().strip()
                
                # 如果用户没有选择音频文件，尝试自动生成
                if not audio_path:
                    base_name = os.path.splitext(input_path)[0]
                    audio_path = base_name + '.wav'
                    
                    # 尝试其他音频格式
                    if not os.path.exists(audio_path):
                        audio_extensions = ['.mp3', '.m4a', '.flac', '.ogg']
                        found = False
                        for ext in audio_extensions:
                            test_path = base_name + ext
                            if os.path.exists(test_path):
                                audio_path = test_path
                                found = True
                                break
                        
                        if not found:
                            self.output_text.insert(tk.END, "\n错误: 未找到对应的音频文件\n")
                            if hasattr(self, 'execute_stop_btn'):
                                self.root.after(0, self.safe_configure_execute_stop_btn)
                            return
                
                # 生成输出文件路径
                base_name = os.path.splitext(input_path)[0]
                output_path = base_name + '_校准后.ass'
                
                # 使用命令行参数模式
                cmd = [python_exe, "-s", program_path, "-a", audio_path, "-s", input_path, "-o", output_path, "--debug"]
                self.output_text.insert(tk.END, f"\n使用命令行模式执行A.py\n")
                self.output_text.insert(tk.END, f"音频文件: {audio_path}\n")
                self.output_text.insert(tk.END, f"字幕文件: {input_path}\n")
                self.output_text.insert(tk.END, f"输出文件: {output_path}\n\n")
            elif os.path.basename(program_path) == "B.py":
                # 对于B.py，使用命令行参数模式
                # 处理包含"|"分隔符的输入路径
                ass_path = input_path
                if "|" in input_path:
                    ass_path = input_path.split("|", 1)[0]
                
                # 生成输出文件路径
                base_name = os.path.splitext(ass_path)[0]
                output_path = base_name + '_自动打轴.ass'
                
                # 使用命令行参数模式
                cmd = [python_exe, "-s", program_path, "--input", input_path, "--output", output_path]
                self.output_text.insert(tk.END, f"\n使用命令行模式执行B.py\n")
                self.output_text.insert(tk.END, f"输入文件: {input_path}\n")
                self.output_text.insert(tk.END, f"输出文件: {output_path}\n\n")
            elif os.path.basename(program_path) in ["Z1.py", "Z.py"]:
                # 对于Z1.py和Z.py，支持将多个字幕模式打包到一个文件
                is_all_selected = False
                current_mode = None
                
                # 检查是否处于全选模式
                if os.path.basename(program_path) == "Z1.py":
                    if hasattr(self, 'is_all_selected') and self.is_all_selected:
                        is_all_selected = True
                    elif hasattr(self, 'subtitle_mode_var'):
                        current_mode = self.subtitle_mode_var.get()
                    else:
                        # 兼容旧模式，默认使用模式2
                        current_mode = 2
                else:  # Z.py
                    # 检查两种可能的全选变量
                    if (hasattr(self, 'z_all_selected') and self.z_all_selected) or (hasattr(self, 'is_all_selected') and self.is_all_selected):
                        is_all_selected = True
                    elif hasattr(self, 'real_karaoke_var'):
                        current_mode = self.real_karaoke_var.get()
                    else:
                        # 兼容旧模式，默认使用模式0
                        current_mode = 0
                
                if is_all_selected:
                    # 全选模式，使用A模式
                    self.output_text.insert(tk.END, f"\n字幕处理模式: A（全部效果打包）")
                    self.output_text.see(tk.END)
                    subtitle_mode = "A"
                else:
                    # 单选模式，使用当前选择的模式
                    self.output_text.insert(tk.END, f"\n字幕处理模式: {current_mode}")
                    self.output_text.see(tk.END)
                    subtitle_mode = str(current_mode)
                
                # 构建命令行参数，传递subtitle-mode
                cmd = [python_exe, "-s", program_path, "--subtitle-mode", subtitle_mode, input_path]
            else:
                # 对于其他脚本，使用常规模式
                cmd = [python_exe, "-s", program_path, input_path]
            
            # 4. 运行程序，不使用stdin交互
            # 设置子进程的环境变量，禁用缓冲
            env = {**os.environ, 'PATH': new_path, 'PYTHONUNBUFFERED': '1'}
            
            self.process = subprocess.Popen(
                cmd, 
                cwd=os.path.join(current_dir, ".."),  # 使用项目根目录作为工作目录
                stdin=subprocess.DEVNULL,  # 不使用stdin
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',  # 使用UTF-8编码，适配Python默认输出编码
                errors='replace',  # 替换编码错误，避免乱码
                bufsize=0,  # 无缓冲，实时输出
                env=env  # 设置环境变量
            )
            
            # 5. 读取并显示输出
            # 创建一个队列来存储输出行
            output_queue = queue.Queue()
            
            # 定义一个函数来读取输出
            def read_output():
                while self.process is not None:
                    try:
                        # 非阻塞读取，使用较小的缓冲区
                        line = self.process.stdout.readline()
                        if not line:
                            break
                        output_queue.put(line)
                    except:
                        break
                
                # 读取剩余的输出
                if self.process is not None:
                    try:
                        while True:
                            line = self.process.stdout.readline()
                            if not line:
                                break
                            output_queue.put(line)
                    except:
                        pass
            
            # 启动读取线程
            read_thread = threading.Thread(target=read_output, daemon=True)
            read_thread.start()
            
            # 处理输出的循环
            while True:
                # 检查进程是否为None（用户可能点击了停止按钮）
                if self.process is None:
                    break
                
                # 检查进程是否已经结束且读取线程已完成
                if self.process.poll() is not None and not read_thread.is_alive():
                    # 处理队列中剩余的所有输出
                    while not output_queue.empty():
                        line = output_queue.get()
                        if 'Progress: ' not in line and 'Extracting track' not in line:
                            def update_gui_final(line=line):
                                self.output_text.insert(tk.END, line)
                                self.output_text.see(tk.END)
                            self.root.after(0, update_gui_final)
                    break
                
                # 处理队列中的输出
                while not output_queue.empty():
                    line = output_queue.get()
                    if 'Progress: ' not in line and 'Extracting track' not in line:
                        def update_gui(line=line):
                            self.output_text.insert(tk.END, line)
                            self.output_text.see(tk.END)
                        self.root.after(0, update_gui)
                
                # 短暂休眠，避免CPU占用过高
                time.sleep(0.01)
            
        except Exception as e:
            # 发生异常时，清理进程
            if hasattr(self, 'process') and self.process is not None:
                self.process = None
            # 显示错误信息
            self.output_text.insert(tk.END, f"\n启动失败: {str(e)}\n")
            # 提供更详细的错误信息
            self.output_text.insert(tk.END, f"\n错误详情: {repr(e)}\n")
            self.output_text.insert(tk.END, f"\n输入路径: {input_path}\n")
            self.output_text.insert(tk.END, f"\n程序路径: {program_path}\n")
            self.output_text.see(tk.END)  # 自动滚动到最新内容
        finally:
            # 确保资源被释放
            if self.process:
                try:
                    self.process.stdout.close()
                except:
                    pass
            self.process = None
            # 程序执行完成后，将按钮文本改回"执行"
            if hasattr(self, 'execute_stop_btn'):
                self.root.after(0, self.safe_configure_execute_stop_btn)

    
    def _run_program(self, program_path, current_dir):
        """在后台线程中运行程序（旧版本，保留用于兼容）"""
        # 调用新版本方法，传入空的输入路径
        self._run_program_with_input(program_path, current_dir, "")
    
    def stop_program(self):
        """停止当前运行的程序"""
        if self.process:
            try:
                self.process.terminate()
                self.output_text.insert(tk.END, "\n程序已停止\n")
                self.output_text.see(tk.END)  # 自动滚动到最新内容
            except Exception as e:
                self.output_text.insert(tk.END, f"\n停止程序失败: {str(e)}\n")
                self.output_text.see(tk.END)  # 自动滚动到最新内容
            finally:
                self.process = None
                # 程序停止后，将按钮文本改回"执行"
                try:
                    if hasattr(self, 'execute_stop_btn'):
                        self.execute_stop_btn.configure(text="开始处理")
                except Exception:
                    # 部件已销毁，忽略错误
                    pass
    
    def safe_configure_execute_stop_btn(self):
        """安全地配置执行/停止按钮，忽略部件已销毁的情况"""
        try:
            if hasattr(self, 'execute_stop_btn'):
                self.execute_stop_btn.configure(text="开始处理")
        except Exception:
            # 部件已销毁，忽略错误
            pass
    
    def create_settings_frame(self, program_name):
        """创建设置区域，显示字幕式样和字体配置选项"""
        # 只有字幕打包程序需要显示设置
        if program_name != "Z.py":
            return
        
        # 创建设置框架
        settings_frame = ttk.LabelFrame(self.right_frame, text="设置选项")
        settings_frame.pack(fill=tk.X, padx=4, pady=10, side=tk.BOTTOM)
        
        # 读取z.py文件中的配置
        z_config = self.read_z_config()
        c_config = self.read_c_config()
        
        # 字幕式样设置
        style_frame = ttk.LabelFrame(settings_frame, text="字幕式样")
        style_frame.pack(fill=tk.X, padx=4, pady=2)
        
        # 卡拉OK效果
        karaoke_frame = ttk.Frame(style_frame)
        karaoke_frame.pack(fill=tk.X, padx=4, pady=2)
        
        ttk.Label(karaoke_frame, text="卡拉OK开关: ").pack(side=tk.LEFT, padx=4, pady=2)
        
        # 卡拉OK效果选项
        self.karaoke_var = tk.IntVar(value=z_config.get("KARAOKE_EFFECT", 1))
        
        ttk.Radiobutton(karaoke_frame, text="不启用", variable=self.karaoke_var, value=0).pack(side=tk.LEFT, padx=4, pady=2)
        ttk.Radiobutton(karaoke_frame, text="启用", variable=self.karaoke_var, value=1).pack(side=tk.LEFT, padx=4, pady=2)
        
        # 真实卡拉OK效果
        real_karaoke_frame = ttk.Frame(style_frame)
        real_karaoke_frame.pack(fill=tk.X, padx=4, pady=2)
        
        ttk.Label(real_karaoke_frame, text="卡拉OK效果: ").pack(side=tk.LEFT, padx=4, pady=2)
        
        # 真实卡拉OK效果选项，纯单选逻辑
        real_effect = z_config.get("REAL_KARAOKE_EFFECT", 0)
        # 初始化变量 - 如果是'A'（全选），转换为全选选项值-1
        # 确保传递给IntVar的是整数
        if real_effect == 'A':
            real_karaoke_var_value = -1
        else:
            # 确保real_effect是整数，支持负数值
            real_karaoke_var_value = int(real_effect) if isinstance(real_effect, str) and (real_effect.isdigit() or real_effect == '-1') else real_effect
        self.real_karaoke_var = tk.IntVar(value=real_karaoke_var_value)
        self.z_all_selected = False  # 取消全选模式
        
        # 创建单选按钮
        self.z_all_radio = ttk.Radiobutton(real_karaoke_frame, text="全选", variable=self.real_karaoke_var, value=-1, command=lambda: self.on_z_radio_click(-1))
        self.z_radio0 = ttk.Radiobutton(real_karaoke_frame, text="默认", variable=self.real_karaoke_var, value=0, command=lambda: self.on_z_radio_click(0))
        self.z_radio1 = ttk.Radiobutton(real_karaoke_frame, text="真实卡拉OK", variable=self.real_karaoke_var, value=1, command=lambda: self.on_z_radio_click(1))
        self.z_radio2 = ttk.Radiobutton(real_karaoke_frame, text="提词器", variable=self.real_karaoke_var, value=2, command=lambda: self.on_z_radio_click(2))
        
        # 打包单选按钮
        self.z_all_radio.pack(side=tk.LEFT, padx=4, pady=2)
        self.z_radio0.pack(side=tk.LEFT, padx=4, pady=2)
        self.z_radio1.pack(side=tk.LEFT, padx=4, pady=2)
        self.z_radio2.pack(side=tk.LEFT, padx=4, pady=2)
        
        # 设置按钮状态 - 纯粹单选，只高亮当前选项
        # 重置所有选项状态
        for radio in [self.z_all_radio, self.z_radio0, self.z_radio1, self.z_radio2]:
            radio.state(['!selected'])
        
        # 高亮当前选中的选项
        if self.real_karaoke_var.get() == -1:
            # 如果是全选选项，高亮全选按钮
            self.z_all_radio.state(['selected'])
        else:
            # 否则高亮对应的效果选项
            for radio in [self.z_radio0, self.z_radio1, self.z_radio2]:
                if int(radio.cget('value')) == self.real_karaoke_var.get():
                    radio.state(['selected'])
        
        # 字体设置
        font_frame = ttk.LabelFrame(settings_frame, text="字体设置")
        font_frame.pack(fill=tk.X, padx=4, pady=2)
        
        # 简体中文字体
        sc_font_frame = ttk.Frame(font_frame)
        sc_font_frame.pack(fill=tk.X, padx=4, pady=2)
        
        ttk.Label(sc_font_frame, text="简体中文字体: ").pack(side=tk.LEFT, padx=4, pady=2)
        
        sc_font = c_config.get('simplified_chinese', {}).get('font_name', '方正准圆简体')
        self.sc_font_var = tk.StringVar(value=sc_font)
        
        sc_entry = ttk.Entry(sc_font_frame, textvariable=self.sc_font_var, width=20)
        sc_entry.pack(side=tk.LEFT, padx=4, pady=2)
        
        # 日语和繁体中文字体
        jt_font_frame = ttk.Frame(font_frame)
        jt_font_frame.pack(fill=tk.X, padx=4, pady=2)
        
        ttk.Label(jt_font_frame, text="日语繁体字体: ").pack(side=tk.LEFT, padx=4, pady=2)
        
        jt_font = c_config.get('japanese_traditional', {}).get('font_name', '夏花绚烂前程似锦')
        self.jt_font_var = tk.StringVar(value=jt_font)
        
        jt_entry = ttk.Entry(jt_font_frame, textvariable=self.jt_font_var, width=20)
        jt_entry.pack(side=tk.LEFT, padx=4, pady=2)
        
        # 保存设置按钮
        save_btn = ttk.Button(settings_frame, text="保存设置", command=self.save_settings)
        save_btn.pack(padx=4, pady=2, side=tk.RIGHT)
    
    def read_z_config(self):
        """读取z.py文件中的配置"""
        config = {}
        try:
            with open(os.path.join(os.path.dirname(__file__), "Z.py"), "r", encoding="utf-8") as f:
                content = f.read()
                
            # 解析KARAOKE_EFFECT
            match = re.search(r'KARAOKE_EFFECT\s*=\s*(\d+)', content)
            if match:
                config["KARAOKE_EFFECT"] = int(match.group(1))
            
            # 解析REAL_KARAOKE_EFFECT，支持数字、负数和'A'（全选模式），考虑注释
            match = re.search(r'REAL_KARAOKE_EFFECT\s*=\s*(-?\d+|\'A\')', content)
            if match:
                value = match.group(1)
                if value == "'A'":
                    config["REAL_KARAOKE_EFFECT"] = 'A'
                else:
                    config["REAL_KARAOKE_EFFECT"] = int(value)
            
            # 解析CUSTOM_FONT
            match = re.search(r'CUSTOM_FONT\s*=\s*(\d+)', content)
            if match:
                config["CUSTOM_FONT"] = int(match.group(1))
                
        except Exception as e:
            print(f"读取z.py配置失败: {e}")
        
        return config
    
    def read_c_config(self):
        """读取C.py文件中的字体配置"""
        config = {
            'simplified_chinese': {
                'font_name': '方正准圆简体',
                'font_file': '方正准圆简体.ttf',
                'default_font_name': 'Microsoft YaHei'
            },
            'japanese_traditional': {
                'font_name': '夏花绚烂前程似锦',
                'font_file': '夏花绚烂前程似锦.ttf',
                'default_font_name': 'Microsoft YaHei'
            }
        }
        
        try:
            # 更可靠的方式：直接执行整个文件，获取FONT_CONFIG变量
            c_file_path = os.path.join(os.path.dirname(__file__), "C.py")
            
            # 创建一个临时模块，执行C.py文件
            import importlib.util
            spec = importlib.util.spec_from_file_location("c_config", c_file_path)
            c_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(c_module)
            
            # 获取FONT_CONFIG变量
            config = getattr(c_module, "FONT_CONFIG", config)
            
        except Exception as e:
            print(f"读取C.py配置失败: {e}")
            # 使用默认配置
        
        return config
    
    def read_b_config(self):
        """读取B.py的配置"""
        b_path = os.path.join(os.path.dirname(__file__), "B.py")
        config = {
            "ENABLE_BEGINNING_SUSTAIN_DETECTION": 0,
            "ENABLE_ENDING_SUSTAIN_DETECTION": 0
        }
        
        try:
            with open(b_path, "r", encoding="utf-8") as f:
                content = f.read()
                
                # 提取ENABLE_BEGINNING_SUSTAIN_DETECTION
                match = re.search(r'ENABLE_BEGINNING_SUSTAIN_DETECTION\s*=\s*(\d+)', content)
                if match:
                    config["ENABLE_BEGINNING_SUSTAIN_DETECTION"] = int(match.group(1))
                else:
                    config["ENABLE_BEGINNING_SUSTAIN_DETECTION"] = 0
                    
                # 提取ENABLE_ENDING_SUSTAIN_DETECTION
                match = re.search(r'ENABLE_ENDING_SUSTAIN_DETECTION\s*=\s*(\d+)', content)
                if match:
                    config["ENABLE_ENDING_SUSTAIN_DETECTION"] = int(match.group(1))
                else:
                    config["ENABLE_ENDING_SUSTAIN_DETECTION"] = 0
                    
        except Exception as e:
            print(f"读取B.py配置失败: {e}")
            config = {
                "ENABLE_BEGINNING_SUSTAIN_DETECTION": 0,
                "ENABLE_ENDING_SUSTAIN_DETECTION": 0
            }
        
        return config
    
    def save_b_settings(self):
        """保存B.py的设置"""
        b_path = os.path.join(os.path.dirname(__file__), "B.py")
        
        try:
            with open(b_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 更新ENABLE_BEGINNING_SUSTAIN_DETECTION
            if hasattr(self, 'beginning_sustain_detection_var'):
                mode = self.beginning_sustain_detection_var.get()
                content = re.sub(r'ENABLE_BEGINNING_SUSTAIN_DETECTION\s*=\s*\d+', f'ENABLE_BEGINNING_SUSTAIN_DETECTION = {mode}', content)
            
            # 更新ENABLE_ENDING_SUSTAIN_DETECTION
            if hasattr(self, 'ending_sustain_detection_var'):
                mode = self.ending_sustain_detection_var.get()
                content = re.sub(r'ENABLE_ENDING_SUSTAIN_DETECTION\s*=\s*\d+', f'ENABLE_ENDING_SUSTAIN_DETECTION = {mode}', content)
            
            with open(b_path, "w", encoding="utf-8") as f:
                f.write(content)
                
        except Exception as e:
            print(f"保存B.py设置失败: {e}")
    
    def save_settings(self):
        """保存设置到相应的配置文件"""
        try:
            # 保存字幕式样设置到z.py
            self.save_z_settings()
            
            # 保存字体设置到C.py
            self.save_c_settings()
            
            # 保存拖长音检测设置到B.py
            self.save_b_settings()
            
            # 显示保存成功信息
            self.output_text.insert(tk.END, "\n设置已保存！\n")
            self.output_text.see(tk.END)
            
        except Exception as e:
            self.output_text.insert(tk.END, f"\n保存设置失败: {str(e)}\n")
            self.output_text.see(tk.END)
    
    def on_custom_font_changed(self, *args):
        """自定义字体开关状态变化时的处理逻辑"""
        # 根据CUSTOM_FONT的值更新字体选择框的状态
        if self.custom_font_var.get() == 1:
            # 开启自定义字体
            self.sc_combobox.configure(state="readonly")  # 启用自定义字体选择
            self.system_font_combobox.configure(state="disabled")  # 禁用系统字体选择
            
            # 隐藏自定义字体的提示标签
            for widget in self.sc_combobox.master.winfo_children():
                if isinstance(widget, ttk.Label) and widget.cget("text") == "(需开启自定义)":
                    widget.pack_forget()
            
            # 显示系统字体的提示标签
            system_label_found = False
            for widget in self.system_font_combobox.master.winfo_children():
                if isinstance(widget, ttk.Label) and widget.cget("text") == "(不启用时使用)":
                    widget.pack(side=tk.LEFT, padx=4, pady=1)
                    system_label_found = True
                    break
            if not system_label_found:
                # 如果标签不存在，创建并显示
                selected_font = GUI_CONFIG.get("ui_font", "微软雅黑")
                font_size = GUI_CONFIG.get("ui_font_size", 16.0)
                small_font_size = max(6, int(round(font_size * 0.8)))
                font_weight = "bold" if GUI_CONFIG.get("ui_bold", False) else "normal"
                ttk.Label(self.system_font_combobox.master, text="(不启用时使用)", foreground="#808080", font=(selected_font, small_font_size, font_weight)).pack(side=tk.LEFT, padx=4, pady=1)
        else:
            # 关闭自定义字体
            self.sc_combobox.configure(state="disabled")  # 禁用自定义字体选择
            self.system_font_combobox.configure(state="readonly")  # 启用系统字体选择
            
            # 显示自定义字体的提示标签
            custom_label_found = False
            for widget in self.sc_combobox.master.winfo_children():
                if isinstance(widget, ttk.Label) and widget.cget("text") == "(需开启自定义)":
                    widget.pack(side=tk.LEFT, padx=4, pady=2)
                    custom_label_found = True
                    break
            if not custom_label_found:
                # 如果标签不存在，创建并显示
                selected_font = GUI_CONFIG.get("ui_font", "微软雅黑")
                font_size = GUI_CONFIG.get("ui_font_size", 16.0)
                small_font_size = max(6, int(round(font_size * 0.8)))
                font_weight = "bold" if GUI_CONFIG.get("ui_bold", False) else "normal"
                ttk.Label(self.sc_combobox.master, text="(需开启自定义)", foreground="#808080", font=(selected_font, small_font_size, font_weight)).pack(side=tk.LEFT, padx=4, pady=2)
            
            # 隐藏系统字体的提示标签
            for widget in self.system_font_combobox.master.winfo_children():
                if isinstance(widget, ttk.Label) and widget.cget("text") == "(不启用时使用)":
                    widget.pack_forget()
    
    def on_d_system_font_changed(self, *args):
        """D.py系统字体开关状态变化时的处理逻辑"""
        # 根据use_system_font的值更新字体选择框的状态
        if self.use_system_font_var.get() == 1:
            # 不启用自定义字体（使用系统字体）
            self.sc_combobox.configure(state="disabled")
            self.system_font_combobox.configure(state="readonly")
            
            # 显示自定义字体的提示标签
            custom_label_found = False
            for widget in self.sc_combobox.master.winfo_children():
                if isinstance(widget, ttk.Label) and widget.cget("text") == "(需开启自定义)":
                    widget.pack(side=tk.LEFT, padx=4, pady=2)
                    custom_label_found = True
                    break
            if not custom_label_found:
                # 获取当前字体配置，使用相对字体大小
                selected_font = GUI_CONFIG.get("ui_font", "微软雅黑")
                font_size = GUI_CONFIG.get("ui_font_size", 16.0)
                small_font_size = max(6, int(round(font_size * 0.8)))
                font_weight = "bold" if GUI_CONFIG.get("ui_bold", False) else "normal"
                ttk.Label(self.sc_combobox.master, text="(需开启自定义)", foreground="#808080", font=(selected_font, small_font_size, font_weight)).pack(side=tk.LEFT, padx=4, pady=2)
            
            # 隐藏系统字体的提示标签
            for widget in self.system_font_combobox.master.winfo_children():
                if isinstance(widget, ttk.Label) and widget.cget("text") == "(不启用时使用)":
                    widget.pack_forget()
        else:
            # 启用自定义字体
            self.sc_combobox.configure(state="readonly")
            self.system_font_combobox.configure(state="disabled")
            
            # 隐藏自定义字体的提示标签
            for widget in self.sc_combobox.master.winfo_children():
                if isinstance(widget, ttk.Label) and widget.cget("text") == "(需开启自定义)":
                    widget.pack_forget()
            
            # 显示系统字体的提示标签
            system_label_found = False
            for widget in self.system_font_combobox.master.winfo_children():
                if isinstance(widget, ttk.Label) and widget.cget("text") == "(不启用时使用)":
                    widget.pack(side=tk.LEFT, padx=4, pady=2)
                    system_label_found = True
                    break
            if not system_label_found:
                # 获取当前字体配置，使用相对字体大小
                selected_font = GUI_CONFIG.get("ui_font", "微软雅黑")
                font_size = GUI_CONFIG.get("ui_font_size", 16.0)
                small_font_size = max(6, int(round(font_size * 0.8)))
                font_weight = "bold" if GUI_CONFIG.get("ui_bold", False) else "normal"
                ttk.Label(self.system_font_combobox.master, text="(不启用时使用)", foreground="#808080", font=(selected_font, small_font_size, font_weight)).pack(side=tk.LEFT, padx=4, pady=2)
        # 保存设置
        self.save_d_settings()
    
    def on_karaoke_toggled(self, *args):
        """卡拉OK开关状态变化时的处理逻辑"""
        # 根据卡拉OK开关状态决定是否启用卡拉OK效果选项
        karaoke_enabled = self.karaoke_var.get() == 1
        
        # 更新卡拉OK效果选项的状态
        self.default_effect_radio.configure(state="normal" if karaoke_enabled else "disabled")
        self.ktv_effect_radio.configure(state="normal" if karaoke_enabled else "disabled")
        self.prompter_effect_radio.configure(state="normal" if karaoke_enabled else "disabled")
        
        # 同时更新拖长音检测选项的状态
        if hasattr(self, 'beginning_sustain_off_radio') and hasattr(self, 'beginning_sustain_on_radio'):
            self.beginning_sustain_off_radio.configure(state="normal" if karaoke_enabled else "disabled")
            self.beginning_sustain_on_radio.configure(state="normal" if karaoke_enabled else "disabled")
        if hasattr(self, 'ending_sustain_off_radio') and hasattr(self, 'ending_sustain_on_radio'):
            self.ending_sustain_off_radio.configure(state="normal" if karaoke_enabled else "disabled")
            self.ending_sustain_on_radio.configure(state="normal" if karaoke_enabled else "disabled")
    
    def save_z_settings(self):
        """保存字幕式样设置到z.py"""
        # 读取z.py文件内容
        z_path = os.path.join(os.path.dirname(__file__), "Z.py")
        with open(z_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 先打印当前配置，用于调试
        # print("DEBUG: 当前全选模式状态:")
        # print(f"DEBUG: z_all_selected = {getattr(self, 'z_all_selected', False)}")
        # print(f"DEBUG: is_all_selected = {getattr(self, 'is_all_selected', False)}")
        # print(f"DEBUG: real_karaoke_var.get() = {self.real_karaoke_var.get()}")
        
        # 更新KARAOKE_EFFECT
        karaoke_effect = self.karaoke_var.get()
        # 确保能匹配带有注释的情况
        content = re.sub(r'KARAOKE_EFFECT\s*=\s*\d+\s*#.*', f'KARAOKE_EFFECT = {karaoke_effect}                # 0=不启用，1=启用卡拉OK效果', content)
        content = re.sub(r'KARAOKE_EFFECT\s*=\s*\d+', f'KARAOKE_EFFECT = {karaoke_effect}', content)
        
        # 更新REAL_KARAOKE_EFFECT，考虑全选选项
        real_karaoke_var_value = self.real_karaoke_var.get()
        if real_karaoke_var_value == -1:
            # 如果选择了"全选"选项，保存为-1
            real_karaoke_effect = -1
            # print(f"DEBUG: 选择了全选选项，保存为REAL_KARAOKE_EFFECT = {real_karaoke_effect}")
        else:
            # 否则保存为当前选中的选项值
            real_karaoke_effect = real_karaoke_var_value
            # print(f"DEBUG: 保存为单选模式，REAL_KARAOKE_EFFECT = {real_karaoke_effect}")
        
        # 更新REAL_KARAOKE_EFFECT，确保能匹配带有注释的情况
        # 使用更宽松的正则表达式，能匹配数字和'A'（字符串格式）
        regex_pattern = r'REAL_KARAOKE_EFFECT\s*=\s*(-?\d+|\'A\')\s*(#.*)?'
        # 直接保存为数字格式，因为real_karaoke_effect现在只会是数字
        replacement = f"REAL_KARAOKE_EFFECT = {real_karaoke_effect}           # 真实卡拉OK效果设置：0=默认效果，1=真实卡拉OK式样，2=提词器式样，-1=全选"
        
        # 使用re.sub的count=1参数，只替换第一个匹配项
        content = re.sub(regex_pattern, replacement, content, count=1)
        
        # 更新CUSTOM_FONT
        custom_font = self.custom_font_var.get()
        # 确保能匹配带有注释的情况
        content = re.sub(r'CUSTOM_FONT\s*=\s*\d+\s*#.*', f'CUSTOM_FONT = {custom_font}                   # 0=不启用，1=启用自定义字体', content)
        content = re.sub(r'CUSTOM_FONT\s*=\s*\d+', f'CUSTOM_FONT = {custom_font}', content)
        
        # 写入更新后的内容
        with open(z_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        # print("DEBUG: 保存完成！")
    
    def on_z_radio_click(self, clicked_value):
        """处理Z.py字幕单选按钮的点击事件，实现纯粹的单选逻辑：
        - 只能选择一个选项
        - 取消全选模式，恢复正常单选行为
        """
        # 重置所有选项状态
        self.z_all_radio.state(['!selected'])
        for radio in [self.z_radio0, self.z_radio1, self.z_radio2]:
            radio.state(['!selected'])
        
        # 只选择当前点击的选项
        self.real_karaoke_var.set(clicked_value)
        
        # 设置当前点击的选项为选中状态
        if clicked_value == -1:
            self.z_all_radio.state(['selected'])
        else:
            for radio in [self.z_radio0, self.z_radio1, self.z_radio2]:
                if int(radio.cget('value')) == clicked_value:
                    radio.state(['selected'])
        
        # 确保全选模式标记为False
        self.z_all_selected = False
    
    def save_c_settings(self):
        """保存字体设置到C.py"""
        # 读取C.py文件内容
        c_path = os.path.join(os.path.dirname(__file__), "C.py")
        with open(c_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # 读取当前的FONT_CONFIG
        c_config = self.read_c_config()
        
        # 更新字体配置
        # 简体中文字体：同步更新font_name和font_file
        sc_font_name = self.sc_font_var.get()
        c_config['simplified_chinese']['font_name'] = sc_font_name
        c_config['simplified_chinese']['font_file'] = f'{sc_font_name}.ttf'  # 自动同步font_file
        
        # 日语繁体字体：同步更新font_name和font_file
        jt_font_name = self.jt_font_var.get()
        c_config['japanese_traditional']['font_name'] = jt_font_name
        c_config['japanese_traditional']['font_file'] = f'{jt_font_name}.ttf'  # 自动同步font_file
        
        # 系统自带字体（统一设置，同时更新两个配置）
        default_font_display = self.default_font_var.get()
        # 将中文显示值转换为英文实际值
        default_font = self.font_map.get(default_font_display, default_font_display)
        c_config['simplified_chinese']['default_font_name'] = default_font
        c_config['japanese_traditional']['default_font_name'] = default_font
        
        # 生成新的FONT_CONFIG代码
        font_config_str = json.dumps(c_config, ensure_ascii=False, indent=4)
        # 将JSON布尔值转换为Python布尔值
        font_config_str = font_config_str.replace('true', 'True').replace('false', 'False')
        font_config_code = f'FONT_CONFIG = {font_config_str}'
        
        # 找到FONT_CONFIG的开始和结束位置
        start_line = -1
        end_line = -1
        brace_count = 0
        found_start = False
        
        for i, line in enumerate(lines):
            if 'FONT_CONFIG = ' in line:
                start_line = i
                found_start = True
                # 计算这一行中的大括号
                brace_count = line.count('{') - line.count('}')
                if brace_count == 0:
                    end_line = i
                    break
            elif found_start:
                # 继续计算大括号，直到找到匹配的结束
                brace_count += line.count('{') - line.count('}')
                if brace_count == 0:
                    end_line = i
                    break
        
        # 替换FONT_CONFIG
        if start_line != -1 and end_line != -1:
            # 构建新的内容
            new_lines = lines[:start_line] + [font_config_code + '\n'] + lines[end_line + 1:]
            content = ''.join(new_lines)
        else:
            # 如果没有找到FONT_CONFIG，使用原始内容
            content = ''.join(lines)
        
        # 写入更新后的内容
        with open(c_path, "w", encoding="utf-8") as f:
            f.write(content)
    
    def clear_output(self):
        """清空输出文本框"""
        self.output_text.delete(1.0, tk.END)
    
    def on_enter(self, event):
        """处理鼠标进入事件"""
        event.widget.config(highlightbackground="#007acc")
        return event.widget
    
    def on_leave(self, event):
        """处理鼠标离开事件"""
        event.widget.config(highlightbackground="#404040")
        return event.widget
    
    def on_paste(self, event):
        """处理粘贴事件，支持粘贴文件路径"""
        try:
            # 获取剪贴板内容
            clipboard_content = self.root.clipboard_get()
            # 去除可能的引号
            file_path = clipboard_content.strip().strip('"')
            # 检查文件是否存在
            if os.path.exists(file_path):
                # 将文件路径设置到输入框
                self.input_entry.delete(0, tk.END)
                self.input_entry.insert(0, file_path)
                # 显示信息
                self.output_text.insert(tk.END, f"\n文件粘贴: {file_path}\n")
                self.output_text.insert(tk.END, "开始自动处理...\n")
                self.output_text.see(tk.END)
                # 执行当前程序
                self.execute_current_program(file_path)
        except Exception as e:
            # 显示错误信息
            self.output_text.insert(tk.END, f"\n粘贴失败: {str(e)}\n")
            self.output_text.see(tk.END)
        return "break"  # 阻止默认粘贴行为
    
    def execute_current_program(self, file_path):
        """执行当前选中的程序"""
        # 获取当前运行的程序
        current_program = None
        for i, btn in enumerate(self.buttons):
            if btn.cget("style") == "Highlight.TButton":
                if i == 0:
                    current_program = "Z.py"
                elif i == 1:
                    current_program = "Z1.py"
                elif i == 2:
                    current_program = "D.py"
                elif i == 3:
                    # 字幕文件独立修改是独立功能，不与C.py绑定
                    # 这里我们不设置current_program，因为它有自己的处理逻辑
                    # 但为了保持兼容性，我们可以返回而不执行任何操作
                    return
                elif i == 4:
                    current_program = "M.py"
                elif i == 5:
                    current_program = "x.py"
                elif i == 6:
                    current_program = "V.py"
                break
        # 如果没有高亮按钮，默认使用第一个程序
        if not current_program:
            current_program = "Z.py"
        # 执行程序
        self.toggle_execute(os.path.join(os.path.dirname(__file__), current_program), os.path.dirname(__file__))
    
    def auto_save_settings(self, *args):
        """自动保存设置，当配置变量变化时触发"""
        try:
            # 保存字幕式样设置到z.py
            self.save_z_settings()
            
            # 保存字体设置到C.py
            self.save_c_settings()
            
            # 保存拖长音检测设置到B.py
            self.save_b_settings()
            
            # 不显示保存成功信息，保持界面简洁
            pass
        except Exception as e:
            if hasattr(self, 'output_text'):
                self.output_text.insert(tk.END, f"\n保存设置失败: {str(e)}\n")
                self.output_text.see(tk.END)
    
    def adjust_font_size(self, delta):
        """调整字体大小"""
        current_size = self.ui_font_size_var.get()
        new_size = max(5.0, min(30.0, current_size + delta))  # 限制字体大小在5.0-30.0之间
        # 四舍五入到一位小数
        new_size = round(new_size, 1)
        self.ui_font_size_var.set(new_size)
    
    def load_and_apply_font_config(self):
        """加载并应用保存的字体配置"""
        global GUI_CONFIG
        
        # 从全局配置中获取字体设置
        selected_font = GUI_CONFIG.get("ui_font", "微软雅黑")
        font_size = GUI_CONFIG.get("ui_font_size", 16.0)
        # 确保字体大小是有效的数值
        try:
            font_size = float(font_size)
        except:
            font_size = 10.0
        # 限制字体大小范围
        font_size = max(5.0, min(30.0, font_size))
        is_bold = GUI_CONFIG.get("ui_bold", False)
        
        # 构建字体配置
        font_weight = "bold" if is_bold else "normal"
        # 使用整数字体大小，确保所有Tkinter版本和主题都能正常显示
        font_size_int = int(round(font_size))
        
        # 应用字体设置到所有tkinter组件的默认字体
        self.root.option_add("*Font", f"{selected_font} {font_size_int} {font_weight}")
        
        # 应用字体设置到所有ttk样式
        self.style.configure(
            ".",
            font=(selected_font, font_size_int, font_weight)
        )
        
        # 应用字体设置到所有具体样式
        self.style.configure("TLabel", font=(selected_font, font_size_int, font_weight))
        # 左侧功能按钮使用120%的全局字体大小
        button_font_size = int(round(font_size_int * 1.2))
        self.style.configure("TButton", font=(selected_font, button_font_size, font_weight))
        self.style.configure("TEntry", font=(selected_font, font_size_int, font_weight))
        self.style.configure("Custom.TCombobox", font=(selected_font, font_size_int, font_weight))
        self.style.configure("TRadiobutton", font=(selected_font, font_size_int, font_weight))
        self.style.configure("Custom.TCheckbutton", font=(selected_font, font_size_int, font_weight))
        
        # 应用字体设置到高亮按钮（TButton字体的120%，即全局字体的144%）
        highlight_font_size = int(round(font_size_int * 1.44))
        self.style.configure(
            "Highlight.TButton",
            font=(selected_font, highlight_font_size, font_weight)
        )
        
        # 确保日志输出框应用新的字体设置
        if hasattr(self, 'output_text') and self.output_text is not None:
            try:
                # 检查控件是否还存在
                if self.output_text.winfo_exists():
                    # 日志文本使用90%的全局字体大小
                    log_font_size = int(round(font_size_int * 0.9))
                    self.output_text.configure(font=(selected_font, log_font_size, font_weight))
            except:
                # 如果控件不存在或已被销毁，忽略错误
                pass
        
    
    def apply_ui_font_settings(self):
        """应用UI字体设置"""
        selected_font = self.ui_font_var.get()
        is_bold = self.ui_bold_var.get() == 1
        font_size = self.ui_font_size_var.get()
        
        # 构建字体配置
        font_weight = "bold" if is_bold else "normal"
        # 使用整数字体大小，确保所有Tkinter版本和主题都能正常显示
        font_size_int = int(round(font_size))
        
        # 应用字体设置到所有tkinter组件的默认字体
        self.root.option_add("*Font", f"{selected_font} {font_size_int} {font_weight}")
        
        # 应用字体设置到所有ttk样式
        self.style.configure(
            ".",
            font=(selected_font, font_size_int, font_weight)
        )
        
        # 应用字体设置到所有具体样式
        self.style.configure("TLabel", font=(selected_font, font_size_int, font_weight))
        # 左侧功能按钮使用120%的全局字体大小
        button_font_size = int(round(font_size_int * 1.2))
        self.style.configure("TButton", font=(selected_font, button_font_size, font_weight))
        self.style.configure("TEntry", font=(selected_font, font_size_int, font_weight))
        self.style.configure("Custom.TCombobox", font=(selected_font, font_size_int, font_weight))
        self.style.configure("TRadiobutton", font=(selected_font, font_size_int, font_weight))
        self.style.configure("Custom.TCheckbutton", font=(selected_font, font_size_int, font_weight))
        
        # 应用字体设置到高亮按钮（TButton字体的120%，即全局字体的144%）
        highlight_font_size = int(round(font_size_int * 1.44))
        self.style.configure(
            "Highlight.TButton",
            font=(selected_font, highlight_font_size, font_weight)
        )
        
        # 确保日志输出框应用新的字体设置
        if hasattr(self, 'output_text') and self.output_text is not None:
            try:
                # 检查控件是否还存在
                if self.output_text.winfo_exists():
                    # 日志文本使用90%的全局字体大小
                    log_font_size = int(round(font_size_int * 0.9))
                    self.output_text.configure(font=(selected_font, log_font_size, font_weight))
            except:
                # 如果控件不存在或已被销毁，忽略错误
                pass
        
        
        # 更新字体加粗复选框的字体
        if hasattr(self, 'font_bold_checkbox') and self.font_bold_checkbox is not None:
            try:
                if self.font_bold_checkbox.winfo_exists():
                    self.font_bold_checkbox.configure(font=(selected_font, font_size_int, font_weight))
            except:
                pass
        
        # 更新所有功能按钮的字体
        for btn in getattr(self, 'buttons', []):
            try:
                if btn.winfo_exists():
                    btn.configure(style="TButton")
            except:
                pass
        
        # 更新当前选中功能按钮的高亮样式
        for i, btn in enumerate(getattr(self, 'buttons', [])):
            try:
                if btn.winfo_exists():
                    if btn.cget("style") == "Highlight.TButton":
                        btn.configure(style="Highlight.TButton")
            except:
                pass
        
        # 保存配置到全局变量
        global GUI_CONFIG
        GUI_CONFIG["ui_font"] = selected_font
        GUI_CONFIG["ui_font_size"] = font_size
        GUI_CONFIG["ui_bold"] = is_bold
        
        # 保存配置回文件本身，实现持久化存储
        self.save_config_to_file()
        
        # 显示应用成功信息
        try:
            if hasattr(self, 'output_text') and self.output_text is not None:
                # 检查控件是否还存在
                self.output_text.winfo_exists()
                self.output_text.insert(tk.END, f"\n字体设置已应用: {selected_font}, 大小: {font_size}, 加粗: {'是' if is_bold else '否'}\n")
                self.output_text.see(tk.END)
        except:
            # 控件不存在或已被销毁，忽略错误
            pass
    
    def save_config_to_file(self):
        """将配置保存回GUI.py文件本身，只替换文件开头的配置部分"""
        global GUI_CONFIG
        
        try:
            # 获取当前文件路径
            current_file = os.path.abspath(__file__)
            
            # 读取文件内容
            with open(current_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 构建新的配置字符串
            # 手动构建配置字符串，确保使用Python格式的布尔值
            new_config = 'GUI_CONFIG = {'
            for key, value in GUI_CONFIG.items():
                if isinstance(value, bool):
                    # 布尔值使用Python格式（True/False，首字母大写）
                    new_config += f'\n    "{key}": {value},'
                elif isinstance(value, str):
                    # 字符串添加引号
                    new_config += f'\n    "{key}": "{value}",'
                else:
                    # 其他类型直接使用
                    new_config += f'\n    "{key}": {value},'
            # 移除最后一个逗号
            new_config = new_config.rstrip(',') + '\n}'
            
            # 构建完整的替换内容，包括唯一标记
            # 保持与原始文件相同的结束标记格式
            full_replacement = '# GUI_CONFIG_START - 唯一配置开始标记\n'
            full_replacement += new_config + '\n'
            full_replacement += '# GUI_CONFIG_END'
            
            # 替换GUI_CONFIG变量的定义，使用唯一标记进行精确定位
            # 匹配从GUI_CONFIG_START到包含所有结束标记的完整配置部分
            # 使用re.DOTALL标志以匹配跨多行的内容
            import re
            # 更精确的正则表达式，匹配从开始标记到结束标记的完整配置部分
            pattern = r'# GUI_CONFIG_START.*?# GUI_CONFIG_END'
            
            # 执行替换，只替换第一个匹配项，避免影响其他代码
            new_content = re.sub(pattern, full_replacement, content, count=1, flags=re.DOTALL | re.MULTILINE)
            
            # 写回文件
            with open(current_file, "w", encoding="utf-8") as f:
                f.write(new_content)
            
            # 显示保存成功信息
            if hasattr(self, 'output_text') and self.output_text is not None:
                try:
                    self.output_text.winfo_exists()
                    self.output_text.insert(tk.END, "\n配置已保存到文件！\n")
                    self.output_text.see(tk.END)
                except:
                    pass
                    
        except Exception as e:
            print(f"保存配置到文件失败: {e}")
            # 显示保存失败信息
            if hasattr(self, 'output_text') and self.output_text is not None:
                try:
                    self.output_text.winfo_exists()
                    self.output_text.insert(tk.END, f"\n保存配置到文件失败: {e}\n")
                    self.output_text.see(tk.END)
                except:
                    pass
    
    def run_sub_function(self, sub_program_name):
        """执行单个子功能"""
        file_path = self.input_entry.get().strip()
        if not file_path:
            self.output_text.insert(tk.END, "请先选择文件！\n")
            return
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sub_program_path = os.path.join(current_dir, sub_program_name)
        
        if not os.path.exists(sub_program_path):
            self.output_text.insert(tk.END, f"子功能文件不存在: {sub_program_name}\n")
            return
        
        self.output_text.insert(tk.END, f"\n执行子功能: {sub_program_name}\n")
        self.output_text.insert(tk.END, f"输入路径: {file_path}\n\n")
        
        # 启动子功能并传递输入参数
        threading.Thread(
            target=self._run_program_with_input, 
            args=(sub_program_path, current_dir, file_path), 
            daemon=True
        ).start()
    
    def run_all_sub_functions(self, file_path):
        """执行所有子功能"""
        # 清理日志
        self.clear_output()
        
        sub_functions = ["A.py", "B.py", "K.py", "T.py"]
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        for sub_program_name in sub_functions:
            sub_program_path = os.path.join(current_dir, sub_program_name)
            if os.path.exists(sub_program_path):
                self.output_text.insert(tk.END, f"\n执行子功能: {sub_program_name}\n")
                self.output_text.insert(tk.END, f"输入路径: {file_path}\n\n")
                
                # 执行子功能
                self._run_program_with_input(sub_program_path, current_dir, file_path)
            else:
                self.output_text.insert(tk.END, f"子功能文件不存在: {sub_program_name}\n")
        
        self.output_text.insert(tk.END, "\n所有子功能执行完成！\n")
    
    def browse_sub_function_file(self, script_name, entry):
        """为子功能选择文件并自动执行"""
        # 根据脚本名称设置文件类型过滤
        if script_name == "A.py":
            # 字幕校对功能只允许选择字幕文件
            file_path = filedialog.askopenfilename(
                title=f"选择{script_name}的输入文件",
                filetypes=[
                    ("字幕文件", "*.srt *.ass *.ssa")
                ]
            )
        elif script_name in ["B.py", "K.py", "T.py"]:
            # 卡拉OK相关功能只允许选择ASS文件
            file_path = filedialog.askopenfilename(
                title=f"选择{script_name}的输入文件",
                filetypes=[
                    ("ASS字幕文件", "*.ass")
                ]
            )
        else:
            # 其他功能保持原有的文件类型选择
            file_path = filedialog.askopenfilename(
                title=f"选择{script_name}的输入文件",
                filetypes=[
                    ("所有文件", "*.*"),
                    ("字幕文件", "*.srt *.ass *.ssa"),
                    ("视频文件", "*.mp4 *.mkv *.avi *.mov")
                ]
            )
        
        if file_path:
            # 清理日志
            self.clear_output()
            
            # 更新输入框
            entry.delete(0, tk.END)
            entry.insert(0, file_path)
            
            # 对于A.py，自动弹出音频文件选择对话框
            if script_name == "A.py" and hasattr(self, "subtitle_proofreading_audio_entry"):
                # 打开音频文件选择对话框
                audio_path = filedialog.askopenfilename(
                    title="选择音频文件",
                    filetypes=[
                        ("音频文件", "*.wav *.mp3 *.m4a *.flac *.ogg"),
                        ("视频文件", "*.mp4 *.mkv *.avi *.mov")
                    ]
                )
                
                if audio_path:
                    # 更新音频输入框
                    audio_entry = getattr(self, "subtitle_proofreading_audio_entry")
                    audio_entry.delete(0, tk.END)
                    audio_entry.insert(0, audio_path)
                    self.output_text.insert(tk.END, f"\n音频文件: {audio_path}\n")
            
            # 对于B.py（卡拉OK自动打轴），根据延长音检测开关状态决定是否需要选择音频文件
            if script_name == "B.py":
                # 检查是否开启了任何一种延长音检测
                beginning_sustain_enabled = hasattr(self, "beginning_sustain_detection_var") and self.beginning_sustain_detection_var.get() == 1
                ending_sustain_enabled = hasattr(self, "ending_sustain_detection_var") and self.ending_sustain_detection_var.get() == 1
                sustain_enabled = beginning_sustain_enabled or ending_sustain_enabled
                if sustain_enabled:
                    # 开启延长音检测：需要选择音频文件
                    audio_path = filedialog.askopenfilename(
                        title="选择音频文件",
                        filetypes=[
                            ("音频文件", "*.wav *.mp3 *.m4a *.flac *.ogg"),
                            ("视频文件", "*.mp4 *.mkv *.avi *.mov")
                        ]
                    )
                    
                    # 自动执行子功能，传递ASS文件路径和音频文件路径
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    script_path = os.path.join(current_dir, script_name)
                    
                    if os.path.exists(script_path):
                        self.output_text.insert(tk.END, f"\n执行子功能: {script_name}\n")
                        self.output_text.insert(tk.END, f"ASS文件: {file_path}\n")
                        if audio_path:
                            self.output_text.insert(tk.END, f"音频文件: {audio_path}\n\n")
                            # 启动子功能并传递输入参数（ASS文件路径和音频文件路径）
                            threading.Thread(
                                target=self._run_program_with_input, 
                                args=(script_path, current_dir, f"{file_path}|{audio_path}"), 
                                daemon=True
                            ).start()
                        else:
                            self.output_text.insert(tk.END, "未选择音频文件，无法执行延长音检测！\n")
                    else:
                        self.output_text.insert(tk.END, f"子功能文件不存在: {script_name}\n")
                else:
                    # 关闭延长音检测：直接执行子功能，只需要ASS文件
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    script_path = os.path.join(current_dir, script_name)
                    
                    if os.path.exists(script_path):
                        self.output_text.insert(tk.END, f"\n执行子功能: {script_name}\n")
                        self.output_text.insert(tk.END, f"ASS文件: {file_path}\n\n")
                        # 启动子功能并传递输入参数（只需要ASS文件路径）
                        threading.Thread(
                            target=self._run_program_with_input, 
                            args=(script_path, current_dir, file_path), 
                            daemon=True
                        ).start()
                    else:
                        self.output_text.insert(tk.END, f"子功能文件不存在: {script_name}\n")
            # 自动执行子功能
            else:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                script_path = os.path.join(current_dir, script_name)
                
                if os.path.exists(script_path):
                    self.output_text.insert(tk.END, f"\n执行子功能: {script_name}\n")
                    self.output_text.insert(tk.END, f"输入路径: {file_path}\n\n")
                    
                    # 启动子功能并传递输入参数
                    threading.Thread(
                        target=self._run_program_with_input, 
                        args=(script_path, current_dir, file_path), 
                        daemon=True
                    ).start()
                else:
                    self.output_text.insert(tk.END, f"子功能文件不存在: {script_name}\n")
    
    def execute_sub_function(self, script_name, entry):
        """执行子功能"""
        file_path = entry.get().strip()
        if not file_path:
            self.output_text.insert(tk.END, "请先选择文件！\n")
            return
        
        # 清理日志
        self.clear_output()
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(current_dir, script_name)
        
        if not os.path.exists(script_path):
            self.output_text.insert(tk.END, f"子功能文件不存在: {script_name}\n")
            return
        
        self.output_text.insert(tk.END, f"\n执行子功能: {script_name}\n")
        self.output_text.insert(tk.END, f"输入路径: {file_path}\n\n")
        
        # 启动子功能并传递输入参数
        threading.Thread(
            target=self._run_program_with_input, 
            args=(script_path, current_dir, file_path), 
            daemon=True
        ).start()
    
    def browse_audio_file(self, entry):
        """浏览并选择音频文件"""
        # 打开音频文件选择对话框
        audio_path = filedialog.askopenfilename(
            title="选择音频文件",
            filetypes=[
                ("所有文件", "*.*"),
                ("音频文件", "*.wav *.mp3 *.m4a *.flac *.ogg"),
                ("视频文件", "*.mp4 *.mkv *.avi *.mov")
            ]
        )
        
        if audio_path:
            # 更新音频输入框
            entry.delete(0, tk.END)
            entry.insert(0, audio_path)
            self.output_text.insert(tk.END, f"\n音频文件: {audio_path}\n")
    
    def on_drop(self, event):
        """处理拖拽事件，获取文件路径"""
        # 获取拖拽的文件路径
        file_path = event.data
        
        # 清理路径格式，Windows下拖拽可能会带有大括号
        if isinstance(file_path, str):
            if file_path.startswith("{") and file_path.endswith("}"):
                file_path = file_path[1:-1]
            
            # 将文件路径设置到输入框
            if hasattr(self, 'input_entry'):
                self.input_entry.delete(0, tk.END)
                self.input_entry.insert(0, file_path)
                # 显示拖拽信息
                if hasattr(self, 'output_text'):
                    self.output_text.insert(tk.END, f"\n文件拖拽: {file_path}\n")
                    self.output_text.insert(tk.END, "开始自动处理...\n")
                    self.output_text.see(tk.END)
                    # 自动执行当前选中的程序
                    self.execute_current_program(file_path)
        
        return "break"
    
    def on_sub_function_drop(self, event, script_name, entry):
        """处理子功能输入栏的拖拽事件"""
        # 获取拖拽的文件路径
        file_path = event.data
        
        # 清理路径格式，Windows下拖拽可能会带有大括号
        if isinstance(file_path, str):
            if file_path.startswith("{") and file_path.endswith("}"):
                file_path = file_path[1:-1]
            
            # 将文件路径设置到输入框
            entry.delete(0, tk.END)
            entry.insert(0, file_path)
            
            # 显示拖拽信息
            if hasattr(self, 'output_text'):
                self.output_text.insert(tk.END, f"\n文件拖拽到 {script_name} 输入栏: {file_path}\n")
                self.output_text.insert(tk.END, f"开始执行 {script_name} 功能...\n")
                self.output_text.see(tk.END)
                
                # 执行对应的子功能
                current_dir = os.path.dirname(os.path.abspath(__file__))
                script_path = os.path.join(current_dir, script_name)
                
                if os.path.exists(script_path):
                    # 启动子功能并传递输入参数
                    threading.Thread(
                        target=self._run_program_with_input, 
                        args=(script_path, current_dir, file_path), 
                        daemon=True
                    ).start()
                else:
                    self.output_text.insert(tk.END, f"子功能文件不存在: {script_name}\n")
        
        return "break"

    def on_close(self):
        """处理窗口关闭事件，直接关闭Python窗口"""
        import os
        import sys
        
        # 销毁GUI窗口
        self.root.destroy()
        
        # 使用os._exit()函数立即终止Python进程，不执行任何清理操作
        # 这是最底层的退出方法，应该能够立即终止进程，不显示任何提示
        os._exit(0)
    
    def show_subtitle_independent_modification(self):
        """显示字幕文件独立修改功能界面，作为一个独立的大类"""
        self.clear_right_frame()
        
        # 创建子功能按钮区域
        sub_functions_frame = ttk.LabelFrame(self.right_frame, text="")
        sub_functions_frame.pack(fill=tk.X, padx=4, pady=2)
        
        # 创建竖向排列的子功能项目
        sub_functions = [
            ("《字幕校对》 - 先选择字幕文件后选择纯人声音频文件", "A.py", "subtitle_proofreading_entry"),
            ("《卡拉OK自动打轴》 - 选择ASS字幕后自动执行", "B.py", "karaoke_timing_entry"),
            ("《卡拉OK转KTV效果》 - 选择ASS字幕后自动执行", "K.py", "karaoke_to_ktv_entry"),
            ("《卡拉OK转提词器效果》 - 选择ASS字幕后自动执行", "T.py", "karaoke_to_prompter_entry")
        ]
        
        # 读取B.py的配置
        b_config = self.read_b_config()
        
        # 为每个子功能创建独立的输入框、选择文件按钮和执行按钮
        for func_name, script_name, entry_name in sub_functions:
            # 创建子功能框架
            func_frame = ttk.LabelFrame(sub_functions_frame, text=func_name)
            func_frame.pack(fill=tk.X, padx=4, pady=2)
            
            # 创建输入框和按钮框架
            input_frame = ttk.Frame(func_frame)
            input_frame.pack(fill=tk.X, padx=4, pady=2)
            
            # 创建输入框
            entry = ttk.Entry(input_frame, width=60)
            entry.pack(side=tk.LEFT, padx=4, pady=2, fill=tk.X, expand=True)
            # 保存输入框引用
            setattr(self, entry_name, entry)
            
            # 为输入框添加拖拽功能
            entry.drop_target_register(DND_FILES)
            entry.dnd_bind("<<Drop>>", lambda e, script=script_name, entry=entry: self.on_sub_function_drop(e, script, entry))
            
            # 创建按钮容器
            button_frame = ttk.Frame(input_frame)
            button_frame.pack(side=tk.RIGHT, padx=4, pady=2)
            
            # 创建选择文件按钮（选择后自动执行）
            browse_btn = ttk.Button(
                button_frame, 
                text="选择文件", 
                command=lambda script=script_name, entry=entry: self.browse_sub_function_file(script, entry)
            )
            browse_btn.pack(side=tk.LEFT, padx=4, pady=2)
            
            # 为卡拉OK自动打轴功能添加延长音检测开关
            if script_name == "B.py":
                # 创建延长音检测开关框架
                sustain_frame = ttk.Frame(func_frame)
                sustain_frame.pack(fill=tk.X, padx=4, pady=2)
                
                # 句首延长音开关
                beginning_sustain_frame = ttk.Frame(sustain_frame)
                beginning_sustain_frame.pack(fill=tk.X, padx=4, pady=1)
                ttk.Label(beginning_sustain_frame, text="句首延长音: " ).pack(side=tk.LEFT, padx=4, pady=1)
                self.beginning_sustain_detection_var = tk.IntVar(value=b_config.get("ENABLE_BEGINNING_SUSTAIN_DETECTION", 0))
                ttk.Radiobutton(beginning_sustain_frame, text="关闭", variable=self.beginning_sustain_detection_var, value=0).pack(side=tk.LEFT, padx=4, pady=1)
                ttk.Radiobutton(beginning_sustain_frame, text="开启", variable=self.beginning_sustain_detection_var, value=1).pack(side=tk.LEFT, padx=4, pady=1)
                ttk.Label(beginning_sustain_frame, text="(关闭则只需要ASS文件，开启则需要ASS文件+音频文件)", foreground="#808080").pack(side=tk.LEFT, padx=4, pady=1)
                
                # 句末延长音开关
                ending_sustain_frame = ttk.Frame(sustain_frame)
                ending_sustain_frame.pack(fill=tk.X, padx=4, pady=1)
                ttk.Label(ending_sustain_frame, text="句末延长音: " ).pack(side=tk.LEFT, padx=4, pady=1)
                self.ending_sustain_detection_var = tk.IntVar(value=b_config.get("ENABLE_ENDING_SUSTAIN_DETECTION", 0))
                ttk.Radiobutton(ending_sustain_frame, text="关闭", variable=self.ending_sustain_detection_var, value=0).pack(side=tk.LEFT, padx=4, pady=1)
                ttk.Radiobutton(ending_sustain_frame, text="开启", variable=self.ending_sustain_detection_var, value=1).pack(side=tk.LEFT, padx=4, pady=1)
                ttk.Label(ending_sustain_frame, text="(关闭则只需要ASS文件，开启则需要ASS文件+音频文件)", foreground="#808080").pack(side=tk.LEFT, padx=4, pady=1)
                
                # 绑定状态变化事件
                self.beginning_sustain_detection_var.trace("w", lambda *args: self.save_b_settings())
                self.ending_sustain_detection_var.trace("w", lambda *args: self.save_b_settings())
        
        # 为A.py(字幕校对)创建音频文件输入框引用（不显示在UI上）
        if "A.py" in [script for _, script, _ in sub_functions]:
            # 创建一个隐藏的音频输入框引用
            # 这样在选择字幕后仍然可以自动弹出音频文件选择对话框
            # 但不在UI上显示音频输入框
            class HiddenEntry:
                def __init__(self):
                    self.value = ""
                def delete(self, *args):
                    self.value = ""
                def insert(self, *args):
                    # 使用最后一个参数作为value值
                    if args:
                        self.value = args[-1]
                def get(self):
                    return self.value
            
            # 保存隐藏的音频输入框引用
            setattr(self, "subtitle_proofreading_audio_entry", HiddenEntry())
        
        # 创建输出显示区域 - 放到最下面
        output_frame = ttk.LabelFrame(self.right_frame, text="程序输出")
        output_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)
        
        # 创建滚动条和文本框
        scrollbar = ttk.Scrollbar(output_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 为文本框设置暗黑主题样式
        self.output_text = tk.Text(
            output_frame, 
            wrap=tk.WORD, 
            yscrollcommand=scrollbar.set, 
            height=18,
            bg=self.bg_color,
            fg=self.fg_color,
            insertbackground=self.fg_color,
            selectbackground=self.accent_color,
            selectforeground="#ffffff",
            borderwidth=1,
            relief="solid",
            highlightbackground=self.border_color,
            highlightcolor=self.accent_color
        )
        # 添加拖放功能
        # 启用拖放
        self.output_text.bind("<Enter>", self.on_enter)
        self.output_text.bind("<Leave>", self.on_leave)
        # 绑定粘贴事件，支持从剪贴板粘贴文件路径
        self.output_text.bind("<Control-v>", self.on_paste)
        
        # 为字幕文件独立修改功能禁用日志页的拖拽功能
        # 只保留输入栏的拖拽功能
        
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)
        scrollbar.config(command=self.output_text.yview)
        
        # 在输出框中显示功能说明
        description = [
            "===================",
            "字幕文件独立修改功能使用说明：",
            "===================",
            "",
            "功能说明：",
            "- (!!注意!!需手动将字幕时间轴首尾对其)",
            "- 字幕校对(校对是根据人声进行断句) - 需人声分离音频文件",
            "- 目前技术问题准确率只能到80%",
            "- ",
            "- 卡拉OK自动打轴 - 按时间分配",
            "- 卡拉OK效果转换KTV效果 - ",
            "- 卡拉OK效果转换提词器效果 - ",
            "",
            "使用方法：",
            "1. 点击'选择文件'按钮选择字幕文件",
            "2. 选择文件后将自动执行所有子功能",
        ]
        
        for line in description:
            self.output_text.insert(tk.END, line + "\n")
        
        # 初始化进程为None
        self.process = None
        
        # 高亮对应的功能按钮
        for i, btn in enumerate(self.buttons):
            if i == 3:  # 字幕文件独立修改是第四个大类
                self.highlight_button(btn)
                break

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = MainGUI(root)
    root.mainloop()