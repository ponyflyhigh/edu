// static/js/voice-streamer.js
class VoiceStreamer {
    constructor(socket) {
        this.socket = socket;
        this.mediaStream = null;
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.encoder = null;
        this.recorder = null;
        this.isRecording = false;
        this.chunkSize = 1024;
    }

    startStreaming() {
        if (this.isRecording) return;

        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                this.mediaStream = stream;
                this.isRecording = true;

                const source = this.audioContext.createMediaStreamSource(stream);
                const processor = this.audioContext.createScriptProcessor(
                    this.chunkSize, 1, 1
                );

                this.encoder = this.createWavEncoder();

                processor.onaudioprocess = (e) => {
                    if (!this.isRecording) return;
                    this.processAudioChunk(e.inputBuffer);
                };

                source.connect(processor);
                processor.connect(this.audioContext.destination);
                this.recorder = processor;
            })
            .catch(err => console.error("获取麦克风权限失败:", err));
    }

    processAudioChunk(buffer) {
        const channelData = buffer.getChannelData(0);
        const pcmData = new Float32Array(channelData);

        const int16Data = new Int16Array(pcmData.length);
        for (let i = 0; i < pcmData.length; i++) {
            int16Data[i] = Math.max(-32768, Math.min(32767, pcmData[i] * 32767));
        }

        const chunk = this.encoder.encode(int16Data);
        this.socket.emit('audio_chunk', {
            chunk: chunk.buffer,
            is_end: false
        });
    }

    createWavEncoder() {
        let buffer = new ArrayBuffer(44);
        let view = new DataView(buffer);

        writeString(view, 0, 'RIFF');
        view.setUint32(4, 36, true);
        view.setUint32(8, 'WAVE', true);
        view.setUint32(12, 'fmt ', true);
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);
        view.setUint16(22, 1, true);
        view.setUint32(24, 16000, true);
        view.setUint32(28, 32000, true);
        view.setUint16(32, 2, true);
        view.setUint16(34, 16, true);

        return {
            encode: (pcmData) => {
                const dataLength = pcmData.byteLength;
                const totalLength = 44 + dataLength;

                view.setUint32(4, totalLength - 8, true);
                view.setUint32(40, dataLength, true);

                const result = new ArrayBuffer(totalLength);
                const resultView = new DataView(result);

                for (let i = 0; i < 44; i++) {
                    resultView.setUint8(i, view.getUint8(i));
                }

                const pcmView = new Uint8Array(pcmData.buffer);
                for (let i = 0; i < dataLength; i++) {
                    resultView.setUint8(44 + i, pcmView[i]);
                }

                return resultView;
            }
        };
    }

    stopStreaming() {
        if (!this.isRecording) return;

        this.isRecording = false;
        this.socket.emit('audio_chunk', {
            chunk: new ArrayBuffer(0),
            is_end: true
        });

        if (this.recorder) {
            this.recorder.disconnect();
            this.recorder = null;
        }

        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }
    }
}

function writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
    }
}

console.log("voice-streamer.js loaded");