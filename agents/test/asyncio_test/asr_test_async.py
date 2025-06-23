import asyncio
import websockets
import pyaudio
from dashscope.audio.tts_v2 import SpeechSynthesizer, AudioFormat, ResultCallback
from dashscope import Generation

HOST = 'localhost'
PORT = 9000
model = "cosyvoice-v1"
voice = "longxiaochun"
llm_model = "qwen-turbo"

class TTSCallback(ResultCallback):
    def __init__(self):
        self._player = None
        self._stream = None
        self._interrupt_flag = False

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
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
        if self._player:
            self._player.terminate()

    def on_data(self, data: bytes) -> None:
        if not self._interrupt_flag:
            self._stream.write(data)

    def interrupt(self):
        self._interrupt_flag = True

async def handle_websocket(websocket, path):
    print(f"🟢 客户端已连接：{websocket.remote_address}")
    conversation_history = []

    try:
        async for message in websocket:
            user_text = message.strip()
            print(f"🗣️ 收到用户输入：{user_text}")
            if not user_text:
                continue

            conversation_history.append({"role": "user", "content": user_text})

            print("🚀 正在调用大模型...")
            responses = Generation.call(
                model=llm_model,
                messages=conversation_history,
                result_format="message",
                stream=True,
                incremental_output=True,
            )

            ai_response = ""
            tts_callback = TTSCallback()
            synthesizer = SpeechSynthesizer(
                model=model,
                voice=voice,
                format=AudioFormat.PCM_22050HZ_MONO_16BIT,
                callback=tts_callback,
            )

            for response in responses:
                if response.status_code == 200:
                    content = response.output.choices[0]["message"]["content"]
                    ai_response += content
                    print(content, end="", flush=True)
                    synthesizer.streaming_call(content)
                else:
                    print(f"\n❌ 大模型调用失败：{response.message}")

            conversation_history.append({"role": "assistant", "content": ai_response})
            print(f"\n🤖 大模型响应完毕：{ai_response[:50]}...")
            synthesizer.streaming_complete()
            tts_callback.on_close()

            # 发送回复给客户端
            await websocket.send(ai_response)

    except websockets.exceptions.ConnectionClosedError:
        print("❌ 客户端断开连接")
    except Exception as e:
        print(f"❌ 发生错误：{e}")
    finally:
        print(f"🛑 客户端连接关闭：{websocket.remote_address}")

async def start_server():
    print(f"🚀 WebSocket 语音服务启动中，监听 {HOST}:{PORT}")
    try:
        async with websockets.serve(handle_websocket, HOST, PORT):
            print("✅ WebSocket 服务已成功启动")
            await asyncio.Future()  # 永久运行
    except OSError as e:
        print(f"❌ 端口绑定失败：{e}")
    except Exception as e:
        print(f"❌ 启动失败：{e}")

if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        print("🛑 用户终止程序")