from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from sqlalchemy import Integer, String, DateTime, ARRAY, Float, ForeignKey, URL, select, func
from typing import Optional, List
from datetime import datetime

class Base(DeclarativeBase):
    pass

class Event(Base):
    __tablename__ = "events"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement="auto")
    title: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(String)
    start_date: Mapped[datetime] = mapped_column(DateTime)
    end_date: Mapped[datetime] = mapped_column(DateTime)
    latitude: Mapped[float] = mapped_column(Float)
    longitude:Mapped[float]=mapped_column(Float)
    author: Mapped[str] = mapped_column(String)
    keywords: Mapped[List["Keyword"]] = relationship("Keyword", back_populates="event")
    source:Mapped[str]=mapped_column(String)
    
class Keyword(Base):
    __tablename__ = "keywords"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement="auto")
    name: Mapped[str] = mapped_column(String)
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("events.id"))
    event: Mapped["Event"] = relationship("Event", back_populates="keywords")
