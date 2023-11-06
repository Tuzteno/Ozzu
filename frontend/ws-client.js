// Create a WebSocket connection to the server
const socket = new WebSocket('ws://localhost:8765'); // Use the correct WebSocket server port
socket.binaryType = 'arraybuffer';  // We're working with binary data

// Audio context and queue for audio data
let audioCtx = new AudioContext({ sampleRate: 16000 });
let bufferQueue = [];
let lastEndTime = 0;

// Connection opened
socket.addEventListener('open', (event) => {
    console.log("Connected to WebSocket server");
    
    // Start the AudioContext when the WebSocket connection is opened (user action)
    if (audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
});

// Connection closed
socket.addEventListener('close', (event) => {
    console.log("Disconnected from WebSocket server");
});

// Connection error
socket.addEventListener('error', (event) => {
    console.error("WebSocket error:", event);
});

// Listen for messages
socket.addEventListener('message', (event) => {
    // We're assuming the data is Float32Array.
    let dataView = new Float32Array(event.data);
    let audioData = Array.from(dataView);

    // Queue the audio data for playback
    queueAudio(audioData);
});

function queueAudio(audioData) {
    // Create an audio buffer and source
    let audioBuffer = audioCtx.createBuffer(1, audioData.length, audioCtx.sampleRate);
    let source = audioCtx.createBufferSource();
    source.buffer = audioBuffer;

    // Copy audioData to buffer
    audioBuffer.copyToChannel(Float32Array.from(audioData), 0);

    // Connect source to output
    source.connect(audioCtx.destination);

    if (audioCtx.currentTime > lastEndTime) {
        lastEndTime = audioCtx.currentTime;
    }

    source.start(lastEndTime);
    lastEndTime += audioBuffer.duration;

    // When this chunk finishes playing, remove it from the queue
    source.onended = () => {
        bufferQueue.shift();
        if (bufferQueue.length === 0) {
            lastEndTime = audioCtx.currentTime;
        }
    };

    bufferQueue.push(source);
}
