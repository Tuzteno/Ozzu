import asyncio
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FastAPI app")

app = FastAPI()

# Maintain a list of connected clients.
connected_clients = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Accept the connection from a client.
    await websocket.accept()

    # Add the client to the list of connected clients.
    connected_clients.append(websocket)

    try:
        while True:
            # Receive data sent by a client.
            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                # WebSocket connection closed by the client.
                connected_clients.remove(websocket)
                logger.info(f"A client disconnected. {len(connected_clients)} client(s) remaining.")
                break

            if message["type"] == "websocket.receive":
                # Process the received message.
                if message.get("text"):
                    # Send the text message to all other clients.
                    for client in connected_clients:
                        if client != websocket:
                            await client.send_text(message["text"])
                elif message.get("bytes"):
                    # Send the binary data to all other clients.
                    for client in connected_clients:
                        if client != websocket:
                            await client.send_bytes(message["bytes"])
                else:
                    logger.warning("Received message without 'text' or 'bytes' field.")

    except WebSocketDisconnect:
        # WebSocket connection closed unexpectedly.
        connected_clients.remove(websocket)
        logger.info(f"A client disconnected unexpectedly. {len(connected_clients)} client(s) remaining.")
