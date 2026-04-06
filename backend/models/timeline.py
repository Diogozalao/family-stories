from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from backend.models.media import Base
from datetime import datetime
import enum

class ConfidenceLevel(str, enum.Enum):
    HIGH   = "high"    # data exata do EXIF
    MEDIUM = "medium"  # estimada pelo Gemini
    LOW    = "low"     # desconhecida, inferida

class Person(Base):
    __tablename__ = "persons"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String(255), nullable=False)
    birth_date   = Column(DateTime, nullable=True)
    death_date   = Column(DateTime, nullable=True)
    birth_place  = Column(String(255), nullable=True)
    notes        = Column(Text, nullable=True)
    gedcom_id    = Column(String(100), nullable=True)  # ID do ficheiro GEDCOM
    created_at   = Column(DateTime, default=datetime.utcnow)

class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id               = Column(Integer, primary_key=True, index=True)
    
    # Quando
    event_date       = Column(DateTime, nullable=True)
    date_confidence  = Column(Enum(ConfidenceLevel), default=ConfidenceLevel.LOW)
    date_label       = Column(String(100), nullable=True)  # ex: "Anos 80", "Verão 1995"
    
    # O quê
    event_type       = Column(String(50), nullable=True)   # nascimento, casamento, viagem...
    title            = Column(String(255), nullable=True)
    description      = Column(Text, nullable=True)
    location         = Column(String(255), nullable=True)
    latitude         = Column(Float, nullable=True)
    longitude        = Column(Float, nullable=True)
    
    # Ligação ao media
    media_file_id    = Column(Integer, ForeignKey("media_files.id"), nullable=True)
    
    # Pessoas envolvidas (JSON com IDs)
    person_ids       = Column(JSON, default=list)
    
    # Ordem na timeline
    sort_order       = Column(Integer, default=0)
    
    created_at       = Column(DateTime, default=datetime.utcnow)
