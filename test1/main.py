from flask import Flask, render_template, request
from flask_socketio import SocketIO
from backend.stt import SpeechToText
from backend.tts import STT_TTS_Service
import threading

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

stt_sessions = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def on_connect():
    sid = request.sid
    print(f"[INFO] 客户端 {sid} 连接")
    stt_sessions[sid] = SpeechToText(socketio, sid)

@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    print(f"[INFO] 客户端 {sid} 断开")
    stt = stt_sessions.pop(sid, None)
    if stt:
        stt.stop()

@socketio.on('audio_chunk')
def handle_audio_chunk(data):
    sid = request.sid
    pcm_chunk = data.get('chunk')
    if not pcm_chunk:
        #print(f"[WARN] 空音频块，客户端 {sid}")
        return
    #print(f"[DEBUG] 客户端 {sid} 音频块大小: {len(pcm_chunk)}")
    stt = stt_sessions.get(sid)
    if stt:
        stt.send_audio(pcm_chunk)

@socketio.on('asr_final_text')
def handle_asr_final_text(data):
    user_text = data.get('text')
    sid = request.sid

    print(f"[SocketIO] 收到最终识别文本: {user_text} 来自客户端 {sid}")

    # 创建服务实例
    service = STT_TTS_Service(socketio, sid)

    # 异步调用，避免阻塞
    threading.Thread(target=service.generate_and_speak, args=(user_text,)).start()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)