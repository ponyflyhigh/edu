document.addEventListener("DOMContentLoaded", async () => {
    const socket = io();

    const startBtn = document.getElementById("start");
    const stopBtn = document.getElementById("stop");
    const transcriptDiv = document.getElementById("transcript");

    let audioContext;
    let workletNode;
    let micStream;

    startBtn.onclick = async () => {
        startBtn.disabled = true;
        stopBtn.disabled = false;

        audioContext = new AudioContext({ sampleRate: 16000 });
        await audioContext.audioWorklet.addModule("static/js/processor.js");

        micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const source = audioContext.createMediaStreamSource(micStream);

        workletNode = new AudioWorkletNode(audioContext, "pcm-processor");

        workletNode.port.onmessage = (e) => {
            socket.emit("audio_chunk", { chunk: e.data });
        };

        source.connect(workletNode);
        workletNode.connect(audioContext.destination);
    };

    stopBtn.onclick = () => {
        startBtn.disabled = false;
        stopBtn.disabled = true;

        if (micStream) {
            micStream.getTracks().forEach(t => t.stop());
        }
        if (workletNode) {
            workletNode.disconnect();
        }
        if (audioContext) {
            audioContext.close();
        }
        socket.emit("audio_chunk_end");
    };

    socket.on("transcript", (data) => {
        transcriptDiv.textContent = "识别文本：" + data.text;
    });

    socket.on("tts_chunk", (data) => {
        playAudioChunk(data.chunk);
    });
    socket.on("connect", () => {
        console.log("Socket.IO connected, id:", socket.id);
    });

    socket.on("connect_error", (error) => {
        console.error("Socket.IO connect error:", error);
    });

    socket.on("disconnect", (reason) => {
        console.log("Socket.IO disconnected:", reason);
    });

    // 播放流式音频示范（简单）
    let audioQueue = [];
    const audioCtx = new AudioContext();
    function playAudioChunk(chunk) {
        audioCtx.decodeAudioData(chunk).then(buffer => {
            const source = audioCtx.createBufferSource();
            source.buffer = buffer;
            source.connect(audioCtx.destination);
            source.start();
        });
    }
});
