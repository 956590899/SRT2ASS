import os
import re
import sys
from datetime import timedelta

###############################################################################
#                             删除规则配置区
# 在这里添加或修改删除规则，方便后续调整
###############################################################################

def parse_time_to_milliseconds(time_str):
    """将LRC时间格式[mm:ss.xx]转换为毫秒"""
    time_str = time_str.strip('[]')
    
    if '.' in time_str:
        minutes_str, rest = time_str.split(':', 1)
        seconds_str, centiseconds_str = rest.split('.')
    else:
        minutes_str, seconds_str = time_str.split(':', 1)
        centiseconds_str = '00'
    
    minutes = int(minutes_str)
    seconds = int(seconds_str)
    centiseconds = int(centiseconds_str.ljust(2, '0')[:2])
    
    total_milliseconds = (minutes * 60 + seconds) * 1000 + (centiseconds * 10)
    return total_milliseconds

# 全局删除规则（无论时间轴在哪里都删除）
GLOBAL_DELETE_RULES = [
    # 规则1: 删除无时间轴段（包含时间轴为[00:00.00]的行）
    {
        'name': '无时间轴或00:00.00',
        'condition': lambda stripped, time_matches, content: (
            not time_matches or any(time_match == '[00:00.00]' for time_match in time_matches)
        ),
        'reason': lambda stripped, content: "无时间轴或时间轴为00:00.00"
    },
    
    # 规则2: 文本内容包含冒号(:)符号 - 全局删除
    {
        'name': '包含冒号(全局)',
        'condition': lambda stripped, time_matches, content: (
            ':' in content or '：' in content
        ),
        'reason': lambda stripped, content: "包含冒号符号(全局)"
    },
]

# 前10秒删除规则（只在时间轴在0-30秒内的行中删除）
# 要检查的时间范围（毫秒）
TIME_LIMIT_MS = 10000  # 10秒 = 10000毫秒

# 要删除的关键词列表（任意一个出现就会触发）
DELETE_KEYWORDS = [
    '/',           # 斜杠
    '-',         # 横线连接符（有空格）
    '本翻译作品的著作权',  # 版权声明
    '翻译',        # 翻译字样
    '歌词'         # 歌词字样
]

# 规则名称（显示用）
RULE_NAME = "前10秒删除规则"

# 删除原因（显示用）
DELETE_REASON = "前10秒内包含斜杠/横线/版权声明/翻译/歌词字样"

# ================================
# 【代码区域】以下部分不需要修改
# ================================

FIRST_10S_DELETE_RULES = [
    {
        'name': RULE_NAME,
        'condition': lambda stripped, time_matches, content: (
            any(keyword in content for keyword in DELETE_KEYWORDS) and
            # 只检查第一个时间戳（开始时间）
            time_matches and  # 确保有时间戳
            parse_time_to_milliseconds(time_matches[0]) <= TIME_LIMIT_MS
        ),
        'reason': lambda stripped, content: DELETE_REASON
    },
]

# 合并所有规则（先应用全局规则，再应用前10秒规则）
DELETE_RULES = GLOBAL_DELETE_RULES + FIRST_10S_DELETE_RULES

###############################################################################
#                             主程序代码
###############################################################################

def detect_encoding(file_path):
    """文件编码检测"""
    try:
        with open(file_path, 'rb') as f:
            raw = f.read(4)
        
        if raw.startswith(b'\xff\xfe\x00\x00'):
            return 'utf-32-le'
        elif raw.startswith(b'\x00\x00\xfe\xff'):
            return 'utf-32-be'
        elif raw.startswith(b'\xff\xfe'):
            return 'utf-16-le'
        elif raw.startswith(b'\xfe\xff'):
            return 'utf-16-be'
        elif raw.startswith(b'\xef\xbb\xbf'):
            return 'utf-8-sig'
    except:
        pass
    
    encodings = ['utf-8-sig', 'gbk', 'gb2312', 'gb18030', 'utf-8']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read(100)
            return encoding
        except:
            continue
    
    return 'utf-8'

def should_delete_line(line):
    """判断一行是否应该删除"""
    stripped = line.strip()
    
    # 空行直接删除
    if not stripped:
        return True, "空行"
    
    # 检查是否包含时间轴字符
    time_pattern = r'\[\d{1,2}:\d{2}\.\d{2}\]'
    time_matches = re.findall(time_pattern, stripped)
    
    # 提取时间轴之后的内容
    content = re.sub(time_pattern, '', stripped).strip()
    
    # 应用删除规则
    for rule in DELETE_RULES:
        if rule['condition'](stripped, time_matches, content):
            return True, rule['reason'](stripped, content)
    
    # 如果没有匹配任何删除规则，则保留
    return False, "保留"

