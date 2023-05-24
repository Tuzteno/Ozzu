import uvicorn
from fastapi import FastAPI, HTTPException
from transformers import Wav2Vec2ForCTC

app = FastAPI()

model = Wav2Vec2ForCTC.from_pretrained("voidful/wav2vec2-xlsr-multilingual-56")

@app.post("/transcription")
async def convert_audio_to_text(file: UploadFile):
    """Converts an audio file to text.

    Args:
        file: The audio file to convert.

    Returns:
        The transcript of the audio file.

    """
    # Load the audio file.
    try:
        audio = await file.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found.")

    # Convert the audio to text.
    try:
        transcript = model.predict(audio)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Return the transcript.
    return {"transcript": transcript}

