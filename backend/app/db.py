import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def _database_url() -> str:
    """DATABASE_URL, or (on AWS) the parts injected separately from the RDS-managed secret, so the password is never
    written into a URL by hand."""
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    if os.getenv("DB_HOST"):
        user, password = quote_plus(os.environ["DB_USER"]), quote_plus(os.environ["DB_PASSWORD"])
        return (f"postgresql+psycopg://{user}:{password}@{os.environ['DB_HOST']}:{os.getenv('DB_PORT', '5432')}/"
                f"{os.getenv('DB_NAME', 'obras')}?sslmode=require")
    return "sqlite+pysqlite:///./local-dev.db"


DATABASE_URL = _database_url()
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    with SessionLocal() as session:
        yield session
