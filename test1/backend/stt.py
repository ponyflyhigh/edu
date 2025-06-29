from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult

class STTCallback(RecognitionCallback):
    def __init__(self, socketio, sid):
        super().__init__()
        self.socketio = socketio
        self.sid = sid

    def on_event(self, result: RecognitionResult):
        text = result.get_sentence()
        print(f"[STT] 识别结果: {text['text']}")
        self.socketio.emit('transcript', {'text': text}, room=self.sid)

class SpeechToText:
    def __init__(self, socketio, sid):
        self.socketio = socketio
        self.sid = sid
        self.callback = STTCallback(socketio, sid)
        self.recognition = Recognition(
            model='paraformer-realtime-v2',
            format='pcm',
            sample_rate=16000,
            callback=self.callback
        )
        self.recognition.start()

    def stop(self):
        self.recognition.stop()

    def send_audio(self, pcm_chunk):
        self.recognition.send_audio_frame(pcm_chunk)
