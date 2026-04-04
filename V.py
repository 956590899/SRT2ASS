import os
import sys
import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import ttk

# 设置环境变量，确保Python使用UTF-8编码
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LANG'] = 'zh_CN.UTF-8'
os.environ['LC_ALL'] = 'zh_CN.UTF-8'

# 确保标准输出/错误使用UTF-8编码
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import time
import re
import shutil
import subprocess
import tempfile
import pyautogui

# 设置项目自带的ffmpeg路径
ffmpeg_path = os.path.join(os.path.dirname(__file__), 'Python', 'ffmpeg', 'ffmpeg.exe')
if os.path.exists(ffmpeg_path):
    os.environ['PATH'] = os.path.dirname(ffmpeg_path) + os.pathsep + os.environ['PATH']
    print(f"OK 设置ffmpeg路径: {ffmpeg_path}")
else:
    print(f"警告: ffmpeg文件不存在: {ffmpeg_path}")

# 导入pydub
from pydub import AudioSegment
from pydub.generators import Sine

# 重写print函数，确保每次输出后都刷新缓冲区
original_print = print
def print(*args, **kwargs):
    # 只有当kwargs中没有flush参数时，才添加flush=True
    if 'flush' not in kwargs:
        kwargs['flush'] = True
    original_print(*args, **kwargs)

# ====== 新增导入（用于带超时的输入） ======
if sys.platform == 'win32':
    import msvcrt

# ====== 用户可调参数配置区 ======
# 0为关 1为开
# V1转换选项
ENABLE_V1_CONVERSION = 1

# 文件保存选项
SAVE_ORIGINAL_LRC = 0

# 目录打开选项
AUTO_OPEN_OUTPUT_DIR = 0

# 日志详细程度
SHOW_DETAILED_LOGS = 1

# 字幕对齐功能
ENABLE_SUBTITLE_ALIGNMENT = 1

# Z打包功能
ENABLE_Z_PACKAGING = 1

# 字幕打包时间差异阈值（秒）
PACKAGING_DIFF_THRESHOLD = 4.0

# 时间轴差异警告阈值（秒）
TIME_DIFF_WARNING_THRESHOLD = 2.0

# 歌词选择最大行数
MAX_SELECTABLE_ROWS = 4

# MusicTag图像识别等待时间配置（单位：秒）
WAIT_OPEN = 3           # 等待MusicTag启动的时间
WAIT_FILE_LOAD = 2      # 等待文件加载的时间
WAIT_UI_LOAD = 2        # 等待UI加载的时间
WAIT_SEARCH = 8        # 等待搜索结果的时间
WAIT_CONFIRM = 1        # 等待歌词加载的时间
WAIT_SAVE = 2           # 等待保存完成的时间

# 新增：歌词确认等待时间
LYRIC_CONFIRM_TIMEOUT = 5  # 歌词确认倒计时（秒）
MANUAL_OPERATION_TIMEOUT = 60  # 手动操作最大等待时间（秒）
MOUSE_MOVEMENT_THRESHOLD = 10  # 鼠标移动检测阈值（像素）

# 图像识别置信度（0.0-1.0）
CONFIDENCE = 0.7

# 自动化提示窗口位置配置（像素）
NOTIFICATION_WINDOW_X = 100  # 距离左侧像素
NOTIFICATION_WINDOW_Y = 50  # 距离顶部像素

# ====== 基础路径配置 ======
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MUSICTAG_PATH = os.path.join(BASE_DIR, "Python", "音乐标签", "MusicTag.exe")
RESOURCE_DIR = os.path.join(BASE_DIR, "Python", "lrc")
Z_SCRIPT_PATH = os.path.join(BASE_DIR, "z.py")

# 使用系统临时目录作为缓存
TEMP_BASE_DIR = os.path.join(tempfile.gettempdir(), "music_tag_tool")
TEMP_MP3_DIR = os.path.join(TEMP_BASE_DIR, "temp_mp3")

# 截图文件路径
FILE_LIST_IMG = os.path.join(RESOURCE_DIR, "file_list.png")
LYRIC_ICON = os.path.join(RESOURCE_DIR, "lyric_icon.png")
SEARCH_BTN = os.path.join(RESOURCE_DIR, "search_btn.png")
CONFIRM_BTN = os.path.join(RESOURCE_DIR, "confirm_btn.png")
SAVE_LRC_BTN = os.path.join(RESOURCE_DIR, "save_lrc_btn.png")
LRC_QQ_ROW = os.path.join(RESOURCE_DIR, "lrc_qq_row.png")

# ====== Windows API 常量和函数声明（用于窗口置顶） ======
# 窗口样式常量
GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x0008

# 窗口操作常量
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010

# 窗口类名
MUSICTAG_WINDOW_CLASS = "TfrmMain"

# 定义 FindWindow 函数
def FindWindow(lpClassName, lpWindowName):
    """查找窗口并返回窗口句柄"""
    user32 = ctypes.windll.user32
    return user32.FindWindowW(lpClassName, lpWindowName)

# 定义 SetWindowPos 函数
def SetWindowPos(hWnd, hWndInsertAfter, X, Y, cx, cy, uFlags):
    """设置窗口位置和样式"""
    user32 = ctypes.windll.user32
    return user32.SetWindowPosW(hWnd, hWndInsertAfter, X, Y, cx, cy, uFlags)

# 定义 GetWindowTextLength 函数
def GetWindowTextLength(hWnd):
    """获取窗口标题长度"""
    user32 = ctypes.windll.user32
    return user32.GetWindowTextLengthW(hWnd)

# 定义 GetWindowText 函数
def GetWindowText(hWnd, lpString, nMaxCount):
    """获取窗口标题"""
    user32 = ctypes.windll.user32
    return user32.GetWindowTextW(hWnd, lpString, nMaxCount)

# 定义 EnumWindowsProc 回调类型
EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

# 定义 EnumWindows 函数
def EnumWindows(lpEnumFunc, lParam):
    """枚举所有顶级窗口"""
    user32 = ctypes.windll.user32
    return user32.EnumWindowsW(lpEnumFunc, lParam)

# 定义 IsWindowVisible 函数
def IsWindowVisible(hWnd):
    """检查窗口是否可见"""
    user32 = ctypes.windll.user32
    return user32.IsWindowVisible(hWnd)

# ====== 窗口置顶函数 ======
def make_window_topmost(window_title=None, window_class=None):
    """
    将指定标题或类名的窗口置顶
    :param window_title: 窗口标题（可选）
    :param window_class: 窗口类名（可选）
    :return: 是否成功置顶
    """
    try:
        print("   INFO 尝试将窗口置顶...")
        user32 = ctypes.windll.user32
        
        # 简化实现：检查Windows API函数是否可用，如果不可用则跳过
        # 检查user32模块中是否有FindWindowW和SetWindowPosW函数
        has_findwindow = hasattr(user32, 'FindWindowW')
        has_setwindowpos = hasattr(user32, 'SetWindowPosW')
        
        if not has_findwindow or not has_setwindowpos:
            print("   INFO Windows API函数不可用，跳过窗口置顶操作")
            return True
        
        # 1. 优先通过类名查找（更可靠）
        if window_class:
            try:
                hWnd = user32.FindWindowW(window_class, None)
                if hWnd:
                    print(f"   OK 通过类名 '{window_class}' 找到窗口句柄: {hWnd}")
                    # 设置窗口为置顶
                    result = user32.SetWindowPosW(hWnd, -1, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE)
                    if result:
                        print(f"   OK 已将窗口置顶")
                        return True
                    else:
                        print(f"   INFO 置顶窗口失败，错误码: {ctypes.GetLastError()}")
            except Exception as e:
                print(f"   INFO 通过类名查找失败: {e}")
        
        # 2. 尝试通过常见标题查找
        print("   INFO 简化模式：尝试通过常见标题查找 MusicTag 窗口")
        common_titles = ["MusicTag", "音乐标签"]
        
        for title in common_titles:
            try:
                hWnd = user32.FindWindowW(None, title)
                if hWnd:
                    print(f"   OK 通过标题 '{title}' 找到窗口句柄: {hWnd}")
                    # 设置窗口为置顶
                    result = user32.SetWindowPosW(hWnd, -1, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE)
                    if result:
                        print(f"   OK 已将窗口置顶")
                        return True
                    else:
                        print(f"   INFO 置顶窗口失败，错误码: {ctypes.GetLastError()}")
            except Exception as e:
                print(f"   INFO 通过标题 '{title}' 查找失败: {e}")
        
        # 3. 如果都找不到，不报错，只是记录信息
        print(f"   INFO 未找到 MusicTag 窗口，跳过置顶操作")
        return True
            
    except Exception as e:
        print(f"   INFO 窗口置顶操作失败: {e}")
        print(f"   INFO 跳过置顶操作，继续执行")
        return True

# ====== 自动化运行提示窗口函数 ======
def create_automation_notification():
    """
    创建并显示桌面层置顶的自动化运行提示窗口
    :return: (窗口对象, 标题标签对象, 提示标签对象)，用于后续更新和关闭
    """
    try:
        # 创建主窗口
        root = tk.Tk()
        root.title("自动化运行中")
        
        # 设置窗口大小和固定位置
        root.geometry(f"400x150+{NOTIFICATION_WINDOW_X}+{NOTIFICATION_WINDOW_Y}")
        root.resizable(False, False)
        
        # 设置窗口始终置顶
        root.wm_attributes("-topmost", 1)
        
        # 设置窗口为工具窗口（无任务栏图标）
        root.wm_attributes("-toolwindow", 1)
        
        # 设置窗口透明度
        root.wm_attributes("-alpha", 0.9)
        
        # 设置窗口样式
        root.configure(bg="#2c3e50")
        
        # 创建样式
        style = ttk.Style()
        style.theme_use("clam")
        
        # 配置标签样式
        style.configure("Title.TLabel", 
                       foreground="#3498db", 
                       background="#2c3e50", 
                       font=("Microsoft YaHei", 14, "bold"))
        
        style.configure("Info.TLabel", 
                       foreground="#ecf0f1", 
                       background="#2c3e50", 
                       font=("Microsoft YaHei", 10))
        
        style.configure("Progress.TLabel", 
                       foreground="#f39c12", 
                       background="#2c3e50", 
                       font=("Microsoft YaHei", 11, "bold"))
        
        # 配置进度条样式
        style.configure("Custom.Horizontal.TProgressbar",
                       background="#3498db",
                       troughcolor="#34495e",
                       borderwidth=0,
                       thickness=10)
        
        # 添加标题标签
        title_label = ttk.Label(root, text="自动化运行中", style="Title.TLabel")
        title_label.pack(pady=10)
        
        # 添加信息标签
        info_label = ttk.Label(root, text="当前正在处理歌词适配...", style="Info.TLabel")
        info_label.pack(pady=5)
        
        # 添加动态进度标签
        progress_text_label = ttk.Label(root, text="", style="Progress.TLabel")
        progress_text_label.pack(pady=5)
        
        # 添加进度条
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(root, 
                                      length=350, 
                                      mode="indeterminate",
                                      variable=progress_var,
                                      style="Custom.Horizontal.TProgressbar")
        progress_bar.pack(pady=10)
        
        # 启动进度条动画，加快滚动速度（值越小速度越快）
        progress_bar.start(5)
        
        # 确保窗口始终固定在配置位置
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = NOTIFICATION_WINDOW_X  # 使用配置的左侧距离
        y = NOTIFICATION_WINDOW_Y  # 使用配置的顶部距离
        root.geometry(f"{width}x{height}+{x}+{y}")
        
        # 显示窗口
        root.update()
        
        return root, title_label, info_label, progress_text_label
        
    except Exception as e:
        print(f"   ERROR 创建自动化提示窗口失败: {e}")
        return None, None, None, None

