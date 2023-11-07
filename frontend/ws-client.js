const socket = new WebSocket('ws://localhost:8765');
socket.binaryType = 'arraybuffer';

const audioCtx = new AudioContext({ sampleRate: 16000 });
let bufferQueue = [];
let lastEndTime = 0;

socket.addEventListener('open', () => audioCtx.state === 'suspended' && audioCtx.resume());
socket.addEventListener('close', () => console.log("Disconnected from WebSocket server"));
socket.addEventListener('error', (event) => console.error("WebSocket error:", event));

socket.addEventListener('message', (event) => {
    const dataLength = event.data.byteLength;

    if (dataLength > 0) {
        const audioBuffer = audioCtx.createBuffer(1, dataLength / 4, audioCtx.sampleRate);
        audioBuffer.copyToChannel(new Float32Array(event.data), 0);

        const source = audioCtx.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioCtx.destination);

        if (audioCtx.currentTime > lastEndTime) lastEndTime = audioCtx.currentTime;
        source.start(lastEndTime);
        lastEndTime += audioBuffer.duration;

        source.onended = () => {
            bufferQueue.shift();
            if (bufferQueue.length === 0) lastEndTime = audioCtx.currentTime;
        };

        bufferQueue.push(source);
    }
});
