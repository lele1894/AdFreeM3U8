import customtkinter as ctk
from tkinter import scrolledtext, filedialog
import requests
import re
from pathlib import Path
import subprocess
import os
import threading
from datetime import datetime
import tkinter as tk

class M3u8DownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("M3U8下载器-QQ:273356663")
        
        # 设置主题
        ctk.set_appearance_mode("dark")  # 暗色主题
        ctk.set_default_color_theme("blue")  # 蓝色主题
        
        # 设置最小窗口大小
        root.minsize(800, 600)
        
        # 创建主框架
        main_frame = ctk.CTkFrame(root)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # 创建顶部控件框架
        top_frame = ctk.CTkFrame(main_frame)
        top_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        # URL输入框和加载按钮框架
        url_label = ctk.CTkLabel(top_frame, text="M3U8链接:")
        url_label.grid(row=0, column=0, sticky="w")
        
        url_frame = ctk.CTkFrame(top_frame)
        url_frame.grid(row=0, column=1, sticky="ew", padx=5)
        url_frame.grid_columnconfigure(0, weight=1)
        
        self.url_entry = ctk.CTkEntry(url_frame, width=600)
        self.url_entry.grid(row=0, column=0, sticky="ew")
        # 绑定回车键
        self.url_entry.bind('<Return>', lambda e: self.start_download())
        
        # 添加加载M3U8内容按钮
        self.load_btn = ctk.CTkButton(
            url_frame,
            text="加载M3U8内容",
            command=self.load_m3u8_content,
            width=100
        )
        self.load_btn.grid(row=0, column=1, padx=5)
        
        # 创建广告过滤框架
        ad_frame = ctk.CTkFrame(main_frame)
        ad_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(0,5))
        
        # 添加广告过滤开关
        self.enable_ad_filter = tk.BooleanVar(value=False)
        self.ad_filter_checkbox = ctk.CTkCheckBox(
            ad_frame,
            text="启用广告过滤",
            variable=self.enable_ad_filter,
            command=self.toggle_ad_filter
        )
        self.ad_filter_checkbox.grid(row=0, column=0, padx=5)
        
        # 广告关键词输入框
        ad_label = ctk.CTkLabel(ad_frame, text="广告关键词:")
        ad_label.grid(row=0, column=1, sticky="w", padx=(10,0))
        
        self.ad_keywords_entry = ctk.CTkEntry(ad_frame, width=300)
        self.ad_keywords_entry.grid(row=0, column=2, sticky="ew", padx=5)
        self.ad_keywords_entry.insert(0, "adjump")  # 默认关键词
        self.ad_keywords_entry.configure(state="disabled")  # 初始状态禁用
        
        # 添加链接拼接选项
        self.should_concat = tk.BooleanVar(value=True)
        self.concat_checkbox = ctk.CTkCheckBox(
            ad_frame,
            text="拼接不完整链接",
            variable=self.should_concat
        )
        self.concat_checkbox.grid(row=0, column=3, padx=5)
        
        # 线程数输入框
        thread_label = ctk.CTkLabel(top_frame, text="线程数:")
        thread_label.grid(row=0, column=2, sticky="w", padx=(10,0))
        
        self.thread_entry = ctk.CTkEntry(top_frame, width=50)
        self.thread_entry.grid(row=0, column=3, padx=5)
        self.thread_entry.insert(0, "16")  # 默认16线程
        
        # 下载按钮
        self.download_btn = ctk.CTkButton(
            top_frame, 
            text="下载",
            command=self.start_download
        )
        self.download_btn.grid(row=0, column=4, padx=5)
        
        # 批量下载按钮
        self.batch_btn = ctk.CTkButton(
            top_frame,
            text="批量下载",
            command=self.batch_download
        )
        self.batch_btn.grid(row=0, column=5, padx=5)
        
        # 创建第二行框架
        second_frame = ctk.CTkFrame(main_frame)
        second_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=(0,5))
        
        # 保存路径选择
        path_label = ctk.CTkLabel(second_frame, text="保存目录:")
        path_label.grid(row=0, column=0, sticky="w")
        
        self.path_var = tk.StringVar(value="./downloads")  # 默认下载目录
        self.path_entry = ctk.CTkEntry(second_frame, textvariable=self.path_var, width=300)
        self.path_entry.grid(row=0, column=1, sticky="w", padx=5)
        
        self.path_btn = ctk.CTkButton(
            second_frame,
            text="选择目录",
            command=self.choose_directory,
            width=80
        )
        self.path_btn.grid(row=0, column=2, padx=5)

        # 代理设置
        # 代理启用复选框
        self.use_proxy_var = tk.BooleanVar(value=False)
        self.use_proxy_checkbox = ctk.CTkCheckBox(
            second_frame,
            text="启用代理",
            variable=self.use_proxy_var,
            command=self.toggle_proxy
        )
        self.use_proxy_checkbox.grid(row=0, column=3, padx=(20,5))
        
        # 代理地址输入框
        proxy_label = ctk.CTkLabel(second_frame, text="代理地址:")
        proxy_label.grid(row=0, column=4, padx=5)
        
        self.proxy_entry = ctk.CTkEntry(second_frame, width=200)
        self.proxy_entry.grid(row=0, column=5, sticky="ew", padx=5)
        self.proxy_entry.insert(0, "http://127.0.0.1:10809")  # 默认代理地址
        self.proxy_entry.configure(state="disabled")  # 初始状态禁用

        # 创建日志控制框架
        log_control_frame = ctk.CTkFrame(main_frame)
        log_control_frame.grid(row=3, column=0, sticky="ew", padx=5, pady=(0,5))

        # 添加日志自动滚动开关
        self.auto_scroll = tk.BooleanVar(value=True)
        self.auto_scroll_checkbox = ctk.CTkCheckBox(
            log_control_frame,
            text="日志自动滚动",
            variable=self.auto_scroll
        )
        self.auto_scroll_checkbox.grid(row=0, column=0, padx=5)

        # 添加清空日志按钮
        self.clear_log_btn = ctk.CTkButton(
            log_control_frame,
            text="清空日志",
            command=self.clear_log,
            width=80
        )
        self.clear_log_btn.grid(row=0, column=1, padx=5)
        
        # 日志显示区域
        self.log_area = scrolledtext.ScrolledText(
            main_frame,
            font=("Consolas", 10),
            bg="#2b2b2b",
            fg="#ffffff"
        )
        self.log_area.grid(row=4, column=0, sticky="nsew", padx=5, pady=5)
        
        # 配置grid权重
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)
        
        main_frame.grid_rowconfigure(4, weight=1)  # 日志区域可扩展
        main_frame.grid_columnconfigure(0, weight=1)
        second_frame.grid_columnconfigure(5, weight=1)  # 代理地址输入框可扩展

        # 显示使用说明
        self.show_usage_guide()

    def show_usage_guide(self):
        """显示详细使用说明"""
        self.log("=" * 50)
        self.log("M3U8下载器使用说明")
        self.log("=" * 50)
        self.log("\n1. 基本功能:")
        self.log("   - 支持M3U8视频下载")
        self.log("   - 支持广告内容过滤（可选）")
        self.log("   - 支持批量下载")
        self.log("   - 支持代理设置")
        
        self.log("\n2. 使用步骤:")
        self.log("   2.1 单个视频下载:")
        self.log("       a) 输入M3U8链接")
        self.log("       b) 点击「加载M3U8内容」按钮分析内容")
        self.log("       c) 如需过滤广告:")
        self.log("          - 勾选「启用广告过滤」")
        self.log("          - 在广告关键词输入框中输入关键词（多个关键词用逗号分隔）")
        self.log("       d) 选择是否需要拼接不完整链接")
        self.log("       e) 设置下载线程数（默认16）")
        self.log("       f) 选择保存目录")
        self.log("       g) 点击「下载」按钮开始下载")
        
        self.log("\n   2.2 批量下载:")
        self.log("       a) 准备包含多个M3U8链接的txt文本文件")
        self.log("       b) 点击「批量下载」按钮选择文件")
        self.log("       c) 程序会自动处理文件中的所有链接")
        
        self.log("\n3. 高级功能:")
        self.log("   3.1 广告过滤（可选功能）:")
        self.log("       - 默认关闭，需手动启用")
        self.log("       - 勾选「启用广告过滤」复选框开启功能")
        self.log("       - 在广告关键词输入框中输入关键词")
        self.log("       - 支持多个关键词，用逗号分隔")
        self.log("       - 建议先加载M3U8内容分析可能的广告特征")
        
        self.log("   3.2 代理设置:")
        self.log("       - 勾选「启用代理」复选框")
        self.log("       - 输入代理服务器地址（默认http://127.0.0.1:10809）")
        self.log("       - 代理设置对加载M3U8内容和下载过程都有效")
        
        self.log("\n4. 注意事项:")
        self.log("   - 建议先使用「加载M3U8内容」分析链接")
        self.log("   - 广告过滤功能默认关闭，需要时请手动启用")
        self.log("   - 如遇下载失败，可尝试启用代理")
        self.log("   - 批量下载时会使用当前的广告过滤设置")
        
        self.log("\n5. 快捷操作:")
        self.log("   - 输入链接后按回车键快速开始下载")
        self.log("   - 可以随时点击「选择目录」更改保存位置")
        self.log("   - 可以关闭日志自动滚动以查看历史记录")
        self.log("   - 使用清空日志按钮快速清除日志")
        
        self.log("\n" + "=" * 50)
        self.log("准备就绪，请开始使用！")
        self.log("=" * 50 + "\n")

    def toggle_proxy(self):
        """切换代理输入框状态"""
        if self.use_proxy_var.get():
            self.proxy_entry.configure(state="normal")
        else:
            self.proxy_entry.configure(state="disabled")

    def toggle_ad_filter(self):
        """切换广告过滤状态"""
        if self.enable_ad_filter.get():
            self.ad_keywords_entry.configure(state="normal")
        else:
            self.ad_keywords_entry.configure(state="disabled")

    def log(self, message):
        """添加日志信息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.insert("end", f"[{timestamp}] {message}\n")
        # 只在启用自动滚动时滚动到最新内容
        if self.auto_scroll.get():
            self.log_area.see("end")

    def start_download(self):
        """开始下载"""
        url = self.url_entry.get().strip()
        if not url:
            self.log("错误: 链接不能为空!")
            return
            
        # 获取并验证线程数
        try:
            thread_count = int(self.thread_entry.get())
            if thread_count < 1:
                raise ValueError
        except ValueError:
            self.log("错误: 线程数必须是正整数!")
            return
            
        # 禁用UI
        self.disable_ui()
        
        # 在新线程中执行下载
        thread = threading.Thread(
            target=self.download_process,
            args=(url, thread_count)
        )
        thread.daemon = True
        thread.start()

    def disable_ui(self):
        """禁用UI控件"""
        self.download_btn.configure(state="disabled")
        self.batch_btn.configure(state="disabled") 
        self.url_entry.configure(state="disabled")
        self.thread_entry.configure(state="disabled")
        self.load_btn.configure(state="disabled")  # 添加加载按钮禁用
        self.use_proxy_checkbox.configure(state="disabled")  # 添加代理复选框禁用
        if self.use_proxy_var.get():
            self.proxy_entry.configure(state="disabled")  # 如果代理已启用，禁用代理输入框

    def enable_ui(self):
        """启用UI控件"""
        self.download_btn.configure(state="normal")
        self.batch_btn.configure(state="normal")
        self.url_entry.configure(state="normal")
        self.thread_entry.configure(state="normal")
        self.load_btn.configure(state="normal")  # 添加加载按钮启用
        self.use_proxy_checkbox.configure(state="normal")  # 添加代理复选框启用
        if self.use_proxy_var.get():
            self.proxy_entry.configure(state="normal")  # 如果代理已启用，启用代理输入框

    def choose_directory(self):
        """选择保存目录"""
        directory = filedialog.askdirectory(
            title="选择保存目录",
            initialdir=self.path_var.get()
        )
        if directory:
            self.path_var.set(directory)

    def download_process(self, url, thread_count):
        """下载处理流程"""
        try:
            # 从URL中提取文件名
            filename = url.split('/')[-1].split('.')[0]
            
            # 使用选择的输出路径
            output_dir = self.path_var.get()
            temp_m3u8 = f"./temp_{filename}.m3u8"
            
            # 获取m3u8内容
            self.log(f"正在获取m3u8内容: {url}")
            content = self.get_m3u8_content(url)
            if not content:
                return
            
            # 分析和过滤广告
            self.log("正在分析m3u8内容...")
            filtered_content = self.analyze_m3u8(content)
            if not filtered_content:
                return
            
            # 保存处理后的文件
            self.log("正在保存处理后的m3u8文件...")
            if not self.save_m3u8(filtered_content, temp_m3u8):
                return
            
            # 下载视频
            self.log("开始下载视频...")
            self.download_video(temp_m3u8, output_dir, thread_count)
            
        except Exception as e:
            self.log(f"错误: {str(e)}")
        finally:
            # 清理临时文件
            try:
                os.remove(temp_m3u8)
            except:
                pass
                
            # 恢复UI状态
            self.root.after(0, self.finish_download)

    def finish_download(self):
        """完成下载,恢复UI状态"""
        self.enable_ui()
        self.log("处理完成!")

    def get_m3u8_content(self, url):
        """获取m3u8文件内容"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
        }
        try:
            # 设置代理
            proxies = None
            if self.use_proxy_var.get():
                proxy_url = self.proxy_entry.get().strip()
                if proxy_url:
                    proxies = {
                        'http': proxy_url,
                        'https': proxy_url
                    }
                    self.log(f"使用代理加载M3U8: {proxy_url}")

            response = requests.get(url, headers=headers, proxies=proxies, timeout=10)
            if response.status_code == 200:
                return response.text
            else:
                self.log(f"获取m3u8内容失败: HTTP {response.status_code}")
        except Exception as e:
            self.log(f"获取m3u8内容失败: {e}")
        return None

    def analyze_m3u8(self, content):
        """分析m3u8内容,返回过滤广告后的内容"""
        if not content:
            return None
            
        # 获取m3u8的基础URL
        m3u8_url = self.url_entry.get().strip()
        base_url = '/'.join(m3u8_url.split('/')[:-1]) + '/'
        self.log(f"基础URL: {base_url}")

        # 分析M3U8内容
        lines = content.split('\n')
        
        # 创建域名统计字典
        domain_stats = {}
        
        # 创建文件类型统计
        file_stats = {
            'normal': {'count': 0, 'duration': 0, 'files': []},
            'ad': {'count': 0, 'duration': 0, 'files': []}
        }
        
        # 用于临时存储当前处理的时长
        current_duration = 0
        
        # 统计不同域名的URL数量
        for i, line in enumerate(lines):
            if line.startswith('http'):
                domain = line.split('/')[2]  # 提取域名
                if domain not in domain_stats:
                    domain_stats[domain] = {'count': 0, 'urls': set()}
                domain_stats[domain]['count'] += 1
                domain_stats[domain]['urls'].add(line)
            
            # 处理EXTINF行
            if line.startswith('#EXTINF:'):
                try:
                    duration = float(line.split(':')[1].split(',')[0])
                    current_duration = duration
                    
                    # 检查下一行是否是文件路径
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line:  # 确保下一行不是空行
                            # 判断是否是广告文件
                            is_ad = 'adjump' in next_line.lower() or '/ad/' in next_line.lower()
                            stats_key = 'ad' if is_ad else 'normal'
                            
                            file_stats[stats_key]['count'] += 1
                            file_stats[stats_key]['duration'] += duration
                            file_stats[stats_key]['files'].append({
                                'path': next_line,
                                'duration': duration
                            })
                except:
                    pass

        http_files = [line for line in lines if line.startswith('http')]
        non_http_files = [line for line in lines if not line.startswith('http') and (line.endswith('.ts') or line.endswith('.key'))]

        # 显示处理结果统计
        self.log("\n文件类型分析:")
        self.log("-" * 50)
        
        # 显示普通视频片段统计
        self.log("\n1. 普通视频片段:")
        self.log(f"   - 文件数量: {file_stats['normal']['count']}个")
        self.log(f"   - 总时长: {file_stats['normal']['duration']:.2f}秒")
        if file_stats['normal']['files']:
            self.log("   - 示例文件:")
            for i, file in enumerate(file_stats['normal']['files'][:3]):  # 只显示前3个示例
                self.log(f"     {i+1}. {file['path']} (时长: {file['duration']}秒)")
            if len(file_stats['normal']['files']) > 3:
                self.log(f"     ... 等共{len(file_stats['normal']['files'])}个文件")
        
        # 显示广告片段统计
        self.log("\n2. 疑似广告片段:")
        self.log(f"   - 文件数量: {file_stats['ad']['count']}个")
        self.log(f"   - 总时长: {file_stats['ad']['duration']:.2f}秒")
        if file_stats['ad']['files']:
            self.log("   - 示例文件:")
            for i, file in enumerate(file_stats['ad']['files'][:3]):  # 只显示前3个示例
                self.log(f"     {i+1}. {file['path']} (时长: {file['duration']}秒)")
            if len(file_stats['ad']['files']) > 3:
                self.log(f"     ... 等共{len(file_stats['ad']['files'])}个文件")
        
        # 显示域名统计
        self.log("\n3. 域名分布:")
        for domain, stats in domain_stats.items():
            self.log(f"   域名: {domain}")
            self.log(f"   - URL数量: {stats['count']}个")
            self.log(f"   - 文件类型: {', '.join(set([url.split('.')[-1] for url in stats['urls']]))}")
        
        self.log("\n4. 总体统计:")
        self.log(f"   - 完整URL数量: {len(http_files)}")
        self.log(f"   - 非完整URL数量: {len(non_http_files)}")
        total_duration = file_stats['normal']['duration'] + file_stats['ad']['duration']
        self.log(f"   - 总时长: {total_duration:.2f}秒")
        if file_stats['ad']['count'] > 0:
            ad_percentage = (file_stats['ad']['duration'] / total_duration) * 100
            self.log(f"   - 广告占比: {ad_percentage:.2f}%")
        
        self.log("\n提示:")
        self.log("1. 建议使用以下关键词进行广告过滤:")
        ad_keywords = set()
        for file in file_stats['ad']['files']:
            # 从文件路径中提取可能的广告关键词
            path_parts = file['path'].lower().split('/')
            for part in path_parts:
                if 'ad' in part or 'jump' in part:
                    ad_keywords.add(part)
        if ad_keywords:
            self.log(f"   {', '.join(ad_keywords)}")
        
        self.log("\n2. 文件特征:")
        if file_stats['normal']['files']:
            normal_name = file_stats['normal']['files'][0]['path'].split('/')[-1]
            self.log(f"   - 普通片段命名模式: {normal_name}")
        if file_stats['ad']['files']:
            ad_name = file_stats['ad']['files'][0]['path'].split('/')[-1]
            self.log(f"   - 广告片段命名模式: {ad_name}")
        
        self.log("-" * 50)

        # 处理内容（保持原有的处理逻辑）
        new_content = []
        skip_next = False
        ad_count = 0
        has_key = False

        # 获取广告关键词（仅在启用广告过滤时）
        ad_keywords = []
        if self.enable_ad_filter.get():
            ad_keywords = [kw.strip() for kw in self.ad_keywords_entry.get().split(',') if kw.strip()]
            self.log(f"使用广告关键词: {', '.join(ad_keywords)}")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if skip_next:
                skip_next = False
                continue

            # 处理加密相关的行
            if line.startswith('#EXT-X-KEY'):
                has_key = True
                # 检查URI是否是相对路径
                if 'URI="' in line and not line.lower().startswith('http'):
                    key_path = line[line.find('URI="')+5:line.find('"', line.find('URI="')+5)]
                    if key_path.startswith('/'):
                        # 绝对路径
                        domain = '/'.join(m3u8_url.split('/')[:3])
                        full_key_path = domain + key_path
                    else:
                        # 相对路径
                        full_key_path = base_url + key_path
                    # 替换key路径
                    line = line.replace(f'URI="{key_path}"', f'URI="{full_key_path}"')
                    self.log(f"处理加密key路径: {full_key_path}")

            # 处理EXTINF行
            elif line.startswith('#EXTINF'):
                next_line_index = lines.index(line) + 1
                if next_line_index < len(lines):
                    next_line = lines[next_line_index]
                    # 检查是否包含广告关键词（仅在启用广告过滤时）
                    if self.enable_ad_filter.get() and any(kw.lower() in next_line.lower() for kw in ad_keywords):
                        skip_next = True
                        ad_count += 1
                        continue

            # 处理TS文件路径
            elif line.endswith('.ts') or line.endswith('.jpeg'):
                # 检查是否包含广告关键词（仅在启用广告过滤时）
                if self.enable_ad_filter.get() and any(kw.lower() in line.lower() for kw in ad_keywords):
                    ad_count += 1
                    continue

                if not line.startswith('http') and self.should_concat.get():
                    if line.startswith('/'):
                        # 绝对路径
                        domain = '/'.join(m3u8_url.split('/')[:3])
                        line = domain + line
                    else:
                        # 相对路径
                        line = base_url + line

            new_content.append(line)

        # 合并内容并去除空行
        final_content = '\n'.join(new_content)
        final_content = re.sub(r'\n+', '\n', final_content)

        return final_content

    def save_m3u8(self, content, output_file):
        """保存m3u8文件"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            self.log(f"保存文件失败: {e}")
            return False

    def download_video(self, m3u8_file, output_dir, thread_count):
        """使用N_m3u8DL-RE下载视频"""
        try:
            # 确保输出目录存在
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # 从临时文件名中提取视频文件名
            filename = Path(m3u8_file).stem.replace('temp_', '')
            
            cmd = [
                "N_m3u8DL-RE",
                m3u8_file,
                "--save-dir", output_dir,
                "--thread-count", str(thread_count),
                "--auto-select",
                "--binary-merge",
                "--no-date-info",
                "--save-name", filename,
                "-M", "format=mp4:muxer=ffmpeg",
                "--download-retry-count", "10",  # 设置重试次数为10次
                "--check-segments-count",  # 检查分片数量
                "--concurrent-download",  # 启用并发下载
            ]
            
            self.log(f"执行命令: {' '.join(cmd)}")
            
            # 执行下载,实时获取输出
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            # 记录上一行内容,用于去重
            last_line = ""
            
            # 读取输出
            for line in process.stdout:
                line = line.strip()
                # 跳过空行
                if not line:
                    continue
                # 跳过重复行    
                if line == last_line:
                    continue
                # 更新上一行内容    
                last_line = line
                # 输出日志
                self.log(line)
                
            process.wait()
            
            if process.returncode == 0:
                self.log(f"下载完成! 保存在: {output_dir}")
                return True
            else:
                # 如果下载失败，尝试重新下载
                self.log("下载失败，尝试重新下载...")
                # 增加线程数和重试次数
                cmd = [
                    "N_m3u8DL-RE",
                    m3u8_file,
                    "--save-dir", output_dir,
                    "--thread-count", "32",  # 增加线程数
                    "--auto-select",
                    "--binary-merge",
                    "--no-date-info",
                    "--save-name", filename,
                    "-M", "format=mp4:muxer=ffmpeg",
                    "--download-retry-count", "20",  # 增加重试次数
                    "--check-segments-count",
                    "--concurrent-download",
                    "--tmp-dir", "./temp",  # 指定临时目录
                    "--write-meta-json",  # 写入元数据
                ]
                
                self.log(f"重试命令: {' '.join(cmd)}")
                
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
                
                for line in process.stdout:
                    line = line.strip()
                    if line and line != last_line:
                        last_line = line
                        self.log(line)
                        
                process.wait()
                
                if process.returncode == 0:
                    self.log(f"重试下载成功! 保存在: {output_dir}")
                    return True
                else:
                    self.log("重试下载也失败了!")
                    return False
                
        except Exception as e:
            self.log(f"下载失败: {e}")
            return False

    def batch_download(self):
        """批量下载"""
        from tkinter import filedialog
        
        # 打开文件选择对话框
        files = filedialog.askopenfilenames(
            title="选择包含M3U8链接的文本文件",
            filetypes=[("Text files", "*.txt")]
        )
        
        if not files:
            return
        
        # 禁用所有按钮
        self.disable_ui()
        
        # 获取线程数
        try:
            thread_count = int(self.thread_entry.get())
            if thread_count < 1:
                raise ValueError
        except ValueError:
            self.log("错误: 线程数必须是正整数!")
            return
        
        # 在新线程中执行批量下载
        thread = threading.Thread(target=self.batch_process, args=(files, thread_count))
        thread.daemon = True
        thread.start()

    def batch_process(self, files, thread_count):
        """批量处理文件"""
        try:
            for file in files:
                self.log(f"\n开始处理文件: {file}")
                
                # 读取文件内容
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 提取m3u8链接
                # 匹配http(s)开头,m3u8结尾的URL
                urls = re.findall(r'https?://[^\s<>"]+?\.m3u8', content)
                
                if not urls:
                    self.log(f"在文件 {file} 中未找到m3u8链接")
                    continue
                    
                self.log(f"找到 {len(urls)} 个m3u8链接")
                
                # 逐个下载
                for url in urls:
                    self.log(f"\n开始下载: {url}")
                    self.download_process(url, thread_count)
                    
        except Exception as e:
            self.log(f"批量处理错误: {str(e)}")
        finally:
            # 恢复UI状态
            self.root.after(0, self.finish_batch)

    def finish_batch(self):
        """完成批量下载,恢复UI状态"""
        self.enable_ui()
        self.log("\n批量下载完成!")

    def load_m3u8_content(self):
        """加载并显示M3U8内容"""
        url = self.url_entry.get().strip()
        if not url:
            self.log("错误: 链接不能为空!")
            return
            
        self.log(f"正在加载M3U8内容: {url}")
        
        # 禁用加载按钮
        self.load_btn.configure(state="disabled")
        
        # 在新线程中执行加载
        thread = threading.Thread(target=self._load_m3u8_content_thread)
        thread.daemon = True
        thread.start()
    
    def _load_m3u8_content_thread(self):
        """在线程中加载M3U8内容"""
        try:
            url = self.url_entry.get().strip()
            content = self.get_m3u8_content(url)
            
            if content:
                # 清空日志区域
                self.root.after(0, lambda: self.log_area.delete(1.0, tk.END))
                
                # 显示原始内容
                self.root.after(0, lambda: self.log("原始M3U8内容:"))
                self.root.after(0, lambda: self.log("-" * 50))
                self.root.after(0, lambda: self.log(content))
                self.root.after(0, lambda: self.log("-" * 50))
                
                # 分析内容
                self.analyze_m3u8(content)
                
                # 显示提示
                self.root.after(0, lambda: self.log("\n提示: 请根据以上内容设置广告关键词，多个关键词用逗号分隔。"))
                self.root.after(0, lambda: self.log("例如: ad,adjump,banner"))
                
        except Exception as e:
            self.root.after(0, lambda: self.log(f"加载失败: {str(e)}"))
        finally:
            # 恢复加载按钮状态
            self.root.after(0, lambda: self.load_btn.configure(state="normal"))

    def clear_log(self):
        """清空日志区域"""
        self.log_area.delete(1.0, tk.END)
        self.show_usage_guide()

def main():
    root = ctk.CTk()
    root.title("M3U8下载器")
    app = M3u8DownloaderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 