#@title 视频识别配音-1.1
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 安装必要的依赖
import subprocess
import sys
import re

def check_package_installed(package_name):
    """检查包是否已安装"""
    try:
        __import__(package_name.replace('-', '_').split('>=')[0].split('==')[0])
        return True
    except ImportError:
        return False

def check_cuda_dependencies():
    """检查并安装CUDA相关依赖"""
    print("检查CUDA相关依赖...")
    try:
        # 检查是否在Linux环境下
        if os.name != 'posix':
            print("非Linux环境，跳过CUDA依赖检查")
            return
            
        # 检查是否已安装libcudnn8
        result = subprocess.run(['dpkg', '-l', 'libcudnn8'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print("正在安装CUDA依赖...")
            # 更新包列表
            subprocess.run(['apt-get', 'update'], check=True)
            # 安装libcudnn8和libcudnn8-dev
            subprocess.run(['apt-get', 'install', '-y', 'libcudnn8', 'libcudnn8-dev'], check=True)
            print("✓ CUDA依赖安装成功")
        else:
            print("✓ CUDA依赖已安装")
            
    except Exception as e:
        print(f"警告: CUDA依赖安装失败: {str(e)}")
        print("这可能会影响GPU加速功能，但程序仍可继续运行")

def install_dependencies():
    """安装运行环境所需的所有依赖"""
    print("检查并安装必要的依赖...")
    
    # 首先检查CUDA相关依赖
    check_cuda_dependencies()
    
    dependencies = {
        #"whisperx": "git+https://github.com/m-bain/whisperx.git",
        "whisperx": "whisperx",
        "torch": "torch",
        "torchaudio": "torchaudio",
        "ffmpeg": "ffmpeg-python",
        "deep_translator": "deep-translator",
        "edge_tts": "edge-tts",
        "pydub": "pydub",
        "nest_asyncio": "nest_asyncio",
        "langdetect": "langdetect"
    }

    for package_name, install_name in dependencies.items():
        if not check_package_installed(package_name):
            print(f"安装 {install_name}...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", install_name], check=True)
                print(f"✓ {install_name} 安装成功")
            except subprocess.CalledProcessError as e:
                print(f"✗ {install_name} 安装失败: {str(e)}")
        else:
            print(f"✓ {install_name} 已安装")

# 首先安装依赖
install_dependencies()

# 然后导入所需的模块
import whisperx
import gc
import os
from tqdm import tqdm
from pathlib import Path
import datetime
from deep_translator import GoogleTranslator
import time
import asyncio
import edge_tts
from pydub import AudioSegment
from concurrent.futures import ThreadPoolExecutor
import nest_asyncio
import shutil
import torch


# 应用nest_asyncio
nest_asyncio.apply()

def check_dependencies():
    """检查必要的依赖是否都已安装"""
    missing_deps = []
    dependencies = {
        "whisperx": "whisperx",
        "ffmpeg": "ffmpeg-python",
        "deep_translator": "deep-translator",
        "edge_tts": "edge-tts",
        "langdetect": "langdetect"
    }

    for package_name in dependencies:
        if not check_package_installed(package_name):
            missing_deps.append(dependencies[package_name])

    if missing_deps:
        print("以下依赖缺失，正在安装：")
        for dep in missing_deps:
            print(f"安装 {dep}...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", dep], check=True)
                print(f"✓ {dep} 安装成功")
            except subprocess.CalledProcessError as e:
                print(f"✗ {dep} 安装失败: {str(e)}")
                raise RuntimeError(f"依赖安装失败: {dep}")

