import logging
import asyncio
from datetime import datetime
import json
import torch
import soundfile as sf
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
from datasets import load_dataset
import websockets

app = FastAPI()
logger = logging.getLogger(__name__)

processor = SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")
model = SpeechT5ForTextToSpeech.from_pretrained("microsoft/speecht5_tts")
vocoder = SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan")

# Load the dataset at startup
embeddings_dataset = load_dataset("Matthijs/cmu-arctic-xvectors", split="validation")

class TextRequest(BaseModel):
    text: str

async def send_audio(audio_data):
    async with websockets.connect('ws://ws:5002/ws/client2') as websocket:
        print('WebSocket connection established.')
        await websocket.send(audio_data.cpu().numpy().tobytes())
        print('Audio data sent to WebSocket server.')

@app.post("/synthesize")
async def synthesize(request: TextRequest):
     if not request.text:
         raise HTTPException(status_code=400, detail="Text cannot be empty")
     if len(request.text) > 500:
         raise HTTPException(status_code=400, detail="Text is too long")
     try:
         # Generate speech waveform
         inputs = processor(text=request.text, return_tensors="pt")
         speaker_embeddings = torch.tensor(embeddings_dataset[7306]["xvector"]).unsqueeze(0)
         speech = model.generate_speech(inputs["input_ids"], speaker_embeddings, vocoder=vocoder)

         # Send speech waveform to WebSocket server
         asyncio.create_task(send_audio(speech))

         # Write speech waveform to WAV file
         now = datetime.now()
         timestamp = now.strftime("%Y%m%d_%H%M%S")
         output_file = f"speech_{timestamp}.wav"
         sf.write(output_file, speech.cpu().numpy(), 16000)

         # Return response with output text
         return {"result": "success", "output_text": request.text}

     except Exception as e:
         logger.exception(f"Error generating speech: {str(e)}")
         raise HTTPException(status_code=500, detail="Error generating speech")
