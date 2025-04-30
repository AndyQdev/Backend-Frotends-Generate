from app.database import SessionLocal
from app.models.models import Permiso

def inicializar_permisos():
    db = SessionLocal()

    permisos = ["ver_proyecto", "editar_proyecto", "eliminar_proyecto", "invitar_colaboradores", "crear_interfaz"]

    for nombre in permisos:
        if not db.query(Permiso).filter_by(nombre=nombre).first():
            db.add(Permiso(nombre=nombre))
    
    db.commit()
    db.close()

if __name__ == "__main__":
    inicializar_permisos()
    print("✅ Permisos inicializados.")
