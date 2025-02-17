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
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import warnings
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

def print_banner():
    """打印美化的横幅"""
    print("\n" + "=" * 50)
    print("M3U8视频下载助手 v1.1")
    print("=" * 50)
    print("✨ 支持断点续传")
    print("✨ 自动合并分片")
    print("✨ 多线程下载加速")
    print("✨ 自动去除广告")
    print("✨ 支持代理设置")
    print("=" * 50 + "\n")

def print_step(message, step=None):
    """打印带有步骤的消息"""
    if step is None:
        print(f"[INFO] {message}")
    else:
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

def analyze_m3u8(url, enable_ad_filter=True, ad_keywords=None):
    """分析m3u8文件，找出广告片段和分片URL"""
    try:
        print_step("🔍", "分析m3u8内容...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        content = response.text
        base_url = '/'.join(url.split('/')[:-1]) + '/'
        
        # 统计信息
        stats = {
            'normal': {'count': 0, 'duration': 0},
            'ad': {'count': 0, 'duration': 0}
        }
        
        segments = []
        duration = 0
        
        if not ad_keywords:
            ad_keywords = ['adjump', '/ad/', 'redtraffic']
            
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('#EXTINF:'):
                try:
                    duration = float(line.split(':')[1].split(',')[0])
                except:
                    duration = 0
                    
            elif line.startswith('#EXT-X-KEY'):
                if not line.startswith('http'):
                    key_path = re.search(r'URI="([^"]+)"', line)
                    if key_path:
                        full_key_url = urljoin(base_url, key_path.group(1))
                        line = line.replace(key_path.group(1), full_key_url)
                segments.append({'type': 'key', 'content': line})
                
            elif line.endswith('.ts') or line.endswith('.m4s') or line.endswith('.jpeg'):
                if not line.startswith('http'):
                    line = urljoin(base_url, line)
                    
                is_ad = False
                if enable_ad_filter:
                    is_ad = any(kw.lower() in line.lower() for kw in ad_keywords)
                    
                if is_ad:
                    stats['ad']['count'] += 1
                    stats['ad']['duration'] += duration
                else:
                    stats['normal']['count'] += 1
                    stats['normal']['duration'] += duration
                    segments.append({
                        'type': 'segment',
                        'url': line,
                        'duration': duration
                    })
            else:
                segments.append({'type': 'other', 'content': line})
        
        # 打印分析结果
        print_step("📊", "内容分析结果:")
        print(f"    视频片段: {stats['normal']['count']}个 ({stats['normal']['duration']:.1f}秒)")
        if stats['ad']['count'] > 0:
            print(f"    广告片段: {stats['ad']['count']}个 ({stats['ad']['duration']:.1f}秒)")
            ad_percentage = (stats['ad']['duration'] / (stats['normal']['duration'] + stats['ad']['duration'])) * 100
            print(f"    广告占比: {ad_percentage:.1f}%")
            
        return segments
        
    except Exception as e:
        print_step("⚠️", f"分析失败: {str(e)}")
        return None

def download_segment(seg_info):
    """下载单个分片，支持多次重试"""
    seg_path, url, index, total = seg_info
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # 增加重试次数和等待时间
    max_retries = 5
    retry_delays = [1, 2, 4, 8, 16]  # 递增的等待时间
    
    for retry in range(max_retries):
        try:
            # 使用session来保持连接
            with requests.Session() as session:
                response = session.get(
                    url,
                    headers=headers,
                    timeout=30,
                    stream=True,
                    verify=False  # 忽略SSL证书验证
                )
                
                if response.status_code == 200:
                    # 确保目录存在
                    os.makedirs(os.path.dirname(seg_path), exist_ok=True)
                    
                    # 分块下载
                    content_length = int(response.headers.get('content-length', 0))
                    downloaded_size = 0
                    
                    with open(seg_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded_size += len(chunk)
                    
                    # 验证下载的文件大小
                    if content_length > 0 and downloaded_size != content_length:
                        raise Exception("文件大小不匹配")
                    
                    if os.path.getsize(seg_path) > 0:
                        return index, True, downloaded_size
                    else:
                        raise Exception("下载的文件大小为0")
                
                elif response.status_code == 404:
                    print(f"\n⚠️ 分片 {index+1} 不存在 (404)")
                    return index, False, 0
                else:
                    print(f"\n⚠️ 分片 {index+1} 返回状态码: {response.status_code}")
            
            # 如果需要重试，等待一段时间
            if retry < max_retries - 1:
                time.sleep(retry_delays[retry])
                
        except requests.exceptions.Timeout:
            print(f"\n⚠️ 分片 {index+1} 下载超时")
            if retry < max_retries - 1:
                time.sleep(retry_delays[retry])
                
        except requests.exceptions.ConnectionError:
            print(f"\n⚠️ 分片 {index+1} 连接错误")
            if retry < max_retries - 1:
                time.sleep(retry_delays[retry])
                
        except Exception as e:
            print(f"\n⚠️ 分片 {index+1} 下载错误: {str(e)}")
            if retry < max_retries - 1:
                time.sleep(retry_delays[retry])
    
    return index, False, 0

def download_m3u8(url, output_dir, filename, enable_ad_filter=True, thread_count=32, max_retries=10):
    """下载M3U8视频"""
    temp_dir = None
    start_time = time.time()
    
    for retry_count in range(max_retries):
        try:
            # 确保安装了依赖
            if not install_dependencies():
                return False
            
            # 分析m3u8内容
            analyze_start = time.time()
            segments = analyze_m3u8(url, enable_ad_filter)
            analyze_time = time.time() - analyze_start
            print_step("⏱️", f"分析耗时: {analyze_time:.1f}秒")
            
            if not segments:
                print_step("⚠️", "无法分析视频片段")
                continue  # 重试
            
            # 创建临时目录
            temp_dir = os.path.join(output_dir, "temp")
            os.makedirs(temp_dir, exist_ok=True)
            
            # 准备下载任务
            download_tasks = []
            for i, seg in enumerate(segments):
                if seg['type'] == 'segment':  # 只下载视频片段
                    seg_path = os.path.join(temp_dir, f"seg_{i:04d}.ts")
                    download_tasks.append((seg_path, seg['url'], i, len(segments)))
            
            if not download_tasks:
                print_step("⚠️", "没有找到可下载的视频片段")
                continue  # 重试
            
            # 使用线程池下载
            download_start = time.time()
            print_step("🚀", f"开始多线程下载 {len(download_tasks)} 个分片...")
            successful_segments = []
            failed_segments = []
            downloaded_count = 0
            total_size = 0
            
            with ThreadPoolExecutor(max_workers=thread_count) as executor:
                futures = [executor.submit(download_segment, task) for task in download_tasks]
                for future in as_completed(futures):
                    index, success, size = future.result()
                    downloaded_count += 1
                    if success:
                        successful_segments.append(index)
                        total_size += size
                    else:
                        failed_segments.append(index)
                        print(f"\n⚠️ 分片 {index+1} 下载失败")
                        
                    # 显示下载进度
                    progress = downloaded_count / len(download_tasks) * 100
                    size_mb = total_size / (1024 * 1024)
                    print(f"\r进度: {downloaded_count}/{len(download_tasks)} ({progress:.1f}%) - 已下载: {size_mb:.1f}MB", end="")
            
            print("\n")
            
            # 如果有失败的分片，重试这些分片
            if failed_segments:
                print_step("⚠️", f"有 {len(failed_segments)} 个分片下载失败，正在重试...")
                retry_tasks = []
                for index in failed_segments:
                    for task in download_tasks:
                        if task[2] == index:  # task[2] 是 index
                            retry_tasks.append(task)
                            break
                
                with ThreadPoolExecutor(max_workers=thread_count) as executor:
                    futures = [executor.submit(download_segment, task) for task in retry_tasks]
                    for future in as_completed(futures):
                        index, success, size = future.result()
                        if success:
                            successful_segments.append(index)
                            total_size += size
                            print(f"\r重试成功: 分片 {index+1}", end="")
                        else:
                            print(f"\n❌ 分片 {index+1} 重试失败")
                
                print("\n")
            
            download_time = time.time() - download_start
            print_step("⏱️", f"下载耗时: {download_time:.1f}秒")
            
            if not successful_segments:
                print_step("❌", "没有成功下载的分片，准备重试...")
                continue  # 重试整个下载过程
            
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
            
            if merge_result.returncode != 0:
                print_step("⚠️", f"合并失败: {merge_result.stderr}")
                continue  # 重试
            
            print_step("⏱️", f"合并耗时: {merge_time:.1f}秒")
            
            # 检查结果
            if os.path.exists(final_path):
                size = os.path.getsize(final_path) / (1024*1024)  # 转换为MB
                total_time = time.time() - start_time
                print_step(f"下载完成: {filename} ({size:.1f}MB)")
                print_step(f"总耗时: {total_time:.1f}秒")
                return True
            
            print_step("⚠️", "输出文件不存在，准备重试...")
            
        except Exception as e:
            print_step("❌", f"下载出错: {str(e)}")
            if retry_count < max_retries - 1:
                print_step("⚠️", f"第 {retry_count + 1} 次重试失败，准备下一次重试...")
                time.sleep(2)  # 等待2秒后重试
            else:
                print_step("❌", "已达到最大重试次数，下载失败")
        finally:
            # 清理临时文件
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
    
    return False

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

def analyze_m3u8_for_keywords(url):
    """分析m3u8内容以寻找可能的广告关键词"""
    try:
        print("\n正在分析M3U8内容...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        content = response.text
        lines = content.split('\n')
        
        # 分析不连续的行
        print("\n" + "=" * 50)
        print("M3U8文件内容分析:")
        print("=" * 50)
        
        # 查找不连续的片段
        discontinuity_positions = []
        for i, line in enumerate(lines):
            if '#EXT-X-DISCONTINUITY' in line:
                discontinuity_positions.append(i)
        
        # 显示不连续点的上下文
        if discontinuity_positions:
            print("\n发现不连续点:")
            for pos in discontinuity_positions:
                print("\n" + "-" * 30)
                print(f"不连续点位置: 第{pos + 1}行")
                # 显示前5行和后5行
                start = max(0, pos - 5)
                end = min(len(lines), pos + 6)
                for i in range(start, end):
                    prefix = ">>> " if i == pos else "    "
                    print(f"{prefix}[{i + 1:4d}] {lines[i]}")
        else:
            print("\n未发现不连续点")
            
        print("\n" + "=" * 50)
        
        # 分析可能的广告关键词
        potential_keywords = set()
        for line in lines:
            if line.strip() and (line.endswith('.ts') or line.endswith('.m4s')):
                parts = line.lower().split('/')
                for part in parts:
                    if 'ad' in part or 'jump' in part or 'promo' in part:
                        potential_keywords.add(part)
        
        return potential_keywords
        
    except Exception as e:
        print(f"\n分析失败: {str(e)}")
        return set()

def get_user_input():
    """获取用户输入的所有配置"""
    print("\n" + "=" * 50)
    print("请配置下载选项:")
    print("=" * 50)
    
    # 获取输入链接或文件
    while True:
        input_path = input("1. 请输入m3u8链接或包含链接的文本文件路径: ").strip()
        if input_path:
            break
        print("❌ 输入不能为空，请重试")
    
    # 如果是单个m3u8链接，分析内容
    potential_keywords = set()
    if input_path.lower().endswith('.m3u8'):
        # 询问是否需要拼接网址
        should_concat = input("\n链接是否不完整? (y/N): ").strip().lower() == 'y'
        if should_concat:
            # 从URL中提取基础URL
            m3u8_url = input_path
            base_url = '/'.join(m3u8_url.split('/')[:-1]) + '/'
            if not input_path.startswith('http'):
                input_path = urljoin(base_url, input_path)
                print(f"完整链接: {input_path}")
        potential_keywords = analyze_m3u8_for_keywords(input_path)
    
    # 询问广告关键词
    print("\n2. 请输入广告关键词:")
    if potential_keywords:
        print("发现可能的广告关键词:")
        for kw in potential_keywords:
            print(f"• {kw}")
    keywords = input("请输入广告关键词(多个关键词用逗号分隔): ").strip()
    ad_keywords = [kw.strip() for kw in keywords.split(',')] if keywords else ['adjump', '/ad/', 'redtraffic']
    
    # 询问输出目录
    output_dir = input("\n3. 请输入保存目录 (直接回车使用默认目录'output'): ").strip()
    if not output_dir:
        output_dir = 'output'
    
    return {
        'input_path': input_path,
        'enable_ad_filter': True,
        'ad_keywords': ad_keywords,
        'output_dir': output_dir,
        'thread_count': 32
    }

def main():
    """主函数"""
    print_banner()
    
    try:
        # 获取用户配置
        config = get_user_input()
        
        # 创建输出目录
        output_dir = os.path.join(os.getcwd(), config['output_dir'])
        os.makedirs(output_dir, exist_ok=True)
        
        # 获取下载链接
        urls_to_download = []
        if config['input_path'].lower().endswith('.m3u8'):
            urls_to_download = [config['input_path']]
        else:
            if not os.path.exists(config['input_path']):
                print_step("❌", "错误：文件不存在")
                return
            urls_to_download = extract_m3u8_urls(config['input_path'])
        
        if not urls_to_download:
            print_step("❌", "未找到任何m3u8链接")
            return
        
        print_step("📂", f"视频将保存到: {output_dir}")
        print("=" * 50)
        
        # 开始下载
        for i, url in enumerate(urls_to_download, 1):
            print(f"\n正在处理第 {i}/{len(urls_to_download)} 个文件")
            filename = os.path.splitext(os.path.basename(urlparse(url).path))[0] + ".mp4"
            print_step("📝", f"文件名: {filename}")
            download_m3u8(
                url=url,
                output_dir=output_dir,
                filename=filename,
                enable_ad_filter=config['enable_ad_filter'],
                thread_count=config['thread_count']
            )
            print("=" * 50)
            
    except KeyboardInterrupt:
        print_step("🛑", "下载已取消")
    except Exception as e:
        print_step("❌", f"发生错误: {str(e)}")

if __name__ == "__main__":
    main()
