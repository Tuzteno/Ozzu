import torch
import asyncio
import websockets
import numpy as np
import soundfile as sf
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
from datasets import load_dataset
import logging
from fastapi.responses import JSONResponse

app = FastAPI()

# Load the TTS model, processor, and vocoder
processor = SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")
model = SpeechT5ForTextToSpeech.from_pretrained("microsoft/speecht5_tts")
vocoder = SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan")

# Load xvector containing speaker's voice characteristics from a dataset
embeddings_dataset = load_dataset("Matthijs/cmu-arctic-xvectors", split="validation")
speaker_embeddings = torch.tensor(embeddings_dataset[7306]["xvector"]).unsqueeze(0)

class Data(BaseModel):
    text: str

CHUNK_SIZE = 4096  # Size of each chunk in bytes

async def send_audio_to_server(audio_data: bytes, websocket: websockets.WebSocketClientProtocol):
    try:
        writer = await websocket.send()
        for i in range(0, len(audio_data), CHUNK_SIZE):
            chunk = audio_data[i:i+CHUNK_SIZE]
            await writer.drain()  # Ensure the stream buffer is flushed
            writer.write(chunk)

        await writer.drain()  # Ensure all data is sent
    except websockets.exceptions.ConnectionClosed:
        logging.error("WebSocket connection closed")

@app.post("/tts")
async def tts_endpoint(data: Data, background_tasks: BackgroundTasks):
    try:
        # Generate the TTS audio
        inputs = processor(text=data.text, return_tensors="pt")
        speech = model.generate_speech(inputs["input_ids"], speaker_embeddings, vocoder=vocoder)
        
        # Save audio to a .wav file for troubleshooting
        sf.write('audio.wav', speech.numpy(), samplerate=16000)

        # Convert waveform to bytes
        audio_data = speech.numpy().astype(np.int16).tobytes()

        # Establish the WebSocket connection
        uri = "ws://your-websocket-server-uri"  # Replace with your WebSocket server's URI
        websocket = await websockets.connect(uri)

        # Send audio data to the WebSocket server
        await send_audio_to_server(audio_data, websocket)

        # Close the WebSocket connection
        await websocket.close()

        return {"status": "Audio data sent"}
    except Exception as e:
        logging.error(f"TTS synthesis failed: {str(e)}")
        raise HTTPException(status_code=500, detail="TTS synthesis failed")

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"message": exc.detail})
