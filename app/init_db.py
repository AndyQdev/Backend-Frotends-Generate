from app.database import engine
from app.models.models import Base

print("⏳ Creando tablas...")
Base.metadata.create_all(bind=engine)
print("✅ Tablas creadas exitosamente.")
