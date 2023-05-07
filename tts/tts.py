import pybase64
import logging
import asyncio
from datetime import datetime
from aiohttp import request
import pika
import json
import torch
import soundfile as sf
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
from datasets import load_dataset
import numpy as np

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

        # Send speech waveform to RabbitMQ message queue
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
        channel = connection.channel()
        channel.queue_declare(queue='speech_queue', durable=True)
        speech_base64 = pybase64.b64encode(speech.numpy())
        channel.basic_publish(exchange='', routing_key='speech_queue', body=json.dumps(speech_base64.decode()))

        output_text = request.text

        # Return response with output text
        return {"result": "success", "output_text": output_text}
    except Exception as e:
        logger.exception(f"Error generating speech: {str(e)}")
        raise HTTPException(status_code=500, detail="Error generating speech")

@app.websocket("/stream")
async def stream(websocket: WebSocket):
    await websocket.accept()

    # Connect to RabbitMQ message queue
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
    channel = connection.channel()
    channel.queue_declare(queue='speech_queue', durable=True)

    try:
        while True:
            # Consume speech waveform messages from RabbitMQ message queue
            method_frame, header_frame, body = channel.basic_get(queue='speech_queue')
            if method_frame:
                chunk_size = 8000  # Number of bytes to send in each chunk
                speech_base64 = json.loads(body)
                speech = np.frombuffer(pybase64.b64decode(speech_base64.encode()), dtype=np.float32)
                for i in range(0, len(speech), chunk_size):
                    chunk = speech[i:i+chunk_size].tobytes()
                    await websocket.send_bytes(chunk)
                    await asyncio.sleep(0.01)  # Add a small delay to reduce CPU usage
                channel.basic_ack(delivery_tag=method_frame.delivery_tag)

    except WebSocketDisconnect:
        pass
    finally:
        connection.close()

@app.middleware("http")
async def set_csp_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = "script-src 'self' blob: filesystem:; object-src 'none';"
    return response
