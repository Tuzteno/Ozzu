from fastapi import FastAPI, File, HTTPException
from transformers import Wav2Vec2Processor, Wav2Vec2ForCTC
import torch
import soundfile as sf
import io

app = FastAPI()

# Load pre-trained model and tokenizer
processor = Wav2Vec2Processor.from_pretrained("openai/whisper-small")
model = Wav2Vec2ForCTC.from_pretrained("openai/whisper-small")

@app.post("/transcribe")
async def transcribe_audio(audio_file: bytes = File(...)):
    # Load audio
    try:
        # Convert bytes to a stream
        audio_stream = io.BytesIO(audio_file)
        # Load audio file with soundfile
        audio_input, sample_rate = sf.read(audio_stream)

        # Process the audio file
        inputs = processor(audio_input, sampling_rate=16_000, return_tensors="pt", padding=True)

        # Make a forward pass in the model
        with torch.no_grad():
            logits = model(inputs.input_values).logits

        # Take argmax of logits to get predicted ids and decode them.
        predicted_ids = torch.argmax(logits, dim=-1)
        transcription = processor.decode(predicted_ids[0])
        
        return {"transcription": transcription}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
