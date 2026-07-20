import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Lê a URL da nuvem das variáveis de ambiente
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///:memory:"  # Valor padrão caso esteja rodando localmente sem .env
)

# Se a URL começar com 'postgres://', corrige para 'postgresql://' (exigência do SQLAlchemy)
if SQLALCHEMY_DATABASE_URL.startswith("postgresql://postgres:[Gabinete#$10]@db.skhxtfrmtalbtdsrsvuz.supabase.co:5432/postgres"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# O argumento 'check_same_thread' só é usado no SQLite, por isso a condicional
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()