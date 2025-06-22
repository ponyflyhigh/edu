import pyaudio
import webrtcvad
import wave
import time
import threading
from dashscope.audio.asr import Recognition, RecognitionCallback
import numpy as np
import os
from collections import deque
# 配置参数
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 320  # 20ms帧长
VAD_AGGRESSIVENESS = 2  # VAD灵敏度 (0-3)
SILENCE_THRESHOLD = 15   # 连续静音帧数阈值（300ms）
PRE_ROLL = 10            # 预录制帧数（保留触发前的音频）
OUTPUT_FILE = "output.wav"

# 配置阿里云API Key（替换为你的实际值）


class MyCallback(RecognitionCallback):
    """识别回调函数，处理识别结果"""
    def on_open(self):
        print("🔌 ASR连接已建立")
    
    def on_result(self, result):
        print(f"🎙️ 识别结果: {result.get_sentence()}")
    
    def on_close(self):
        print("🔌 ASR连接已关闭")

def record_with_vad():
    """使用VAD检测语音并录制"""
    vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
    p = pyaudio.PyAudio()
    
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    
    print("\n👂 开始监听麦克风...")
    print("💬 请开始说话，系统会自动检测语音开始和结束")
    
    # 预录制缓冲区（保存触发前的音频）
    pre_buffer = deque(maxlen=PRE_ROLL)
    frames = []
    silence_frames = 0
    speech_detected = False
    
    try:
        while True:
            # 读取音频帧
            data = stream.read(CHUNK)
            
            # 使用VAD检测语音
            is_speech = vad.is_speech(data, RATE)
            
            if not speech_detected:
                # 语音未开始，收集预录制缓冲区
                pre_buffer.append(data)
                
                if is_speech:
                    # 检测到语音开始
                    speech_detected = True
                    frames = list(pre_buffer)  # 添加预录制内容
                    frames.append(data)
                    print("🎤 检测到语音，开始录制...")
            else:
                # 语音已开始，继续录制
                frames.append(data)
                
                if is_speech:
                    silence_frames = 0
                else:
                    silence_frames += 1
                    
                    # 检测到足够长时间的静音，认为语音结束
                    if silence_frames > SILENCE_THRESHOLD:
                        print("🔇 语音结束，停止录制")
                        break
    
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
    
    # 保存录音文件
    if frames:
        with wave.open(OUTPUT_FILE, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
        print(f"💾 录音已保存至: {OUTPUT_FILE}")
        return OUTPUT_FILE
    else:
        print("⚠️ 未检测到语音")
        return None

def recognize_audio(audio_file):
    """调用阿里云API识别音频"""
    if not audio_file:
        return
    
    print("🚀 正在调用语音识别模型...")
    recognition = Recognition(
        model='paraformer-realtime-v2',
        format='wav',
        sample_rate=16000,
        language_hints=['zh', 'en'],
        callback=MyCallback(),
    )
    
    result = recognition.call(audio_file)
    if result.status_code == 200:
        print("✅ 识别完成")
    else:
        print(f"❌ 识别失败: {result.message}")

def main():
    """主函数：循环监听语音并识别"""
    try:
        while True:
            print("\n" + "="*50)
            print("🔁 按Enter开始新的录音，输入q退出...")
            user_input = input().strip().lower()
            if user_input == 'q':
                break
                
            audio_file = record_with_vad()
            recognize_audio(audio_file)
            
            # 可选：删除临时文件
         
    
    finally:
        print("\n👋 程序已退出")

if __name__ == "__main__":
    main()