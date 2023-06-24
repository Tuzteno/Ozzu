from fastapi import FastAPI, File
from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
from datasets import load_dataset
import torch
import soundfile as sf
import shutil
import os

from tasks import run_ffmpeg

app = FastAPI()

processor = SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")
model = SpeechT5ForTextToSpeech.from_pretrained("microsoft/speecht5_tts")
vocoder = SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan")

embeddings_dataset = load_dataset("Matthijs/cmu-arctic-xvectors", split="validation")

@app.post("/tts")
async def text_to_speech(text: str):
    inputs = processor(text=text, return_tensors="pt")
    speaker_embeddings = torch.tensor(embeddings_dataset[7306]["xvector"]).unsqueeze(0)

    speech = model.generate_speech(inputs["input_ids"], speaker_embeddings, vocoder=vocoder)

    audio_path = "speech.wav"
    sf.write(audio_path, speech.numpy(), samplerate=16000)

    # Create HLS segments
    segments_path = "segments"
    os.makedirs(segments_path, exist_ok=True)

    # Convert the audio file into HLS segments
    cmd = f"ffmpeg -i {audio_path} -c:a libfdk_aac -b:a 128k -f segment -segment_time 10 {segments_path}/output%03d.aac"
    run_ffmpeg.delay(cmd)

    # Generate HLS playlist (M3U8 file)
    playlist_path = "playlist.m3u8"
    with open(playlist_path, "w") as playlist_file:
        playlist_file.write("#EXTM3U\n")
        playlist_file.write("#EXT-X-VERSION:3\n")
        playlist_file.write("#EXT-X-TARGETDURATION:10\n")
        playlist_file.write("#EXT-X-MEDIA-SEQUENCE:0\n")
        segment_files = sorted(os.listdir(segments_path))
        for i, segment_file in enumerate(segment_files):
            playlist_file.write(f"#EXTINF:10.0,\n")
            playlist_file.write(f"{segments_path}/{segment_file}\n")
        playlist_file.write("#EXT-X-ENDLIST\n")

    return {"url": f"http://your-server-address/{playlist_path}"}

@app.get("/audio/{audio_file}")
async def get_audio(audio_file: str):
    return File(audio_file)

@app.on_event("startup")
async def startup_event():
    # Clean up any previous audio files and segments
    if os.path.exists("speech.wav"):
        os.remove("speech.wav")
    if os.path.exists("segments"):
        shutil.rmtree("segments")
    if os.path.exists("playlist.m3u8"):
        os.remove("playlist.m3u8")
