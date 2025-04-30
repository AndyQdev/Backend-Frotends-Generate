from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os

# 🚨 Configura tu URL de PostgreSQL aquí
# DATABASE_URL = os.getenv("DATABASE_URL", DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/backend_app")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/backend_app")


# Crear engine
engine = create_engine(DATABASE_URL, echo=True)

# Sesión de base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para heredar
Base = declarative_base()
