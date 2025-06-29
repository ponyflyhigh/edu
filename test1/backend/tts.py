import threading
from http import HTTPStatus
from dashscope import Generation
from dashscope.audio.tts_v2 import SpeechSynthesizer, AudioFormat, ResultCallback

class Callback(ResultCallback):
    def __init__(self, socketio, sid):
        self.socketio = socketio
        self.sid = sid

    def on_open(self):
        print("[TTS] WebSocket连接已打开")

    def on_complete(self):
        print("[TTS] 语音合成完成")
        self.socketio.emit('tts_complete', {}, room=self.sid)

    def on_error(self, message: str):
        print(f"[TTS] 语音合成错误: {message}")
        self.socketio.emit('tts_error', {'error': message}, room=self.sid)

    def on_close(self):
        print("[TTS] WebSocket连接已关闭")

    def on_event(self, message):
        print(f"[TTS] 事件消息: {message}")

    def on_data(self, data: bytes) -> None:
        # 直接把合成的PCM音频流发给客户端（前端接收后用 Web Audio API 播放）
        self.socketio.emit('tts_chunk', {'chunk': data}, room=self.sid)


class STT_TTS_Service:
    def __init__(self, socketio, sid):
        self.socketio = socketio
        self.sid = sid
        self.model = "cosyvoice-v1"      # TTS模型名
        self.voice = "longxiaochun"      # 选择语音
        self.callback = Callback(socketio, sid)
        self.synthesizer = SpeechSynthesizer(
            model=self.model,
            voice=self.voice,
            format=AudioFormat.PCM_22050HZ_MONO_16BIT,
            callback=self.callback,
        )

    def generate_and_speak(self, user_text: str):
        """
        传入识别出的文本，调用大模型生成对话回复，随后调用TTS流式合成音频。
        """
        print(f"[STT_TTS] 收到用户文本：{user_text}")

        # 构造对话消息
        messages = [{"role": "user", "content": user_text}]

        # 调用大模型生成接口（stream=True支持流式增量返回）
        responses = Generation.call(
            model="qwen-turbo",
            messages=messages,
            result_format="message",
            stream=True,
            incremental_output=True,
        )

        # 流式处理生成的文本
        for response in responses:
            if response.status_code == HTTPStatus.OK:
                content = response.output.choices[0]["message"]["content"]
                print(f"[STT_TTS] 生成文本片段: {content}")
                # 通过TTS流式合成
                self.synthesizer.streaming_call(content)
            else:
                err = (response.request_id, response.status_code, response.code, response.message)
                print(f"[STT_TTS] 大模型调用失败: 请求ID {err[0]}, 状态码 {err[1]}, 错误码 {err[2]}, 信息 {err[3]}")

        self.synthesizer.streaming_complete()
        print("[STT_TTS] 语音合成流程结束")