def milliseconds_to_srt_time(milliseconds):
    """将毫秒转换为SRT时间格式: HH:MM:SS,mmm"""
    td = timedelta(milliseconds=milliseconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    ms = td.microseconds // 1000
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"

def convert_lrc_to_srt(lyric_lines):
    """将LRC歌词行转换为SRT格式，支持双语字幕"""
    if not lyric_lines:
        return []
    
    # 解析所有歌词行
    lyric_data = []
    for line in lyric_lines:
        stripped = line.strip()
        if not stripped:
            continue
        
        match = re.match(r'\[(\d{1,2}:\d{2}\.\d{2})\](.*)', stripped)
        if match:
            time_str = match.group(1)
            lyric_text = match.group(2).strip()
            
            if lyric_text:
                milliseconds = parse_time_to_milliseconds(time_str)
                lyric_data.append({
                    'time': milliseconds,
                    'text': lyric_text
                })
    
    # 按时间排序
    lyric_data.sort(key=lambda x: x['time'])
    
    # 找出所有唯一的时间点
    unique_times = []
    for item in lyric_data:
        if item['time'] not in unique_times:
            unique_times.append(item['time'])
    
    # 创建SRT条目
    srt_entries = []
    entry_number = 1
    
    for i, current_time in enumerate(unique_times):
        # 获取当前时间点的所有歌词
        current_lyrics = [item for item in lyric_data if item['time'] == current_time]
        
        # 计算结束时间
        if i < len(unique_times) - 1:
            next_time = unique_times[i + 1]
            end_time = next_time - 100  # 减0.1秒
        else:
            end_time = current_time + 5000  # 最后一句显示5秒
        
        # 确保结束时间晚于开始时间
        if end_time <= current_time:
            end_time = current_time + 100
        
        # 为当前时间点的每句歌词创建SRT条目
        for lyric_item in current_lyrics:
            start_srt = milliseconds_to_srt_time(current_time)
            end_srt = milliseconds_to_srt_time(end_time)
            
            entry = f"{entry_number}\n{start_srt} --> {end_srt}\n{lyric_item['text']}\n\n"
            srt_entries.append(entry)
            entry_number += 1
    
    return srt_entries

def print_detailed_deletion_log(deleted_lines_info):
    """打印详细的删除日志 - 显示所有删除行（跳过空行）"""
    if not deleted_lines_info:
        print("没有删除任何行")
        return
    
    # 过滤掉空行的删除日志
    filtered_deleted_lines = [(line, reason) for line, reason in deleted_lines_info if reason != "空行"]
    
    if not filtered_deleted_lines:
        print("没有删除任何非空行")
        return
    
    print("\n" + "=" * 100)
    print("全部删除日志 (显示所有被删除的行):")
    print("=" * 100)
    
    for i, (line, reason) in enumerate(filtered_deleted_lines, 1):
        line_stripped = line.strip()
        print(f"{i:3}. 删除原因: {reason}")
        print(f"    行内容: {line_stripped}")
        if i < len(filtered_deleted_lines):
            print("-" * 40)
    
    print("=" * 100)
    print(f"总计: {len(deleted_lines_info)} 行被删除（其中 {len(filtered_deleted_lines)} 行为非空行）")

def process_single_file(input_path):
    """处理单个LRC文件"""
    try:
        print(f"正在处理文件: {os.path.basename(input_path)}")
        
        # 检测编码并读取文件
        encoding = detect_encoding(input_path)
        
        with open(input_path, 'r', encoding=encoding, errors='replace') as file:
            lines = file.readlines()
        
        print(f"文件编码: {encoding}")
        print(f"原始行数: {len(lines)}")
        print("正在应用删除规则...")
        
        # 显示删除规则信息
        print(f"\n当前删除规则配置:")
        print(f"  全局删除规则: {len(GLOBAL_DELETE_RULES)} 条")
        print(f"  前10秒删除规则: {len(FIRST_10S_DELETE_RULES)} 条")
        print(f"  总计: {len(DELETE_RULES)} 条规则")
        
        # 应用删除规则，同时记录删除日志
        cleaned_lines = []
        deleted_count = 0
        delete_reasons = {}
        deleted_lines_info = []  # 存储被删除的行和原因
        
        for line_number, line in enumerate(lines, 1):
            should_delete, reason = should_delete_line(line)
            if should_delete:
                deleted_count += 1
                delete_reasons[reason] = delete_reasons.get(reason, 0) + 1
                deleted_lines_info.append((line, reason))
            else:
                cleaned_lines.append(line)
        
        # 显示删除统计
        print(f"\n处理完成!")
        print(f"保留行数: {len(cleaned_lines)}")
        print(f"删除行数: {deleted_count}")
        
        if deleted_count > 0:
            print("\n删除原因统计:")
            for reason, count in delete_reasons.items():
                print(f"  {reason}: {count}行")
            
            # 显示全部删除日志
            print_detailed_deletion_log(deleted_lines_info)
        else:
            print("没有删除任何行")
        
        # 转换为SRT格式
        srt_entries = convert_lrc_to_srt(cleaned_lines)
        
        if not srt_entries:
            print("⚠ 警告: 没有有效的歌词行，无法转换")
            return False
        
        # 生成输出文件名
        base_name = os.path.splitext(input_path)[0]
        srt_path = f"{base_name}.srt"
        
        # 写入SRT文件
        with open(srt_path, 'w', encoding='utf-8') as file:
            file.writelines(srt_entries)
        
        print(f"\n✓ 转换完成!")
        print(f"  SRT文件: {srt_path}")
        print(f"  字幕条数: {len(srt_entries)}")
        
        # 显示转换后的前10行预览
        if srt_entries and len(srt_entries) > 0:
            print("\nSRT文件预览 (前10条):")
            for i, entry in enumerate(srt_entries[:10]):
                entry_lines = entry.split('\n')
                if len(entry_lines) >= 3:
                    time_info = entry_lines[1]
                    text_info = entry_lines[2].strip()
                    print(f"{i+1:2}. {time_info} - {text_info}")
        
        return True
        
    except Exception as e:
        print(f"✗ 处理出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def process_directory(input_dir):
    """处理目录中的所有LRC文件"""
    try:
        print(f"正在处理目录: {input_dir}")
        
        # 创建SRT子目录
        srt_dir = os.path.join(input_dir, "SRT")
        if not os.path.exists(srt_dir):
            os.makedirs(srt_dir)
        
        # 支持的文件扩展名
        valid_extensions = ['.lrc', '.txt']
        
        processed_count = 0
        failed_count = 0
        
        for root, dirs, files in os.walk(input_dir):
            # 跳过SRT子目录本身
            if "SRT" in root and root.endswith("SRT"):
                continue
            
            for file in files:
                # 检查文件扩展名
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in valid_extensions:
                    file_path = os.path.join(root, file)
                    
                    # 处理文件
                    success = process_single_file(file_path)
                    if success:
                        processed_count += 1
                    else:
                        failed_count += 1
                    
                    print()  # 空行分隔每个文件
        
        print(f"\n目录处理完成:")
        print(f"  成功转换: {processed_count} 个文件")
        print(f"  转换失败: {failed_count} 个文件")
        if processed_count > 0:
            print(f"  输出目录: {srt_dir}")
        
        return processed_count > 0
        
    except Exception as e:
        print(f"✗ 处理出错: {e}")
        return False

def quick_process(input_path):
    """快速处理模式"""
    if os.path.isfile(input_path):
        return process_single_file(input_path)
    else:
        return process_directory(input_path)

def interactive_mode():
    """交互模式"""
    print("歌词文件转SRT字幕工具 v4.2")
    print("功能：歌词清理并转换为SRT字幕格式")
    print("\n当前删除规则配置:")
    print("  全局删除规则:")
    for i, rule in enumerate(GLOBAL_DELETE_RULES, 1):
        print(f"    {i}. {rule['name']}")
    print("  前10秒删除规则 (仅在时间轴0-10秒内生效):")
    for i, rule in enumerate(FIRST_10S_DELETE_RULES, 1):
        print(f"    {i}. {rule['name']}")
    print("\n支持的输入格式：.lrc, .txt")
    print("输出格式：.srt（UTF-8编码）")
    print("\n支持拖放文件或目录到窗口\n")
    
    while True:
        input_path = input("请输入歌词文件或目录路径（直接回车退出）: ").strip()
        input_path = input_path.strip('"\'')
        
        if not input_path:
            print("已退出程序")
            break
        
        if not os.path.exists(input_path):
            print(f"错误：路径 '{input_path}' 不存在")
            continue
        
        if os.path.isfile(input_path):
            success = process_single_file(input_path)
        else:
            success = process_directory(input_path)
        
        if success:
            print(f"\n✓ 转换完成！")
        
        print()

def main():
    """主函数"""
    if len(sys.argv) > 1:
        # 命令行模式：快速处理
        success = True
        for arg in sys.argv[1:]:
            if not os.path.exists(arg):
                print(f"错误：路径 '{arg}' 不存在")
                success = False
                continue
            
            if not quick_process(arg):
                success = False
        
        # 设置退出代码
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        # 交互模式
        interactive_mode()

if __name__ == "__main__":
    main()