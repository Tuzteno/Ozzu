import asyncio
import websockets
import soundfile as sf
import numpy as np

# Initialize a counter for file naming
file_counter = 0
connected_clients = set()

async def register_client(websocket):
    connected_clients.add(websocket)

async def unregister_client(websocket):
    connected_clients.remove(websocket)

async def send_to_all_clients(message, sender):
    for client in connected_clients:
        if client != sender:
            await client.send(message)

async def audio_handler(websocket, path):
    global file_counter  # Use the global counter
    await register_client(websocket)
    
    try:
        while True:
            audio_data = await websocket.recv()
            # Process audio_data as needed, e.g., save it to a file, perform further analysis, etc.
            print("Received audio data:", len(audio_data), "bytes")

            # Convert the audio data to 'float32'
            audio_data = np.frombuffer(audio_data, dtype='float32')

            # Generate a new file name with a consecutive number
            file_name = f"received_audio_{file_counter}.wav"

            # Save the audio data to the new file
            with sf.SoundFile(file_name, mode="w", samplerate=16000, channels=1, subtype="FLOAT") as f:
                f.write(audio_data)

            file_counter += 1  # Increment the counter

            # Broadcast the received audio to all other clients
            await send_to_all_clients(audio_data.tobytes(), websocket)

    except websockets.ConnectionClosedOK:
        print(f"WebSocket connection closed by the client: {websocket.remote_address}")
    except websockets.ConnectionClosedError:
        print(f"WebSocket connection closed unexpectedly: {websocket.remote_address}")
    finally:
        await unregister_client(websocket)

start_server = websockets.serve(audio_handler, "localhost", 8765)  # WebSocket server listens on localhost:8765

async def main():
    await start_server
    await asyncio.Future()  # Keep the server running indefinitely

asyncio.get_event_loop().run_until_complete(main())
