// --- web/js/audio_processor.js ---

// Number of samples accumulated before a message is posted.
// 1024 = 8 render quanta (8 * 128) = ~21.3 ms @ 48 kHz.
// Chosen as an exact multiple of the 128-sample render quantum so a batch
// boundary can never fall inside a quantum. Drops the postMessage/WebSocket
// message rate from ~375/s to ~47/s (8x).
const BATCH_SAMPLES = 1024;

/**
 * Mixed audio processor that combines microphone and system audio
 * while tracking volume levels for speaker detection.
 */
class MixedProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this.micInputIndex = 0;
        this.systemInputIndex = 1;

        // Batching state: PCM accumulates here and is posted once full.
        this.batch = new Int16Array(BATCH_SAMPLES);
        this.batchFill = 0;
        this.micLevelSum = 0;
        this.systemLevelSum = 0;
    }

    process(inputs, outputs, parameters) {
        // We expect two inputs: [0] = microphone, [1] = system audio
        const micInput = inputs[0] && inputs[0][0] ? inputs[0][0] : new Float32Array(128);
        const systemInput = inputs[1] && inputs[1][0] ? inputs[1][0] : new Float32Array(128);
        
        const frameLength = Math.max(micInput.length, systemInput.length);
        if (frameLength === 0) return true;

        for (let i = 0; i < frameLength; i++) {
            const micSample = i < micInput.length ? micInput[i] : 0;
            const systemSample = i < systemInput.length ? systemInput[i] : 0;

            // Mix the audio (simple addition with slight attenuation).
            // Math.fround reproduces the float32 rounding the old code got for
            // free by staging the mix in a Float32Array, so the PCM bytes on the
            // wire are bit-identical to before.
            const mixed = Math.fround((micSample + systemSample) * 0.7);

            // Convert to 16-bit PCM directly into the batch buffer
            const s = Math.max(-1, Math.min(1, mixed));
            this.batch[this.batchFill++] = s < 0 ? s * 0x8000 : s * 0x7FFF;

            // Track volume levels across the whole batch
            this.micLevelSum += Math.abs(micSample);
            this.systemLevelSum += Math.abs(systemSample);

            if (this.batchFill === BATCH_SAMPLES) {
                this.flushBatch();
            }
        }

        return true;
    }

    /**
     * Posts the accumulated batch with batch-averaged volume levels.
     * The batch buffer is replaced BEFORE postMessage transfers (detaches) it,
     * so the detached ArrayBuffer is never read or written again.
     */
    flushBatch() {
        const pcmData = this.batch;
        const sampleCount = this.batchFill;

        // Average the volume levels over the batch (equivalent to the mean of
        // the per-render-quantum averages the old code produced).
        const micLevel = this.micLevelSum / sampleCount;
        const systemLevel = this.systemLevelSum / sampleCount;

        this.batch = new Int16Array(BATCH_SAMPLES);
        this.batchFill = 0;
        this.micLevelSum = 0;
        this.systemLevelSum = 0;

        // Send mixed audio with volume levels for speaker detection
        this.port.postMessage({
            audioData: pcmData.buffer,
            micLevel: micLevel,
            systemLevel: systemLevel
        }, [pcmData.buffer]);
    }
}

registerProcessor('mixed-processor', MixedProcessor);