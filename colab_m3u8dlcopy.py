#@title M3U8下载-1.1
import os
import sys
import subprocess
import requests
import re
import json
import time
import shutil
from pathlib import Path
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

def print_banner():
    """打印美化的横幅"""
    print("\n" + "=" * 50)
    print("M3U8视频下载助手 v1.0")
    print("=" * 50)
    print("✨ 支持断点续传")
    print("✨ 自动合并分片")
    print("✨ 多线程下载加速")
    print("✨ 自动去除广告")
    print("=" * 50 + "\n")

def print_step(step, message):
    """打印带有步骤的消息"""
    print(f"[{step}] {message}")

def check_ffmpeg():
    """检查ffmpeg是否已安装"""
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def install_dependencies():
    """安装依赖"""
    try:
        print_step("⏬", "检查依赖...")
        if check_ffmpeg():
            print_step("ffmpeg已安装，跳过安装步骤")
            return True
            
        print_step("⏬", "正在安装ffmpeg...")
        # 只需要安装ffmpeg
        subprocess.run(["apt-get", "update", "-qq"], capture_output=True)
        subprocess.run(["apt-get", "install", "-y", "ffmpeg"], capture_output=True)
        print_step("依赖安装成功!")
        return True
    except Exception as e:
        print_step("❌", f"依赖安装失败: {str(e)}")
        return False

def analyze_m3u8(url):
    """分析m3u8文件，找出广告片段和分片URL"""
    try:
        print_step("🔍", "分析m3u8内容...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://vod.mycamtv.net',
            'Referer': 'https://vod.mycamtv.net/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Connection': 'keep-alive'
        }
        response = requests.get(url, headers=headers, timeout=10)
        content = response.text
        base_url = '/'.join(url.split('/')[:-1]) + '/'
        
        # 查找所有分片和时长
        segments = []
        total_duration = 0
        is_ad_segment = False
        duration = 0
        
        for line in content.split('\n'):
            if line.startswith('#EXTINF:'):
                duration = float(line.split(':')[1].split(',')[0])
            elif line.startswith('#EXT-X-DISCONTINUITY'):
                if duration > 0:
                    segments.append({
                        'start': total_duration,
                        'duration': duration,
                        'is_ad': is_ad_segment
                    })
                    total_duration += duration
                is_ad_segment = not is_ad_segment
            elif line.endswith('.ts') or line.endswith('.jpeg'):
                if not line.startswith('http'):
                    line = base_url + line
                if 'redtraffic' in line:
                    is_ad_segment = True
                segments.append({
                    'start': total_duration,
                    'duration': duration,
                    'is_ad': is_ad_segment,
                    'url': line
                })
                total_duration += duration
                duration = 0
        
        # 计算广告和视频时长
        ad_duration = sum(s['duration'] for s in segments if s['is_ad'])
        video_duration = sum(s['duration'] for s in segments if not s['is_ad'])
        
        print_step(f"视频总长: {video_duration:.1f}秒")
        print_step(f"广告时长: {ad_duration:.1f}秒")
        
        # 返回非广告片段
        non_ad_segments = [s for s in segments if not s['is_ad']]
        print_step(f"总片段数: {len(non_ad_segments)}")
        return non_ad_segments
        
    except Exception as e:
        print_step("⚠️", f"分析失败: {str(e)}")
        return None

