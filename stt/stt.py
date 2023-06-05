from fastapi import FastAPI, UploadFile, HTTPException, File
from speechbrain.pretrained import EncoderDecoderASR
from pydantic import BaseModel
import os

app = FastAPI()

class TranscriptionResponse(BaseModel):
    transcription: str

@app.on_event("startup")
async def startup_event():
    global asr_model
    asr_model = EncoderDecoderASR.from_hparams(source="speechbrain/asr-wav2vec2-commonvoice-en", savedir="pretrained_models/asr-wav2vec2-commonvoice-en")

@app.post("/transcribe/", response_model=TranscriptionResponse)
async def transcribe_audio(audio_file: UploadFile = File(...)):
    try:
        # Write out the audio file to disk
        with open(audio_file.filename, 'wb') as buffer:
            buffer.write(audio_file.file.read())

        # Transcribe the audio file
        transcription = asr_model.transcribe_file(audio_file.filename)

        # Delete the audio file from disk
        os.remove(audio_file.filename)

        return TranscriptionResponse(transcription=transcription)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
