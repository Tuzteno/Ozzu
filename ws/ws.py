import asyncio
import logging
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FastAPI app")

app = FastAPI()

# Create two lists to store the WebSocket instances for each connected client.
clients = {
    "client1": None,
    "client2": None,
}


async def handle_client(websocket: WebSocket, client_name: str):
    """Handles a single client connection."""
    clients[client_name] = websocket
    logger.info(f"Client {client_name} connected.")
    try:
        while True:
            # Receive audio data from the connected client.
            data = await websocket.receive_bytes()
            # Relay the audio data to the other client.
            other_client = "client2" if client_name == "client1" else "client1"
            if clients[other_client]:
                await clients[other_client].send_bytes(data)
    except WebSocketDisconnect:
        logger.info(f"Client {client_name} disconnected.")
    finally:
        clients[client_name] = None


# Note that the verb is `websocket` here, not `get`, `post`, etc.
@app.websocket("/ws/{client_name}")
async def audio_endpoint(websocket: WebSocket, client_name: str):
    # Accept the connection from the client.
    await websocket.accept()
    try:
        await handle_client(websocket, client_name)
    except Exception as e:
        logger.exception(e)
        await websocket.close()
