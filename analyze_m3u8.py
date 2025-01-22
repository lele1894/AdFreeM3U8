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
        
        # URL输入框
        url_label = ctk.CTkLabel(top_frame, text="M3U8链接:")
        url_label.grid(row=0, column=0, sticky="w")
        
        self.url_entry = ctk.CTkEntry(top_frame, width=600)
        self.url_entry.grid(row=0, column=1, sticky="ew", padx=5)
        # 绑定回车键
        self.url_entry.bind('<Return>', lambda e: self.start_download())
        
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
        second_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(0,5))
        
        # 保存路径选择
        path_label = ctk.CTkLabel(second_frame, text="保存目录:")
        path_label.grid(row=0, column=0, sticky="w")
        
        self.path_var = tk.StringVar(value="./downloads")  # 默认下载目录
        self.path_entry = ctk.CTkEntry(second_frame, textvariable=self.path_var, width=500)
        self.path_entry.grid(row=0, column=1, sticky="ew", padx=5)
        
        self.path_btn = ctk.CTkButton(
            second_frame,
            text="选择目录",
            command=self.choose_directory,
            width=80
        )
        self.path_btn.grid(row=0, column=2, padx=5)
        
        # 日志显示区域移到第三行
        self.log_area = scrolledtext.ScrolledText(
            main_frame,
            font=("Consolas", 10),
            bg="#2b2b2b",
            fg="#ffffff"
        )
        self.log_area.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        
        # 配置grid权重
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)
        
        main_frame.grid_rowconfigure(2, weight=1)  # 日志区域可扩展
        main_frame.grid_columnconfigure(0, weight=1)
        second_frame.grid_columnconfigure(1, weight=1)  # 路径输入框可扩展

    def log(self, message):
        """添加日志信息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.insert("end", f"[{timestamp}] {message}\n")
        self.log_area.see("end")  # 滚动到最新内容
        
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

    def enable_ui(self):
        """启用UI控件"""
        self.download_btn.configure(state="normal")
        self.batch_btn.configure(state="normal")
        self.url_entry.configure(state="normal")
        self.thread_entry.configure(state="normal")

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
            response = requests.get(url, headers=headers, timeout=10)
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
            
        # 匹配带路径的URL
        dir_url_list = re.findall('(.*/)', content)
        dir_ts_list = re.findall('(.*\.(ts|jpeg|jpg|png|mp4))', content)

        if dir_url_list:
            # 去重
            dir_url = list(set(dir_url_list))
            
            # 统计每个路径出现的次数
            dicts = {}
            for url in dir_url:
                dicts[url] = content.count(url)
                self.log(f"发现路径: {url} (出现{dicts[url]}次)")

            # 按出现次数排序
            dicts = sorted(dicts.items(), key=lambda x: x[1])

            new_content = content
            # 过滤广告
            if len(dicts) > 1:
                self.log("检测到多个路径,开始过滤广告...")
                for ii in dicts[:-1]:
                    self.log(f"移除广告路径: {ii[0]}")
                    new_content = re.sub(f"{ii[0]}.*", '', new_content)
            elif len(dicts) == 1:
                try:
                    if dicts[0][1] < len(dir_ts_list) / 2:
                        self.log(f"移除可疑广告路径: {dicts[0][0]}")
                        new_content = re.sub(f"{dicts[0][0]}.*", '', new_content)
                except Exception as e:
                    self.log(f"分析异常: {e}")
                    
            # 去除空行
            new_content = re.sub(r'\n+', '\n', new_content)
            
            return new_content
        
        return content

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
                "-M", "format=mp4:muxer=ffmpeg"  # 指定输出格式为mp4
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
                self.log("下载失败!")
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

def main():
    root = ctk.CTk()
    root.title("M3U8下载器")
    app = M3u8DownloaderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 