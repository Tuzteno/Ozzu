from fastapi import FastAPI, UploadFile, HTTPException, File
from pydantic import BaseModel
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
import torchaudio
import torch

# Load the pre-trained model and the tokenizer
processor = Wav2Vec2Processor.from_pretrained("openai/whisper-tiny.en")
model = Wav2Vec2ForCTC.from_pretrained("openai/whisper-tiny.en")

app = FastAPI()

# Define a response model
class ASRResponse(BaseModel):
    text: str

@app.post("/asr", response_model=ASRResponse)
async def asr(file: UploadFile = File(...)):
    # Check file format
    if file.filename.split(".")[-1] != "wav":
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload a .wav file.")
    
    # Load audio
    try:
        speech, _ = torchaudio.load(file.file)
        # Ensure mono audio
        if speech.shape[0] > 1:
            speech = speech.mean(dim=0)
        # Convert tensor to 1D numpy array
        speech = speech.numpy()[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Unable to load audio file.")
    
    # Preprocess audio
    inputs = processor(speech, return_tensors="pt", padding=True, sampling_rate=16000)

    # Make prediction
    with torch.no_grad():
        logits = model(inputs.input_values).logits

    # Decode predicted id into text
    predicted_ids = torch.argmax(logits, dim=-1)
    transcription = processor.decode(predicted_ids[0])

    # Return transcription
    return {"text": transcription}
