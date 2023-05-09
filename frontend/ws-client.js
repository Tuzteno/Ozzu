const audioContext = new AudioContext();

const websocket = new WebSocket('ws://localhost:5001/synthesize');

// Wait for user gesture to start AudioContext
document.addEventListener('click', async () => {
  await audioContext.resume();
});

// Connection opened
websocket.addEventListener('open', (event) => {
    console.log('Connected to websocket server.');
    
    // Create an example audio buffer
    const audioBuffer = audioContext.createBuffer(2, 44100, 44100);
    const audioData = audioBuffer.getChannelData(0);
    for (let i = 0; i < audioData.length; i++) {
        audioData[i] = Math.sin(i / 10);
    }
    const audioBlob = new Blob([audioBuffer.getChannelData(0)]);
    
    // Send the audio buffer to the server
    websocket.send(audioBlob);
});

// Listen for messages
websocket.addEventListener('message', async (event) => {
    // Decode the audio data received from the server
    const arrayBuffer = await event.data.arrayBuffer();
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
    // Create a new AudioBufferSourceNode
    const source = audioContext.createBufferSource();
    // Set the buffer of the AudioBufferSourceNode
    source.buffer = audioBuffer;
    // Connect the AudioBufferSourceNode to the destination (speakers)
    source.connect(audioContext.destination);
    // Start playing the audio
    source.start();
});

// Connection closed
websocket.addEventListener('close', (event) => {
    console.log('Disconnected from websocket server.');
});
