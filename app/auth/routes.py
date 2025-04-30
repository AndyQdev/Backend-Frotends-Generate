from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.models import Usuario, ColaboradorProyecto, Permiso
from app.auth.schemas import UserCreate, UserLogin, UserOut, Token, SubUserOut
from app.auth.auth_utils import hash_password, verify_password, create_access_token
from app.auth.dependencies import get_current_user
from app.auth.schemas import SubUserCreate
from app.schemas.auth import LoginRequest
from app.models.models import Proyecto  # Asegúrate de importar esto
from typing import Dict
router = APIRouter(prefix="/auth", tags=["auth"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(Usuario).filter(Usuario.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email ya registrado")

    new_user = Usuario(
        email=user.email,
        password=hash_password(user.password),
        name=user.name,
        telefono=user.telefono
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Devuelve los mismos datos que /login
    rol = "admin"
    permisos = [p.nombre for p in db.query(Permiso).all()]
    colaboradores = db.query(Usuario).filter(Usuario.parent_user_id == new_user.id).all()
    colaboradores_data = [{"id": c.id, "email": c.email} for c in colaboradores]

    token = create_access_token({"sub": str(new_user.id)})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "name": new_user.name,
            "telefono": new_user.telefono,
            "rol": rol,
            "permisos": permisos,
            "colaboradores": colaboradores_data
        }
    }


@router.post("/login")
async def login(user_data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.email == user_data.email).first()
    if not user or not verify_password(user_data.password, user.password):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    if user.is_main:
        rol = "admin"
        permisos = [p.nombre for p in db.query(Permiso).all()]
        colaboradores = db.query(Usuario).filter(Usuario.parent_user_id == user.id).all()
        colaboradores_data = [{"id": c.id, "email": c.email} for c in colaboradores]
        relacion_extra = {"colaboradores": colaboradores_data}
    else:
        rol = "colaborador"
        colaborador = db.query(ColaboradorProyecto).filter_by(usuario_id=user.id).first()
        permisos = [p.permiso.nombre for p in colaborador.permisos_asignados] if colaborador else []
        admin = db.query(Usuario).filter(Usuario.id == user.parent_user_id).first()
        admin_data = {"id": admin.id, "email": admin.email} if admin else None
        relacion_extra = {"admin": admin_data}

    token = create_access_token({"sub": str(user.id)})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "rol": rol,
            "permisos": permisos,
            **relacion_extra
        }
    }

@router.post("/subuser", response_model=Dict[str, SubUserOut])
def create_subuser(
    subuser: SubUserCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    if not current_user.is_main:
        raise HTTPException(status_code=403, detail="No autorizado para crear colaboradores")

    if db.query(Usuario).filter(Usuario.email == subuser.email).first():
        raise HTTPException(status_code=400, detail="Email ya registrado")

    # ✅ Crear el subusuario
    new_subuser = Usuario(
        email=subuser.email,
        password=hash_password(subuser.password),
        name=subuser.name,
        telefono=subuser.telefono,
        is_main=False,
        parent_user_id=current_user.id
    )
    db.add(new_subuser)
    db.commit()
    db.refresh(new_subuser)

    # ✅ Si llegan proyectos, asignarlos
    from app.models.models import Permiso, PermisoColaborador, ColaboradorProyecto, Proyecto

    if subuser.proyectos_ids:
        for proyecto_id in subuser.proyectos_ids:
            proyecto = db.query(Proyecto).filter_by(id=proyecto_id, owner_id=current_user.id).first()
            if proyecto:
                relacion = ColaboradorProyecto(
                    usuario_id=new_subuser.id,
                    proyecto_id=proyecto.id
                )
                db.add(relacion)
                db.commit()
                db.refresh(relacion)

                # 🎯 Asignar permisos si llegan
                for permiso_nombre in subuser.permisos:
                    permiso = db.query(Permiso).filter(Permiso.nombre == permiso_nombre).first()
                    if permiso:
                        db.add(PermisoColaborador(
                            colaborador_id=relacion.id,
                            permiso_id=permiso.id
                        ))
                db.commit()

    return {
        "data": {
            "id": new_subuser.id,
            "email": new_subuser.email,
            "name": new_subuser.name,
            "telefono": new_subuser.telefono,
            "rol": "colaborador",
            "permisos": [],
            "proyectos_ids": subuser.proyectos_ids,
        }
    }


@router.get("/check-token")
async def check_token_endpoint(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.models.models import ColaboradorProyecto, Permiso, Usuario

    if current_user.is_main:
        rol = "admin"
        permisos = [p.nombre for p in db.query(Permiso).all()]
        colaboradores = db.query(Usuario).filter(Usuario.parent_user_id == current_user.id).all()
        colaboradores_data = [{"id": c.id, "email": c.email} for c in colaboradores]
        return {
            "id": current_user.id,
            "email": current_user.email,
            "rol": rol,
            "permisos": permisos,
            "colaboradores": colaboradores_data
        }

    else:
        rol = "colaborador"
        colaborador = db.query(ColaboradorProyecto).filter_by(usuario_id=current_user.id).first()
        permisos = [p.permiso.nombre for p in colaborador.permisos_asignados] if colaborador else []
        admin = db.query(Usuario).filter(Usuario.id == current_user.parent_user_id).first()
        admin_data = {"id": admin.id, "email": admin.email} if admin else None

        return {
            "id": current_user.id,
            "email": current_user.email,
            "rol": rol,
            "permisos": permisos,
            "admin": admin_data
        }
    
@router.get("/user/{user_id}")
def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if user.is_main:
        rol = "admin"
        permisos = [p.nombre for p in db.query(Permiso).all()]
        colaboradores = db.query(Usuario).filter(Usuario.parent_user_id == user.id).all()
        # colaboradores_data = [{"id": c.id, "email": c.email, "name": c.name} for c in colaboradores]
        colaboradores_data = []
        for c in colaboradores:
            proyectos_asignados = [
                {
                    "id": rel.proyecto.id,
                    "name": rel.proyecto.name,
                    "descripcion": rel.proyecto.descripcion
                }
                for rel in c.colaboraciones
            ]
            colaboradores_data.append({
                "id": c.id,
                "email": c.email,
                "name": c.name,
                "telefono": c.telefono,
                "proyectos": proyectos_asignados
            })
        return {
            "data": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "telefono": user.telefono,
                "rol": rol,
                "permisos": permisos,
                "colaboradores": colaboradores_data
            }
        }

    else:
        rol = "colaborador"
        colaborador = db.query(ColaboradorProyecto).filter_by(usuario_id=user.id).first()
        permisos = [p.permiso.nombre for p in colaborador.permisos_asignados] if colaborador else []

        admin = db.query(Usuario).filter(Usuario.id == user.parent_user_id).first()

        return {
            "data": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "telefono": user.telefono,
                "rol": rol,
                "permisos": permisos,
                "admin": {
                    "id": admin.id,
                    "email": admin.email,
                    "name": admin.name
                } if admin else None
            }
        }