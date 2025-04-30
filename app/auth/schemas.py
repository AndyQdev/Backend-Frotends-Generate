from pydantic import BaseModel, EmailStr
from typing import Optional, List
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None
    telefono: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: str
    name: Optional[str]
    telefono: Optional[str]
    rol: str
    permisos: List[str]

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class SubUserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str]
    telefono: Optional[str]
    permisos: Optional[List[str]] = []
    proyectos_ids: Optional[List[int]] = [] 

class SubUserOut(BaseModel):
    id: int
    email: str
    name: Optional[str]
    telefono: Optional[str]
    rol: str = "colaborador"
    permisos: List[str] = []
    proyectos_ids: Optional[List[int]] = []

    class Config:
        from_attributes = True