def download_segment(seg_info):
    """下载单个分片，支持重试"""
    seg_path, url, index, total = seg_info
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Origin': 'https://vod.mycamtv.net',
        'Referer': 'https://vod.mycamtv.net/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'Connection': 'keep-alive'
    }
    
    for retry in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=30, stream=True)
            if response.status_code == 200:
                with open(seg_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                return index, True
            time.sleep(1)
        except Exception:
            if retry < 2:
                time.sleep(2)
            continue
    return index, False

def download_m3u8(url, output_dir, filename):
    """下载M3U8视频"""
    temp_dir = None
    start_time = time.time()
    try:
        # 确保安装了依赖
        if not install_dependencies():
            return
        
        # 分析m3u8内容
        analyze_start = time.time()
        segments = analyze_m3u8(url)
        analyze_time = time.time() - analyze_start
        print_step("⏱️", f"分析耗时: {analyze_time:.1f}秒")
        
        if not segments:
            print_step("⚠️", "无法分析视频片段，尝试直接下载...")
            segments = [{'url': url}]
        
        # 创建临时目录
        temp_dir = os.path.join(output_dir, "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        # 准备下载任务
        total_segments = len(segments)
        download_tasks = []
        for i, seg in enumerate(segments):
            seg_path = os.path.join(temp_dir, f"seg_{i:04d}.ts")
            download_tasks.append((seg_path, seg['url'], i, total_segments))
        
        # 使用线程池下载
        download_start = time.time()
        print_step("🚀", f"开始多线程下载 {total_segments} 个分片...")
        successful_segments = []
        failed_segments = []
        downloaded_count = 0
        
        with ThreadPoolExecutor(max_workers=32) as executor:
            futures = [executor.submit(download_segment, task) for task in download_tasks]
            for future in as_completed(futures):
                index, success = future.result()
                downloaded_count += 1
                if success:
                    successful_segments.append(index)
                else:
                    failed_segments.append(index)
                    print(f"\n⚠️ 分片 {index+1} 下载失败")
                print(f"\r进度: {downloaded_count}/{total_segments} ({(downloaded_count/total_segments)*100:.1f}%)", end="")
        print("\n")
        
        download_time = time.time() - download_start
        print_step("⏱️", f"下载耗时: {download_time:.1f}秒")
        
        if not successful_segments:
            raise Exception("没有成功下载的分片")
        
        if failed_segments:
            print_step("📊", f"成功: {len(successful_segments)}个, 失败: {len(failed_segments)}个")
        
        # 合并分片
        merge_start = time.time()
        print_step("📦", "合并分片...")
        # 创建文件列表
        list_file = os.path.join(temp_dir, "files.txt")
        with open(list_file, "w") as f:
            for i in sorted(successful_segments):
                f.write(f"file 'seg_{i:04d}.ts'\n")
        
        # 使用ffmpeg合并
        final_path = os.path.join(output_dir, filename)
        merge_cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            "-bsf:a", "aac_adtstoasc",
            "-movflags", "+faststart",
            final_path
        ]
        
        merge_result = subprocess.run(merge_cmd, capture_output=True, text=True)
        merge_time = time.time() - merge_start
        print_step("⏱️", f"合并耗时: {merge_time:.1f}秒")
        
        if merge_result.returncode != 0:
            print_step("⚠️", f"合并失败: {merge_result.stderr}")
            raise Exception("视频合并失败")
        
        # 检查结果
        if os.path.exists(final_path):
            size = os.path.getsize(final_path) / (1024*1024)  # 转换为MB
            total_time = time.time() - start_time
            print_step(f"下载完成: {filename} ({size:.1f}MB)")
            print_step(f"总耗时: {total_time:.1f}秒")
        else:
            raise Exception("输出文件不存在")
            
    except Exception as e:
        print_step("❌", f"下载失败: {str(e)}")
        total_time = time.time() - start_time
        print_step("⏱️", f"总耗时: {total_time:.1f}秒")
    finally:
        # 清理临时文件
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

def extract_m3u8_urls(file_path):
    """从文本文件中提取m3u8链接"""
    urls = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # 匹配以.m3u8结尾的URL
            pattern = r'https?://[^\s<>"\']+?\.m3u8'
            matches = re.findall(pattern, content)
            urls = list(set(matches))  # 去重
        print_step("🔍", f"找到 {len(urls)} 个m3u8链接")
        return urls
    except Exception as e:
        print_step("❌", f"提取链接失败: {str(e)}")
        return []

if __name__ == "__main__":
    print_banner()
    
    try:
        # 获取用户输入
        input_path = input("🔗 请输入m3u8链接或包含m3u8链接的文本文件路径: ").strip()
        if not input_path:
            print_step("❌", "错误：输入不能为空")
            sys.exit(1)
        
        # 设置输出目录
        output_dir = os.path.join(os.getcwd(), "output")
        os.makedirs(output_dir, exist_ok=True)
        
        urls_to_download = []
        if input_path.lower().endswith('.m3u8'):
            # 直接下载单个m3u8链接
            urls_to_download = [input_path]
        else:
            # 从文件中提取m3u8链接
            if not os.path.exists(input_path):
                print_step("❌", "错误：文件不存在")
                sys.exit(1)
            urls_to_download = extract_m3u8_urls(input_path)
            if not urls_to_download:
                print_step("❌", "未找到任何m3u8链接")
                sys.exit(1)
        
        print_step("📂", f"视频将保存到: {output_dir}")
        print("=" * 50)
        
        # 批量下载所有链接
        for i, url in enumerate(urls_to_download, 1):
            print(f"\n正在处理第 {i}/{len(urls_to_download)} 个文件")
            # 从URL中提取文件名
            filename = os.path.splitext(os.path.basename(urlparse(url).path))[0] + ".mp4"
            print_step("📝", f"文件名: {filename}")
            # 开始下载
            download_m3u8(url, output_dir, filename)
            print("=" * 50)
        
    except KeyboardInterrupt:
        print_step("🛑", "下载已取消")
    except Exception as e:
        print_step(f"发生错误: {str(e)}")
