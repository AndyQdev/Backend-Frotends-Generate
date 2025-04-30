from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Proyecto(Base):
    __tablename__ = "proyectos"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    descripcion = Column(String, nullable=True)
    status = Column(String, nullable=True)
    create_date = Column(DateTime, default=datetime.utcnow)
    last_modified = Column(
        DateTime,
        default=datetime.utcnow,           # al crear
        onupdate=datetime.utcnow,          # al modificar
        nullable=False
    )
    owner_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    pages = relationship("Page", back_populates="proyecto", cascade="all, delete-orphan")


class Page(Base):
    __tablename__ = "pages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    order = Column(Integer, nullable=False)
    background_color = Column(String, default="#ffffff")
    grid_enabled = Column(Boolean, default=False)
    device_mode = Column(String, default="desktop")

    proyecto_id = Column(Integer, ForeignKey("proyectos.id"), nullable=False)
    proyecto = relationship("Proyecto", back_populates="pages")
    components = relationship("Component", back_populates="page", cascade="all, delete-orphan")


class Component(Base):
    __tablename__ = "components"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)
    x = Column(Integer, nullable=False)
    y = Column(Integer, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    z_index = Column(Integer, default=1)
    is_locked = Column(Boolean, default=False)
    properties = Column(JSON, default={})  # para label, placeholder, etc.
    styles = Column(JSON, default={})  # para Tailwind o estilos

    page_id = Column(Integer, ForeignKey("pages.id"), nullable=False)
    page = relationship("Page", back_populates="components")
