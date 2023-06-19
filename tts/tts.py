import torch
import asyncio
import websockets
import numpy as np
import soundfile as sf
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
from datasets import load_dataset

app = FastAPI()

# Load the TTS model, processor and vocoder
processor = SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")
model = SpeechT5ForTextToSpeech.from_pretrained("microsoft/speecht5_tts")
vocoder = SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan")

# Load xvector containing speaker's voice characteristics from a dataset
embeddings_dataset = load_dataset("Matthijs/cmu-arctic-xvectors", split="validation")
speaker_embeddings = torch.tensor(embeddings_dataset[7306]["xvector"]).unsqueeze(0)

class Data(BaseModel):
    text: str

CHUNK_SIZE = 4096  # Size of each chunk in bytes

async def send_audio_to_server(audio_data: bytes):
    uri = "ws://tts:5002ws"  # Replace with your server's URL
    async with websockets.connect(uri) as websocket:
        # Split the audio data into chunks and send each one
        for i in range(0, len(audio_data), CHUNK_SIZE):
            chunk = audio_data[i:i+CHUNK_SIZE]
            await websocket.send(chunk)

@app.post("/tts")
async def tts_endpoint(data: Data, background_tasks: BackgroundTasks):
    # Generate the TTS audio
    inputs = processor(text=data.text, return_tensors="pt")
    speech = model.generate_speech(inputs["input_ids"], speaker_embeddings, vocoder=vocoder)
    
    # Save audio to a .wav file for troubleshooting
    sf.write('audio.wav', speech.numpy(), samplerate=16000)

    # Convert waveform to bytes
    audio_data = speech.numpy().astype(np.int16).tobytes()

    # Send audio data to another server in the background
    background_tasks.add_task(send_audio_to_server, audio_data)

    return {"status": "Audio data sent"}
