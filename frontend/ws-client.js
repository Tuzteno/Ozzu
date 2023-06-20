// Create a WebSocket connection to the server
const socket = new WebSocket('ws://localhost:5002/ws');
socket.binaryType = 'arraybuffer';  // We're working with binary data

// Audio context and queue for audio data
let audioCtx = new AudioContext({ sampleRate: 16000 });
let audioQueue = [];

// Connection opened
socket.addEventListener('open', (event) => {
    console.log("Connected to WebSocket server");
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
    // We're assuming the data is 16-bit integers in little-endian order.
    let dataView = new Int16Array(event.data);
    let audioData = Array.from(dataView).map(n => n / 32768);  // Normalize to range [-1, 1]

    // Queue the audio data for playback
    audioQueue.push(audioData);

    // If audio is not currently playing, start playback
    if (audioCtx.state === 'suspended') {
        playAudio();
    }
});

function playAudio() {
    // If there's no audio data left, stop playback
    if (audioQueue.length === 0) {
        audioCtx.suspend();
        return;
    }

    // Get the next chunk of audio data from the queue
    let audioData = audioQueue.shift();

    // Create an audio buffer and source
    let audioBuffer = audioCtx.createBuffer(1, audioData.length, audioCtx.sampleRate);
    let source = audioCtx.createBufferSource();
    source.buffer = audioBuffer;

    // Copy audioData to buffer
    audioBuffer.copyToChannel(Float32Array.from(audioData), 0);

    // Connect source to output and start playback
    source.connect(audioCtx.destination);
    source.start();

    // When this chunk finishes playing, start the next one
    source.onended = playAudio;
}

// Start audio context (must be resumed in response to user interaction)
document.body.addEventListener('click', () => {
    if (audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
});
