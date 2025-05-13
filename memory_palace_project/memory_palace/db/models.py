from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from . import Base

class MemoryPalace(Base):
    __tablename__ = 'memory_palaces'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    description = Column(Text)
    created_at = Column(DateTime)

class Timeline(Base):
    __tablename__ = 'timelines'
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    palace_id = Column(Integer, ForeignKey('memory_palaces.id'))
    order = Column(Integer)

class MemoryObject(Base):
    __tablename__ = 'memory_objects'
    id = Column(Integer, primary_key=True)
    title = Column(String(200))
    content = Column(Text)
    timeline_id = Column(Integer, ForeignKey('timelines.id'))
    position = Column(Integer)