from transformers import VitsModel, AutoTokenizer
import torch
import random
import asyncio
import websockets

# Function to set seed for reproducibility
def set_seed(seed):
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    random.seed(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

# Set the seed for reproducibility
set_seed(555)

model = VitsModel.from_pretrained("facebook/mms-tts-eng")
tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-eng")

# List of texts to convert to waveforms and send via WebSocket
texts = ["Your login session has expired Please login again"]

async def send_audio_via_websocket():
    async with websockets.connect("ws://localhost:8765") as websocket:  # Replace with your WebSocket server URL
        for text in texts:
            inputs = tokenizer(text, return_tensors="pt")
            with torch.no_grad():
                waveform = model(**inputs).waveform.cpu().numpy()[0]

            # Add a debug statement to print the data type of waveform
            print("Data type of waveform:", waveform.dtype)

            await websocket.send(waveform.tobytes())

asyncio.get_event_loop().run_until_complete(send_audio_via_websocket())