# ====== 更新自动化提示窗口函数 ======
def update_automation_notification(window, title_label, info_label, progress_text_label, title="", info="", progress_text=""):
    """
    更新自动化运行提示窗口的显示内容
    :param window: 窗口对象
    :param title_label: 标题标签对象
    :param info_label: 信息标签对象
    :param progress_text_label: 进度文本标签对象
    :param title: 新的标题（可选）
    :param info: 新的信息文本（可选）
    :param progress_text: 新的进度文本（可选）
    """
    try:
        if window:
            if title and title_label:
                title_label.config(text=title)
            if info and info_label:
                info_label.config(text=info)
            if progress_text and progress_text_label:
                progress_text_label.config(text=progress_text)
            
            # 更新窗口
            window.update()
            return True
    except Exception as e:
        print(f"   ERROR 更新自动化提示窗口失败: {e}")
        return False

# ====== 关闭自动化提示窗口函数 ======
def close_automation_notification(window):
    """
    关闭自动化运行提示窗口
    :param window: 要关闭的窗口对象
    """
    try:
        if window:
            window.destroy()
            print("   OK 自动化提示窗口已关闭")
            return True
    except Exception as e:
        print(f"   ERROR 关闭自动化提示窗口失败: {e}")
        return False

# ====== 新增：鼠标移动检测 ======
def detect_mouse_movement(sample_interval=0.5):
    """
    检测鼠标是否发生显著移动
    返回：True如果检测到移动超过阈值
    """
    try:
        # 记录起始位置
        start_pos = pyautogui.position()
        time.sleep(sample_interval)
        
        # 检查当前位置
        current_pos = pyautogui.position()
        
        # 计算移动距离
        distance = ((current_pos.x - start_pos.x) ** 2 + 
                   (current_pos.y - start_pos.y) ** 2) ** 0.5
        
        # 如果移动超过阈值，认为是有意操作
        return distance > MOUSE_MOVEMENT_THRESHOLD
    except Exception as e:
        if SHOW_DETAILED_LOGS:
            print(f"鼠标检测异常: {e}")
        return False

# ====== 新增：计算文件匹配分数 ======
def calculate_file_match_score(file_path, artist, title):
    """
    计算歌词文件匹配分数
    返回：匹配分数（越高越匹配）
    """
    score = 0
    
    if not os.path.exists(file_path):
        return score
    
    # 基础分：文件存在
    score += 10
    
    # 文件大小分
    try:
        file_size = os.path.getsize(file_path)
        if 100 < file_size < 100000:  # 100字节到100KB之间为合理大小
            score += 20
        elif file_size >= 100000:  # 太大可能不是歌词
            score -= 10
    except:
        pass
    
    # 文件名匹配分
    file_name = os.path.basename(file_path).lower()
    artist_lower = artist.lower()
    title_lower = title.lower()
    
    # 检查文件名是否包含歌手或歌名
    if artist_lower in file_name:
        score += 30
    if title_lower in file_name:
        score += 30
    
    # 内容匹配分
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(1000).lower()  # 只读前1000字符
        
        if artist_lower in content:
            score += 10
        if title_lower in content:
            score += 10
        # 标准LRC标签
        if '[ti:' in content or '[ar:' in content or '[00:' in content:
            score += 20
    except:
        pass
    
    return score

# ====== 新增：检查MusicTag进程是否存在 ======
def is_musictag_process_running():
    """
    检查MusicTag进程是否正在运行
    """
    try:
        import psutil
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and 'musictag' in proc.info['name'].lower():
                return True
        return False
    except ImportError:
        # 如果没有psutil，使用简单的方法
        try:
            subprocess.check_output(['tasklist', '/fi', 'imagename eq MusicTag.exe'], 
                                   shell=True, stderr=subprocess.DEVNULL)
            return True
        except:
            return False

# ====== 新增：查找现有歌词文件 ======
def find_existing_lrc_file(directory, artist, title):
    """
    查找目录中已有的最佳匹配歌词文件
    """
    if not os.path.exists(directory):
        return None
    
    best_match = None
    best_score = 0
    
    for f in os.listdir(directory):
        if f.lower().endswith('.lrc'):
            file_path = os.path.join(directory, f)
            score = calculate_file_match_score(file_path, artist, title)
            
            if score > best_score:
                best_score = score
                best_match = file_path
    
    return best_match

# ====== 新增：等待手动保存 ======
def wait_for_manual_save(directory, artist, title, timeout=60):
    """
    等待用户手动保存歌词文件
    返回：检测到的文件路径，或None
    """
    start_time = time.time()
    check_interval = 1  # 每秒检查一次
    
    print(f"\nWAIT 等待手动保存（{timeout}秒限时）")
    
    # 先等待一小段时间，让可能的文件保存完成
    time.sleep(2)
    
    # 检查是否有新的LRC文件
    new_lrc = find_existing_lrc_file(directory, artist, title)
    
    if new_lrc:
        print(f"\nOK 检测到歌词文件：{os.path.basename(new_lrc)}")
        return new_lrc
    
    while time.time() - start_time < timeout:
        elapsed = int(time.time() - start_time)
        remaining = timeout - elapsed
        
        # 显示倒计时
        print(f"\r[{remaining}秒] 正在检测保存文件...", end="", flush=True)
        
        # 检查是否有新的LRC文件
        new_lrc = find_existing_lrc_file(directory, artist, title)
        
        if new_lrc:
            print(f"\nOK 检测到新文件：{os.path.basename(new_lrc)}")
            return new_lrc
        
        # 检查MusicTag进程是否关闭（用户可能已关闭程序）
        if not is_musictag_process_running():
            print("\nINFO MusicTag已关闭，检查最终文件...")
            time.sleep(2)  # 给文件保存一点时间
            new_lrc = find_existing_lrc_file(directory, artist, title)
            if new_lrc:
                return new_lrc
            break
        
        time.sleep(check_interval)
    
    return None

# ====== 新增：歌词满意度检查 ======
def check_lyric_satisfaction(artist, title):
    """
    歌词满意度检查点
    在点击确定按钮后、保存之前调用
    返回：True如果自动继续，False如果进入手动模式
    """
    print("\n" + "="*60)
    print("TARGET 请确认歌词是否满意！可手动选择")
    print("="*60)
    print("当前歌词预览已显示在MusicTag中")
    print("\n您可以：")
    print("  1. 如果满意，等待5秒自动继续")
    print("  2. 如果不满意，现在手动选择正确歌词")
    print("  3. 手动操作后，程序会自动检测您保存的文件")
    print("\n提示：手动操作时请确保最终保存LRC文件")
    print("="*60)
    
    print(f"\nWAIT 歌词确认倒计时（{LYRIC_CONFIRM_TIMEOUT}秒）：")
    
    # 倒计时循环，同时检测鼠标活动
    for i in range(LYRIC_CONFIRM_TIMEOUT, 0, -1):
        print(f"\r[{i}]秒后自动继续...", end="", flush=True)
        
        # 检测鼠标活动
        mouse_moved = detect_mouse_movement(sample_interval=0.5)
        
        if mouse_moved:
            print(f"\n\nWARN 检测到鼠标活动，进入手动操作模式...")
            return False  # 进入手动模式
        
        time.sleep(1)
    
    print("\n\nOK 歌词确认完成，继续自动保存...")
    return True  # 自动继续

# ====== 新增：处理手动操作模式 ======
def handle_manual_operation(artist, title):
    """
    处理手动操作模式
    返回：检测到的歌词文件路径，或None
    """
    print("\n" + "="*60)
    print("OK 已进入手动操作模式")
    print("="*60)
    print("手动操作指引：")
    print("  1. 您现在可以完全控制MusicTag界面")
    print("  2. 请选择正确的歌词并保存")
    print("  3. 点击另存为Lrc按钮")
    print(f"  4. 保存位置会自动检测，默认在：")
    print(f"     {TEMP_MP3_DIR}")
    print(f"\n程序将等待{MANUAL_OPERATION_TIMEOUT}秒，检测到保存文件后自动继续")
    print("="*60)
    
    # 给用户3秒准备时间
    print("\nWAIT 准备手动操作...")
    for i in range(3, 0, -1):
        print(f"\r[{i}]", end="", flush=True)
        time.sleep(1)
    
    print("\n\nMANUAL 开始手动操作")
    
    # 等待用户手动保存
    manual_lrc = wait_for_manual_save(TEMP_MP3_DIR, artist, title, MANUAL_OPERATION_TIMEOUT)
    
    if manual_lrc:
        print(f"OK 检测到手动保存的文件：{os.path.basename(manual_lrc)}")
        return manual_lrc
    else:
        print(f"TIMEOUT {MANUAL_OPERATION_TIMEOUT}秒超时，未检测到手动保存的歌词")
        return None

