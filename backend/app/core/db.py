from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings


engine = create_engine(str(settings.SQL_ALCHEMY_URI), echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)