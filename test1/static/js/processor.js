class PCMProcessor extends AudioWorkletProcessor {
    process(inputs) {
        const input = inputs[0];
        if (input && input[0]) {
            const floatSamples = input[0];
            const int16Samples = new Int16Array(floatSamples.length);
            for (let i = 0; i < floatSamples.length; i++) {
                let s = floatSamples[i];
                s = Math.max(-1, Math.min(1, s)); // 限幅
                int16Samples[i] = s * 0x7fff;
            }
            this.port.postMessage(int16Samples.buffer, [int16Samples.buffer]);
        }
        return true;
    }
}

registerProcessor("pcm-processor", PCMProcessor);
