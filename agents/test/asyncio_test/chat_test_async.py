import asyncio
import websockets
import json
import pyaudio

# 配置参数
WS_HOST = "localhost"
WS_PORT = 9000  # 对接 asr_test_async.py 的服务端口

# TTS 接收和播放类
class TTSCallback:
    def __init__(self):
        self._player = pyaudio.PyAudio()
        self._stream = self._player.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=22050,
            output=True
        )

    def on_data(self, data: bytes):
        self._stream.write(data)

    def close(self):
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
        if self._player:
            self._player.terminate()


async def chat_client():
    uri = f"ws://{WS_HOST}:{WS_PORT}"
    print(f"🔌 正在连接到 WebSocket 服务端：{uri}")
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ 已连接到服务端")

            tts_callback = TTSCallback()

            while True:
                user_input = input("\n🗣️ 输入要发送的消息（输入 q 退出）：")
                if user_input.lower() == 'q':
                    break

                # 发送消息给服务端
                await websocket.send(user_input)
                print("📩 消息已发送")

                # 接收服务端响应
                while True:
                    try:
                        response = await websocket.recv()

                        # 如果是二进制音频数据
                        if isinstance(response, bytes):
                            print("🔊 正在播放语音...")
                            tts_callback.on_data(response)

                        # 如果是文本回复
                        else:
                            print(f"🤖 收到回复：{response}")

                    except websockets.exceptions.ConnectionClosed:
                        print("🛑 与服务端的连接已断开")
                        break

    except Exception as e:
        print(f"❌ 连接失败：{e}")
    finally:
        tts_callback.close()


if __name__ == "__main__":
    asyncio.run(chat_client())