# ====== 以下是原有的函数，保持不变 ======
def import_v1_module():
    """动态导入 v1.py 模块"""
    import importlib.util
    
    v1_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v1.py")
    
    if not os.path.exists(v1_path):
        print("ERROR 错误：找不到 v1.py 文件")
        return None
    
    try:
        spec = importlib.util.spec_from_file_location("v1_module", v1_path)
        v1_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(v1_module)
        if SHOW_DETAILED_LOGS:
            print("OK 成功导入 v1.py 模块")
        return v1_module
    except Exception as e:
        print(f"ERROR 导入 v1.py 失败: {e}")
        return None

def extract_internal_subtitles(video_path):
    """提取视频内嵌字幕 - 有效版本"""
    try:
        video_dir = os.path.dirname(video_path)
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        
        print(f"VIDEO 处理视频文件: {os.path.basename(video_path)}")
        
        # 直接尝试提取字幕，不探测轨道信息（简化）
        subtitle_path = os.path.join(video_dir, f"{video_name}_internal.srt")
        
        print(f"NOTE 提取字幕到: {os.path.basename(subtitle_path)}")
        
        # 尝试多种格式
        formats = ['subrip', 'srt']  # subrip优先
        
        for fmt in formats:
            try:
                cmd = [
                    'ffmpeg',
                    '-i', video_path,
                    '-map', '0:s:0',  # 第一个字幕轨道
                    '-c:s', fmt,
                    '-y',
                    subtitle_path
                ]
                
                # 运行命令，隐藏输出
                with open(os.devnull, 'w') as devnull:
                    result = subprocess.run(cmd, stdout=devnull, stderr=devnull)
                
                if os.path.exists(subtitle_path) and os.path.getsize(subtitle_path) > 100:
                    file_size = os.path.getsize(subtitle_path)
                    print(f"OK 成功提取内嵌字幕 ({file_size} 字节，格式: {fmt})")
                    
                    # 清理HTML标签（如果存在）
                    if clean_html_tags(subtitle_path):
                        print("OK 已清理字幕中的HTML标签")
                    
                    return subtitle_path
                    
            except Exception as e:
                continue
        
        print("ERROR 字幕提取失败")
        return None
            
    except Exception as e:
        print(f"ERROR 提取内嵌字幕失败: {e}")
        return None

def clean_html_tags(srt_path):
    """清理SRT文件中的HTML标签"""
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 移除常见的HTML标签
        html_patterns = [
            (r'<font[^>]*>', ''),      # <font>标签
            (r'</font>', ''),          # </font>标签
            (r'<b>', ''),              # <b>标签
            (r'</b>', ''),             # </b>标签
            (r'<i>', ''),              # <i>标签
            (r'</i>', ''),             # </i>标签
            (r'<u>', ''),              # <u>标签
            (r'</u>', ''),             # </u>标签
            (r'<color=[^>]*>', ''),    # <color=...>标签
            (r'</color>', ''),         # </color>标签
            (r'<size=[^>]*>', ''),     # <size=...>标签
            (r'</size>', ''),          # </size>标签
            (r'<face=[^>]*>', ''),     # <face=...>标签
            (r'</face>', ''),          # </face>标签
            (r'\{\\an[0-9]\}', ''),    # ASS对齐标签
        ]
        
        cleaned = content
        for pattern, replacement in html_patterns:
            cleaned = re.sub(pattern, replacement, cleaned)
        
        # 如果内容有变化，保存
        if cleaned != original_content:
            with open(srt_path, 'w', encoding='utf-8') as f:
                f.write(cleaned)
            return True
        else:
            return False
            
    except Exception as e:
        print(f"ERROR 清理HTML标签失败: {e}")
        return False

def parse_time_to_seconds(time_str):
    """将时间字符串转换为秒数"""
    try:
        time_str = time_str.strip()
        
        # 处理空字符串情况
        if not time_str:
            print(f"时间解析失败: 空字符串")
            return 0
            
        if ',' in time_str:
            time_str = time_str.replace(',', '.')
        
        if '.' in time_str:
            main_part, ms_part = time_str.split('.', 1)
            milliseconds = int(ms_part[:3].ljust(3, '0'))
        else:
            main_part = time_str
            milliseconds = 0
        
        segments = main_part.split(':')
        
        if len(segments) == 3:
            hours = int(segments[0]) if segments[0] else 0
            minutes = int(segments[1]) if segments[1] else 0
            seconds = int(segments[2]) if segments[2] else 0
        elif len(segments) == 2:
            hours = 0
            minutes = int(segments[0]) if segments[0] else 0
            seconds = int(segments[1]) if segments[1] else 0
        else:
            hours = 0
            minutes = 0
            seconds = int(segments[0]) if segments[0] else 0
        
        total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000
        return total_seconds
    except Exception as e:
        print(f"时间解析失败: {time_str}, 错误: {e}")
        return 0

