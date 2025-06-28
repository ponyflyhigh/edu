from flask import Flask, request,render_template
from flask_socketio import SocketIO, emit
import numpy as np
import soundfile as sf
import os
import time
from threading import Lock

app = Flask(__name__, template_folder='templates', static_folder='static')
socketio = SocketIO(app, cors_allowed_origins="*")

# 音频处理参数
AUDIO_SAMPLE_RATE = 16000  # 采样率
AUDIO_CHANNELS = 1        # 单声道
AUDIO_FORMAT = "pcm_16"   # 16位PCM编码

# 存储客户端音频流
client_audio_streams = {}
stream_locks = {}

@app.route('/')
def index():
    return render_template('index.html')
@app.route('/test-static')
def test_static():
    return app.send_static_file('js/chat.js')@socketio.on('connect')
def handle_connect():
    client_id = request.sid
    print(f"客户端连接: {client_id}")
    
    # 为新客户端初始化音频流存储
    client_audio_streams[client_id] = b""
    stream_locks[client_id] = Lock()
    
    # 响应连接确认
    emit('connect_ack', {'status': 'connected', 'timestamp': time.time()})

@socketio.on('audio_chunk')
def handle_audio_chunk(data):
    """接收前端发送的音频数据块"""
    client_id = request.sid
    chunk = data.get('chunk')
    is_end = data.get('is_end', False)
    
    if not chunk:
        return
    
    with stream_locks[client_id]:
        # 追加音频数据
        client_audio_streams[client_id] += chunk
        
        if is_end:
            # 处理完整音频流
            socketio.start_background_task(process_full_audio, client_id)

def process_full_audio(client_id):
    """处理完整音频流（可用于LLM语音识别）"""
    with stream_locks[client_id]:
        audio_data = client_audio_streams[client_id]
        client_audio_streams[client_id] = b""  # 清空缓冲区
    
    if not audio_data:
        return
    
    try:
        # 示例：将音频数据保存为文件（实际应用中可替换为语音识别）
        temp_file = f"temp_audio_{client_id}_{int(time.time())}.wav"
        # 注意：PCM数据需要转换为WAV格式（添加头部信息）
        # 简化处理：使用soundfile库保存（实际应根据编码格式调整）
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        sf.write(temp_file, audio_array, AUDIO_SAMPLE_RATE)
        
        # 调用LLM语音识别（如OpenAI Whisper）
        # response = openai.Audio.transcribe("whisper-1", open(temp_file, "rb"))
        # text = response["text"]
        
        # 模拟识别结果
        text = "模拟识别结果：这是一段测试语音内容。"
        
        # 发送识别结果给前端
        socketio.emit('speech_recognition', 
                     {'text': text, 'client_id': client_id}, 
                     room=client_id)
        
        # 清理临时文件
        os.remove(temp_file)
        
    except Exception as e:
        print(f"音频处理错误: {str(e)}")
        socketio.emit('audio_error', 
                     {'error': str(e), 'client_id': client_id}, 
                     room=client_id)
@socketio.on('audio_chunk')
def handle_audio_chunk(data):
    print("接收到音频块:", data)
@socketio.on('disconnect')
def handle_disconnect():
    client_id = request.sid
    print(f"客户端断开: {client_id}")
    with stream_locks.get(client_id, Lock()):
        client_audio_streams.pop(client_id, None)
        stream_locks.pop(client_id, None)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)