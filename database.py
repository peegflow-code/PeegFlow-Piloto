import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# =========================================================
# CONFIGURAÇÃO SEGURA VIA VARIÁVEIS DE AMBIENTE
# =========================================================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL não configurada no ambiente")

# =========================================================
# ENGINE
# =========================================================

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,     # Evita conexões mortas
    pool_recycle=300,       # Recicla conexões
    connect_args={"connect_timeout": 10},
)

# =========================================================
# SESSION
# =========================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

# =========================================================
# DEPENDÊNCIA DE BANCO (USO CORRETO)
# =========================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
