import torch
import torchaudio
import numpy as np
import websockets
from speechbrain.pretrained import Tacotron2
from speechbrain.pretrained import HIFIGAN
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List

class TextRequest(BaseModel):
    text: str

app = FastAPI()
tacotron2 = Tacotron2.from_hparams(source="speechbrain/tts-tacotron2-ljspeech", savedir="tmpdir_tts")
hifi_gan = HIFIGAN.from_hparams(source="speechbrain/tts-hifigan-ljspeech", savedir="tmpdir_vocoder")

def tts(text: str) -> np.ndarray:
    # Running the TTS
    mel_output, mel_length, alignment = tacotron2.encode_text(text)
    # Running the Vocoder (spectrogram-to-waveform)
    waveforms = hifi_gan.decode_batch(mel_output)
    return waveforms.squeeze().detach().cpu().numpy()

class WebSocketManager:
    def __init__(self, uri):
        self.uri = uri
        self.websocket = None

    async def connect(self):
        self.websocket = await websockets.connect(self.uri)

    async def send_binary(self, data):
        if self.websocket is None:
            raise Exception("WebSocket is not connected")
        await self.websocket.send(data)

    async def close(self):
        if self.websocket is not None:
            await self.websocket.close()
            self.websocket = None

# Set up WebSocketManager
websocket_manager = WebSocketManager('ws://10.147.20.23:5002/ws')

@app.on_event("startup")
async def startup_event():
    # Connect to the WebSocket server
    await websocket_manager.connect()

@app.on_event("shutdown")
async def shutdown_event():
    # Close the WebSocket connection
    await websocket_manager.close()

@app.post("/synthesize")
async def convert_text_to_speech(text_request: TextRequest):
    try:
        waveforms = tts(text_request.text)

        # Send audio waveform to WebSocket server
        await websocket_manager.send_binary(waveforms.tobytes())

        # Save audio to a file
        filename = "/app/audio.wav"
        sample_rate = 22050  # Sample rate of the audio (22050 Hz)
        waveforms_tensor = torch.from_numpy(waveforms)[None, :]
        torchaudio.save(filename, waveforms_tensor, sample_rate)

        return FileResponse(filename, media_type="audio/wav")
    except Exception as e:
        error_message = f"Error: {str(e)}"
        print(error_message)
        return {"error": error_message}
