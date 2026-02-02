"""
Configuración de Base de Datos - Control de Patio
La conexión se configura automáticamente desde variables de entorno
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ========================================
# 🔧 CONFIGURACIÓN DE BASE DE DATOS
# ========================================
# En producción (Railway/Render): Se usa DATABASE_URL automáticamente
# En local: Crea un archivo .env o configura la variable de entorno

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://usuario:password@localhost:5432/patio_control")

# Railway usa postgres:// pero SQLAlchemy necesita postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
