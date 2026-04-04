import os
import sys
import re
import argparse
import random

# ====================== 核心配置区域 ======================

# ====================== 字体大小配置 ======================
FONT_SIZE_KARAOKE = 70     # 卡拉OK主文字大小
FONT_SIZE_CHINESE = 50     # 中文文字大小
FONT_SIZE_COUNTDOWN = 50   # 倒计时文字大小

# ====================== 卡拉OK颜色配置 ======================
KARAOKE_PRIMARY = "&H20FF80FF"     # 主颜色
KARAOKE_SECONDARY = "&H20FFFFFF"   # 次颜色
KARAOKE_OUTLINE = "&H00804000"     # 边框颜色
KARAOKE_BACK = "&H00000000"        # 背景颜色

# ====================== 预备字幕颜色配置 ======================
PREP_PRIMARY = "&H90FFFFFF"
PREP_SECONDARY = "&H90FF0000"
PREP_OUTLINE = "&H00000000"
PREP_BACK = "&H80000000"

# ====================== 中文样式颜色配置 ======================
CHINESE_PRIMARY = "&H20FFFFFF"
CHINESE_SECONDARY = "&H20000000"
CHINESE_OUTLINE = "&H00804000"
CHINESE_BACK = "&H00000000"

# ====================== 倒计时颜色配置 ======================
COUNTDOWN_PRIMARY = "&H80FFFFFF"
COUNTDOWN_SECONDARY = "&H800000FF"
COUNTDOWN_OUTLINE = "&H00000000"
COUNTDOWN_BACK = "&H00000000"

# ====================== 倒计时效果配置 ======================
COUNTDOWN_FADEIN_ENABLE = 1          # 倒计时淡入效果开关 (0=关闭，1=开启)
COUNTDOWN_FADEIN_DURATION = 1.0      # 倒计时淡入时长（秒）
# 注意：倒计时淡入效果只应用于第一句倒计时（三个点）

# ====================== 边框和阴影配置 ======================
BORDER_STYLE = 1           # 边框样式 (1=普通边框)
KARAOKE_OUTLINE_WIDTH = 3  # 卡拉OK边框宽度（预备字幕也使用这个）
CHINESE_OUTLINE_WIDTH = 1  # 中文独立样式边框宽度
CHINESE_K_OUTLINE_WIDTH = 2  # 中文带K值样式边框宽度
COUNTDOWN_OUTLINE_WIDTH = 2  # 倒计时边框宽度
SHADOW_DEPTH = 0           # 所有样式阴影深度

# ====================== 加粗配置 ======================
KARAOKE_BOLD = 0           # 卡拉OK加粗（预备字幕也使用这个）
CHINESE_BOLD = 0          # 中文独立样式加粗
CHINESE_NORMAL_BOLD = 0    # 中文正常样式加粗
COUNTDOWN_BOLD = 1         # 倒计时加粗

# ====================== 其他样式参数 ======================
ITALIC = 0                 # 斜体 (所有样式)
UNDERLINE = 0              # 下划线 (所有样式)
STRIKEOUT = 0              # 删除线 (所有样式)
SCALE_X = 100              # 水平缩放 (所有样式)
SCALE_Y = 100              # 垂直缩放 (所有样式)
SPACING = 0                # 字符间距 (所有样式)
ANGLE = 0                  # 旋转角度 (所有样式)
ENCODING = 1               # 编码 (所有样式)

# ====================== 边距配置 ======================
# 卡拉OK边距
MARGIN_L_KARAOKE = 120     # 卡拉OK左边距 
MARGIN_R_KARAOKE = 30      # 卡拉OK右边距

# 中文边距偏移量(根据卡拉OK左右边距偏移)
MARGIN_L_CHINESE_OFFSET = 5  # 中文左边距偏移量
MARGIN_R_CHINESE_OFFSET = 5  # 中文右边距偏移量

# 垂直边距配置
MARGIN_V_K1 = 180          # K1样式垂直边距
MARGIN_V_K2 = 40           # K2样式垂直边距
MARGIN_V_K1_CHINESE = 250  # K1中文样式垂直边距
MARGIN_V_K2_CHINESE = 110  # K2中文样式垂直边距
MARGIN_V_CHINESE = 0       # 独立中文样式垂直边距（备用）
MARGIN_V_COUNTDOWN = 0     # 倒计时垂直边距

# ====================== 显示效果配置 ======================
# 中文翻译显示模式
# 0: 分开效果 - 中文翻译在每组上面显示 (使用k1_Chinese和k2_Chinese样式)
# 1: 独立效果 - 中文翻译统一使用Chinese样式 (在屏幕单独显示)
CHINESE_DISPLAY_MODE = 0

# 预备字幕配置
PREP_ADVANCE_MAX_SECONDS = 2.0  # 预备字幕最大提前时间（秒）
PREP_FADEIN_ENABLE = 1          # 预备字幕淡入效果开关
PREP_FADEIN_DURATION = 1.0      # 预备字幕淡入时长（秒）

# 重置样式的空档时间阈值（秒）
RESET_GAP_THRESHOLD = 5.0

# 倒计时配置
COUNTDOWN_LEFT_POSITION = (120, 810)   # 倒计时左边显示位置 (x, y)
COUNTDOWN_RIGHT_POSITION = (1690, 810) # 倒计时右边显示位置 (x, y)
COUNTDOWN_SYMBOL = '●'                 # 倒计时符号

# 卡拉OK效果配置
KARAOKE_EFFECT_LINE = 1         # 卡拉OK效果采取字幕第一行或者第二行显示 (1或者2)
REMOVE_KARAOKE_EFFECT = 0       # 是否删除翻译的卡拉OK效果(0否, 1是)

# 字幕对齐模式
ALIGNMENT_MODE = 0              # 0:左右区分 1:全体靠左 2:全体靠右

# ====================== 独立显示模式中文样式配置 ======================
# 当 CHINESE_DISPLAY_MODE = 1 时生效
CHINESE_INDEPENDENT_ALIGNMENT = 0  # 独立显示模式的中文样式对齐方式 (0=独立设置, 1=随动)
CHINESE_INDEPENDENT_POSITION = 2   # 画面位置：1=顶部，2=中部，3=底部

# 独立中文样式边距配置（根据位置选择使用）
CHINESE_INDEPENDENT_MARGIN_L = 120    # 独立中文样式左边距
CHINESE_INDEPENDENT_MARGIN_R = 220    # 独立中文样式右边距
CHINESE_INDEPENDENT_MARGIN_V_TOP = 100    # 独立中文样式顶部位置时的垂直边距
CHINESE_INDEPENDENT_MARGIN_V_MIDDLE = 0  # 独立中文样式中部位置时的垂直边距
CHINESE_INDEPENDENT_MARGIN_V_BOTTOM = 80  # 独立中文样式底部位置时的垂直边距

# ====================== 故障特效配置 ======================
GLITCH_EFFECT_ENABLE = 1          # 故障特效开关
GLITCH_TRANSLATION_ENABLE = 1     # 翻译故障特效开关
GLITCH_GAP_THRESHOLD = 3.0        # 歌词间隔多少秒才增加特效(秒)
GLITCH_OVERLAP_TIME = 0.1         # 与正式字幕的重叠时间(秒)
GLITCH_DURATION = 0.3             # 故障特效总持续时间(秒)

# ====================== 垂直拉伸/扁平化配置 ======================
# 垂直拉伸/扁平化效果配置
VERTICAL_SCALE_ENABLE = 0          # 垂直缩放效果开关 (0=关闭，1=开启)

# 参数说明：
# - 小于100%：垂直压缩（扁平化）效果，例如80表示压缩到80%
# - 大于100%：垂直拉伸效果，例如120表示拉伸到120%
# - 范围建议：50-200，50为极度扁平，200为极度拉伸
# - 正常为100，表示不进行垂直缩放
KARAOKE_VERTICAL_SCALE = 100       # 卡拉OK样式垂直缩放比例 (%)
CHINESE_VERTICAL_SCALE = 100       # 中文样式垂直缩放比例 (%)
COUNTDOWN_VERTICAL_SCALE = 100     # 倒计时样式垂直缩放比例 (%)
# 注意：预备字幕使用KARAOKE_VERTICAL_SCALE，以保持与卡拉OK字幕一致

# ===========================================================

if sys.platform == "win32":
    import io
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleOutputCP(65001)
    
    if sys.stdout.encoding != 'UTF-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if sys.stderr.encoding != 'UTF-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def time_str_to_seconds(time_str):
    if '.' in time_str:
        h, m, s_ms = time_str.split(':')
        s, ms = s_ms.split('.')
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 100
    else:
        h, m, s, cs = time_str.split(':')
        return int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100

