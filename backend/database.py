import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# We will look for an environment variable called DATABASE_URL.
# If you are using MySQL, your .env should look like this:
# DATABASE_URL=mysql+pymysql://username:password@localhost/fixmyhyd
# 
# For now, if no .env is set, we fallback to a local SQLite for immediate testing without errors.
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./fixmyhyd_fastapi.db"
)

# Connect args specific to SQLite to avoid thread issues. Ignored by MySQL.
connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get the database session in FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
