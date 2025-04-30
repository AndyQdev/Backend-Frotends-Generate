from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship, declarative_base
from app.database import Base
from datetime import datetime
# Base = declarative_base()

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    is_main = Column(Boolean, default=True)  # True = usuario principal
    parent_user_id = Column(Integer, ForeignKey('usuarios.id'), nullable=True)
    name = Column(String, nullable=True)
    telefono = Column(String, nullable=True)

    proyectos = relationship("Proyecto", back_populates="owner")
    subusuarios = relationship("Usuario")  # hijos de este usuario
    colaboraciones = relationship("ColaboradorProyecto", back_populates="usuario")


class Proyecto(Base):
    __tablename__ = "proyectos"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    descripcion = Column(String, nullable=True)  # ✅ AGREGA ESTA LÍNEA
    status = Column(String, nullable=True)  # ✅ AGREGA ESTA LÍNEA
    last_modified = Column(
        DateTime,
        default=datetime.utcnow,           # al crear
        onupdate=datetime.utcnow,          # al modificar
        nullable=False
    )
    create_date = Column(DateTime, default=datetime.utcnow)
    owner_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    owner = relationship("Usuario", back_populates="proyectos")
    # pages = relationship("Page", back_populates="proyecto", cascade="all, delete-orphan")
    pages = relationship(
        "Page",
        back_populates="proyecto",
        cascade="all, delete-orphan",
        order_by="Page.order"          # ← aquí
    )
    colaboradores = relationship("ColaboradorProyecto", back_populates="proyecto")


class ColaboradorProyecto(Base):
    __tablename__ = "colaboradores_proyecto"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'))
    proyecto_id = Column(Integer, ForeignKey('proyectos.id'))
    permisos = Column(String, default="ver")  # puede ser 'ver', 'editar', etc

    usuario = relationship("Usuario", back_populates="colaboraciones")
    proyecto = relationship("Proyecto", back_populates="colaboradores")
    permisos_asignados = relationship("PermisoColaborador", back_populates="colaborador", cascade="all, delete")

class Permiso(Base):
    __tablename__ = "permisos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, nullable=False)  # Ej: 'ver_proyecto'


class PermisoColaborador(Base):
    __tablename__ = "permisos_colaborador"

    id = Column(Integer, primary_key=True, index=True)
    colaborador_id = Column(Integer, ForeignKey('colaboradores_proyecto.id'))
    permiso_id = Column(Integer, ForeignKey('permisos.id'))

    colaborador = relationship("ColaboradorProyecto", back_populates="permisos_asignados")
    permiso = relationship("Permiso")

class Page(Base):
    __tablename__ = "pages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    order = Column(Integer, nullable=False)
    background_color = Column(String, default="#ffffff")
    grid_enabled = Column(Boolean, default=False)
    device_mode = Column(String, default="desktop")
    proyecto_id = Column(Integer, ForeignKey("proyectos.id"), nullable=False)
    components = Column(JSON, default=[])  # Ahora guardamos todos los componentes como JSON

    proyecto = relationship("Proyecto", back_populates="pages")

# class Component(Base):
#     __tablename__ = "components"

#     id = Column(Integer, primary_key=True, index=True)
#     type = Column(String, nullable=False)
#     x = Column(Integer, nullable=False)
#     y = Column(Integer, nullable=False)
#     width = Column(Integer, nullable=False)
#     height = Column(Integer, nullable=False)
#     z_index = Column(Integer, default=1)
#     is_locked = Column(Boolean, default=False)
#     properties = Column(String, default="{}")  # Usa JSON si lo prefieres
#     styles = Column(String, default="{}")

#     page_id = Column(Integer, ForeignKey("pages.id"), nullable=False)
#     page = relationship("Page", back_populates="components")