def seconds_to_time_str(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 100)
    return f"{h}:{m:02d}:{s:02d}.{ms:02d}"

def extract_font_from_ass(content):
    styles_match = re.search(r'\[V4\+? Styles\](.*?)(?=\[|$)', content, re.S | re.I)
    if not styles_match:
        return None
    
    styles_content = styles_match.group(1)
    
    format_match = re.search(r'Format:\s*([^,\n]+(?:,[^,\n]+)*)', styles_content, re.I)
    if not format_match:
        return None
    
    format_line = format_match.group(1)
    format_parts = [part.strip().lower() for part in format_line.split(',')]
    
    if 'fontname' not in format_parts:
        return None
    
    fontname_idx = format_parts.index('fontname')
    
    style_match = re.search(r'Style:\s*([^,\n]+(?:,[^,\n]+)*)', styles_content, re.I)
    if not style_match:
        return None
    
    style_line = style_match.group(1)
    style_parts = style_line.split(',')
    
    if len(style_parts) > fontname_idx:
        font_name = style_parts[fontname_idx].strip()
        return font_name
    
    return None

def clean_text(text):
    text = re.sub(r'\\K\d+', '', text)
    text = re.sub(r'\\k[fd]?\d+', '', text)
    
    while True:
        new_text = re.sub(r'\{\s*\}', '', text)
        if new_text == text:
            break
        text = new_text
    
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_alignment_for_style(style_name):
    """根据样式名称获取对齐方式"""
    if "Countdown" in style_name:
        return 1
    
    if "Chinese" in style_name:
        if CHINESE_DISPLAY_MODE == 0:
            # 分开效果模式
            if "k1_Chinese" in style_name:
                return 1 if ALIGNMENT_MODE != 2 else 3
            elif "k2_Chinese" in style_name:
                return 3 if ALIGNMENT_MODE != 1 else 1
            else:
                return 2
        else:
            # 独立效果模式
            if CHINESE_INDEPENDENT_ALIGNMENT == 0:
                # 居中模式
                return 2  # 底部居中
            else:
                # 随动模式
                if ALIGNMENT_MODE == 1:
                    return 1  # 左下对齐
                elif ALIGNMENT_MODE == 2:
                    return 3  # 右下对齐
                else:
                    return 2  # 默认居中
    
    if "K1" in style_name or "K1_Prep" in style_name:
        return 1 if ALIGNMENT_MODE != 2 else 3
    elif "K2" in style_name or "K2_Prep" in style_name:
        return 3 if ALIGNMENT_MODE != 1 else 1
    
    return 2

def get_vertical_margin_for_style(style_name):
    """根据样式名称获取垂直边距"""
    if "Chinese" in style_name and CHINESE_DISPLAY_MODE == 1:
        # 独立显示模式下的中文样式
        if CHINESE_INDEPENDENT_POSITION == 1:  # 顶部
            return CHINESE_INDEPENDENT_MARGIN_V_TOP
        elif CHINESE_INDEPENDENT_POSITION == 2:  # 中部
            return CHINESE_INDEPENDENT_MARGIN_V_MIDDLE
        else:  # 底部
            return CHINESE_INDEPENDENT_MARGIN_V_BOTTOM
    elif "k1_Chinese" in style_name:
        return MARGIN_V_K1_CHINESE
    elif "k2_Chinese" in style_name:
        return MARGIN_V_K2_CHINESE
    elif "K1" in style_name or "K1_Prep" in style_name:
        return MARGIN_V_K1
    elif "K2" in style_name or "K2_Prep" in style_name:
        return MARGIN_V_K2
    elif "Countdown" in style_name:
        return MARGIN_V_COUNTDOWN
    else:
        return MARGIN_V_CHINESE

def get_horizontal_margins_for_style(style_name):
    """根据样式名称获取水平边距"""
    if "Chinese" in style_name and CHINESE_DISPLAY_MODE == 1:
        # 独立显示模式下的中文样式
        return CHINESE_INDEPENDENT_MARGIN_L, CHINESE_INDEPENDENT_MARGIN_R
    
    if "K1" in style_name or "K1_Prep" in style_name:
        if ALIGNMENT_MODE == 0:
            return MARGIN_L_KARAOKE, MARGIN_R_KARAOKE
        elif ALIGNMENT_MODE == 1:
            return MARGIN_L_KARAOKE, MARGIN_R_KARAOKE
        else:  # ALIGNMENT_MODE == 2
            return MARGIN_R_KARAOKE, MARGIN_L_KARAOKE
    elif "K2" in style_name or "K2_Prep" in style_name:
        if ALIGNMENT_MODE == 0:
            return MARGIN_R_KARAOKE, MARGIN_L_KARAOKE
        elif ALIGNMENT_MODE == 1:
            return MARGIN_L_KARAOKE, MARGIN_R_KARAOKE
        else:  # ALIGNMENT_MODE == 2
            return MARGIN_R_KARAOKE, MARGIN_L_KARAOKE
    elif "k1_Chinese" in style_name:
        if ALIGNMENT_MODE == 0:
            return MARGIN_L_KARAOKE + MARGIN_L_CHINESE_OFFSET, MARGIN_R_KARAOKE
        elif ALIGNMENT_MODE == 1:
            return MARGIN_L_KARAOKE + MARGIN_L_CHINESE_OFFSET, MARGIN_R_KARAOKE
        else:  # ALIGNMENT_MODE == 2
            return MARGIN_R_KARAOKE, MARGIN_L_KARAOKE + MARGIN_R_CHINESE_OFFSET
    elif "k2_Chinese" in style_name:
        if ALIGNMENT_MODE == 0:
            return MARGIN_R_KARAOKE, MARGIN_L_KARAOKE + MARGIN_R_CHINESE_OFFSET
        elif ALIGNMENT_MODE == 1:
            return MARGIN_L_KARAOKE + MARGIN_L_CHINESE_OFFSET, MARGIN_R_KARAOKE
        else:  # ALIGNMENT_MODE == 2
            return MARGIN_R_KARAOKE, MARGIN_L_KARAOKE + MARGIN_R_CHINESE_OFFSET
    else:
        return 0, 0

def get_vertical_scale_for_style(style_name):
    """根据样式名称获取垂直缩放比例"""
    if VERTICAL_SCALE_ENABLE == 0:
        return SCALE_Y  # 默认100%
    
    if "Chinese" in style_name:
        return CHINESE_VERTICAL_SCALE
    elif "Countdown" in style_name:
        return COUNTDOWN_VERTICAL_SCALE
    else:
        # K1, K2, K1_Prep, K2_Prep 都使用卡拉OK的垂直缩放比例
        return KARAOKE_VERTICAL_SCALE

def get_outline_width_for_style(style_name):
    """根据样式名称获取边框宽度"""
    if "Chinese_K" in style_name or "k1_Chinese_K" in style_name or "k2_Chinese_K" in style_name:
        return CHINESE_K_OUTLINE_WIDTH
    elif "Chinese" in style_name:
        return CHINESE_OUTLINE_WIDTH
    elif "Countdown" in style_name:
        return COUNTDOWN_OUTLINE_WIDTH
    else:
        return KARAOKE_OUTLINE_WIDTH

def get_bold_for_style(style_name):
    """根据样式名称获取加粗设置"""
    if "Countdown" in style_name:
        return COUNTDOWN_BOLD
    elif "Chinese" in style_name and "Chinese_K" not in style_name:
        return CHINESE_BOLD
    elif "k1_Chinese" in style_name or "k2_Chinese" in style_name:
        return CHINESE_NORMAL_BOLD
    else:
        return KARAOKE_BOLD

