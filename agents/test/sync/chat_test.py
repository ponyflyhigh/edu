import socket
import threading
import pyaudio
from dashscope.audio.tts_v2 import SpeechSynthesizer, AudioFormat, ResultCallback
from dashscope import Generation

# 配置参数
HOST = '127.0.0.1'
PORT = 5000
model = "cosyvoice-v1"
voice = "longxiaochun"
llm_model = "qwen-turbo"  # 大模型名称
current_tts_callback = None
current_synthesizer = None
class TTSCallback(ResultCallback):
    """TTS回调函数，处理语音合成音频流"""
    _player = None
    _stream = None
    _interrupt_flag = False  # 新增中断标志

    def on_open(self):
        print("🔌 TTS连接已建立")
        self._player = pyaudio.PyAudio()
        self._stream = self._player.open(
            format=pyaudio.paInt16, channels=1, rate=22050, output=True
        )

    def on_complete(self):
        print("🎶 合成任务完成")
        self._interrupt_flag = False

    def on_error(self, message: str):
        print(f"❌ 合成失败: {message}")

    def on_close(self):
        print("🔌 TTS连接已关闭")
        self._stream.stop_stream()
        self._stream.close()
        self._player.terminate()

    def on_data(self, data: bytes) -> None:
        if self._interrupt_flag:
            print("🛑 当前语音播放被中断")
            return
        self._stream.write(data)

    def interrupt(self):
        """外部调用此方法以中断当前播放"""
        self._interrupt_flag = True
def handle_client(client_socket, addr):
    """处理客户端连接"""
    print(f"🟢 接受来自 {addr} 的连接")
    global current_tts_callback, current_synthesizer

    tts_callback = TTSCallback()
    synthesizer = SpeechSynthesizer(
        model=model,
        voice=voice,
        format=AudioFormat.PCM_22050HZ_MONO_16BIT,
        callback=tts_callback,
    )
    current_tts_callback = tts_callback
    current_synthesizer = synthesizer    
    # 对话历史
    conversation_history = []
    
    try:
        while True:
            # 接收ASR识别文本
            text_chunks = []
            while True:
                data = client_socket.recv(1024)
                if not data or b'\n' in data:
                    text_chunks.append(data.decode('utf-8').replace('\n', ''))
                    break
                text_chunks.append(data.decode('utf-8'))
            
            user_text = ''.join(text_chunks).strip()
            print(f"🔍 原始接收数据: {'|'.join(text_chunks)}")

            if not user_text:
                print("⚠️ 接收到空文本")
                continue
            
            print(f"用户输入: {user_text}")
            
            # 添加到对话历史
            conversation_history.append({"role": "user", "content": user_text})
            
            # 调用大模型
            print("🚀 正在调用大模型...")
            responses = Generation.call(
                model=llm_model,
                messages=conversation_history,
                result_format="message",
                stream=True,
                incremental_output=True,
            )
            
            ai_response = ""
            for response in responses:
                if response.status_code == 200:
                    content = response.output.choices[0]["message"]["content"]
                    ai_response += content
                    print(content, end="")

                    # 实时TTS合成
                    synthesizer.streaming_call(content)
                else:
                    print(f"❌ 大模型调用失败: {response.message}")
            
            # 添加到对话历史
            conversation_history.append({"role": "assistant", "content": ai_response})
            print(f"\n大模型响应: {ai_response[:30]}...")
            
            # 关闭当前TTS流，准备下一次使用
            synthesizer.streaming_complete()
            tts_callback.on_close()
            
            # 重新初始化 TTS 流
            tts_callback = TTSCallback()
            synthesizer = SpeechSynthesizer(
                model=model,
                voice=voice,
                format=AudioFormat.PCM_22050HZ_MONO_16BIT,
                callback=tts_callback,
            )
            
    except KeyboardInterrupt:
        print("\n🛑 用户中断程序")
    except Exception as e:
        print(f"❌ 发生错误: {e}")
    
    finally:
        client_socket.close()
        print(f"🛑 客户端 {addr} 连接关闭")

def start_server():
    """启动服务端并处理多个并发连接"""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)  # 支持最大并发数为5
    print(f"🚀 文本处理服务启动，监听 {HOST}:{PORT}，等待连接...")

    try:
        while True:
            client_socket, addr = server_socket.accept()
            # 为每个连接启动一个新的线程来处理
            threading.Thread(target=handle_client, args=(client_socket, addr)).start()

    except KeyboardInterrupt:
        print("\n🛑 用户中断服务")

    finally:
        server_socket.close()

if __name__ == "__main__":
    start_server()
