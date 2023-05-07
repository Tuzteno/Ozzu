import os
from dotenv import load_dotenv
import aiohttp
from fastapi import FastAPI, HTTPException
import openai
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()

# Check if OPENAI_API_KEY environment variable is defined
if "OPENAI_API_KEY" not in os.environ:
    raise ValueError("OPENAI_API_KEY environment variable not defined")

# Set up OpenAI API
openai.api_key = os.environ["OPENAI_API_KEY"]
model_engine = os.environ.get("OPENAI_MODEL_ENGINE", "text-davinci-002")
max_tokens = int(os.environ.get("OPENAI_MAX_TOKENS", "1024"))
temperature = float(os.environ.get("OPENAI_TEMPERATURE", "0.7"))

# Create the FastAPI app
app = FastAPI()

# Define the request body schema
class InputText(BaseModel):
    text: str

# Define the endpoint to generate speech from the text
@app.post("/core")
async def synthesize(input_text: InputText):
    prompt = input_text.text

    # Send HTTP POST request to OpenAI API to generate text
    completions = openai.Completion.create(
        engine=model_engine,
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=temperature
    )
    # Get the first generated text choice
    generated_text = completions.choices[0].text.strip()

    # Send HTTP POST request to TTS component to synthesize audio from generated text
    async with aiohttp.ClientSession() as session:
        response = await session.post(
            f"http://tts:5001/synthesize",
            json={"text": generated_text},
        )
        response.raise_for_status()
        output_audio = await response.read()

    return {"audio": output_audio}