def create_glitch_effect(start_time, end_time, style, text, line_index, next_line_start=None):
    """创建故障特效字幕行"""
    if GLITCH_EFFECT_ENABLE == 0:
        return []
    
    # 检查是否需要添加故障特效（歌词间隔大于阈值）
    if next_line_start:
        gap = time_str_to_seconds(next_line_start) - time_str_to_seconds(end_time)
        if gap < GLITCH_GAP_THRESHOLD:
            return []
    
    glitch_lines = []
    start_seconds = time_str_to_seconds(start_time)
    end_seconds = time_str_to_seconds(end_time)
    
    # 计算故障特效开始时间（结束前GLITCH_OVERLAP_TIME秒）
    glitch_start_seconds = end_seconds - GLITCH_OVERLAP_TIME
    glitch_start = seconds_to_time_str(glitch_start_seconds)
    
    # 故障特效结束时间
    glitch_end_seconds = glitch_start_seconds + GLITCH_DURATION
    glitch_end = seconds_to_time_str(glitch_end_seconds)
    
    # 清理文本，移除K值
    clean_text_str = clean_text(text)
    if not clean_text_str:
        return []
    
    # 故障字符
    glitch_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?/~`"
    
    # 创建故障特效（分成多个片段）
    segment_count = 5  # 将故障特效分成5个片段
    segment_duration = GLITCH_DURATION / segment_count
    
    for i in range(segment_count):
        segment_start = glitch_start_seconds + (i * segment_duration)
        segment_end = segment_start + segment_duration
        
        # 不同类型的故障效果
        if i == 0:  # 轻微抖动
            effect_tags = f"{{\\fad(0,0)\\t(0,100,\\fscx115\\fscy115\\1c&H0000FF&)}}"
            glitch_text = clean_text_str
        elif i == 1:  # 颜色变化+缩放
            effect_tags = f"{{\\fad(0,0)\\t(0,100,\\fscx85\\fscy85\\1c&HFF0000&)}}"
            glitch_text = clean_text_str
        elif i == 2:  # 颜色变化+缩放
            effect_tags = f"{{\\fad(0,0)\\t(0,100,\\fscx105\\fscy95\\1c&H00FF00&)}}"
            glitch_text = clean_text_str
        elif i == 3:  # 字符损坏
            # 随机替换一些字符
            chars = list(clean_text_str)
            for j in range(len(chars)):
                if random.random() < 0.3 and chars[j] not in [' ', '\n']:
                    chars[j] = random.choice(glitch_chars)
            glitch_text = ''.join(chars)
            effect_tags = f"{{\\fad(0,0)\\t(0,100,\\fscx95\\fscy105\\1c&HFFFFFF&)}}"
        else:  # 严重损坏+消失
            glitch_text = ''.join([random.choice(glitch_chars) if random.random() < 0.7 else ' ' for _ in range(len(clean_text_str))])
            effect_tags = f"{{\\fad(0,0)\\t(0,100,\\fscx120\\fscy80\\1c&H00FFFF&)}}"
        
        glitch_line = f"Dialogue: 10,{seconds_to_time_str(segment_start)},{seconds_to_time_str(segment_end)},{style},,0,0,0,,{effect_tags}{glitch_text}"
        glitch_lines.append(glitch_line)
    
    return glitch_lines

def create_bilingual_ass(input_file, auto_overwrite=False, output_path=None):
    """创建优化的双语ASS文件"""
    input_file = input_file.strip().strip('"\'')
    
    if not os.path.exists(input_file):
        print(f"错误: 找不到文件 '{input_file}'")
        return False, None
    
    print(f"[OK] 找到文件: {input_file}")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        try:
            with open(input_file, 'r', encoding='utf-8-sig') as f:
                content = f.read()
        except:
            try:
                with open(input_file, 'r', encoding='gbk') as f:
                    content = f.read()
            except Exception as e:
                print(f"[ERROR] 读取文件失败: {e}")
                return False, None
    
    font_name = extract_font_from_ass(content)
    if font_name:
        print(f"[OK] 从输入文件提取字体: {font_name}")
    else:
        font_name = "Microsoft YaHei"
        print(f"[WARN] 未找到字体，使用默认字体: {font_name}")
    
    events_start = content.find('[Events]')
    if events_start == -1:
        print("[ERROR] 未找到[Events]部分")
        return False, None
    
    events_content = content[events_start:]
    
    # 如果指定了输出路径，直接使用，否则使用默认命名规则
    if output_path:
        output_file = output_path
    else:
        base_name = os.path.splitext(input_file)[0]
        output_file = base_name + "_KTV效果.ass"
    
    if os.path.exists(output_file):
        if auto_overwrite:
            print(f"[INFO] 覆盖已存在的文件: {output_file}")
        else:
            counter = 1
            while os.path.exists(f"{base_name}_KTV效果_{counter}.ass"):
                counter += 1
            output_file = f"{base_name}_KTV效果_{counter}.ass"
            print(f"[INFO] 文件已存在，自动重命名为: {output_file}")
    
    # 构建样式字符串
    styles_lines = []
    
    # 定义所有样式
    style_definitions = [
        # Default样式
        {
            'name': 'Default',
            'fontsize': 50,
            'colors': ('&H00FFFFFF', '&H00000000', '&H00804000', '&H00000000'),
            'bold': -1,
            'scale_y': 100,
            'outline': 2,
            'alignment': 2,
            'margin_l': 5,
            'margin_r': 5,
            'margin_v': 2
        },
        # K1样式
        {
            'name': 'K1',
            'fontsize': FONT_SIZE_KARAOKE,
            'colors': (KARAOKE_PRIMARY, KARAOKE_SECONDARY, KARAOKE_OUTLINE, KARAOKE_BACK),
            'bold': get_bold_for_style('K1'),
            'scale_y': get_vertical_scale_for_style('K1'),
            'outline': get_outline_width_for_style('K1'),
            'alignment': get_alignment_for_style('K1'),
            'margin_l': get_horizontal_margins_for_style('K1')[0],
            'margin_r': get_horizontal_margins_for_style('K1')[1],
            'margin_v': get_vertical_margin_for_style('K1')
        },
        # K2样式
        {
            'name': 'K2',
            'fontsize': FONT_SIZE_KARAOKE,
            'colors': (KARAOKE_PRIMARY, KARAOKE_SECONDARY, KARAOKE_OUTLINE, KARAOKE_BACK),
            'bold': get_bold_for_style('K2'),
            'scale_y': get_vertical_scale_for_style('K2'),
            'outline': get_outline_width_for_style('K2'),
            'alignment': get_alignment_for_style('K2'),
            'margin_l': get_horizontal_margins_for_style('K2')[0],
            'margin_r': get_horizontal_margins_for_style('K2')[1],
            'margin_v': get_vertical_margin_for_style('K2')
        },
        # K1_Prep样式
        {
            'name': 'K1_Prep',
            'fontsize': FONT_SIZE_KARAOKE,
            'colors': (PREP_PRIMARY, PREP_SECONDARY, PREP_OUTLINE, PREP_BACK),
            'bold': get_bold_for_style('K1_Prep'),
            'scale_y': get_vertical_scale_for_style('K1_Prep'),
            'outline': get_outline_width_for_style('K1_Prep'),
            'alignment': get_alignment_for_style('K1_Prep'),
            'margin_l': get_horizontal_margins_for_style('K1_Prep')[0],
            'margin_r': get_horizontal_margins_for_style('K1_Prep')[1],
            'margin_v': get_vertical_margin_for_style('K1_Prep')
        },
        # K2_Prep样式
        {
            'name': 'K2_Prep',
            'fontsize': FONT_SIZE_KARAOKE,
            'colors': (PREP_PRIMARY, PREP_SECONDARY, PREP_OUTLINE, PREP_BACK),
            'bold': get_bold_for_style('K2_Prep'),
            'scale_y': get_vertical_scale_for_style('K2_Prep'),
            'outline': get_outline_width_for_style('K2_Prep'),
            'alignment': get_alignment_for_style('K2_Prep'),
            'margin_l': get_horizontal_margins_for_style('K2_Prep')[0],
            'margin_r': get_horizontal_margins_for_style('K2_Prep')[1],
            'margin_v': get_vertical_margin_for_style('K2_Prep')
        }
    ]
    
    # 中文样式
    if REMOVE_KARAOKE_EFFECT == 0:
        # 带K值的中文样式
        style_definitions.extend([
            {
                'name': 'Chinese_K',
                'fontsize': FONT_SIZE_CHINESE,
                'colors': (KARAOKE_PRIMARY, KARAOKE_SECONDARY, KARAOKE_OUTLINE, KARAOKE_BACK),
                'bold': get_bold_for_style('Chinese_K'),
                'scale_y': get_vertical_scale_for_style('Chinese_K'),
                'outline': get_outline_width_for_style('Chinese_K'),
                'alignment': get_alignment_for_style('Chinese_K'),
                'margin_l': get_horizontal_margins_for_style('Chinese_K')[0],
                'margin_r': get_horizontal_margins_for_style('Chinese_K')[1],
                'margin_v': get_vertical_margin_for_style('Chinese_K')
            },
            {
                'name': 'k1_Chinese_K',
                'fontsize': FONT_SIZE_CHINESE,
                'colors': (KARAOKE_PRIMARY, KARAOKE_SECONDARY, KARAOKE_OUTLINE, KARAOKE_BACK),
                'bold': get_bold_for_style('k1_Chinese_K'),
                'scale_y': get_vertical_scale_for_style('k1_Chinese_K'),
                'outline': get_outline_width_for_style('k1_Chinese_K'),
                'alignment': get_alignment_for_style('k1_Chinese_K'),
                'margin_l': get_horizontal_margins_for_style('k1_Chinese_K')[0],
                'margin_r': get_horizontal_margins_for_style('k1_Chinese_K')[1],
                'margin_v': get_vertical_margin_for_style('k1_Chinese_K')
            },
            {
                'name': 'k2_Chinese_K',
                'fontsize': FONT_SIZE_CHINESE,
                'colors': (KARAOKE_PRIMARY, KARAOKE_SECONDARY, KARAOKE_OUTLINE, KARAOKE_BACK),
                'bold': get_bold_for_style('k2_Chinese_K'),
                'scale_y': get_vertical_scale_for_style('k2_Chinese_K'),
                'outline': get_outline_width_for_style('k2_Chinese_K'),
                'alignment': get_alignment_for_style('k2_Chinese_K'),
                'margin_l': get_horizontal_margins_for_style('k2_Chinese_K')[0],
                'margin_r': get_horizontal_margins_for_style('k2_Chinese_K')[1],
                'margin_v': get_vertical_margin_for_style('k2_Chinese_K')
            }
        ])
    
    # 不带K值的中文样式
    style_definitions.extend([
        {
            'name': 'k1_Chinese',
            'fontsize': FONT_SIZE_CHINESE,
            'colors': (CHINESE_PRIMARY, CHINESE_SECONDARY, CHINESE_OUTLINE, CHINESE_BACK),
            'bold': get_bold_for_style('k1_Chinese'),
            'scale_y': get_vertical_scale_for_style('k1_Chinese'),
            'outline': get_outline_width_for_style('k1_Chinese'),
            'alignment': get_alignment_for_style('k1_Chinese'),
            'margin_l': get_horizontal_margins_for_style('k1_Chinese')[0],
            'margin_r': get_horizontal_margins_for_style('k1_Chinese')[1],
            'margin_v': get_vertical_margin_for_style('k1_Chinese')
        },
        {
            'name': 'k2_Chinese',
            'fontsize': FONT_SIZE_CHINESE,
            'colors': (CHINESE_PRIMARY, CHINESE_SECONDARY, CHINESE_OUTLINE, CHINESE_BACK),
            'bold': get_bold_for_style('k2_Chinese'),
            'scale_y': get_vertical_scale_for_style('k2_Chinese'),
            'outline': get_outline_width_for_style('k2_Chinese'),
            'alignment': get_alignment_for_style('k2_Chinese'),
            'margin_l': get_horizontal_margins_for_style('k2_Chinese')[0],
            'margin_r': get_horizontal_margins_for_style('k2_Chinese')[1],
            'margin_v': get_vertical_margin_for_style('k2_Chinese')
        },
        {
            'name': 'Chinese',
            'fontsize': FONT_SIZE_CHINESE,
            'colors': (CHINESE_PRIMARY, CHINESE_SECONDARY, CHINESE_OUTLINE, CHINESE_BACK),
            'bold': get_bold_for_style('Chinese'),
            'scale_y': get_vertical_scale_for_style('Chinese'),
            'outline': get_outline_width_for_style('Chinese'),
            'alignment': get_alignment_for_style('Chinese'),
            'margin_l': get_horizontal_margins_for_style('Chinese')[0],
            'margin_r': get_horizontal_margins_for_style('Chinese')[1],
            'margin_v': get_vertical_margin_for_style('Chinese')
        },
        {
            'name': 'Countdown',
            'fontsize': FONT_SIZE_COUNTDOWN,
            'colors': (COUNTDOWN_PRIMARY, COUNTDOWN_SECONDARY, COUNTDOWN_OUTLINE, COUNTDOWN_BACK),
            'bold': get_bold_for_style('Countdown'),
            'scale_y': get_vertical_scale_for_style('Countdown'),
            'outline': get_outline_width_for_style('Countdown'),
            'alignment': get_alignment_for_style('Countdown'),
            'margin_l': 120,
            'margin_r': 30,
            'margin_v': get_vertical_margin_for_style('Countdown')
        }
    ])
    
    # 生成样式字符串
    for style_def in style_definitions:
        # 所有样式统一使用提取的字体
        font = font_name  # 使用提取的字体或默认字体
        
        style_line = f"Style: {style_def['name']},{font},{style_def['fontsize']},{style_def['colors'][0]},{style_def['colors'][1]},{style_def['colors'][2]},{style_def['colors'][3]},{style_def['bold']},{ITALIC},{UNDERLINE},{STRIKEOUT},{SCALE_X},{style_def['scale_y']},{SPACING},{ANGLE},{BORDER_STYLE},{style_def['outline']},{SHADOW_DEPTH},{style_def['alignment']},{style_def['margin_l']},{style_def['margin_r']},{style_def['margin_v']},{ENCODING}"
        styles_lines.append(style_line)
    
    styles = "\n".join(styles_lines)
    
    ass_template = f"""[Script Info]
Title: KTV效果
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{styles}
"""
    
    lines = events_content.split('\n')
    dialogues = []
    default_lines = []
    
    for line in lines:
        line = line.strip()
        if line.startswith('Dialogue:'):
            # 检查样式和内容
            parts = line.split(',', 9)
            if len(parts) >= 10:
                style = parts[3].strip()
                text = parts[9].strip()
                
                # 检查文本是否包含K值特效
                has_k_effect = bool(re.search(r'\\[Kk][0-9df]*', text))
                
                # 如果不包含K值特效，添加到默认行
                if not has_k_effect:
                    default_lines.append(line)
                else:
                    dialogues.append(line)
    
    print(f"找到 {len(dialogues)} 个对话行")
    
    time_groups = {}
    for dialogue in dialogues:
        parts = dialogue.split(',', 4)
        if len(parts) >= 4:
            start_time = parts[1].strip()
            end_time = parts[2].strip()
            time_key = f"{start_time}-{end_time}"
            
            if time_key not in time_groups:
                time_groups[time_key] = []
            time_groups[time_key].append(dialogue)
    
    print(f"按时间分成 {len(time_groups)} 组")
    
    time_groups_list = sorted(time_groups.items(), 
                             key=lambda x: time_str_to_seconds(x[0].split('-')[0]))
    
    processed_lines = []
    original_lines = []
    
    for i, (time_key, group_dialogues) in enumerate(time_groups_list):
        start_time, end_time = time_key.split('-')
        
        if len(group_dialogues) == 1:
            dialogue = group_dialogues[0]
            parts = dialogue.split(',', 9)
            if len(parts) >= 10:
                text = parts[9].strip()
                original_lines.append({
                    'index': i,
                    'start_time': start_time,
                    'end_time': end_time,
                    'text': text,
                    'is_bilingual': False,
                    'karaoke_text': text if KARAOKE_EFFECT_LINE == 1 else "",
                    'chinese_text': "" if KARAOKE_EFFECT_LINE == 1 else text
                })
        
        elif len(group_dialogues) >= 2:
            dialogue1 = group_dialogues[0]
            dialogue2 = group_dialogues[1]
            
            parts1 = dialogue1.split(',', 9)
            parts2 = dialogue2.split(',', 9)
            
            if len(parts1) >= 10 and len(parts2) >= 10:
                text1 = parts1[9].strip()
                text2 = parts2[9].strip()
                
                if KARAOKE_EFFECT_LINE == 1:
                    original_lines.append({
                        'index': i,
                        'start_time': start_time,
                        'end_time': end_time,
                        'text': text1,
                        'is_bilingual': True,
                        'karaoke_text': text1,
                        'chinese_text': text2
                    })
                else:
                    original_lines.append({
                        'index': i,
                        'start_time': start_time,
                        'end_time': end_time,
                        'text': text2,
                        'is_bilingual': True,
                        'karaoke_text': text2,
                        'chinese_text': text1
                    })
    
    prev_k1_end = None
    prev_k2_end = None
    reset_points = []
    current_style = 'K1'
    
    for i, line_info in enumerate(original_lines):
        start_time = line_info['start_time']
        end_time = line_info['end_time']
        karaoke_text = line_info['karaoke_text']
        
        start_seconds = time_str_to_seconds(start_time)
        end_seconds = time_str_to_seconds(end_time)
        
        reset_occurred = False
        if i > 0:
            prev_end_time = original_lines[i-1]['end_time']
            prev_end_seconds = time_str_to_seconds(prev_end_time)
            if start_seconds - prev_end_seconds > RESET_GAP_THRESHOLD:
                current_style = 'K1'
                reset_occurred = True
                reset_points.append(i)
                prev_k1_end = None
                prev_k2_end = None
                print(f"  时间间隔 > {RESET_GAP_THRESHOLD}秒，重置样式为 {current_style}")
        
        if current_style == 'K1' and (i == 0 or reset_occurred):
            if ALIGNMENT_MODE == 2:
                countdown_pos = COUNTDOWN_RIGHT_POSITION
                position_desc = "右边"
            else:
                countdown_pos = COUNTDOWN_LEFT_POSITION
                position_desc = "左边"
            
            countdown_3_start = seconds_to_time_str(max(0, start_seconds - 3))
            countdown_3_end = seconds_to_time_str(max(0, start_seconds - 2))
            if COUNTDOWN_FADEIN_ENABLE == 1:
                fade_in_ms = int(COUNTDOWN_FADEIN_DURATION * 1000)
                countdown_3_line = f"Dialogue: 4,{countdown_3_start},{countdown_3_end},Countdown,,0,0,0,,{{\\fad({fade_in_ms},0)\\an1\\pos({countdown_pos[0]},{countdown_pos[1]})}}{COUNTDOWN_SYMBOL} {COUNTDOWN_SYMBOL} {COUNTDOWN_SYMBOL}"
            else:
                countdown_3_line = f"Dialogue: 4,{countdown_3_start},{countdown_3_end},Countdown,,0,0,0,,{{\\fad(0,0)\\an1\\pos({countdown_pos[0]},{countdown_pos[1]})}}{COUNTDOWN_SYMBOL} {COUNTDOWN_SYMBOL} {COUNTDOWN_SYMBOL}"
            processed_lines.append(countdown_3_line)
            
            countdown_2_start = seconds_to_time_str(max(0, start_seconds - 2))
            countdown_2_end = seconds_to_time_str(max(0, start_seconds - 1))
            countdown_2_line = f"Dialogue: 4,{countdown_2_start},{countdown_2_end},Countdown,,0,0,0,,{{\\fad(0,0)\\an1\\pos({countdown_pos[0]},{countdown_pos[1]})}}{COUNTDOWN_SYMBOL} {COUNTDOWN_SYMBOL}"
            processed_lines.append(countdown_2_line)
            
            countdown_1_start = seconds_to_time_str(max(0, start_seconds - 1))
            countdown_1_end = seconds_to_time_str(start_seconds)
            countdown_1_line = f"Dialogue: 4,{countdown_1_start},{countdown_1_end},Countdown,,0,0,0,,{{\\fad(0,0)\\an1\\pos({countdown_pos[0]},{countdown_pos[1]})}}{COUNTDOWN_SYMBOL}"
            processed_lines.append(countdown_1_line)
            
            print(f"  添加倒计时: 位置: {position_desc}({countdown_pos[0]},{countdown_pos[1]})")
            if COUNTDOWN_FADEIN_ENABLE == 1:
                print(f"  倒计时淡入效果: 开启 (时长: {COUNTDOWN_FADEIN_DURATION}秒)")
        
        karaoke_line = f"Dialogue: 1,{start_time},{end_time},{current_style},,0,0,0,,{karaoke_text}"
        processed_lines.append(karaoke_line)
        
        # 为卡拉OK文本创建故障特效
        if GLITCH_EFFECT_ENABLE == 1 and karaoke_text:
            # 获取下一句的开始时间（如果有的话）
            next_start = None
            if i + 1 < len(original_lines):
                next_start = original_lines[i+1]['start_time']
            
            # 为卡拉OK行创建故障特效
            original_glitch_lines = create_glitch_effect(
                start_time, end_time, current_style, 
                karaoke_text, line_info['index'], next_start
            )
            processed_lines.extend(original_glitch_lines)
        
        prep_style = f"{current_style}_Prep"
        prep_text = clean_text(karaoke_text)
        
        if current_style == 'K1':
            if prev_k1_end is None:
                prep_start_seconds = max(0, start_seconds - PREP_ADVANCE_MAX_SECONDS)
            else:
                prep_start_seconds = max(time_str_to_seconds(prev_k1_end), start_seconds - PREP_ADVANCE_MAX_SECONDS)
            prev_k1_end = end_time
        else:
            if prev_k2_end is None:
                prep_start_seconds = max(0, start_seconds - PREP_ADVANCE_MAX_SECONDS)
            else:
                prep_start_seconds = max(time_str_to_seconds(prev_k2_end), start_seconds - PREP_ADVANCE_MAX_SECONDS)
            prev_k2_end = end_time
        
        prep_start = seconds_to_time_str(prep_start_seconds)
        prep_end = start_time
        
        if start_seconds - prep_start_seconds > 0.1:
            if PREP_FADEIN_ENABLE == 1:
                fade_in_ms = int(PREP_FADEIN_DURATION * 1000)
                prep_line = f"Dialogue: 0,{prep_start},{prep_end},{prep_style},,0,0,0,,{{\\fad({fade_in_ms},0)}}{prep_text}"
            else:
                prep_line = f"Dialogue: 0,{prep_start},{prep_end},{prep_style},,0,0,0,,{prep_text}"
            
            processed_lines.append(prep_line)
            prep_duration = start_seconds - prep_start_seconds
            fade_info = f"淡入:{PREP_FADEIN_DURATION}秒" if PREP_FADEIN_ENABLE == 1 else "无淡入"
            print(f"  预备字幕: {prep_start} -> {prep_end} [{prep_style}] 持续时间: {prep_duration:.2f}秒 {fade_info}")
        
        if line_info.get('is_bilingual', False) or line_info.get('chinese_text'):
            chinese_text = line_info.get('chinese_text', '')
            if chinese_text:
                if REMOVE_KARAOKE_EFFECT == 0:
                    chinese_text_processed = chinese_text
                    if CHINESE_DISPLAY_MODE == 0:
                        chinese_style = 'k1_Chinese_K' if current_style == 'K1' else 'k2_Chinese_K'
                    else:
                        if CHINESE_INDEPENDENT_ALIGNMENT == 1:
                            chinese_style = 'k1_Chinese_K' if current_style == 'K1' else 'k2_Chinese_K'
                        else:
                            chinese_style = 'Chinese_K'
                else:
                    chinese_text_processed = clean_text(chinese_text)
                    if CHINESE_DISPLAY_MODE == 0:
                        chinese_style = 'k1_Chinese' if current_style == 'K1' else 'k2_Chinese'
                    else:
                        if CHINESE_INDEPENDENT_ALIGNMENT == 1:
                            chinese_style = 'k1_Chinese' if current_style == 'K1' else 'k2_Chinese'
                        else:
                            chinese_style = 'Chinese'
                
                chinese_line = f"Dialogue: 2,{start_time},{end_time},{chinese_style},,0,0,0,,{chinese_text_processed}"
                processed_lines.append(chinese_line)
                
                # 为翻译文本创建故障特效（如果启用）
                if GLITCH_EFFECT_ENABLE == 1 and GLITCH_TRANSLATION_ENABLE == 1 and chinese_text_processed:
                    # 获取下一句的开始时间（如果有的话）
                    next_start = None
                    if i + 1 < len(original_lines):
                        next_start = original_lines[i+1]['start_time']
                    
                    # 为翻译行创建故障特效
                    translation_glitch_lines = create_glitch_effect(
                        start_time, end_time, chinese_style, 
                        chinese_text_processed, line_info['index'], next_start
                    )
                    processed_lines.extend(translation_glitch_lines)
        
        current_style = 'K2' if current_style == 'K1' else 'K1'
    
    # 将默认样式的字幕行添加到处理后的行中
    processed_lines.extend(default_lines)
    
    events_lines = ["[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    events_lines.extend(processed_lines)
    
    final_content = ass_template + '\n'.join(events_lines)
    
    try:
        with open(output_file, 'w', encoding='utf-8-sig') as f:
            f.write(final_content)
        
        # 统计各种样式的行数
        k1_count = len([l for l in processed_lines if 'K1,' in l and 'K1_Prep' not in l])
        k2_count = len([l for l in processed_lines if 'K2,' in l and 'K2_Prep' not in l])
        k1_prep_count = len([l for l in processed_lines if 'K1_Prep' in l])
        k2_prep_count = len([l for l in processed_lines if 'K2_Prep' in l])
        k1_chinese_count = len([l for l in processed_lines if 'k1_Chinese' in l])
        k2_chinese_count = len([l for l in processed_lines if 'k2_Chinese' in l])
        k1_chinese_k_count = len([l for l in processed_lines if 'k1_Chinese_K' in l])
        k2_chinese_k_count = len([l for l in processed_lines if 'k2_Chinese_K' in l])
        chinese_count = len([l for l in processed_lines if 'Chinese,' in l and 'Chinese_K' not in l])
        chinese_k_count = len([l for l in processed_lines if 'Chinese_K,' in l])
        countdown_count = len([l for l in processed_lines if 'Countdown' in l])
        
        # 统计故障特效行数
        glitch_count = len([l for l in processed_lines if 'Dialogue: 10' in l])
        
        print(f"\n[OK] ASS文件创建成功!")
        print(f"输入文件: {input_file}")
        print(f"输出文件: {output_file}")
        print(f"输出路径: {os.path.abspath(output_file)}")
        print(f"使用字体: {font_name}")
        print(f"中文显示模式: {CHINESE_DISPLAY_MODE} ({'当前效果(每组上方)' if CHINESE_DISPLAY_MODE == 0 else '新增效果(在屏幕单独显示)'})")
        if CHINESE_DISPLAY_MODE == 1:
            position_names = {1: "顶部", 2: "中部", 3: "底部"}
            print(f"独立中文位置: {CHINESE_INDEPENDENT_POSITION} ({position_names.get(CHINESE_INDEPENDENT_POSITION, '未知')})")
            print(f"独立中文对齐: {CHINESE_INDEPENDENT_ALIGNMENT} ({'居中' if CHINESE_INDEPENDENT_ALIGNMENT == 0 else '随动'})")
            print(f"独立中文边距: 左={CHINESE_INDEPENDENT_MARGIN_L}, 右={CHINESE_INDEPENDENT_MARGIN_R}, 垂直={get_vertical_margin_for_style('Chinese')}")
        print(f"卡拉OK效果行: {KARAOKE_EFFECT_LINE} ({'第一行原文应用K值，第二行翻译为中文' if KARAOKE_EFFECT_LINE == 1 else '第二行翻译应用K值，第一行原文为中文'})")
        print(f"删除翻译K值: {'是' if REMOVE_KARAOKE_EFFECT == 1 else '否'}")
        print(f"预备字幕最大提前时间: {PREP_ADVANCE_MAX_SECONDS}秒")
        print(f"重置样式空档阈值: {RESET_GAP_THRESHOLD}秒")
        print(f"倒计时左边位置: ({COUNTDOWN_LEFT_POSITION[0]}, {COUNTDOWN_LEFT_POSITION[1]})")
        print(f"倒计时右边位置: ({COUNTDOWN_RIGHT_POSITION[0]}, {COUNTDOWN_RIGHT_POSITION[1]})")
        print(f"倒计时符号: '{COUNTDOWN_SYMBOL}'")
        print(f"预备字幕淡入效果: {'开启' if PREP_FADEIN_ENABLE == 1 else '关闭'}")
        if PREP_FADEIN_ENABLE == 1:
            print(f"预备字幕淡入时长: {PREP_FADEIN_DURATION}秒")
        print(f"倒计时淡入效果: {'开启' if COUNTDOWN_FADEIN_ENABLE == 1 else '关闭'}")
        if COUNTDOWN_FADEIN_ENABLE == 1:
            print(f"倒计时淡入时长: {COUNTDOWN_FADEIN_DURATION}秒")
            print(f"倒计时淡入颜色: 从完全透明到 {COUNTDOWN_PRIMARY}")
        print(f"字幕对齐模式: {ALIGNMENT_MODE} ({'左右区分' if ALIGNMENT_MODE == 0 else '全体靠左' if ALIGNMENT_MODE == 1 else '全体靠右'})")
        print(f"垂直缩放效果: {'开启' if VERTICAL_SCALE_ENABLE == 1 else '关闭'}")
        if VERTICAL_SCALE_ENABLE == 1:
            print(f"卡拉OK垂直缩放比例: {KARAOKE_VERTICAL_SCALE}% ({'扁平化' if KARAOKE_VERTICAL_SCALE < 100 else '正常' if KARAOKE_VERTICAL_SCALE == 100 else '垂直拉伸'})")
            print(f"中文垂直缩放比例: {CHINESE_VERTICAL_SCALE}%")
            print(f"倒计时垂直缩放比例: {COUNTDOWN_VERTICAL_SCALE}%")
        print(f"故障特效: {'开启' if GLITCH_EFFECT_ENABLE == 1 else '关闭'}")
        if GLITCH_EFFECT_ENABLE == 1:
            print(f"翻译故障特效: {'开启' if GLITCH_TRANSLATION_ENABLE == 1 else '关闭'}")
            print(f"故障特效间隔阈值: {GLITCH_GAP_THRESHOLD}秒")
            print(f"故障特效重叠时间: {GLITCH_OVERLAP_TIME}秒")
            print(f"故障特效持续时间: {GLITCH_DURATION}秒")
        print(f"总行数: {len(processed_lines)}")
        print(f"K1正式行数: {k1_count}")
        print(f"K2正式行数: {k2_count}")
        print(f"K1预备行数: {k1_prep_count}")
        print(f"K2预备行数: {k2_prep_count}")
        if CHINESE_DISPLAY_MODE == 0:
            if REMOVE_KARAOKE_EFFECT == 0:
                print(f"K1中文行数(带K值): {k1_chinese_k_count}")
                print(f"K2中文行数(带K值): {k2_chinese_k_count}")
            else:
                print(f"K1中文行数: {k1_chinese_count}")
                print(f"K2中文行数: {k2_chinese_count}")
        else:
            if REMOVE_KARAOKE_EFFECT == 0:
                print(f"统一中文行数(带K值): {chinese_k_count}")
            else:
                print(f"统一中文行数: {chinese_count}")
        print(f"倒计时行数: {countdown_count}")
        print(f"故障特效行数: {glitch_count}")
        print(f"重置点数量: {len(reset_points)}")
        
        return True, output_file
        
    except Exception as e:
        print(f"[ERROR] 写入文件失败: {e}")
        return False, None

def parse_drag_paths(user_input):
    print(f"原始输入: {user_input}")
    
    stripped_input = user_input.strip().strip('"\'')
    
    if os.path.exists(stripped_input):
        print(f"找到完整文件路径: {stripped_input}")
        return [stripped_input]
    
    file_paths = []
    
    import re
    quoted_paths = re.findall(r'"(.*?)"', user_input)
    
    if quoted_paths:
        for path in quoted_paths:
            if os.path.exists(path):
                file_paths.append(path)
                print(f"找到带引号的路径: {path}")
            else:
                print(f"警告: 带引号的路径不存在: {path}")
    
    if not file_paths:
        parts = user_input.split()
        
        temp_parts = []
        i = 0
        while i < len(parts):
            if len(parts[i]) >= 2 and parts[i][1] == ':' and parts[i][0].isalpha():
                path_parts = [parts[i]]
                j = i + 1
                
                while j < len(parts):
                    path_parts.append(parts[j])
                    test_path = ' '.join(path_parts).strip('"\'')
                    
                    if test_path.endswith('.ass'):
                        if os.path.exists(test_path):
                            break
                    j += 1
                
                if os.path.exists(' '.join(path_parts).strip('"\'')):
                    temp_parts.append(' '.join(path_parts).strip('"\''))
                    i = j
                else:
                    temp_parts.append(parts[i].strip('"\''))
                    i += 1
            else:
                temp_parts.append(parts[i].strip('"\''))
                i += 1
        
        for path in temp_parts:
            if os.path.exists(path):
                file_paths.append(path)
                print(f"找到路径: {path}")
            else:
                print(f"警告: 路径不存在: {path}")
    
    return file_paths

def restore_original_ass(input_file, auto_overwrite=False, output_path=None):
    """将K.py转换后的ASS文件还原为原始格式"""
    input_file = input_file.strip().strip('"\'')
    
    if not os.path.exists(input_file):
        print(f"错误: 找不到文件 '{input_file}'")
        return False, None
    
    print(f"[OK] 找到文件: {input_file}")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        try:
            with open(input_file, 'r', encoding='utf-8-sig') as f:
                content = f.read()
        except:
            try:
                with open(input_file, 'r', encoding='gbk') as f:
                    content = f.read()
            except Exception as e:
                print(f"[ERROR] 读取文件失败: {e}")
                return False, None
    
    # 提取原始字体信息
    font_name = extract_font_from_ass(content)
    if not font_name:
        font_name = "Microsoft YaHei"
        print(f"[WARN] 未找到字体，使用默认字体: {font_name}")
    else:
        print(f"[OK] 从输入文件提取字体: {font_name}")
    
    # 提取原始的Events部分
    events_match = re.search(r'\[Events\](.*?)$', content, re.S)
    if not events_match:
        print("[ERROR] 未找到Events部分")
        return False, None
    
    events_content = events_match.group(1)
    lines = events_content.split('\n')
    dialogues = []
    
    for line in lines:
        line = line.strip()
        if line.startswith('Dialogue:'):
            parts = line.split(',', 9)
            if len(parts) >= 10:
                start_time = parts[1].strip()
                end_time = parts[2].strip()
                style = parts[3].strip()
                text = parts[9].strip()
                
                # 保留指定样式的行，同时也保留Default样式
                if style in ['K1', 'k1_Chinese_K', 'k1_Chinese', 'K2', 'k2_Chinese_K', 'k2_Chinese', 'Default']:
                    if style.lower() == 'default':
                        # 对于Default样式，直接保留原始文本，不做处理
                        processed_text = text
                        # 清理文本，删除特效标签和转义序列
                        processed_text = re.sub(r'\{[^}]*\}', '', processed_text)
                        processed_text = re.sub(r'\\\w*', '', processed_text)
                        processed_text = re.sub(r'\s+', ' ', processed_text).strip()
                        if processed_text:
                            dialogues.append((start_time, end_time, style, processed_text, 'Default'))
                    else:
                        # 对于非Default样式，处理K值标签
                        # 检测K值，只保留K值和文本，去掉其他特效标签
                        # 查找第一个K值的位置，确保包含完整的标签格式{\K187}
                        k_match = re.search(r'\{\\[Kk][0-9df]*', text)
                        if k_match:
                            # 提取K值和后面的文本，确保包含左大括号
                            k_start = k_match.start()
                            processed_text = text[k_start:].strip()
                        else:
                            # 检查是否有不带左大括号的K值
                            k_match = re.search(r'\\[Kk][0-9df]*', text)
                            if k_match:
                                # 添加左大括号
                                k_start = k_match.start()
                                processed_text = '{' + text[k_start:].strip()
                            else:
                                # 没有K值，直接使用文本
                                processed_text = text.strip()
                        
                        if processed_text:
                            dialogues.append((start_time, end_time, style, processed_text, 'Karaoke'))
    
    # 按时间排序
    dialogues.sort(key=lambda x: (time_str_to_seconds(x[0]), x[0], x[1]))
    
    # 生成原始格式的对话行，按顺序排列
    original_dialogues = []
    for dialogue in dialogues:
        start_time, end_time, style, text, target_style = dialogue
        # 根据目标样式应用相应的样式
        original_dialogues.append(f"Dialogue: 0,{start_time},{end_time},{target_style},,0000,0000,0000,,{text}")
    
    # 生成输出文件名
    if output_path:
        output_file = output_path
    else:
        base_name = os.path.splitext(input_file)[0]
        output_file = base_name + "_还原.ass"
    
    if os.path.exists(output_file):
        if auto_overwrite:
            print(f"[INFO] 覆盖已存在的文件: {output_file}")
        else:
            counter = 1
            while os.path.exists(f"{base_name}_还原_{counter}.ass"):
                counter += 1
            output_file = f"{base_name}_还原_{counter}.ass"
            print(f"[INFO] 文件已存在，自动重命名为: {output_file}")
    
    # 生成原始格式的ASS内容
    original_content = f"""[Script Info]
Title:
ScriptType: v4.00+
Collisions: Normal
PlayResX: 1920
PlayResY: 1080
Timer: 100.0000
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,方正准圆简体,40,&H00FFFFFF,&H00000000,&H00804000,&H00000000,-1,0,0,0,100,100,0,0,1,2,1,2,5,5,2,134
Style: Karaoke,{font_name},40,&H00FF80FF,&H00FFFFFF,&H00804000,&H00000000,-1,0,0,0,100,100,0,0,1,2,1,2,5,5,2,134

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
{chr(10).join(original_dialogues)}
"""
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(original_content)
        
        print(f"\n[OK] ASS文件还原成功!")
        print(f"输入文件: {input_file}")
        print(f"输出文件: {output_file}")
        print(f"输出路径: {os.path.abspath(output_file)}")
        print(f"使用字体: {font_name}")
        print(f"还原对话行数: {len(original_dialogues)}")
        
        return True, output_file
        
    except Exception as e:
        print(f"[ERROR] 写入文件失败: {e}")
        return False, None

def simple_interactive_mode(auto_overwrite=False):
    print("=" * 80)
    print("ASS卡拉OK字幕处理工具")
    print("=" * 80)
    print(f"中文显示模式: {CHINESE_DISPLAY_MODE} ({'当前效果(每组上方)' if CHINESE_DISPLAY_MODE == 0 else '新增效果(在屏幕单独显示)'})")
    if CHINESE_DISPLAY_MODE == 1:
        position_names = {1: "顶部", 2: "中部", 3: "底部"}
        print(f"独立中文位置: {CHINESE_INDEPENDENT_POSITION} ({position_names.get(CHINESE_INDEPENDENT_POSITION, '未知')})")
        print(f"独立中文对齐: {CHINESE_INDEPENDENT_ALIGNMENT} ({'居中' if CHINESE_INDEPENDENT_ALIGNMENT == 0 else '随动'})")
        print(f"独立中文边距: 左={CHINESE_INDEPENDENT_MARGIN_L}, 右={CHINESE_INDEPENDENT_MARGIN_R}")
        print(f"独立中文垂直边距: 顶部={CHINESE_INDEPENDENT_MARGIN_V_TOP}, 中部={CHINESE_INDEPENDENT_MARGIN_V_MIDDLE}, 底部={CHINESE_INDEPENDENT_MARGIN_V_BOTTOM}")
    print(f"卡拉OK效果行: {KARAOKE_EFFECT_LINE} ({'第一行原文应用K值，第二行翻译为中文' if KARAOKE_EFFECT_LINE == 1 else '第二行翻译应用K值，第一行原文为中文'})")
    print(f"删除翻译K值: {'是' if REMOVE_KARAOKE_EFFECT == 1 else '否'}")
    print(f"预备字幕最大提前时间: {PREP_ADVANCE_MAX_SECONDS}秒")
    print(f"重置样式空档阈值: {RESET_GAP_THRESHOLD}秒")
    print(f"倒计时左边位置: ({COUNTDOWN_LEFT_POSITION[0]}, {COUNTDOWN_LEFT_POSITION[1]})")
    print(f"倒计时右边位置: ({COUNTDOWN_RIGHT_POSITION[0]}, {COUNTDOWN_RIGHT_POSITION[1]})")
    print(f"倒计时符号: '{COUNTDOWN_SYMBOL}'")
    print(f"预备字幕淡入效果: {'开启' if PREP_FADEIN_ENABLE == 1 else '关闭'}")
    if PREP_FADEIN_ENABLE == 1:
        print(f"预备字幕淡入时长: {PREP_FADEIN_DURATION}秒")
    print(f"倒计时淡入效果: {'开启' if COUNTDOWN_FADEIN_ENABLE == 1 else '关闭'}")
    if COUNTDOWN_FADEIN_ENABLE == 1:
        print(f"倒计时淡入时长: {COUNTDOWN_FADEIN_DURATION}秒")
        print(f"倒计时淡入颜色: 从完全透明到 {COUNTDOWN_PRIMARY}")
    print(f"字幕对齐模式: {ALIGNMENT_MODE} ({'左右区分' if ALIGNMENT_MODE == 0 else '全体靠左' if ALIGNMENT_MODE == 1 else '全体靠右'})")
    print(f"垂直缩放效果: {'开启' if VERTICAL_SCALE_ENABLE == 1 else '关闭'}")
    if VERTICAL_SCALE_ENABLE == 1:
        print(f"卡拉OK垂直缩放比例: {KARAOKE_VERTICAL_SCALE}% ({'扁平化' if KARAOKE_VERTICAL_SCALE < 100 else '正常' if KARAOKE_VERTICAL_SCALE == 100 else '垂直拉伸'})")
        print(f"中文垂直缩放比例: {CHINESE_VERTICAL_SCALE}%")
        print(f"倒计时垂直缩放比例: {COUNTDOWN_VERTICAL_SCALE}%")
        print(f"注意: 预备字幕使用卡拉OK的垂直缩放比例，确保显示效果一致")
    print(f"故障特效: {'开启' if GLITCH_EFFECT_ENABLE == 1 else '关闭'}")
    if GLITCH_EFFECT_ENABLE == 1:
        print(f"翻译故障特效: {'开启' if GLITCH_TRANSLATION_ENABLE == 1 else '关闭'}")
        print(f"故障特效间隔阈值: {GLITCH_GAP_THRESHOLD}秒")
        print(f"故障特效重叠时间: {GLITCH_OVERLAP_TIME}秒")
        print(f"故障特效持续时间: {GLITCH_DURATION}秒")
    print("直接拖拽ASS文件到此处，或输入文件路径(支持多个文件)")
    print("输入 'restore <文件路径>' 可将转换后的文件还原为原始格式")
    print("=" * 80)
    
    while True:
        try:
            print("\n" + "-" * 60)
            user_input = input("\n拖拽ASS文件到此处或输入路径 (按回车继续处理，输入q退出，输入restore <文件路径>还原): ").strip()
            
            if user_input.lower() in ['q', 'quit', 'exit']:
                print("程序退出。")
                break
            
            if user_input.lower() in ['cls', 'clear']:
                os.system('cls' if sys.platform == 'win32' else 'clear')
                print("=" * 80)
                print("ASS卡拉OK字幕处理工具")
                print("=" * 80)
                print(f"中文显示模式: {CHINESE_DISPLAY_MODE} ({'当前效果(每组上方)' if CHINESE_DISPLAY_MODE == 0 else '新增效果(在屏幕单独显示)'})")
                if CHINESE_DISPLAY_MODE == 1:
                    position_names = {1: "顶部", 2: "中部", 3: "底部"}
                    print(f"独立中文位置: {CHINESE_INDEPENDENT_POSITION} ({position_names.get(CHINESE_INDEPENDENT_POSITION, '未知')})")
                    print(f"独立中文对齐: {CHINESE_INDEPENDENT_ALIGNMENT} ({'居中' if CHINESE_INDEPENDENT_ALIGNMENT == 0 else '随动'})")
                    print(f"独立中文边距: 左={CHINESE_INDEPENDENT_MARGIN_L}, 右={CHINESE_INDEPENDENT_MARGIN_R}")
                    print(f"独立中文垂直边距: 顶部={CHINESE_INDEPENDENT_MARGIN_V_TOP}, 中部={CHINESE_INDEPENDENT_MARGIN_V_MIDDLE}, 底部={CHINESE_INDEPENDENT_MARGIN_V_BOTTOM}")
                print(f"卡拉OK效果行: {KARAOKE_EFFECT_LINE} ({'第一行原文应用K值，第二行翻译为中文' if KARAOKE_EFFECT_LINE == 1 else '第二行翻译应用K值，第一行原文为中文'})")
                print(f"删除翻译K值: {'是' if REMOVE_KARAOKE_EFFECT == 1 else '否'}")
                print(f"预备字幕最大提前时间: {PREP_ADVANCE_MAX_SECONDS}秒")
                print(f"重置样式空档阈值: {RESET_GAP_THRESHOLD}秒")
                print(f"倒计时左边位置: ({COUNTDOWN_LEFT_POSITION[0]}, {COUNTDOWN_LEFT_POSITION[1]})")
                print(f"倒计时右边位置: ({COUNTDOWN_RIGHT_POSITION[0]}, {COUNTDOWN_RIGHT_POSITION[1]})")
                print(f"倒计时符号: '{COUNTDOWN_SYMBOL}'")
                print(f"预备字幕淡入效果: {'开启' if PREP_FADEIN_ENABLE == 1 else '关闭'}")
                if PREP_FADEIN_ENABLE == 1:
                    print(f"预备字幕淡入时长: {PREP_FADEIN_DURATION}秒")
                print(f"倒计时淡入效果: {'开启' if COUNTDOWN_FADEIN_ENABLE == 1 else '关闭'}")
                if COUNTDOWN_FADEIN_ENABLE == 1:
                    print(f"倒计时淡入时长: {COUNTDOWN_FADEIN_DURATION}秒")
                    print(f"倒计时淡入颜色: 从完全透明到 {COUNTDOWN_PRIMARY}")
                print(f"字幕对齐模式: {ALIGNMENT_MODE} ({'左右区分' if ALIGNMENT_MODE == 0 else '全体靠左' if ALIGNMENT_MODE == 1 else '全体靠右'})")
                print(f"垂直缩放效果: {'开启' if VERTICAL_SCALE_ENABLE == 1 else '关闭'}")
                if VERTICAL_SCALE_ENABLE == 1:
                    print(f"卡拉OK垂直缩放比例: {KARAOKE_VERTICAL_SCALE}% ({'扁平化' if KARAOKE_VERTICAL_SCALE < 100 else '正常' if KARAOKE_VERTICAL_SCALE == 100 else '垂直拉伸'})")
                    print(f"中文垂直缩放比例: {CHINESE_VERTICAL_SCALE}%")
                    print(f"倒计时垂直缩放比例: {COUNTDOWN_VERTICAL_SCALE}%")
                    print(f"注意: 预备字幕使用卡拉OK的垂直缩放比例，确保显示效果一致")
                print(f"故障特效: {'开启' if GLITCH_EFFECT_ENABLE == 1 else '关闭'}")
                if GLITCH_EFFECT_ENABLE == 1:
                    print(f"翻译故障特效: {'开启' if GLITCH_TRANSLATION_ENABLE == 1 else '关闭'}")
                    print(f"故障特效间隔阈值: {GLITCH_GAP_THRESHOLD}秒")
                    print(f"故障特效重叠时间: {GLITCH_OVERLAP_TIME}秒")
                    print(f"故障特效持续时间: {GLITCH_DURATION}秒")
                print("直接拖拽ASS文件到此处，或输入文件路径(支持多个文件)")
                print("=" * 80)
                continue
            
            if not user_input:
                continue
            
            file_paths = parse_drag_paths(user_input)
            
            if not file_paths:
                print("未找到有效文件路径!")
                continue
            
            print(f"找到 {len(file_paths)} 个文件")
            
            valid_files = []
            for file_path in file_paths:
                if os.path.exists(file_path):
                    if file_path.lower().endswith('.ass'):
                        valid_files.append(file_path)
                    else:
                        print(f"警告: 文件 '{file_path}' 不是ASS文件，已跳过")
                else:
                    print(f"错误: 找不到文件 '{file_path}'")
            
            if not valid_files:
                print("没有有效的ASS文件可处理!")
                continue
            
            print(f"准备处理 {len(valid_files)} 个ASS文件")
            
            success_count = 0
            processed_files = []
            
            for i, input_file in enumerate(valid_files):
                print(f"\n处理文件 {i+1}/{len(valid_files)}: {os.path.basename(input_file)}")
                print("-" * 40)
                
                success, output_file = create_bilingual_ass(input_file, auto_overwrite)
                if success:
                    success_count += 1
                    processed_files.append(output_file)
                    print(f"✓ 文件处理成功!")
                else:
                    print(f"✗ 文件处理失败!")
                print("-" * 40)
            
            print(f"\n" + "=" * 80)
            print(f"处理完成!")
            print(f"成功: {success_count}/{len(valid_files)}")
            
            if success_count > 0:
                print(f"\n生成的文件:")
                for i, output_file in enumerate(processed_files):
                    print(f"  {i+1}. {os.path.basename(output_file)}")
                    print(f"     完整路径: {output_file}")
            
            print(f"\n" + "-" * 80)
            print("按回车键继续处理其他文件...")
            input()
                
        except KeyboardInterrupt:
            print("\n\n程序被用户中断，退出...")
            break
        except Exception as e:
            print(f"\n发生错误: {e}")
            print("按回车键继续...")
            input()

def main():
    parser = argparse.ArgumentParser(description='ASS卡拉OK字幕处理工具 (简单拖拽版)')
    parser.add_argument('files', nargs='*', help='要处理的ASS文件路径')
    parser.add_argument('-o', '--output', help='指定输出文件路径')
    parser.add_argument('-ow', '--overwrite', action='store_true', help='自动覆盖已存在的输出文件')
    parser.add_argument('-q', '--quiet', action='store_true', help='安静模式，减少输出')
    parser.add_argument('-v', '--version', action='store_true', help='显示版本信息')
    parser.add_argument('-s', '--simple', action='store_true', help='启动简单交互模式(拖拽模式)')
    parser.add_argument('-r', '--restore', action='store_true', help='还原模式，将转换后的文件还原为原始格式')
    
    args = parser.parse_args()
    
    if args.version:
        print("ASS卡拉OK字幕处理工具 v2.0 (简单拖拽版)")
        return
    
    if args.quiet:
        sys.stdout = open(os.devnull, 'w')
    
    if args.simple:
        simple_interactive_mode(args.overwrite)
        return
    
    if args.files:
        success_count = 0
        for input_file in args.files:
            # 自动判断还原模式：如果文件名包含KTV效果，则自动使用还原模式
            auto_restore = args.restore or 'KTV效果' in os.path.basename(input_file)
            
            if auto_restore:
                success, _ = restore_original_ass(input_file, args.overwrite, args.output)
            else:
                success, _ = create_bilingual_ass(input_file, args.overwrite, args.output)
            if success:
                success_count += 1
        
        if not args.quiet:
            if success_count == len(args.files):
                print("所有文件处理完成!")
            else:
                print(f"部分文件处理失败! 成功: {success_count}/{len(args.files)}")
        return
    
    print("检测到没有文件参数，启动简单拖拽交互模式...")
    simple_interactive_mode(args.overwrite)

if __name__ == "__main__":
    main()