def seconds_to_srt_time(seconds):
    """将秒数转换为SRT时间格式"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"

def get_srt_time_info_start_only(srt_path):
    """获取SRT文件的时间信息 - 只关注开始时间"""
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 匹配开始时间，支持非标准格式（1-2位小时/分钟/秒，1-3位毫秒）
        pattern = r'(\d{1,2}:\d{1,2}:\d{1,2},\d{1,3})\s*-->\s*\d{1,2}:\d{1,2}:\d{1,2},\d{1,3}'
        matches = re.findall(pattern, content)
        
        if not matches:
            return None, None
        
        first_start = parse_time_to_seconds(matches[0])
        last_start = parse_time_to_seconds(matches[-1])
        
        if SHOW_DETAILED_LOGS:
            print(f"  文件分析: 共{len(matches)}条字幕")
            print(f"  第一句开始时间: {matches[0]} ({first_start:.3f}s)")
            print(f"  最后一句开始时间: {matches[-1]} ({last_start:.3f}s)")
        
        return first_start, last_start  # 只返回开始时间
    except Exception as e:
        print(f"读取SRT文件失败: {e}")
        return None, None

def get_vtt_time_info_start_only(vtt_path):
    """获取VTT文件的时间信息 - 只关注开始时间，处理内部时间标签"""
    try:
        with open(vtt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 分割VTT文件为多个cue
        content = content.replace('\r\n', '\n')
        cues = re.split(r'\n\n+', content.strip())
        
        valid_start_times = []
        cues_with_internal_time = []
        
        for cue in cues:
            lines = cue.strip().split('\n')
            if not lines:
                continue
            
            # 查找cue的时间行
            time_line = None
            time_line_index = 0
            for i, line in enumerate(lines):
                if '-->' in line:
                    time_line = line
                    time_line_index = i
                    break
            
            if not time_line:
                continue
            
            # 提取cue的开始时间
            cue_start_match = re.search(r'(\d{2}:\d{2}:\d{2}[.,]\d{3}|\d{2}:\d{2}[.,]\d{3})\s*-->', time_line)
            if not cue_start_match:
                continue
            
            cue_start_time = cue_start_match.group(1).strip()
            
            # 提取cue文本
            cue_text_lines = lines[time_line_index+1:] if len(lines) > time_line_index+1 else []
            # 合并并清理cue文本
            cue_text = ' '.join([line.strip() for line in cue_text_lines if line.strip()])
            
            # 检查cue文本是否为空（忽略纯空格和换行）
            if not cue_text or cue_text.strip() == '':
                continue
            
            # 检查cue文本是否只包含特殊标记（如[음악]等）
            if re.match(r'^\[[^\]]+\]$', cue_text.strip()):
                continue
            
            # 检查cue文本中是否包含内部时间标签（如 <00:00:22.680>）
            internal_time_matches = re.findall(r'<(\d{2}:\d{2}:\d{2}[.,]\d{3})>', cue_text)
            
            if internal_time_matches:
                # 使用第一个内部时间标签作为有效开始时间
                valid_start = internal_time_matches[0]
                start_seconds = parse_time_to_seconds(valid_start)
                valid_start_times.append(start_seconds)
                # 记录带有内部时间标签的cue
                cues_with_internal_time.append(start_seconds)
            else:
                # 检查cue是否可能是过渡性的（持续时间极短）
                cue_end_match = re.search(r'-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3}|\d{2}:\d{2}[.,]\d{3})', time_line)
                if cue_end_match:
                    end_time = cue_end_match.group(1).strip()
                    start_seconds = parse_time_to_seconds(cue_start_time)
                    end_seconds = parse_time_to_seconds(end_time)
                    duration = end_seconds - start_seconds
                    
                    # 只接受持续时间大于0.1秒的cue，跳过可能的过渡性cue
                    if duration > 0.1:
                        valid_start_times.append(start_seconds)
                else:
                    # 否则使用cue的开始时间
                    start_seconds = parse_time_to_seconds(cue_start_time)
                    valid_start_times.append(start_seconds)
        
        if not valid_start_times:
            return None, None
        
        # 过滤掉0或负数的时间值（可能是无效的内部时间标签）
        valid_start_times = [t for t in valid_start_times if t > 0]
        
        if not valid_start_times:
            return None, None
        
        # 如果有带有内部时间标签的cue，优先使用它们
        if cues_with_internal_time:
            # 按时间排序
            cues_with_internal_time.sort()
            # 使用第一个带有内部时间标签的cue作为开始时间
            first_start = cues_with_internal_time[0]
        else:
            # 否则使用所有有效开始时间的最早值
            valid_start_times.sort()
            first_start = valid_start_times[0]
        
        # 始终使用最晚的有效开始时间
        last_start = max(valid_start_times)
        
        return first_start, last_start
    except Exception as e:
        print(f"读取VTT文件失败: {e}")
        return None, None

def get_ass_time_info_start_only(ass_path):
    """获取ASS文件的时间信息 - 只关注开始时间"""
    try:
        with open(ass_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # ASS格式的时间轴行通常以 "Dialogue:" 开头
        pattern = r'Dialogue:\s*\d+,\s*(\d+:\d+:\d+[.,]\d+),\d+:\d+:\d+[.,]\d+'
        matches = re.findall(pattern, content)
        
        if not matches:
            # 尝试更宽松的匹配
            pattern = r'(\d+:\d+:\d+[.,]\d+),\d+:\d+:\d+[.,]\d+'
            matches = re.findall(pattern, content)
        
        if not matches:
            return None, None
        
        first_start = parse_time_to_seconds(matches[0])
        last_start = parse_time_to_seconds(matches[-1])
        
        return first_start, last_start
    except Exception as e:
        print(f"读取ASS文件失败: {e}")
        return None, None

def preview_subtitles_simple(srt_path, num_lines=5, description=""):
    """预览SRT文件的内容 - 简化版，按指定格式显示"""
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"\nCHART {description} 字幕预览:")
        print("-" * 70)
        
        # 解析SRT格式
        subtitles = []
        current_sub = {}
        
        for line in lines:
            line = line.strip()
            
            if not line:
                if current_sub:
                    subtitles.append(current_sub)
                    current_sub = {}
                continue
            
            if 'index' not in current_sub and line.isdigit():
                current_sub['index'] = int(line)
            elif '-->' in line:
                current_sub['timeline'] = line
            elif 'text' not in current_sub:
                current_sub['text'] = line
            else:
                # 有多行文本的情况
                current_sub['text'] += ' ' + line
        
        if current_sub:
            subtitles.append(current_sub)
        
        print(f"总字幕数: {len(subtitles)} 条\n")
        
        # 显示前N条字幕
        for i in range(min(num_lines, len(subtitles))):
            sub = subtitles[i]
            idx = sub.get('index', i+1)
            timeline = sub.get('timeline', '00:00:00,000 --> 00:00:00,000')
            text = sub.get('text', '')
            
            # 按指定格式输出
            print(f"  {idx}. {timeline} - {text}")
        
        # 如果字幕数量超过显示数量，也显示最后几条
        if len(subtitles) > num_lines:
            print(f"\n... 中间省略 {len(subtitles) - num_lines * 2} 条 ...\n")
            
            # 显示最后几条
            start_idx = max(num_lines, len(subtitles) - num_lines)
            for i in range(start_idx, len(subtitles)):
                sub = subtitles[i]
                idx = sub.get('index', i+1)
                timeline = sub.get('timeline', '00:00:00,000 --> 00:00:00,000')
                text = sub.get('text', '')
                
                print(f"  {idx}. {timeline} - {text}")
        
        # 显示时间信息
        if subtitles:
            first_sub = subtitles[0]
            last_sub = subtitles[-1]
            
            first_start = first_sub.get('timeline', '').split('-->')[0].strip()
            last_start = last_sub.get('timeline', '').split('-->')[1].strip()
            
            if first_start and last_start:
                first_start_sec = parse_time_to_seconds(first_start)
                last_start_sec = parse_time_to_seconds(last_start)
                duration = last_start_sec - first_start_sec
                
                print(f"\n时间范围: {first_start} ~ {last_start}")
                print(f"开始时间跨度: {duration:.3f}秒 ({duration/60:.2f}分钟)")
        
        print("-" * 70)
        return True
        
    except Exception as e:
        print(f"预览字幕失败: {e}")
        return False

def adjust_subtitle_timing(srt_path, ref_path):
    """
    根据参考字幕时间轴整体偏移SRT字幕 - 优化版，只对比开始时间
    """
    print("\n" + "="*60)
    print("TOOL 开始字幕时间轴对齐")
    print("="*60)
    
    # 使用简化的预览函数
    preview_subtitles_simple(srt_path, 5, "歌词SRT")
    preview_subtitles_simple(ref_path, 5, "参考字幕")
    
    # 获取参考字幕的时间信息 - 只关注开始时间
    ref_ext = os.path.splitext(ref_path)[1].lower()
    
    if ref_ext == '.vtt':
        ref_first_start, ref_last_start = get_vtt_time_info_start_only(ref_path)
        ref_type = "VTT"
    elif ref_ext == '.srt':
        ref_first_start, ref_last_start = get_srt_time_info_start_only(ref_path)
        ref_type = "SRT"
    elif ref_ext == '.ass':
        ref_first_start, ref_last_start = get_ass_time_info_start_only(ref_path)
        ref_type = "ASS"
    elif ref_ext == '.ssa':
        ref_first_start, ref_last_start = get_ass_time_info_start_only(ref_path)
        ref_type = "SSA"
    else:
        print(f"ERROR 不支持的参考字幕格式: {ref_ext}")
        print(f"OK 跳过时间轴对齐，直接使用歌词SRT")
        return True, srt_path, 999
    
    if ref_first_start is None:
        print("ERROR 无法获取参考字幕时间信息")
        print(f"OK 跳过时间轴对齐，直接使用歌词SRT")
        return True, srt_path, 999
    
    # 获取歌词SRT的时间信息 - 只关注开始时间
    srt_first_start, srt_last_start = get_srt_time_info_start_only(srt_path)
    if srt_first_start is None:
        print("ERROR 无法获取SRT时间信息")
        return False, srt_path, 0
    
    # 对于歌词SRT，我们只关心开始时间的偏移
    offset = ref_first_start - srt_first_start
    
    print(f"\nCHART 时间分析 (只对比开始时间):")
    print(f"  参考{ref_type}第一句开始: {ref_first_start:.3f}s")
    print(f"  歌词第一句开始: {srt_first_start:.3f}s")
    print(f"  偏移量: {offset:.3f}s")
    
    # 计算开始时间的分布范围
    lyric_start_range = srt_last_start - srt_first_start
    ref_start_range = ref_last_start - ref_first_start
    
    print(f"\nCHART 开始时间分布范围:")
    print(f"  歌词开始时间范围: {srt_first_start:.3f}s ~ {srt_last_start:.3f}s")
    print(f"  参考开始时间范围: {ref_first_start:.3f}s ~ {ref_last_start:.3f}s")
    print(f"  歌词开始时间跨度: {lyric_start_range:.3f}s")
    print(f"  参考{ref_type}开始时间跨度: {ref_start_range:.3f}s")
    
    start_range_diff = abs(lyric_start_range - ref_start_range)
    print(f"  开始时间跨度差异: {start_range_diff:.3f}s")
    
    if abs(offset) < 0.001:  # 小于1毫秒的差异视为无需调整
        print("OK 无需调整")
        return True, srt_path, start_range_diff
    
    # 备份原始文件
    backup_path = srt_path.replace('.srt', '_原始.srt')
    try:
        shutil.copy2(srt_path, backup_path)
        print(f"NOTE 已备份: {backup_path}")
    except Exception as e:
        print(f"WARN 备份失败: {e}")
    
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        adjusted_lines = []
        for line in lines:
            time_match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', line)
            if time_match:
                start_time = parse_time_to_seconds(time_match.group(1))
                end_time = parse_time_to_seconds(time_match.group(2))
                
                # 只调整开始时间，结束时间保持相对间隔
                start_time += offset
                end_time += offset  # 保持相同的偏移，维持相对时间差
                
                # 确保时间不为负数
                start_time = max(0, start_time)
                end_time = max(0, end_time)
                
                # 对于歌词SRT，确保结束时间至少比开始时间晚一些
                if end_time <= start_time:
                    end_time = start_time + 0.1  # 至少100毫秒
                
                new_start = seconds_to_srt_time(start_time)
                new_end = seconds_to_srt_time(end_time)
                
                line = f"{new_start} --> {new_end}\n"
            
            adjusted_lines.append(line)
        
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.writelines(adjusted_lines)
        
        # 获取调整后的时间信息
        new_first_start, new_last_start = get_srt_time_info_start_only(srt_path)
        
        print(f"\nOK 时间轴调整完成 (只调整开始时间):")
        print(f"  调整后歌词第一句开始: {new_first_start:.3f}s")
        print(f"  调整后歌词最后一句开始: {new_last_start:.3f}s")
        print(f"  调整后歌词开始时间跨度: {new_last_start - new_first_start:.3f}s")
        print(f"  目标{ref_type}第一句开始: {ref_first_start:.3f}s")
        print(f"  目标{ref_type}最后一句开始: {ref_last_start:.3f}s")
        
        # 计算调整后的开始时间差异
        new_lyric_start_range = new_last_start - new_first_start
        new_start_diff = abs(new_lyric_start_range - ref_start_range)
        
        print(f"\nCHART 调整后对比 (只对比开始时间):")
        print(f"  歌词开始时间跨度: {new_lyric_start_range:.3f}s")
        print(f"  参考{ref_type}开始时间跨度: {ref_start_range:.3f}s")
        print(f"  开始时间跨度差异: {new_start_diff:.3f}s")
        
        # 警告阈值只针对开始时间跨度
        if new_start_diff > TIME_DIFF_WARNING_THRESHOLD:
            print(f"\nWARN  【注意】歌词与参考字幕开始时间跨度差异较大")
            print(f"  差异: {new_start_diff:.2f}s (超过 {TIME_DIFF_WARNING_THRESHOLD}s)")
            print(f"  建议检查是否需要人工调整")
        else:
            print(f"\nOK 开始时间跨度差异在可接受范围内")
        
        # 预览调整后的字幕
        preview_subtitles_simple(srt_path, 5, "调整后歌词")
        
        # 清理备份文件
        try:
            if os.path.exists(backup_path):
                os.remove(backup_path)
                print(f"CLEAN 已清理备份文件")
        except Exception as e:
            print(f"WARN 清理备份文件失败: {e}")
        
        return True, srt_path, new_start_diff
        
    except Exception as e:
        print(f"ERROR 调整失败: {e}")
        import traceback
        traceback.print_exc()
        # 恢复备份
        try:
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, srt_path)
                print("已恢复原始文件")
                os.remove(backup_path)
        except:
            pass
        return False, srt_path, 0

# ====== 简化版Z打包函数 ======
def process_with_z_packaging(srt_path):
    """调用Z.py进行打包处理 - 简化版本"""
    print("\n" + "="*60)
    print("PACK 开始Z打包处理")
    print("="*60)
    
    if not os.path.exists(Z_SCRIPT_PATH):
        print(f"ERROR 错误：找不到Z.py脚本: {Z_SCRIPT_PATH}")
        return False
    
    try:
        cmd = [sys.executable, Z_SCRIPT_PATH, srt_path]
        
        print(f"TOOL 调用Z.py命令: {' '.join(cmd)}")
        print(f"FILE 字幕文件: {os.path.basename(srt_path)}")
        print("TIP Z.py将自动查找同名视频文件进行处理")
        print("\n" + "-"*60)
        print("Z.py输出:")
        print("-"*60)
        
        # 直接执行
        process = subprocess.Popen(
            cmd,
            stdout=None,
            stderr=None,
            universal_newlines=True,
            bufsize=1
        )
        
        timeout_seconds = 600
        try:
            return_code = process.wait(timeout=timeout_seconds)
            
            print(f"\nOK Z.py执行完成，返回码: {return_code}")
            
            return return_code == 0
                
        except subprocess.TimeoutExpired:
            print(f"ERROR Z.py执行超时 ({timeout_seconds}秒)")
            process.kill()
            return False
            
    except Exception as e:
        print(f"ERROR 调用Z.py时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def process_lrc_with_v1(lrc_path, output_dir=None):
    """
    使用 v1.py 处理 LRC 文件
    """
    if SHOW_DETAILED_LOGS:
        print(f"\nLOOP 开始处理 LRC 文件: {os.path.basename(lrc_path)}")
    
    v1_module = import_v1_module()
    if not v1_module:
        print("ERROR 无法加载 v1 处理模块")
        return False
    
    try:
        if not os.path.exists(lrc_path):
            print(f"ERROR LRC 文件不存在: {lrc_path}")
            return False
        
        original_lrc_path = lrc_path
        
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
            if SAVE_ORIGINAL_LRC == 1:
                target_lrc = os.path.join(output_dir, os.path.basename(lrc_path))
                try:
                    shutil.copy2(lrc_path, target_lrc)
                    if SHOW_DETAILED_LOGS:
                        print(f"FILE 已复制原始LRC到输出目录: {target_lrc}")
                    lrc_path = target_lrc
                except Exception as e:
                    print(f"ERROR 复制LRC文件失败: {e}")
        
        lrc_path = os.path.abspath(lrc_path)
        original_dir = os.getcwd()
        lrc_dir = os.path.dirname(lrc_path)
        os.chdir(lrc_dir)
        
        success = v1_module.process_single_file(lrc_path)
        os.chdir(original_dir)
        
        if success:
            base_name = os.path.splitext(lrc_path)[0]
            srt_source = base_name + ".srt"
            
            if os.path.exists(srt_source):
                if output_dir and os.path.dirname(srt_source) != os.path.abspath(output_dir):
                    srt_target = os.path.join(output_dir, os.path.basename(srt_source))
                    try:
                        shutil.move(srt_source, srt_target)
                        if SHOW_DETAILED_LOGS:
                            print(f"PACK 已将SRT文件移动到输出目录: {srt_target}")
                    except Exception as e:
                        print(f"ERROR 移动SRT文件失败: {e}")
                        try:
                            shutil.copy2(srt_source, srt_target)
                            os.remove(srt_source)
                            if SHOW_DETAILED_LOGS:
                                print(f"NOTE 已复制SRT文件到输出目录: {srt_target}")
                        except Exception as e2:
                            print(f"ERROR 复制SRT文件也失败: {e2}")
                            return False
                elif SHOW_DETAILED_LOGS:
                    print(f"OK SRT文件已生成: {srt_source}")
                
                if SAVE_ORIGINAL_LRC == 0 and output_dir:
                    try:
                        if os.path.exists(lrc_path) and lrc_path != original_lrc_path:
                            os.remove(lrc_path)
                            if SHOW_DETAILED_LOGS:
                                print(f"CLEAN 已清理临时LRC文件: {lrc_path}")
                    except Exception as e:
                        print(f"WARN 清理临时LRC文件失败: {e}")
                
                return True
            else:
                print(f"ERROR 未找到生成的SRT文件: {srt_source}")
                return False
        else:
            print("ERROR LRC 文件处理失败")
            return False
            
    except Exception as e:
        print(f"ERROR 处理 LRC 文件时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def clean_filename_for_search(filename):
    """清理文件名用于搜索，移除括号等内容"""
    name = os.path.splitext(os.path.basename(filename))[0]
    
    # 移除括号及其内容，包括中文和英文括号
    name = re.sub(r'[\(\（\[\【].*?[\]\】\)\）]', '', name)
    
    # 移除常见后缀
    name = re.sub(r'\.(srt|vtt|ass|ssa|lrc|mp4|mkv|avi|mov|flv|wmv|webm)$', '', name, flags=re.IGNORECASE)
    
    # 移除多余的空格
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name

def parse_artist_title(filename):
    """解析文件名 - 支持多种分隔符，先清理文件名"""
    # 先清理文件名
    clean_name = clean_filename_for_search(filename)
    
    if not clean_name:
        # 如果清理后为空，使用原始文件名（不含扩展名）
        clean_name = os.path.splitext(os.path.basename(filename))[0]
        clean_name = re.sub(r'[\(\（\[\【].*?[\]\】\)\）]', '', clean_name).strip()
    
    print(f"NOTE 清理后的文件名: {clean_name}")
    
    # 支持的多种分隔符
    separators = [" - ", "_", "——", "—", "–", "-"]
    
    for sep in separators:
        if sep in clean_name:
            try:
                parts = clean_name.split(sep, 1)
                if len(parts) == 2:
                    artist = parts[0].strip()
                    title = parts[1].strip()
                    
                    # 进一步清理标题中的括号内容
                    title = re.sub(r'[\(\（\[\【].*?[\]\】\)\）]', '', title).strip()
                    
                    if artist and title:
                        print(f"OK 解析为: {artist} - {title}")
                        return artist, title
            except:
                pass
    
    # 如果没有找到分隔符，尝试其他格式
    # 格式: 歌名(歌手)
    match = re.search(r'(.+?)\s*[\(\（](.+?)[\)\）]', clean_name)
    if match:
        title = match.group(1).strip()
        artist = match.group(2).strip()
        if artist and title:
            print(f"OK 解析为(括号格式): {artist} - {title}")
            return artist, title
    
    # 如果只有一个部分，可能是纯歌名
    if clean_name:
        print(f"WARN 无法确定歌手，将使用清理后的文件名作为歌名")
        print(f"   歌名: {clean_name}")
        
        return "未知歌手", clean_name
    
    # 最后尝试：使用原始文件名
    original_name = os.path.splitext(os.path.basename(filename))[0]
    print(f"WARN 使用原始文件名: {original_name}")
    return "未知歌手", original_name

def create_silent_mp3(artist, title):
    """生成静音MP3"""
    os.makedirs(TEMP_MP3_DIR, exist_ok=True)
    
    safe_artist = re.sub(r'[<>:"/\\|?*]', '_', artist)
    safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
    
    mp3_path = os.path.join(TEMP_MP3_DIR, f"{safe_artist} - {safe_title}.mp3")
    
    silent = Sine(1).to_audio_segment(duration=1000) - 120
    silent.export(mp3_path, format="mp3", bitrate="64k")
    if SHOW_DETAILED_LOGS:
        print(f"OK 已生成静音MP3: {mp3_path}")
    return mp3_path

def locate_and_click(image_path, element_name, timeout=5, offset_x=0, offset_y=0):
    """图像识别定位并点击"""
    try:
        if not os.path.exists(image_path):
            print(f"   缺少截图: {os.path.basename(image_path)}")
            return False
            
        if SHOW_DETAILED_LOGS:
            print(f"SEARCH 定位: {element_name}")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                location = pyautogui.locateOnScreen(image_path, confidence=CONFIDENCE)
                if location:
                    center = pyautogui.center(location)
                    
                    click_x = center.x + offset_x
                    click_y = center.y + offset_y
                    
                    pyautogui.moveTo(click_x, click_y, duration=0.3)
                    time.sleep(0.1)
                    pyautogui.click()
                    if SHOW_DETAILED_LOGS:
                        print(f"   OK 已点击: {element_name} (位置: {click_x}, {click_y})")
                    time.sleep(0.5)
                    return True
            except:
                pass
            time.sleep(0.5)
        
        print(f"   ERROR 未找到: {element_name}")
        return False
    except Exception as e:
        print(f"   定位 {element_name} 出错: {e}")
        return False

def select_file_by_image():
    """通过文件列表截图选择文件"""
    if SHOW_DETAILED_LOGS:
        print("FILE 通过截图选择文件")
    
    if not os.path.exists(FILE_LIST_IMG):
        print("   ERROR 缺少文件列表截图: file_list.png")
        return False
    
    try:
        location = pyautogui.locateOnScreen(FILE_LIST_IMG, confidence=0.6, minSearchTime=3)
        
        if location:
            if SHOW_DETAILED_LOGS:
                print(f"   OK 找到文件列表区域: {location}")
            
            file_x = location.left + location.width // 2
            
            y_positions = [
                location.top + 40,
                location.top + 50,
                location.top + 60,
            ]
            
            for i, file_y in enumerate(y_positions, 1):
                if SHOW_DETAILED_LOGS:
                    print(f"   尝试点击位置 {i}: ({file_x}, {file_y})")
                
                pyautogui.moveTo(file_x, file_y, duration=0.3)
                pyautogui.click()
                time.sleep(0.3)
                
                pyautogui.doubleClick()
                time.sleep(0.5)
                
                if SHOW_DETAILED_LOGS:
                    print(f"   OK 已尝试点击文件位置")
                return True
            
            return True
        else:
            print("   ERROR 未找到文件列表区域")
            return False
            
    except Exception as e:
        print(f"   定位文件列表失败: {e}")
        return False

def click_lyrics_icon():
    """点击歌词图标"""
    if SHOW_DETAILED_LOGS:
        print("\nNOTE 点击歌词图标")
    if locate_and_click(LYRIC_ICON, "歌词图标"):
        return True
    return False

def click_search_button():
    """点击搜索按钮"""
    if SHOW_DETAILED_LOGS:
        print("\nSEARCH 搜索歌词")
    if locate_and_click(SEARCH_BTN, "搜索按钮"):
        return True
    return False

def select_best_lyric_match(artist, title):
    """智能选择最佳歌词匹配 - 只选择前4行，避免模糊错误歌词"""
    if SHOW_DETAILED_LOGS:
        print(f"\nTARGET 智能选择歌词: {artist} - {title}")
        print(f"   由于无法识别文本，只选择前{MAX_SELECTABLE_ROWS}行")
    
    # 策略1：优先尝试图像识别QQ源（如果截图存在）
    if os.path.exists(LRC_QQ_ROW):
        print("\n   尝试策略1: 图像识别QQ源")
        if select_qq_row_by_image():
            if SHOW_DETAILED_LOGS:
                print("     已通过图像识别选择QQ源")
            return True
        else:
            print("     图像识别QQ源失败，尝试其他策略")
    
    # 策略2：按预设顺序尝试前4行
    strategies = [
        {"name": "第1行（通常为QQ源）", "row": 1, "priority": 1.0},
        {"name": "第2行（通常为网易云源）", "row": 2, "priority": 0.8},
        {"name": "第3行（通常为酷狗源）", "row": 3, "priority": 0.6},
        {"name": "第4行（其他源）", "row": 4, "priority": 0.4},
    ]
    
    # 只尝试前MAX_SELECTABLE_ROWS行
    strategies = strategies[:MAX_SELECTABLE_ROWS]
    
    for strategy in strategies:
        print(f"\n   尝试策略: {strategy['name']}")
        
        if select_result_row(strategy['row']):
            if SHOW_DETAILED_LOGS:
                print(f"     已选择第{strategy['row']}行")
            return True
    
    print("   ERROR 所有选择策略都失败")
    return False

def select_qq_row_by_image(timeout=3):
    """通过图像识别选择QQ源歌词行（如果截图存在）"""
    if not os.path.exists(LRC_QQ_ROW):
        return False
        
    try:
        if SHOW_DETAILED_LOGS:
            print("   SEARCH 图像识别QQ源...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                location = pyautogui.locateOnScreen(LRC_QQ_ROW, confidence=CONFIDENCE)
                if location:
                    center = pyautogui.center(location)
                    pyautogui.moveTo(center.x, center.y, duration=0.3)
                    time.sleep(0.1)
                    pyautogui.click()
                    time.sleep(0.1)
                    
                    # 确认选择
                    pyautogui.press('enter')
                    if SHOW_DETAILED_LOGS:
                        print(f"     OK 已通过图像识别选择QQ源")
                    return True
            except:
                time.sleep(0.5)
                continue
        
        return False
    except Exception as e:
        print(f"     图像识别QQ源失败: {e}")
        return False

def extract_keywords(text):
    """提取关键词（用于模糊匹配）"""
    text_lower = text.lower().strip()
    
    if any(c.isascii() and c.isalpha() for c in text):
        words = text_lower.split()
        if len(words) >= 2:
            return words[:2]
        else:
            return words
    
    if len(text_lower) >= 4:
        return [text_lower[:2], text_lower[:4]]
    else:
        return [text_lower]

def select_result_row(row_number):
    """选择搜索结果中的指定行"""
    try:
        if SHOW_DETAILED_LOGS:
            print(f"     选择第{row_number}行...")
        
        # 先按Home键确保回到顶部
        pyautogui.press('home')
        time.sleep(0.1)
        
        # 向下移动到指定行
        for i in range(row_number - 1):
            pyautogui.press('down')
            time.sleep(0.1)
        
        # 确认选择
        pyautogui.press('enter')
        time.sleep(0.3)
        
        if SHOW_DETAILED_LOGS:
            print(f"     已选择第{row_number}行")
        return True
    except Exception as e:
        print(f"     选择第{row_number}行失败: {e}")
        return False

def click_confirm_button():
    """点击确定按钮"""
    if SHOW_DETAILED_LOGS:
        print("\nOK 点击确定按钮")
    if locate_and_click(CONFIRM_BTN, "确定按钮"):
        return True
    return False

def save_as_lrc():
    """保存LRC"""
    if SHOW_DETAILED_LOGS:
        print("\nSAVE 保存LRC文件")
    if locate_and_click(SAVE_LRC_BTN, "另存为LRC"):
        return True
    return False

def kill_musictag_process():
    """结束MusicTag进程"""
    if SHOW_DETAILED_LOGS:
        print("\nKILL 结束MusicTag进程...")
    try:
        result = subprocess.run(
            ["taskkill", "/f", "/im", "MusicTag.exe"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 or "成功" in result.stdout or "terminated" in result.stdout.lower():
            if SHOW_DETAILED_LOGS:
                print("   OK 已结束MusicTag进程")
            return True
        else:
            print(f"   结束进程失败: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("   结束进程超时")
        return False
    except Exception as e:
        print(f"   结束进程出错: {e}")
        return False

def verify_lyrics_file(lrc_path, artist, title):
    """验证LRC文件是否正确"""
    if SHOW_DETAILED_LOGS:
        print(f"\nSEARCH 验证歌词文件: {os.path.basename(lrc_path)}")
    
    if not os.path.exists(lrc_path):
        print("   ERROR LRC文件不存在")
        return False
    
    try:
        # 直接使用UTF-8读取，因为我们已经转换过了
        with open(lrc_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        file_size = os.path.getsize(lrc_path)
        if file_size < 50:
            print("   WARN  文件可能为空或过小")
            return False
        
        lyric_markers = ["[ti:", "[ar:", "[al:", "[by:", "[00:"]
        has_markers = any(marker in content for marker in lyric_markers)
        
        if not has_markers:
            print("   WARN  未找到标准歌词标签")
        
        artist_keywords = extract_keywords(artist)
        title_keywords = extract_keywords(title)
        
        artist_in_file = any(keyword.lower() in content.lower() for keyword in artist_keywords)
        title_in_file = any(keyword.lower() in content.lower() for keyword in title_keywords)
        
        if artist_in_file or title_in_file:
            if SHOW_DETAILED_LOGS:
                print(f"   OK 歌词文件包含歌曲信息")
            return True
        else:
            print("   WARN  歌词文件可能不匹配当前歌曲")
            return False
            
    except Exception as e:
        print(f"   验证歌词文件失败: {e}")
        return False

def fix_lyrics_encoding(lrc_path):
    """修复歌词文件的编码问题 - 专门处理UTF-16 BOM问题"""
    try:
        print(f"TOOL 修复歌词文件编码: {os.path.basename(lrc_path)}")
        
        # 1. 以二进制读取文件
        with open(lrc_path, 'rb') as f:
            raw_data = f.read()
        
        # 2. 检查BOM并解码
        if raw_data.startswith(b'\xff\xfe'):
            # UTF-16 LE BOM - 你的文件就是这个编码
            content = raw_data[2:].decode('utf-16-le', errors='ignore')
            print("检测到UTF-16 LE BOM编码，正在转换...")
        elif raw_data.startswith(b'\xfe\xff'):
            # UTF-16 BE BOM
            content = raw_data[2:].decode('utf-16-be', errors='ignore')
            print("检测到UTF-16 BE BOM编码，正在转换...")
        elif raw_data.startswith(b'\xef\xbb\xbf'):
            # UTF-8 BOM
            content = raw_data[3:].decode('utf-8', errors='ignore')
            print("检测到UTF-8 BOM编码，正在转换...")
        else:
            # 没有BOM，尝试UTF-8
            try:
                content = raw_data.decode('utf-8')
                print("检测到UTF-8编码（无BOM），正在转换...")
            except:
                # 如果UTF-8失败，尝试UTF-16 LE（不带BOM的情况）
                try:
                    content = raw_data.decode('utf-16-le')
                    print("检测到UTF-16 LE编码（无BOM），正在转换...")
                except:
                    # 最后尝试GBK
                    content = raw_data.decode('gbk', errors='ignore')
                    print("使用GBK编码解码...")
        
        # 3. 保存为UTF-8
        with open(lrc_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"OK 已成功转换为UTF-8编码")
        
        # 显示修复后的内容预览
        lines = content.split('\n')
        print("修复后的内容预览:")
        count = 0
        for i, line in enumerate(lines, 1):
            if line.strip():
                count += 1
                print(f"  {count}. {line.strip()}")
                if count >= 5:
                    break
        
        return True
        
    except Exception as e:
        print(f"ERROR 修复歌词文件编码失败: {e}")
        return False

# ====== 修改后的主自动化函数 ======
def automate_musictag(mp3_path, artist, title, output_dir=None):
    """主自动化流程 - 增加歌词满意度检查和手动操作支持"""
    mp3_filename = os.path.basename(mp3_path)
    
    # 创建自动化运行提示窗口
    notification_root, notification_title, notification_info, notification_progress = None, None, None, None
    try:
        print("\nNOTIFY 显示自动化运行提示窗口...")
        notification_root, notification_title, notification_info, notification_progress = create_automation_notification()
        
        if not os.path.exists(MUSICTAG_PATH):
            print(f"ERROR 错误：找不到MusicTag")
            return False
        
        if SHOW_DETAILED_LOGS:
            print(f"LAUNCH 启动MusicTag...")
        process = subprocess.Popen([MUSICTAG_PATH, mp3_path])
        time.sleep(WAIT_OPEN)
        
        # 将MusicTag窗口置顶
        print("\nWINDOW 尝试将MusicTag窗口置顶...")
        make_window_topmost(window_class=MUSICTAG_WINDOW_CLASS)
        
        # 更新通知内容
        update_automation_notification(notification_root, notification_title, notification_info, notification_progress, 
                                      info="正在加载文件...")
        
        if SHOW_DETAILED_LOGS:
            print(f"WAIT 等待文件加载 ({WAIT_FILE_LOAD}秒)...")
        time.sleep(WAIT_FILE_LOAD)
    
        if not select_file_by_image():
            print("   请手动选择文件")
        time.sleep(1)
    
        # 更新通知内容
        update_automation_notification(notification_root, notification_title, notification_info, notification_progress, 
                                      info="正在处理歌词...")
        
        if not click_lyrics_icon():
            print("   请手动点击歌词图标")
        time.sleep(WAIT_UI_LOAD)
    
        if not click_search_button():
            print("   请手动点击搜索按钮")
    
        # ====== 新增：在搜索前提示可手动选择 ======
        print("\n" + "="*60)
        print("WARN  当歌词不满意时可进行手动选择")
        print("="*60)
    
        # 更新通知内容
        update_automation_notification(notification_root, notification_title, notification_info, notification_progress, 
                                      info="正在搜索歌词...")
        
        if SHOW_DETAILED_LOGS:
            print(f"\nWAIT 等待搜索结果 ({WAIT_SEARCH}秒)...")
        time.sleep(WAIT_SEARCH)
    
        if not select_best_lyric_match(artist, title):
            print("   请手动选择正确的歌词")
    
        # 更新通知内容
        update_automation_notification(notification_root, notification_title, notification_info, notification_progress, 
                                      info="正在加载歌词...")
        
        if SHOW_DETAILED_LOGS:
            print(f"WAIT 等待歌词加载 ({WAIT_CONFIRM}秒)...")
        time.sleep(WAIT_CONFIRM)
    
        if not click_confirm_button():
            print("   请手动点击确定按钮")
    
        print("\nOK 点击确定按钮")
        time.sleep(1)
    
        # ====== 新增：歌词满意度检查 ======
        print("\n" + "="*60)
        print("TARGET 请确认歌词是否满意！可手动选择")
        print("="*60)
        print("当前歌词预览已显示在MusicTag中")
        print("\n您可以：")
        print("  1. 如果满意，等待5秒自动继续")
        print("  2. 如果不满意，现在手动选择正确歌词")
        print("  3. 手动操作后，程序会自动检测您保存的文件")
        print("\n提示：手动操作时请确保最终保存LRC文件")
        print("="*60)
    
        print(f"\nWAIT 歌词确认倒计时（{LYRIC_CONFIRM_TIMEOUT}秒）：")
    
        # 更新通知内容为倒计时，修改标题为当前可手动操作
        update_automation_notification(notification_root, notification_title, notification_info, notification_progress, 
                                      title="当前可手动操作",
                                      info="请确认歌词是否满意", 
                                      progress_text="可手动选择正确歌词")
    
        # 倒计时循环，同时检测鼠标活动
        mouse_moved = False
        for i in range(LYRIC_CONFIRM_TIMEOUT, 0, -1):
            print(f"\r[{i}]秒后自动继续...", end="", flush=True)
            
            # 更新通知窗口的倒计时
            update_automation_notification(notification_root, notification_title, notification_info, notification_progress, 
                                          title="当前可手动操作",
                                          progress_text=f"{i}秒后自动继续...")
            
            # 检测鼠标活动
            mouse_moved = detect_mouse_movement(sample_interval=0.5)
            
            if mouse_moved:
                print(f"\n\nWARN 检测到鼠标活动，进入手动操作模式...")
                # 更新通知内容
                update_automation_notification(notification_root, notification_title, notification_info, notification_progress, 
                                              info="手动操作模式", 
                                              progress_text="请选择并保存歌词")
                break
            
            time.sleep(1)
    
        manual_lrc = None
        skip_save = False
    
        if mouse_moved:
            # 进入手动操作模式
            print("\n" + "="*60)
            print("OK 已进入手动操作模式")
            print("="*60)
            print("手动操作指引：")
            print("  1. 您现在可以完全控制MusicTag界面")
            print("  2. 请选择正确的歌词并保存")
            print("  3. 保存快捷键：Ctrl+S 或点击保存按钮")
            print(f"  4. 保存位置会自动检测，默认在：")
            print(f"     {TEMP_MP3_DIR}")
            print(f"\n程序将等待{MANUAL_OPERATION_TIMEOUT}秒，检测到保存文件后自动继续")
            print("="*60)
            
            # 给用户3秒准备时间
            print("\nWAIT 准备手动操作...")
            for i in range(3, 0, -1):
                print(f"\r[{i}]", end="", flush=True)
                time.sleep(1)
            
            print("\n\nMANUAL 开始手动操作")
            
            # 等待用户手动保存
            manual_lrc = wait_for_manual_save(TEMP_MP3_DIR, artist, title, MANUAL_OPERATION_TIMEOUT)
            
            if manual_lrc:
                print(f"OK 检测到手动保存的文件：{os.path.basename(manual_lrc)}")
                skip_save = True
            else:
                print(f"TIMEOUT {MANUAL_OPERATION_TIMEOUT}秒超时，未检测到手动保存的歌词")
                print("INFO 继续自动保存流程")
        else:
            print("\n\nOK 歌词确认完成，继续自动保存...")
            # 恢复通知标题为自动化运行中
            update_automation_notification(notification_root, notification_title, notification_info, notification_progress, 
                                          title="自动化运行中",
                                          info="正在保存歌词文件...")
    
        # 继续原有流程（是否保存）
        if not skip_save:
            print("\nSAVE 保存LRC文件")
            if not save_as_lrc():
                print("   请手动点击另存为LRC")
            time.sleep(WAIT_SAVE)
            
            # 构建预期的LRC文件路径
            safe_artist = re.sub(r'[<>:"/\\|?*]', '_', artist)
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
            temp_lrc_path = os.path.join(TEMP_MP3_DIR, f"{safe_artist} - {safe_title}.lrc")
        else:
            temp_lrc_path = manual_lrc
    
        # 检查LRC文件是否存在
        if not os.path.exists(temp_lrc_path):
            # 尝试其他可能的文件名
            possible_names = [
                f"{artist} - {title}.lrc",
                f"{safe_artist} - {safe_title}.lrc",
                f"{artist}_{title}.lrc",
            ]
            
            for name in possible_names:
                possible_path = os.path.join(TEMP_MP3_DIR, name)
                if os.path.exists(possible_path):
                    temp_lrc_path = possible_path
                    break
    
        if os.path.exists(temp_lrc_path):
            file_size = os.path.getsize(temp_lrc_path)
            if SHOW_DETAILED_LOGS:
                print(f"\nOK 成功生成LRC文件: {os.path.basename(temp_lrc_path)}")
                print(f"SIZE 文件大小: {file_size} 字节")
            
            # 修复编码问题
            print(f"\nTOOL 修复歌词文件编码...")
            if fix_lyrics_encoding(temp_lrc_path):
                print("OK 歌词文件编码修复完成")
            else:
                print("WARN 歌词文件编码可能有问题")
            
            # 验证文件
            is_valid = verify_lyrics_file(temp_lrc_path, artist, title)
            
            if is_valid:
                if SHOW_DETAILED_LOGS:
                    print("OK 歌词验证: 通过")
            else:
                print("WARN 歌词验证: 可能存在问题")
            
            kill_musictag_process()
            
            if not os.path.exists(temp_lrc_path):
                print(f"ERROR LRC文件不存在: {temp_lrc_path}")
                return False
            
            temp_lrc_path = os.path.abspath(temp_lrc_path)
            
            # 根据是否启用V1转换执行不同操作
            if ENABLE_V1_CONVERSION == 1:
                if output_dir:
                    output_dir = os.path.abspath(output_dir)
                    success_v1 = process_lrc_with_v1(temp_lrc_path, output_dir)
                else:
                    success_v1 = process_lrc_with_v1(temp_lrc_path)
            else:
                # 不启用V1转换，直接复制LRC文件到输出目录
                success_v1 = True
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                    target_lrc = os.path.join(output_dir, os.path.basename(temp_lrc_path))
                    try:
                        shutil.copy2(temp_lrc_path, target_lrc)
                        if SHOW_DETAILED_LOGS:
                            print(f"FILE 已复制LRC文件到输出目录: {target_lrc}")
                    except Exception as e:
                        print(f"ERROR 复制LRC文件失败: {e}")
                        success_v1 = False
            
            return success_v1
        else:
            print(f"\nWARN 未检测到LRC文件")
            print(f"   检查路径: {temp_lrc_path}")
            
            try:
                if os.path.exists(TEMP_MP3_DIR):
                    files = os.listdir(TEMP_MP3_DIR)
                    if files:
                        print(f"   缓存目录中的文件: {files}")
                    else:
                        print("   缓存目录为空")
            except:
                pass
            
            kill_musictag_process()
            return False
    finally:
        # 确保自动化提示窗口被关闭
        if notification_root:
            close_automation_notification(notification_root)

# ====== 以下是你原有的其他函数，保持不变 ======
def check_resources():
    """检查资源文件"""
    required = {
        FILE_LIST_IMG: "文件列表区域截图",
        LYRIC_ICON: "歌词图标", 
        SEARCH_BTN: "搜索按钮",
        CONFIRM_BTN: "确定按钮",
        SAVE_LRC_BTN: "保存按钮"
    }
    
    # 可选资源（不影响基本功能，但提供更好的识别）
    optional = {
        LRC_QQ_ROW: "QQ源歌词行识别（可选）"
    }
    
    missing = []
    
    for path, name in required.items():
        if not os.path.exists(path):
            missing.append(f"{name}: {os.path.basename(path)}")
    
    if missing:
        print("\nWARN  缺少必需截图文件:")
        for item in missing:
            print(f"   {item}")
        print(f"\n请将截图放入: {RESOURCE_DIR}")
    
    # 检查可选资源
    for path, name in optional.items():
        if not os.path.exists(path):
            if SHOW_DETAILED_LOGS:
                print(f"INFO  缺少可选截图: {name} - {os.path.basename(path)}")
    
    return len(missing) == 0

def clean_temp_files_before_processing():
    """在处理前强制清理临时文件"""
    print("\nCLEAN 开始清理临时文件...")
    if os.path.exists(TEMP_BASE_DIR):
        try:
            shutil.rmtree(TEMP_BASE_DIR)
            print(f"OK 已清理临时缓存目录: {TEMP_BASE_DIR}")
            return True
        except Exception as e:
            print(f"WARN 清理临时缓存目录失败: {e}")
            return False
    else:
        print("INFO 临时缓存目录不存在，无需清理")
        return True

def clean_temp_files_after_processing():
    """在完成后清理临时文件"""
    if os.path.exists(TEMP_BASE_DIR):
        try:
            shutil.rmtree(TEMP_BASE_DIR)
            print(f"OK 已清理临时缓存目录: {TEMP_BASE_DIR}")
            return True
        except Exception as e:
            print(f"WARN 清理临时缓存目录失败: {e}")
            return False
    return True

# ====== 主程序 ======
if __name__ == "__main__":
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1
    
    print("="*60)
    print("MusicTag 歌词自动获取工具")
    print("="*60)
    print("当前配置:")
    print(f"  保存原始LRC文件: {'是' if SAVE_ORIGINAL_LRC == 1 else '否'}")
    print(f"  自动打开输出目录: {'是' if AUTO_OPEN_OUTPUT_DIR == 1 else '否'}")
    print(f"  显示详细日志: {'是' if SHOW_DETAILED_LOGS == 1 else '否'}")
    print(f"  V1转换为SRT: {'是' if ENABLE_V1_CONVERSION == 1 else '否'}")
    print(f"  字幕自动对齐: {'是' if ENABLE_SUBTITLE_ALIGNMENT == 1 else '否'}")
    print(f"  Z打包功能: {'是' if ENABLE_Z_PACKAGING == 1 else '否'}")
    print(f"  最大选择行数: {MAX_SELECTABLE_ROWS}行")
    if ENABLE_SUBTITLE_ALIGNMENT == 1:
        print(f"  时间差异警告阈值: {TIME_DIFF_WARNING_THRESHOLD}秒")
    if ENABLE_Z_PACKAGING == 1:
        print(f"  打包条件: 时间差异 ≤ {PACKAGING_DIFF_THRESHOLD}秒")
    print("="*60)
    
    os.makedirs(RESOURCE_DIR, exist_ok=True)
    check_resources()
    
    # ====== 在处理前强制清理临时文件 ======
    clean_temp_files_before_processing()
    
    # 处理输入参数
    if len(sys.argv) > 1:
        input_file = sys.argv[1].strip('"')
    else:
        input_file = input("\n请将文件拖拽到本窗口: ").strip('"')
    
    if not os.path.exists(input_file):
        print("ERROR 错误：文件不存在")
        sys.exit(1)
    
    # 判断文件类型
    file_ext = os.path.splitext(input_file)[1].lower()
    input_dir = os.path.dirname(input_file)
    
    # 当输入为srt格式字幕时，先将原文件加上（原文件）字样
    if file_ext == '.srt':
        original_name = os.path.basename(input_file)
        original_path = input_file
        name_without_ext = os.path.splitext(original_name)[0]
        
        # 检查文件名中是否已包含括号内容，如果有则不再重命名
        has_brackets = re.search(r'[\(\)\（\）]', name_without_ext)
        if not has_brackets:
            new_name = f"{name_without_ext}（原文件）{file_ext}"
            new_path = os.path.join(input_dir, new_name)
            
            if not os.path.exists(new_path):
                os.rename(original_path, new_path)
                print(f"NOTE 已将原SRT文件重命名为: {new_name}")
                # 更新input_file为新的路径，后续处理使用原文件
                input_file = new_path
        else:
            print(f"NOTE 原SRT文件名已包含括号，跳过重命名: {original_name}")
    
    # 解析歌手和歌名
    print(f"\nNOTE 解析文件名...")
    artist, title = parse_artist_title(input_file)
    print(f"Music 处理: {artist} - {title}")
    print(f"DIR 工作目录: {input_dir}")
    
    # 创建静音MP3用于MusicTag
    os.makedirs(TEMP_MP3_DIR, exist_ok=True)
    mp3_path = create_silent_mp3(artist, title)
    
    # 运行MusicTag获取歌词
    print("\n" + "="*60)
    print("开始获取歌词...")
    print("="*60)
    
    success = automate_musictag(mp3_path, artist, title, input_dir)
    
    print("\n" + "="*60)
    if success:
        print("SUCCESS 歌词获取完成！")
        
        # 查找生成的SRT文件（根据文件名匹配）
        song_name = f"{artist} - {title}"
        srt_files = []
        
        # 查找可能的SRT文件
        possible_names = [
            f"{artist} - {title}.srt",
            f"{song_name}.srt",
            f"{artist}_{title}.srt",
        ]
        
        # 添加清理后的文件名
        safe_artist = re.sub(r'[<>:"/\\|?*]', '_', artist)
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
        possible_names.append(f"{safe_artist} - {safe_title}.srt")
        possible_names.append(f"{safe_artist}_{safe_title}.srt")
        
        # 查找可能的SRT文件
        for name in possible_names:
            srt_path = os.path.join(input_dir, name)
            if os.path.exists(srt_path):
                srt_files.append(srt_path)
        
        # 如果没有找到，搜索所有SRT文件
        if not srt_files:
            all_srt_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.srt')]
            if all_srt_files:
                # 选择最新的SRT文件
                latest_srt = max(all_srt_files, key=lambda f: os.path.getctime(os.path.join(input_dir, f)))
                srt_files.append(os.path.join(input_dir, latest_srt))
        
        if srt_files:
            target_srt = srt_files[0]
            print(f"OK 找到歌词SRT文件: {os.path.basename(target_srt)}")
            
            # 判断输入文件类型并处理
            if file_ext in ['.srt', '.vtt', '.ass', '.ssa']:
                # 输入的是字幕文件，进行时间轴对齐
                print(f"\nFILE 输入字幕文件: {os.path.basename(input_file)}")
                
                if ENABLE_SUBTITLE_ALIGNMENT == 1:
                    print(f"TOOL 开始时间轴对齐...")
                    alignment_success, adjusted_srt, time_diff = adjust_subtitle_timing(target_srt, input_file)
                    
                    if alignment_success:
                        print(f"OK 时间轴对齐完成，差异: {time_diff:.3f}s")
                        
                        # 检查是否进行Z打包
                        if ENABLE_Z_PACKAGING == 1 and time_diff <= PACKAGING_DIFF_THRESHOLD:
                            print(f"\nPACK 开始Z打包处理...")
                            z_success = process_with_z_packaging(adjusted_srt)
                            
                            if z_success:
                                print(f"OK Z打包成功，已生成MKV文件")
                                # 成功时清理SRT文件（仅清理程序生成的文件，不清理用户原始文件）
                                try:
                                    if os.path.exists(adjusted_srt) and adjusted_srt != input_file:
                                        os.remove(adjusted_srt)
                                        print(f"CLEAN 已清理临时SRT文件: {os.path.basename(adjusted_srt)}")
                                except Exception as e:
                                    print(f"WARN  清理SRT文件失败: {e}")
                                final_file = "已生成MKV文件（请查看Z.py输出获取具体文件名）"
                            else:
                                print(f"ERROR Z打包失败，保留SRT字幕")
                                final_file = adjusted_srt
                        else:
                            print(f"INFO 时间差异 {time_diff:.3f}s 超过阈值 {PACKAGING_DIFF_THRESHOLD}s，跳过Z打包")
                            final_file = adjusted_srt
                    else:
                        print("WARN 时间轴对齐失败，使用原始歌词SRT")
                        final_file = target_srt
                else:
                    print("INFO 字幕对齐功能已禁用")
                    final_file = target_srt
                    
            elif file_ext in ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm']:
                # 输入的是视频文件，提取内嵌字幕并进行对齐
                print(f"\nVIDEO 输入视频文件: {os.path.basename(input_file)}")
                
                # 提取内嵌字幕
                internal_subtitle = extract_internal_subtitles(input_file)
                
                if internal_subtitle and ENABLE_SUBTITLE_ALIGNMENT == 1:
                    print(f"\nFILE 使用内嵌字幕进行时间轴对齐: {os.path.basename(internal_subtitle)}")
                    
                    alignment_success, adjusted_srt, time_diff = adjust_subtitle_timing(target_srt, internal_subtitle)
                    
                    if alignment_success:
                        print(f"OK 时间轴对齐完成，差异: {time_diff:.3f}s")
                        
                        # 清理临时内嵌字幕文件
                        try:
                            if os.path.exists(internal_subtitle):
                                os.remove(internal_subtitle)
                                print(f"CLEAN 已清理临时内嵌字幕文件")
                        except:
                            pass
                        
                        # 检查是否进行Z打包
                        if ENABLE_Z_PACKAGING == 1 and time_diff <= PACKAGING_DIFF_THRESHOLD:
                            print(f"\nPACK 开始Z打包处理...")
                            z_success = process_with_z_packaging(adjusted_srt)
                            
                            if z_success:
                                print(f"OK Z打包成功，已生成MKV文件")
                                # 成功时清理SRT文件
                                try:
                                    if os.path.exists(adjusted_srt):
                                        os.remove(adjusted_srt)
                                        print(f"CLEAN 已清理临时SRT文件: {os.path.basename(adjusted_srt)}")
                                except Exception as e:
                                    print(f"WARN  清理SRT文件失败: {e}")
                                final_file = "已生成MKV文件（请查看Z.py输出获取具体文件名）"
                            else:
                                print(f"ERROR Z打包失败，保留SRT字幕")
                                final_file = adjusted_srt
                        else:
                            print(f"INFO 时间差异 {time_diff:.3f}s 超过阈值 {PACKAGING_DIFF_THRESHOLD}s，跳过Z打包")
                            final_file = adjusted_srt
                    else:
                        print("WARN 时间轴对齐失败，使用原始歌词SRT")
                        # 清理临时文件
                        try:
                            if os.path.exists(internal_subtitle):
                                os.remove(internal_subtitle)
                        except:
                            pass
                        final_file = target_srt
                else:
                    if not internal_subtitle:
                        print("INFO 未提取到内嵌字幕或提取失败")
                    else:
                        print("INFO 字幕对齐功能已禁用")
                    final_file = target_srt
                    
            elif file_ext == '.lrc':
                # 输入的是LRC文件，已经处理过了
                print(f"OK 已处理LRC文件")
                final_file = target_srt
            else:
                # 输入的是其他文件，直接使用生成的SRT
                print(f"OK 生成歌词SRT文件")
                final_file = target_srt
            
            # 显示结果
            print("\n" + "="*60)
            print("CHART 处理完成")
            print("="*60)
            
            if isinstance(final_file, str) and "MKV文件" in final_file:
                print("OK Z打包已成功完成")
                print("   详细输出请查看上方Z.py日志")
            elif os.path.exists(final_file):
                file_name = os.path.basename(final_file)
                try:
                    file_size = os.path.getsize(final_file)
                    print(f"FILE 生成字幕文件: {file_name} ({file_size} 字节)")
                except:
                    print(f"FILE 生成文件: {file_name}")
            else:
                print("INFO 处理状态：已完成")
        else:
            print("INFO 处理状态：歌词获取完成")
        
        if AUTO_OPEN_OUTPUT_DIR == 1:
            os.startfile(input_dir)
            print(f"\nDIR 已自动打开输出目录")
        else:
            try:
                open_dir = input("\n是否打开文件目录？(y/n): ").lower()
                if open_dir.startswith('y'):
                    os.startfile(input_dir)
            except (EOFError, KeyboardInterrupt):
                # 当没有标准输入或用户中断时，跳过打开目录操作
                pass
    else:
        print("WARN 歌词获取可能未完全成功")
        print("\n调试建议:")
        print("  1. 检查截图文件是否准确")
        print("  2. 手动验证MusicTag操作流程")
        print("  3. 检查 v1.py 文件是否存在")
        print("  4. 检查歌词文件编码问题")
        print("  5. 检查缓存目录: " + TEMP_MP3_DIR)
    
    # ====== 处理完成后清理临时文件 ======
    print(f"\nCLEAN 最终清理缓存...")
    clean_temp_files_after_processing()
    
    try:
        input("\n按Enter退出...")
    except (EOFError, KeyboardInterrupt):
        # 当没有标准输入或用户中断时，直接退出
        pass