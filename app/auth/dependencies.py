from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.models import Usuario
from app.auth.auth_utils import decode_token
from app.models.models import ColaboradorProyecto

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Usuario:
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

    user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user

def verificar_permiso(usuario: Usuario, permiso_nombre: str, db: Session) -> bool:
    if usuario.is_main:
        return True  # Admin tiene todos los permisos

    colaborador = db.query(ColaboradorProyecto).filter_by(usuario_id=usuario.id).first()
    if not colaborador:
        return False

    permisos = [p.permiso.nombre for p in colaborador.permisos_asignados]
    return permiso_nombre in permisos
