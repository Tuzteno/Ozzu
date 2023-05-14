const audio = new Audio();

const ws = new WebSocket("ws://localhost:5002/ws");

let pc;

ws.onopen = async () => {
  // initialize WebRTC connection
  pc = new RTCPeerConnection();

  // set up audio stream
  const audioTransceiver = pc.addTransceiver("audio");
  const audioStream = new MediaStream();
  audio.srcObject = audioStream;
  const audioReceiver = audioTransceiver.receiver;
  audioReceiver.track.onunmute = () => {
    audioStream.addTrack(audioReceiver.track);
  };

  // handle audio stream
  pc.addEventListener("track", (event) => {
    if (event.track.kind === "audio") {
      const dataReader = new MediaStreamTrackProcessor(event.track).readable.getReader();
      dataReader.read().then(function processResult(result) {
        if (result.done) {
          dataReader.releaseLock();
          return;
        }
        ws.send(result.value.buffer);
        return dataReader.read().then(processResult);
      });
    }
  });
};

ws.onmessage = async (event) => {
  // handle incoming messages from the server
  const message = JSON.parse(event.data);
  
  if (message.type === "offer") {
    await pc.setRemoteDescription(new RTCSessionDescription({type: "offer", sdp: message.sdp}));

    // send answer to server
    const answer = await pc.createAnswer();
    await pc.setLocalDescription(answer);

    ws.send(JSON.stringify({type: "answer", sdp: answer.sdp}));
  } else if (message.type === "candidate") {
    const candidate = new RTCIceCandidate({
      candidate: message.candidate,
      sdpMid: message.sdpMid,
      sdpMLineIndex: message.sdpMLineIndex
    });
    pc.addIceCandidate(candidate);
  } else if (event.data instanceof ArrayBuffer) {
    const arrayBuffer = event.data;
    audio.srcObject.getTracks().forEach(track => {
      track.enabled && track.readyState === 'live' && track.write(arrayBuffer)
    });
  }
};

ws.onclose = () => {
  // close WebRTC connection
  if (pc) {
    pc.close();
  }
};
