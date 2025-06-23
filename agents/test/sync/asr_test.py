# asr_stream.py
# 实时语音识别模块，增强错误处理和资源管理

import pyaudio
import webrtcvad
import socket
from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult
from dashscope.common.error import InvalidParameter  # 导入错误类型

# 配置参数
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 320
VAD_AGGRESSIVENESS = 2
SILENCE_THRESHOLD = 15
PRE_ROLL = 10
HOST = '127.0.0.1'
PORT = 5000

class ASRCallback(RecognitionCallback):
    """ASR回调函数，处理完整识别文本"""
    def __init__(self):
        self.text = ""
    
    def on_event(self, result: RecognitionResult) -> None:
        sentence = result.get_sentence()
        if isinstance(sentence, str):
            self.text = sentence
            print(f"🎙️ 识别结果: {self.text}")
        elif isinstance(sentence, dict) and 'text' in sentence:
            self.text = sentence['text']
            print(f"🎙️ 解析文本: {self.text}")


class ASRStream:
    """语音识别流管理，增强错误处理"""
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.asr = None
        self.stream = None
        self.connected = False
    
    def connect(self):
        """连接到大模型服务"""
        try:
            self.socket.connect((HOST, PORT))
            self.connected = True
            print(f"✅ 连接到文本服务 {HOST}:{PORT}")
            return True
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            self.connected = False
            return False
    
    def start(self):
        """启动识别流，增强错误处理"""
        if not self.connect():
            return
        
        print("\n👂 开始监听麦克风...")
        
        while True:
            try:
                self._start_new_recognition()
            except InvalidParameter as e:
                if "Speech recognition has stopped." in str(e):
                    print(f"ℹ️ 识别服务已停止，重新启动: {e}")
                else:
                    print(f"❌ 识别错误: {e}")
            except Exception as e:
                print(f"❌ 发生未预期错误: {e}")
            finally:
                self._cleanup_current_session()
                print("\n--- 准备下一次识别 ---")
    
    def _start_new_recognition(self):
        """启动新的识别会话，分离核心逻辑"""
        self.stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        callback = ASRCallback()
        self.asr = Recognition(
            model='paraformer-realtime-v2',
            format='pcm',
            sample_rate=RATE,
            callback=callback
        )
        self.asr.start()
        
        speech_detected = False
        silence_frames = 0
        
        try:
            while True:
                data = self.stream.read(CHUNK, exception_on_overflow=False)
                is_speech = self.vad.is_speech(data, RATE)
                
                if not speech_detected:
                    if is_speech:
                        speech_detected = True
                        silence_frames = 0
                        print("🎤 检测到语音")
                        self.asr.send_audio_frame(data)
                else:
                    self.asr.send_audio_frame(data)
                    
                    if not is_speech:
                        silence_frames += 1
                        if silence_frames > SILENCE_THRESHOLD:
                            print("🔇 语音结束")
                            self._send_text(callback.text)
                            callback.text = ""
                            break
        finally:
            # 确保在异常时也能正确清理
            if self.asr:
                self.asr.stop()
    
    def _send_text(self, text):
        """发送文本到大模型，增强错误处理"""
        if not text:
            print("⚠️ 无有效文本")
            return
        
        print(f"📤 发送文本: {text}")
        try:
            self.socket.sendall(text.encode('utf-8') + b'\n')
        except Exception as e:
            print(f"❌ 发送失败: {e}")
            self.connect()
    
    def _cleanup_current_session(self):
        """清理当前会话资源，避免多次停止错误"""
        if self.asr:
            try:
                self.asr.stop()
            except InvalidParameter:
                pass  # 忽略已停止的错误
            self.asr = None
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
    
    def cleanup(self):
        """全局资源清理"""
        self._cleanup_current_session()
        if self.connected:
            self.socket.close()
        self.p.terminate()
        print("👋 识别模块已退出")

if __name__ == "__main__":
    asr = ASRStream()
    try:
        asr.start()
    except KeyboardInterrupt:
        print("\n🛑 用户中断")
    finally:
        asr.cleanup()