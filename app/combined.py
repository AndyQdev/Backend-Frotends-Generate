# app/combined.py
from fastapi import FastAPI
from app.main import app as api   # ← tu API REST original
from app.sockets.realtime import sio, socket_app

# socket_app es un `ASGIApp`, así que lo montamos:
api.mount("/ws", socket_app)      #  → tus sockets ahora viven en /ws

asgi = api 