def translate_text(text, target_lang='zh-CN', max_retries=10, retry_delay=2):
    """翻译单条文本，添加更多重试次数"""
    for attempt in range(max_retries):
        try:
            translator = GoogleTranslator(source='auto', target=target_lang)
            translated = translator.translate(text)

            # 验证翻译结果不为空且不等于原文
            if translated and translated.strip() and translated != text:
                return translated
            else:
                raise Exception("翻译结果无效")

        except Exception as e:
            if attempt < max_retries - 1:
                print(f"翻译出错 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                print(f"等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
                # 增加重试延迟时间，避免频繁请求
                retry_delay = min(retry_delay * 1.5, 10)
                continue
            print(f"翻译失败: {str(e)}")
            return text

def translate_batch(texts, target_lang='zh-CN', batch_size=5, max_retries=10, retry_delay=2):
    """批量翻译文本，减小批量大小并增加重试次数"""
    results = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        current_retry_delay = retry_delay

        for attempt in range(max_retries):
            try:
                translator = GoogleTranslator(source='auto', target=target_lang)
                translated = []

                # 逐个翻译批次中的文本
                for text in batch:
                    trans = translator.translate(text)
                    # 验证翻译结果
                    if not trans or not trans.strip() or trans == text:
                        raise Exception(f"无效的翻译结果: {text} -> {trans}")
                    translated.append(trans)
                    # 添加短暂延迟避免请求过快
                    time.sleep(0.5)

                results.extend(translated)
                break

            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"批量翻译出错 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                    print(f"等待 {current_retry_delay} 秒后重试...")
                    time.sleep(current_retry_delay)
                    # 增加重试延迟时间
                    current_retry_delay = min(current_retry_delay * 1.5, 10)
                    continue

                print(f"批量翻译失败，切换到单条翻译模式: {str(e)}")
                # 如果批量翻译失败，切换到单条翻译
                for text in batch:
                    translated = translate_text(text, target_lang, max_retries, retry_delay)
                    results.append(translated)
                break

    return results

def print_step(step, total_steps, message):
    """打印带有进度的美化消息"""
    print(f"\n[{step}/{total_steps}] 🚀 {message}")
    print("=" * 50)
    return time.time()  # 返回开始时间

def print_time_cost(start_time, task_name):
    """打印任务耗时"""
    cost = time.time() - start_time
    if cost < 60:
        print(f"⏱️ {task_name}耗时: {cost:.1f}秒")
    else:
        minutes = int(cost // 60)
        seconds = cost % 60
        print(f"⏱️ {task_name}耗时: {minutes}分{seconds:.1f}秒")

async def generate_speech(text, output_file, voice="zh-TW-HsiaoChenNeural", rate="+50%", max_retries=3, retry_delay=2):
    """使用Edge TTS生成语音，添加重试机制"""
    for attempt in range(max_retries):
        try:
            communicate = edge_tts.Communicate(text, voice, rate=rate)
            await communicate.save(output_file)

            # 验证生成的音频文件
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                return
            else:
                raise Exception("生成的音频文件无效")

        except Exception as e:
            if attempt < max_retries - 1:
                print(f"语音生成出错 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                print(f"等待 {retry_delay} 秒后重试...")
                await asyncio.sleep(retry_delay)
                continue
            raise Exception(f"语音生成失败: {str(e)}")

def generate_chinese_srt(segments, output_path, target_lang='zh-CN'):
    """生成中文字幕文件，添加翻译验证"""
    print("正在生成中文字幕...")
    translated_segments = []

    # 提取所有文本进行批量翻译
    texts = [segment["text"].strip() for segment in segments]

    # 使用更小的批量大小
    batch_size = 5
    print(f"将分{len(texts)//batch_size + 1}批进行翻译，每批{batch_size}条...")

    translated_texts = translate_batch(texts, target_lang, batch_size=batch_size)

    # 验证翻译结果
    for i, (original, translated) in enumerate(zip(texts, translated_texts)):
        if not translated or translated == original:
            print(f"警告: 第{i+1}条翻译可能有问题，重新翻译...")
            translated_texts[i] = translate_text(original, target_lang)

    with open(output_path, "w", encoding="utf-8") as f:
        for i, (segment, translated_text) in enumerate(zip(segments, translated_texts), start=1):
            start_time = str(datetime.timedelta(seconds=segment["start"]))[:11].replace(".", ",")
            end_time = str(datetime.timedelta(seconds=segment["end"]))[:11].replace(".", ",")

            f.write(f"{i}\n{start_time} --> {end_time}\n{translated_text}\n\n")

            # 保存翻译后的片段信息
            translated_segments.append({
                "start": segment["start"],
                "end": segment["end"],
                "text": translated_text
            })

    return translated_segments

def extract_audio(video_path):
    """从视频文件中提取音频"""
    audio_path = video_path.rsplit(".", 1)[0] + ".wav"
    print(f"正在从视频提取音频: {video_path}")
    subprocess.run([
        "ffmpeg", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1",
        audio_path, "-y"
    ], check=True)
    return audio_path

async def generate_dubbed_audio(translated_segments, output_dir, voice="zh-TW-HsiaoChenNeural", rate="+50%"):
    """生成中文配音"""
    print("正在生成中文配音...")

    # 创建临时目录
    temp_dir = os.path.join(output_dir, "temp_audio")
    os.makedirs(temp_dir, exist_ok=True)

    # 生成每个片段的音频
    successful_segments = []
    total_duration = 0
    max_retries = 3
    retry_delay = 2

    async def process_segment(index, segment):
        try:
            # 生成音频文件名
            audio_file = os.path.join(temp_dir, f"segment_{index:04d}.mp3")

            # 检查文本是否为空
            if not segment["text"].strip():
                print(f"警告: 片段 {index} 文本为空，跳过")
                return None

            # 生成音频（带重试机制）
            await generate_speech(segment["text"], audio_file, voice, rate, max_retries, retry_delay)

            # 验证生成的音频文件
            if os.path.exists(audio_file) and os.path.getsize(audio_file) > 0:
                return {
                    "file": audio_file,
                    "start": segment["start"],
                    "end": segment["end"],
                    "duration": segment["end"] - segment["start"]
                }
            else:
                print(f"警告: 片段 {index} 音频生成失败")
                return None

        except Exception as e:
            print(f"警告: 生成片段 {index} 时出错: {str(e)}")
            return None

    try:
        # 并行生成所有音频片段
        tasks = [process_segment(i, segment) for i, segment in enumerate(translated_segments)]
        results = await asyncio.gather(*tasks)

        # 过滤掉失败的片段
        successful_segments = [seg for seg in results if seg is not None]

        if not successful_segments:
            raise RuntimeError("没有成功生成的音频片段")

        # 计算总时长
        total_duration = sum(seg["duration"] for seg in successful_segments)

        print(f"成功生成 {len(successful_segments)}/{len(translated_segments)} 个音频片段")
        print(f"音频生成完成，总时长: {total_duration:.2f}秒")

        # 合并音频片段
        output_audio = os.path.join(output_dir, "dubbed_audio.mp3")

        # 创建空白音频
        silence = AudioSegment.silent(duration=int(total_duration * 1000))

        # 将每个片段插入到正确的位置
        for segment in successful_segments:
            try:
                audio_segment = AudioSegment.from_mp3(segment["file"])
                position = int(segment["start"] * 1000)
                silence = silence.overlay(audio_segment, position=position)
            except Exception as e:
                print(f"警告: 合并音频片段时出错: {str(e)}")
                continue

        # 导出最终音频
        silence.export(output_audio, format="mp3")

        # 验证最终音频
        if not os.path.exists(output_audio) or os.path.getsize(output_audio) == 0:
            raise RuntimeError("最终音频文件生成失败")

        # 清理临时文件
        shutil.rmtree(temp_dir, ignore_errors=True)

        return output_audio

    except Exception as e:
        print(f"错误: {str(e)}")
        # 清理临时文件
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None

def mix_audio_and_merge_video(video_path, dubbed_audio_path, output_dir):
    """混合音频并与视频合并"""
    print("正在混合音频并合成最终视频...")

    # 验证配音文件
    if not dubbed_audio_path or not os.path.exists(dubbed_audio_path) or os.path.getsize(dubbed_audio_path) == 0:
        raise RuntimeError("配音文件不存在或为空")

    try:
        # 1. 获取视频时长
        video_duration_cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{video_path}"'
        video_duration = float(subprocess.check_output(video_duration_cmd, shell=True).decode().strip())
        print(f"视频时长: {video_duration:.2f}秒")

        # 2. 提取原始音频（使用视频时长）
        original_audio_path = os.path.join(output_dir, "original_audio.wav")
        subprocess.run([
            "ffmpeg", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "44100", "-ac", "2",
            "-t", str(video_duration),  # 使用视频时长
            original_audio_path, "-y"
        ], check=True)

        # 3. 将配音转换为WAV格式
        dubbed_wav_path = os.path.join(output_dir, "dubbed_audio.wav")
        subprocess.run([
            "ffmpeg", "-i", dubbed_audio_path,
            "-acodec", "pcm_s16le",
            "-ar", "44100", "-ac", "2",
            dubbed_wav_path, "-y"
        ], check=True)

        # 验证音频文件
        if not os.path.exists(original_audio_path) or not os.path.exists(dubbed_wav_path):
            raise RuntimeError("音频提取失败")

        # 4. 读取音频
        print("处理音频...")
        original_audio = AudioSegment.from_wav(original_audio_path)
        dubbed_audio = AudioSegment.from_wav(dubbed_wav_path)

        print(f"原始音频时长: {len(original_audio)/1000:.2f}秒")
        print(f"配音时长: {len(dubbed_audio)/1000:.2f}秒")

        # 创建与视频等长的空白音轨
        target_duration = int(video_duration * 1000)  # 转换为毫秒
        base_track = AudioSegment.silent(duration=target_duration)

        # 降低原始音频音量并确保长度匹配
        original_audio = original_audio - 20  # -20dB ≈ 10% 音量
        if len(original_audio) > target_duration:
            original_audio = original_audio[:target_duration]
        elif len(original_audio) < target_duration:
            original_audio = original_audio + AudioSegment.silent(duration=target_duration - len(original_audio))

        # 将原始音频叠加到基础音轨
        base_track = base_track.overlay(original_audio)

        # 将配音叠加到适当位置
        if len(dubbed_audio) > 0:
            base_track = base_track.overlay(dubbed_audio)

        # 5. 保存最终音频
        mixed_audio_path = os.path.join(output_dir, "mixed_audio.wav")
        base_track.export(
            mixed_audio_path,
            format="wav",
            parameters=["-ar", "44100", "-ac", "2"]
        )

        # 验证混合音频
        if not os.path.exists(mixed_audio_path) or os.path.getsize(mixed_audio_path) == 0:
            raise RuntimeError("混合音频生成失败")

        print("音频混合完成，开始合成视频...")

        # 6. 合并视频和混合音频
        output_video_path = os.path.join(output_dir, os.path.splitext(os.path.basename(video_path))[0] + "_dubbed.mp4")

        # 使用一步处理来合成视频
        subprocess.run([
            "ffmpeg", "-i", video_path,
            "-i", mixed_audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-strict", "experimental",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",  # 使用最短的流长度，避免音频比视频长
            output_video_path, "-y"
        ], check=True)

        # 验证输出视频
        if not os.path.exists(output_video_path) or os.path.getsize(output_video_path) == 0:
            raise RuntimeError("视频合成失败")

        print(f"视频合成完成，输出文件: {output_video_path}")
        return output_video_path

    finally:
        # 清理临时文件
        temp_files = [
            original_audio_path,
            dubbed_wav_path,
            mixed_audio_path
        ]
        for file in temp_files:
            try:
                if os.path.exists(file):
                    os.remove(file)
            except Exception as e:
                print(f"警告: 清理临时文件 {file} 时出错: {str(e)}")

def get_event_loop():
    """获取事件循环"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果当前循环正在运行，创建新的循环
            loop = asyncio.new_event_loop()
        return loop
    except RuntimeError:
        loop = asyncio.new_event_loop()
        return loop

def run_async(coro):
    """运行异步代码的辅助函数"""
    try:
        # 获取当前事件循环
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果当前循环正在运行，创建并使用新的循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    except RuntimeError:
        # 如果出现运行时错误，创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        # 确保循环被关闭
        try:
            loop.close()
        except:
            pass

def generate_original_srt(segments, output_path):
    """生成原始语言字幕文件"""
    print("正在生成原始语言字幕...")
    with open(output_path, "w", encoding="utf-8") as f:
        for i, segment in enumerate(segments, start=1):
            start_time = str(datetime.timedelta(seconds=segment["start"]))[:11].replace(".", ",")
            end_time = str(datetime.timedelta(seconds=segment["end"]))[:11].replace(".", ",")
            text = segment["text"].strip()
            f.write(f"{i}\n{start_time} --> {end_time}\n{text}\n\n")

def detect_language(text):
    """检测文本语言"""
    try:
        # 使用langdetect库检测语言
        from langdetect import detect
        return detect(text)
    except:
        try:
            # 备用方案：使用GoogleTranslator检测语言
            translator = GoogleTranslator(source='auto', target='zh-CN')
            # 通过尝试翻译来获取源语言
            translator.translate(text[:100])  # 只使用前100个字符
            return translator._source
        except:
            return 'unknown'

def process_video(video_path, model_name="large-v2", device="cuda", batch_size=16, compute_type="float4", target_lang='zh-CN', voice="zh-TW-HsiaoChenNeural", rate="+50%"):
    """处理视频并生成字幕和配音"""
    total_time_start = time.time()
    total_steps = 9
    current_step = 1

    step_time = print_step(current_step, total_steps, "初始化转录任务")

    # 1. 提取音频
    current_step += 1
    step_time = print_step(current_step, total_steps, "从视频提取音频")
    audio_path = extract_audio(video_path)
    print_time_cost(step_time, "音频提取")

    # 2. 加载模型
    current_step += 1
    step_time = print_step(current_step, total_steps, "加载 Whisper 模型")
    model_dir = os.path.join(os.getcwd(), "model")
    model = whisperx.load_model(
        model_name,
        device,
        compute_type=compute_type,
        download_root=model_dir
    )
    print_time_cost(step_time, "模型加载")

    # 3. 加载音频并转录
    current_step += 1
    step_time = print_step(current_step, total_steps, "转录音频")
    audio = whisperx.load_audio(audio_path)
    result = model.transcribe(audio, batch_size=batch_size)
    detected_language = result["language"]
    print(f"检测到语言: {detected_language}")
    print_time_cost(step_time, "音频转录")

    # 4. 释放模型内存
    current_step += 1
    step_time = print_step(current_step, total_steps, "清理模型内存")
    del model
    gc.collect()
    torch.cuda.empty_cache()
    print_time_cost(step_time, "内存清理")

    # 5. 对齐转录结果
    current_step += 1
    step_time = print_step(current_step, total_steps, "对齐转录结果")
    model_a, metadata = whisperx.load_align_model(
        language_code=detected_language,
        device=device
    )
    result = whisperx.align(
        result["segments"],
        model_a,
        metadata,
        audio,
        device,
        return_char_alignments=False
    )
    print_time_cost(step_time, "结果对齐")

    # 6. 生成原始语言字幕
    current_step += 1
    step_time = print_step(current_step, total_steps, "生成原始语言字幕")
    output_dir = os.path.dirname(video_path)
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    original_srt = os.path.join(output_dir, f"{base_name}_original.srt")
    chinese_srt = os.path.join(output_dir, f"{base_name}_zh.srt")

    # 生成原始语言字幕
    generate_original_srt(result["segments"], original_srt)
    print_time_cost(step_time, "原始字幕生成")

    # 检查是否需要翻译
    if detected_language == "zh":
        print("检测到中文音频，无需翻译")
        chinese_srt = original_srt
        translated_segments = result["segments"]
    else:
        # 7. 生成中文字幕
        current_step += 1
        step_time = print_step(current_step, total_steps, "生成中文字幕")
        print(f"检测到非中文音频 ({detected_language})，正在翻译为中文...")
        translated_segments = generate_chinese_srt(result["segments"], chinese_srt, target_lang)
        print_time_cost(step_time, "中文字幕生成")

    # 8. 生成配音
    current_step += 1
    step_time = print_step(current_step, total_steps, "生成中文配音")
    dubbed_audio = run_async(generate_dubbed_audio(translated_segments, output_dir, voice, rate))
    print_time_cost(step_time, "配音生成")

    # 9. 混合音频并合成视频
    current_step += 1
    step_time = print_step(current_step, total_steps, "合成最终视频")
    output_video = mix_audio_and_merge_video(video_path, dubbed_audio, output_dir)
    print_time_cost(step_time, "视频合成")

    # 10. 清理临时文件
    os.remove(audio_path)
    print("\n✨ 处理完成！")
    print_time_cost(total_time_start, "总")
    print(f"📝 原始字幕：{original_srt}")
    if detected_language != "zh":
        print(f"📝 中文字幕：{chinese_srt}")
    print(f"🔊 配音文件：{dubbed_audio}")
    print(f"🎥 输出视频：{output_video}")

    return original_srt, chinese_srt, dubbed_audio, output_video

def process_video_with_srt(video_path, srt_file, target_lang='zh-CN', voice="zh-TW-HsiaoChenNeural", rate="+50%"):
    """使用已有字幕文件处理视频"""
    total_time_start = time.time()
    total_steps = 3
    current_step = 1

    # 1. 读取字幕文件
    step_time = print_step(current_step, total_steps, "读取字幕文件")
    print(f"读取字幕文件: {srt_file}")
    segments = []
    detected_language = None

    try:
        with open(srt_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 使用第一段非空字幕检测语言
        text_for_detection = ""
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.isdigit():  # 字幕序号
                i += 1
                if i < len(lines):  # 时间轴
                    i += 1
                    text_lines = []
                    while i < len(lines) and lines[i].strip():
                        text_lines.append(lines[i].strip())
                        i += 1
                    if text_lines:
                        text_for_detection = ' '.join(text_lines)
                        break
            i += 1

        if text_for_detection:
            try:
                detected_language = detect_language(text_for_detection)
                print(f"检测到字幕语言: {detected_language}")
            except Exception as e:
                print(f"语言检测失败: {str(e)}")
                detected_language = 'unknown'
        else:
            print("无法从字幕文件中提取文本进行语言检测")
            detected_language = 'unknown'

        # 解析字幕文件
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.isdigit():  # 字幕序号
                i += 1
                if i >= len(lines):
                    break

                # 时间轴
                time_line = lines[i].strip()
                if '-->' in time_line:
                    start_time, end_time = time_line.split(' --> ')
                    # 转换时间为秒
                    start_seconds = sum(float(x) * 60 ** i for i, x in enumerate(reversed(start_time.replace(',', '.').split(':'))))
                    end_seconds = sum(float(x) * 60 ** i for i, x in enumerate(reversed(end_time.replace(',', '.').split(':'))))

                    i += 1
                    # 读取文本内容
                    text_lines = []
                    while i < len(lines) and lines[i].strip():
                        text_lines.append(lines[i].strip())
                        i += 1

                    if text_lines:  # 只添加有文本的字幕
                        segments.append({
                            "start": start_seconds,
                            "end": end_seconds,
                            "text": ' '.join(text_lines)
                        })
            i += 1

        if not segments:
            raise ValueError("未能从字幕文件中提取到有效字幕")

        print_time_cost(step_time, "字幕读取")

        # 检查是否需要翻译
        output_dir = os.path.dirname(video_path)
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        chinese_srt = os.path.join(output_dir, f"{base_name}_zh.srt")

        # 如果语言未知或非中文，执行翻译
        if detected_language not in ['zh', 'zh-CN', 'zh-TW']:
            # 翻译字幕
            current_step += 1
            step_time = print_step(current_step, total_steps, "翻译字幕")
            print(f"检测到非中文字幕 ({detected_language})，正在翻译为中文...")
            translated_segments = generate_chinese_srt(segments, chinese_srt, target_lang)
            print_time_cost(step_time, "字幕翻译")
        else:
            print("检测到中文字幕，无需翻译")
            chinese_srt = srt_file
            translated_segments = segments

        # 2. 生成配音
        current_step += 1
        step_time = print_step(current_step, total_steps, "生成中文配音")
        print("正在生成中文配音...")
        dubbed_audio = run_async(generate_dubbed_audio(translated_segments, output_dir, voice, rate))

        if not dubbed_audio or not os.path.exists(dubbed_audio) or os.path.getsize(dubbed_audio) == 0:
            raise RuntimeError("配音生成失败")

        print_time_cost(step_time, "配音生成")

        # 3. 混合音频并合成视频
        current_step += 1
        step_time = print_step(current_step, total_steps, "合成最终视频")
        output_video = mix_audio_and_merge_video(video_path, dubbed_audio, output_dir)
        print_time_cost(step_time, "视频合成")

        print("\n✨ 处理完成！")
        print_time_cost(total_time_start, "总")

        print("\n📋 处理结果：")
        print("=" * 50)
        print(f"📝 原始字幕文件：{srt_file}")
        if detected_language not in ['zh', 'zh-CN', 'zh-TW']:
            print(f"📝 中文字幕文件：{chinese_srt}")
        print(f"🎵 配音文件：{dubbed_audio}")
        print(f"🎥 配音后的视频：{output_video}")

        return srt_file, chinese_srt, dubbed_audio, output_video

    except Exception as e:
        print(f"处理字幕文件时出错: {str(e)}")
        raise

def main(video_file, srt_file=None, device="cuda", batch_size=16, compute_type="float16",
         target_lang='zh-CN', voice="zh-TW-HsiaoChenNeural", rate="+50%"):
    """主函数，处理视频和字幕"""
    print("\n🎬 开始处理视频...")
    print("=" * 50)

    # 检查依赖
    check_dependencies()

    if srt_file and os.path.exists(srt_file):
        print(f"📝 检测到字幕文件：{srt_file}")
        original_srt, chinese_srt, dubbed_audio, output_video = process_video_with_srt(
            video_file,
            srt_file,
            target_lang=target_lang,
            voice=voice,
            rate=rate
        )
    else:
        if srt_file:
            print(f"🔍 未检测到字幕文件，将从视频识别开始处理...")
        original_srt, chinese_srt, dubbed_audio, output_video = process_video(
            video_file,
            model_name="large-v2",
            device=device,
            batch_size=batch_size,
            compute_type=compute_type,
            target_lang=target_lang,
            voice=voice,
            rate=rate
        )

    return original_srt, chinese_srt, dubbed_audio, output_video

def get_user_input():
    """获取用户输入"""
    print("\n请选择功能：")
    print("1. 完整运行（识别、翻译、配音）")
    print("2. 仅生成原始字幕")
    while True:
        choice = input("请输入选项 (1/2): ").strip()
        if choice in ['1', '2']:
            break
        print("无效选项，请重新输入")

    # 获取视频文件路径（必须）
    while True:
        video_path = input("\n请输入视频文件路径（必须）: ").strip()
        if video_path and os.path.exists(video_path):
            break
        print("文件不存在，请重新输入")

    # 如果选择完整运行，获取其他参数
    srt_file = None
    voice = "zh-TW-HsiaoChenNeural"
    rate = "+50%"

    if choice == '1':
        # 获取字幕文件路径（可选）
        srt_file = input("\n请输入字幕文件路径（可选，直接回车跳过）: ").strip()
        if not srt_file:
            srt_file = None
        elif not os.path.exists(srt_file):
            print("字幕文件不存在，将从视频识别开始处理")
            srt_file = None

        # 获取语音选项
        temp_voice = input("\n请输入语音选项（直接回车使用默认值：zh-TW-HsiaoChenNeural）: ").strip()
        if temp_voice:
            voice = temp_voice

        # 获取语速
        temp_rate = input("\n请输入语速（直接回车使用默认值：+50%）: ").strip()
        if temp_rate:
            rate = temp_rate

    return choice, video_path, srt_file, voice, rate

def get_video_files(path):
    """获取指定路径下的所有视频文件"""
    video_extensions = ('.mp4', '.avi', '.mkv', '.mov', '.flv', '.wmv')
    if os.path.isfile(path):
        return [path] if path.lower().endswith(video_extensions) else []

    video_files = []
    for root, _, files in os.walk(path):
        for file in files:
            if file.lower().endswith(video_extensions):
                video_files.append(os.path.join(root, file))
    return video_files

if __name__ == "__main__":
    total_time_start = time.time()

    # 获取用户输入
    choice, video_path, srt_file, voice, rate = get_user_input()

    # 获取要处理的视频文件列表
    video_files = get_video_files(video_path)

    if not video_files:
        print(f"❌ 错误：在路径 '{video_path}' 中未找到视频文件")
        sys.exit(1)

    # 显示找到的视频文件
    if len(video_files) > 1:
        print(f"\n📝 找到 {len(video_files)} 个视频文件:")
        for i, video_file in enumerate(video_files, 1):
            print(f"{i}. {os.path.basename(video_file)}")
        print("\n")

    # 处理每个视频文件
    for i, video_file in enumerate(video_files, 1):
        if len(video_files) > 1:
            print(f"\n🎬 处理视频 {i}/{len(video_files)}: {os.path.basename(video_file)}")
            print("=" * 50)

        try:
            if choice == '1':
                # 完整运行
                main(
                    video_file=video_file,
                    srt_file=srt_file,
                    voice=voice,
                    rate=rate
                )
            else:
                # 仅生成原始字幕
                print("\n🎬 开始处理视频...")
                print("=" * 50)

                # 检查依赖
                check_dependencies()

                # 设置设备参数
                device = "cuda" if torch.cuda.is_available() else "cpu"
                batch_size = 16 if torch.cuda.is_available() else 4
                compute_type = "float16" if torch.cuda.is_available() else "int8"

                try:
                    # 提取音频
                    step_time = print_step(1, 4, "从视频提取音频")
                    audio_path = extract_audio(video_file)
                    print_time_cost(step_time, "音频提取")

                    # 加载模型
                    step_time = print_step(2, 4, "加载 Whisper 模型")
                    model_dir = os.path.join(os.getcwd(), "model")
                    model = whisperx.load_model(
                        "large-v2",
                        device,
                        compute_type=compute_type,
                        download_root=model_dir
                    )
                    print_time_cost(step_time, "模型加载")

                    # 转录音频
                    step_time = print_step(3, 4, "转录音频")
                    audio = whisperx.load_audio(audio_path)
                    result = model.transcribe(audio, batch_size=batch_size)
                    detected_language = result["language"]
                    print_time_cost(step_time, "音频转录")

                    # 生成字幕文件
                    step_time = print_step(4, 4, "生成字幕文件")
                    output_dir = os.path.dirname(video_file)
                    base_name = os.path.splitext(os.path.basename(video_file))[0]
                    original_srt = os.path.join(output_dir, f"{base_name}_original.srt")

                    # 生成原始语言字幕
                    generate_original_srt(result["segments"], original_srt)
                    print_time_cost(step_time, "字幕生成")

                    print("\n✨ 处理完成！")
                    print_time_cost(total_time_start, "总")
                    print(f"📝 检测到语言: {detected_language}")
                    print(f"📝 字幕文件：{original_srt}")

                finally:
                    # 清理资源
                    try:
                        if 'audio_path' in locals():
                            os.remove(audio_path)
                        if 'model' in locals():
                            del model
                            gc.collect()
                            torch.cuda.empty_cache()
                    except Exception as e:
                        print(f"清理资源时出错: {str(e)}")

        except Exception as e:
            print(f"\n❌ 处理视频 {os.path.basename(video_file)} 时出错:")
            print(str(e))
            if len(video_files) > 1:
                print("继续处理下一个视频...\n")
                continue
            else:
                raise

    if len(video_files) > 1:
        print(f"\n✨ 所有视频处理完成！总共处理了 {len(video_files)} 个视频文件")
        print_time_cost(total_time_start, "总")