import json
import base64
import time
import asyncio
import websockets
from flask import Flask, render_template,request
from flask_socketio import SocketIO, emit, disconnect
from threading import Thread
from typing import Dict, Any
import os
from flask_socketio import SocketIO


app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")  # 允许跨域（生产环境需限制来源）

# 大模型WSS配置（替换为实际参数）
MODEL_WSS_URL = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime?model=qwen-omni-turbo-realtime"
API_KEY = os.getenv('DASHSCOPE_API_KEY')  # 你的API密钥
MODEL_NAME = "qwen-omni-turbo-realtime"  # 模型名称

# 存储客户端连接信息：{client_id: (模型WSS连接, 事件循环)}
client_connections: Dict[str, tuple] = {}


class ModelConnection:
    """与大模型的WSS连接管理类"""
    def __init__(self, client_id: str):
        self.client_id = client_id  # 前端客户端ID
        self.websocket = None  # 与大模型的WSS连接
        self.loop = asyncio.new_event_loop()  # 异步事件循环
        self.thread = None  # 运行事件循环的线程

    def start(self):
        """启动事件循环线程，连接大模型WSS"""
        self.thread = Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        """在独立线程中运行异步事件循环"""
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._connect_model())

    async def _connect_model(self):
        """建立与大模型的WSS连接并初始化会话"""
        headers = [("Authorization", f"Bearer {API_KEY}")]
        try:
            # 连接大模型WSS接口
            self.websocket = await websockets.connect(
                f"{MODEL_WSS_URL}?model={MODEL_NAME}",
                additional_headers=headers
            )
            print(f"客户端 {self.client_id} 已连接大模型WSS")

            # 初始化会话配置（与前端、模型要求一致）
            await self._send_to_model({
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "voice": "Chelsie",
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {"model": "gummy-realtime-v1"},
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.1,
                        "silence_duration_ms": 900
                    }
                }
            })

            # 持续接收模型回复并转发给前端
            await self._receive_from_model()

        except Exception as e:
            print(f"模型连接错误: {str(e)}")
            # 通知前端连接失败
            socketio.emit(
                'server_message',
                {'type': 'error', 'message': f'模型连接失败: {str(e)}'},
                room=self.client_id
            )

    async def _send_to_model(self, event: Dict[str, Any]):
        """发送事件到大模型WSS接口"""
        if not self.websocket or self.websocket.closed:
            return
        # 补充事件ID（大模型要求）
        event['event_id'] = f"event_{int(time.time() * 1000)}"
        await self.websocket.send(json.dumps(event))

    async def _receive_from_model(self):
        """接收大模型回复并转发给前端"""
        try:
            async for message in self.websocket:
                model_event = json.loads(message)
                # 转发模型回复到前端
                socketio.emit(
                    'server_message',
                    self._format_model_event(model_event),
                    room=self.client_id
                )
        except websockets.exceptions.ConnectionClosed:
            print(f"客户端 {self.client_id} 与模型的连接已关闭")
        finally:
            # 安全关闭WebSocket连接
            if self.websocket and not self.websocket.closed:
                await self.websocket.close()
    def _format_model_event(self, model_event: Dict[str, Any]) -> Dict[str, Any]:
        """转换模型事件格式为前端可识别的格式"""
        if model_event['type'] == 'response.text.delta':
            # 文本增量：直接转发
            return {
                'type': 'text_delta',
                'delta': model_event['delta']
            }
        elif model_event['type'] == 'response.audio.delta':
            # 音频增量：模型返回的是Base64，直接转发
            return {
                'type': 'audio_delta',
                'audio': model_event['delta']
            }
        elif model_event['type'] == 'error':
            # 错误信息
            return {
                'type': 'error',
                'message': model_event['error'].get('message', '未知错误')
            }
        return {'type': 'unknown', 'data': model_event}

    def forward_audio(self, audio_chunk: bytes):
        """将前端音频块转发给大模型（线程安全）"""
        if not self.loop or self.loop.is_closed():
            return
        # 在事件循环中执行异步发送
        asyncio.run_coroutine_threadsafe(
            self._forward_audio_async(audio_chunk),
            self.loop
        )

    async def _forward_audio_async(self, audio_chunk: bytes):
        """异步转发音频块到大模型"""
        if not self.websocket or self.websocket.closed:
            return
        # 音频编码为Base64（大模型要求）
        audio_b64 = base64.b64encode(audio_chunk).decode()
        await self._send_to_model({
            'type': 'input_audio_buffer.append',
            'audio': audio_b64
        })

    def close(self):
        """关闭连接并清理资源"""
        if self.loop and not self.loop.is_closed():
            # 停止事件循环
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.thread.join()
            self.loop.close()
        if self.websocket:
            asyncio.run_coroutine_threadsafe(self.websocket.close(), self.loop)
        print(f"客户端 {self.client_id} 连接已关闭")

@app.route('/')
def index():
    return render_template('index.html')
# Flask-SocketIO 事件处理
@socketio.on('connect')
def handle_connect():
    """前端连接时初始化模型连接"""
    client_id = request.sid  # 获取客户端唯一ID
    print(f"新客户端连接: {client_id}")
    # 创建模型连接实例并启动
    model_conn = ModelConnection(client_id)
    client_connections[client_id] = model_conn
    model_conn.start()
    # 发送连接成功通知
    emit('server_message', {
        'type': 'status',
        'message': '已连接服务器，正在初始化模型...'
    })


@socketio.on('disconnect')
def handle_disconnect():
    """前端断开连接时清理资源"""
    client_id = request.sid
    if client_id in client_connections:
        model_conn = client_connections.pop(client_id)
        model_conn.close()
    print(f"客户端 {client_id} 已断开")


@socketio.on('audio_chunk')
def handle_audio_chunk(audio_data):
    """接收前端音频块并转发给大模型"""
    client_id = request.sid
    if client_id not in client_connections:
        return
    # 前端发送的是Base64编码的音频，解码为字节
    try:
        audio_chunk = base64.b64decode(audio_data)
        # 转发给大模型
        client_connections[client_id].forward_audio(audio_chunk)
    except Exception as e:
        emit('server_message', {
            'type': 'error',
            'message': f'音频处理失败: {str(e)}'
        })




if __name__ == '__main__':
    # 启动Flask-SocketIO服务器（支持WebSocket）
    socketio.run(app, host='0.0.0.0')