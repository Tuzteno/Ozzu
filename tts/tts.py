import torch
import soundfile as sf
import asyncio
import websockets
from fastapi import FastAPI, BackgroundTasks
from transformers import AutoTokenizer, AutoModelWithLMHead
from pydantic import BaseModel

app = FastAPI()

# Load the TTS model and tokenizer
model = AutoModelWithLMHead.from_pretrained("microsoft/speecht5_tts")
tokenizer = AutoTokenizer.from_pretrained("microsoft/speecht5_tts")

class Data(BaseModel):
    text: str

CHUNK_SIZE = 4096  # Size of each chunk in bytes

async def send_audio_to_server(audio_data: bytes):
    uri = "ws://yourwebsocketserver.com"  # Replace with your server's URL
    async with websockets.connect(uri) as websocket:
        # Split the audio data into chunks and send each one
        for i in range(0, len(audio_data), CHUNK_SIZE):
            chunk = audio_data[i:i+CHUNK_SIZE]
            await websocket.send(chunk)

@app.post("/tts")
async def tts_endpoint(data: Data, background_tasks: BackgroundTasks):
    # Generate the TTS audio
    inputs = tokenizer.encode(data.text, return_tensors="pt")
    with torch.no_grad():
        prediction = model.generate(inputs, max_length=800, temperature=0.7, num_return_sequences=1)

    # Save audio to a .wav file for troubleshooting
    sf.write('audio.wav', prediction[0].numpy(), 22050)

    # Convert tensor to bytes
    audio_data = prediction.tobytes()

    # Send audio data to another server in the background
    background_tasks.add_task(send_audio_to_server, audio_data)

    return {"status": "Audio data sent"}
