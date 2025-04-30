from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.auth.routes import router as auth_router
from app.routes import proyectos

app = FastAPI()

origins = [
    "http://localhost:5173",  # Frontend local
    # "https://tu-dominio.com",  # Producción si aplica
]
# Permitir peticiones del frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],  # permite todos los métodos (GET, POST, etc)
    allow_headers=["*"],  # permite todos los headers
)

app.include_router(auth_router)
app.include_router(proyectos.router)
from app.sockets.realtime import socket_app  
app.mount("/ws", socket_app)    