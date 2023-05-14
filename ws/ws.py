from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from starlette.websockets import WebSocketDisconnect
import socketio
import asyncio
import uvicorn
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from fastapi import WebSocket, WebSocketDisconnect
import manager

app = FastAPI()

# Configure static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Configure SocketIO server
sio = socketio.AsyncServer(async_mode="asgi")
app.mount("/", socketio.ASGIApp(sio))


# Define WebRTC signaling
async def on_offer(sid, data):
    await sio.emit("offer", data, room=data["room"], skip_sid=sid)


async def on_answer(sid, data):
    await sio.emit("answer", data, room=data["room"], skip_sid=sid)


async def on_ice(sid, data):
    await sio.emit("ice", data, room=data["room"], skip_sid=sid)


@sio.event
async def connect(sid, environ):
    print(f"Client {sid} connected to server")


@sio.event
async def join(sid, data):
    room = data["room"]
    username = data["username"]
    await sio.enter_room(sid, room)
    await sio.emit(
        "join",
        {"username": username},
        room=room,
        skip_sid=sid,
    )


@sio.event
async def offer(sid, data):
    await on_offer(sid, data)


@sio.event
async def answer(sid, data):
    await on_answer(sid, data)


@sio.event
async def ice(sid, data):
    await on_ice(sid, data)


@sio.event
async def disconnect(sid):
    for room in sio.rooms(sid):
        await sio.leave_room(sid, room)
    print(f"Client {sid} disconnected from server")


# Define WebRTC media streaming
class VideoTrack(VideoStreamTrack):
    def __init__(self, video_path):
        super().__init__()
        self.video_path = video_path

    async def recv(self):
        # Read a frame from the video stream
        data = self.video_path.read_video_frame()
        if data is not None:
            # Convert the frame to bytes
            frame = data.to_ndarray(format="rgb24")
            frame_bytes = frame.tobytes()

            # Return a video frame in RTP format
            pts, time_base = await self.next_timestamp()
            return self.frame_from_bytes(frame_bytes, timestamp=pts, time_base=time_base)
        else:
            return None

@app.websocket("/video_feed/{room}")
async def video_feed(request: Request, websocket: WebSocketDisconnect):
    await manager.connect(websocket)
    await websocket.send_json({"type": "connected"})

    try:
        while True:
            data = await websocket.receive_json()

            if data["type"] == "join":
                username = data["username"]
                room = data["room"]

                await manager.join_room(websocket, room, username)
                await manager.send_to_room(
                    room,
                    {"type": "join", "username": username},
                    exclude=[websocket],
                )

            elif data["type"] == "leave":
                username = data["username"]
                room = data["room"]

                await manager.leave_room(websocket, room, username)
                await manager.send_to_room(
                    room,
                    {"type": "leave", "username": username},
                    exclude=[websocket],
                )

            elif data["type"] == "offer":
                await manager.send_to_room(
                    data["room"],
                    {"type": "offer", "data": data["data"]},
                    exclude=[websocket],
                )

            elif data["type"] == "answer":
                await manager.send_to_room(
                    data["room"],
                    {"type": "answer", "data": data["data"]},
                    exclude=[websocket],
                )

            elif data["type"] == "ice":
                await manager.send_to_room(
                    data["room"],
                    {"type": "ice", "data": data["data"]},
                    exclude=[websocket],
                )

            else:
                print(f"Invalid message type {data['type']}")
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
