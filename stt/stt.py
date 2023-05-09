from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from transformers import Wav2Vec2ForCTC, Wav2Vec2Tokenizer
import torch
import io
import librosa

app = FastAPI()

# Load the pre-trained model and tokenizer
model = Wav2Vec2ForCTC.from_pretrained("jonatasgrosman/wav2vec2-large-xlsr-53-english")
tokenizer = Wav2Vec2Tokenizer.from_pretrained("jonatasgrosman/wav2vec2-large-xlsr-53-english")

# Set the device to use for the model (GPU if available, else CPU)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# Define error handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"message": "Invalid input"}
    )

@app.exception_handler(Exception)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"}
    )

# Define the WebSocket endpoint for speech-to-text transcription
@app.websocket("/transcribe")
async def transcribe_audio(websocket: WebSocket):
    await websocket.accept()

    while True:
        try:
            # Receive audio data from the client
            audio_bytes = await websocket.receive_bytes()

            # Convert the audio data to a format that can be processed by the model
            try:
                audio_input, _ = librosa.load(io.BytesIO(audio_bytes), sr=16000)
            except Exception:
                raise ValueError("Invalid audio file format")

            # Convert the audio data to a tensor and move it to the device
            audio_tensor = torch.tensor(audio_input).to(device)

            # Perform speech-to-text transcription using the model
            with torch.no_grad():
                transcription = model(audio_tensor.unsqueeze(0))[0]
                transcription = transcription.argmax(dim=-1).squeeze().tolist()
                transcription = tokenizer.decode(transcription)

            # Send the transcription to the client
            await websocket.send_json({"transcription": transcription})
        except WebSocketDisconnect:
            break
