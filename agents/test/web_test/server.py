import asyncio
import websockets
from dashscope.audio.asr import (Recognition, RecognitionCallback,
                                 RecognitionResult)
import threading
import queue
import time

# 若没有将API Key配置到环境变量中，需将下面这行代码注释放开，并将apiKey替换为自己的API Key
# import dashscope
# dashscope.api_key = "apiKey"

# ASR回调类
class ASRCallback(RecognitionCallback):
    def __init__(self, client_id):
        self.client_id = client_id
        
    def on_open(self) -> None:
        print(f"🔌 ASR连接已打开 (客户端: {self.client_id})")

    def on_close(self) -> None:
        print(f"🔌 ASR连接已关闭 (客户端: {self.client_id})")

    def on_event(self, result: RecognitionResult) -> None:
        sentence = result.get_sentence()
        if sentence:
            print(f"🎤 ASR识别结果 (客户端: {self.client_id}): {sentence}")
            # 这里可以添加将识别结果发送回客户端的逻辑

# 客户端处理类
class ClientHandler:
    def __init__(self, client_id, websocket):
        self.client_id = client_id
        self.websocket = websocket
        self.audio_queue = queue.Queue()
        self.asr_task = None
        self.asr_running = False
        self.recognition = None
        
    async def start_asr(self):
        """启动ASR处理任务"""
        self.asr_running = True
        callback = ASRCallback(self.client_id)
        
        # 初始化ASR识别器
        self.recognition = Recognition(
            model='paraformer-realtime-v2',
            format='pcm',
            sample_rate=16000,  # 假设音频采样率为16kHz
            callback=callback
        )
        
        # 启动ASR识别
        self.recognition.start()
        
        # 启动音频处理线程
        self.asr_task = threading.Thread(target=self._process_audio_queue)
        self.asr_task.daemon = True
        self.asr_task.start()
        
        print(f"🚀 ASR处理已启动 (客户端: {self.client_id})")
        
    def _process_audio_queue(self):
        """处理音频队列中的数据"""
        while self.asr_running:
            try:
                # 从队列中获取音频数据，超时时间为1秒
                audio_data = self.audio_queue.get(timeout=1)
                
                # 发送音频数据到ASR服务
                self.recognition.send_audio_frame(audio_data)
                
            except queue.Empty:
                # 队列为空，继续等待
                continue
            except Exception as e:
                print(f"❗ 处理音频数据时出错 (客户端: {self.client_id}): {e}")
                break
        
        # 停止ASR识别
        if self.recognition:
            self.recognition.stop()
            self.recognition = None
            
        print(f"🛑 ASR处理已停止 (客户端: {self.client_id})")
        
    def enqueue_audio(self, audio_data):
        """将音频数据加入处理队列"""
        self.audio_queue.put(audio_data)
        
    async def stop(self):
        """停止处理并清理资源"""
        self.asr_running = False
        if self.asr_task and self.asr_task.is_alive():
            self.asr_task.join(timeout=2.0)
            
        if self.recognition:
            self.recognition.stop()
            self.recognition = None
            
        print(f"👋 客户端处理已停止 (客户端: {self.client_id})")

# 客户端管理器
class ClientManager:
    def __init__(self):
        self.clients = {}
        self.next_client_id = 1
        
    def add_client(self, websocket):
        client_id = self.next_client_id
        self.next_client_id += 1
        
        client_handler = ClientHandler(client_id, websocket)
        self.clients[client_id] = client_handler
        
        print(f"🆕 客户端已注册 (ID: {client_id})")
        return client_id, client_handler
        
    def remove_client(self, client_id):
        if client_id in self.clients:
            client_handler = self.clients[client_id]
            asyncio.create_task(client_handler.stop())
            del self.clients[client_id]
            print(f"❌ 客户端已移除 (ID: {client_id})")
            
    def get_client(self, client_id):
        return self.clients.get(client_id)

# WebSocket处理函数
async def handle_audio(websocket, path=None):
    # 创建客户端管理器
    client_manager = ClientManager()
    
    # 添加新客户端
    client_id, client_handler = client_manager.add_client(websocket)
    
    try:
        # 启动ASR处理
        await client_handler.start_asr()
        
        # 接收客户端消息
        async for message in websocket:
            if isinstance(message, bytes):
                # 处理二进制音频数据
                print(f"🔊 收到音频数据 (客户端: {client_id}): 字节数={len(message)}, 前20字节(hex)={message[:20].hex()}")
                
                # 将音频数据加入处理队列
                client_handler.enqueue_audio(message)
            else:
                # 处理文本消息
                print(f"💬 收到文本消息 (客户端: {client_id}): {message}")
                
                # 可以在这里添加对文本消息的处理逻辑
    
    except websockets.exceptions.ConnectionClosedOK:
        print(f"👋 客户端正常断开连接 (ID: {client_id})")
    except Exception as e:
        print(f"❗ 处理客户端连接时出错 (ID: {client_id}): {e}")
    finally:
        # 移除客户端
        client_manager.remove_client(client_id)

# 主函数
async def main():
    async with websockets.serve(handle_audio, "localhost", 8765):
        print("🚀 WebSocket 服务已启动，监听 ws://localhost:8765")
        await asyncio.Future()  # 保持运行

if __name__ == "__main__":
    asyncio.run(main())