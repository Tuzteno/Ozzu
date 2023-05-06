import logging
import asyncio
from datetime import datetime
from aiohttp import request

import torch
import soundfile as sf
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
from datasets import load_dataset

app = FastAPI()
logger = logging.getLogger(__name__)

processor = SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")
model = SpeechT5ForTextToSpeech.from_pretrained("microsoft/speecht5_tts")
vocoder = SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan")

# Load the dataset at startup
embeddings_dataset = load_dataset("Matthijs/cmu-arctic-xvectors", split="validation")

class TextRequest(BaseModel):
    text: str

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

        # Save speech waveform to file
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")
        file_name = f"speech_{timestamp}.wav"
        with open(file_name, mode="wb") as file:
            sf.write(file, speech.numpy(), samplerate=16000)

        output_text = request.text

        # Return response with file name and output text
        return {"result": "success", "file_name": file_name, "output_text": output_text}
    except Exception as e:
        logger.exception(f"Error generating speech: {str(e)}")
        raise HTTPException(status_code=500, detail="Error generating speech")

@app.websocket("/stream")
async def stream(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Wait for a text message from the client
            text_message = await websocket.receive_text()

            # Generate speech waveform for the received text message
            inputs = processor(text=text_message, return_tensors="pt")
            speaker_embeddings = torch.tensor(embeddings_dataset[7306]["xvector"]).unsqueeze(0)
            speech = model.generate_speech(inputs["input_ids"], speaker_embeddings, vocoder=vocoder)

            # Send speech waveform to client in chunks
            chunk_size = 8000  # Number of bytes to send in each chunk
            for i in range(0, len(speech), chunk_size):
                chunk = speech.numpy()[i:i+chunk_size].tobytes()
                await websocket.send_binary(chunk)
                await asyncio.sleep(0.01)  # Add a small delay to reduce CPU usage

    except WebSocketDisconnect:
        pass
