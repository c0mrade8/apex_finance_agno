from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set. Check your .env file.")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=60, pool_size=5, max_overflow=10, connect_args={
        "connect_timeout": 5,
        # "keepalives": 1,
        # "keepalives_idle": 30,
        # "keepalives_interval": 10,
        # "keepalives_count": 5,
    })

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()