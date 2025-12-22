from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Database URL - SQLite por defecto, fácil de cambiar a PostgreSQL en producción
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chalkin.db")

# Para SQLite necesitamos check_same_thread=False
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency para obtener la sesión de DB en los endpoints."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
