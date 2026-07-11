from sqlalchemy import Column, Integer, String, Boolean, DateTime
from database import Base
import datetime

class RSVP(Base):
    __tablename__ = "rsvps"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    phone = Column(String)
    attending = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Wish(Base):
    __tablename__ = "wishes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    message = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Photo(Base):
    __tablename__ = "gallery"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    is_approved = Column(Boolean, default=False) # افتراضياً الصورة مخفية حتى توافقي عليها
    created_at = Column(DateTime, default=datetime.datetime.utcnow)