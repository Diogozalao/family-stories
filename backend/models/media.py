from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Enum, Text, Boolean
from sqlalchemy.orm import DeclarativeBase
from datetime import UTC, datetime
import enum

class Base(DeclarativeBase):
    pass

class MediaType(str, enum.Enum):
    PHOTO = "photo"
    VIDEO = "video"
    DOCUMENT = "document"
    GEDCOM = "gedcom"

class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class MediaFile(Base):
    __tablename__ = "media_files"

    id = Column(Integer, primary_key=True, index=True)
    
    # Ficheiro
    original_filename = Column(String(255), nullable=False)
    stored_filename   = Column(String(255), nullable=False, unique=True)
    file_path         = Column(String(500), nullable=False)
    file_size         = Column(Integer)
    mime_type         = Column(String(100))
    media_type        = Column(Enum(MediaType), nullable=False)
    
    # Metadados EXIF
    date_taken        = Column(DateTime, nullable=True)
    latitude          = Column(Float, nullable=True)
    longitude         = Column(Float, nullable=True)
    location_name     = Column(String(255), nullable=True)
    camera_make       = Column(String(100), nullable=True)
    camera_model      = Column(String(100), nullable=True)
    
    # Análise IA (Gemini Vision)
    ai_description    = Column(Text, nullable=True)
    ai_people_count   = Column(Integer, nullable=True)
    ai_setting        = Column(String(255), nullable=True)
    ai_emotion        = Column(String(100), nullable=True)
    ai_tags           = Column(JSON, nullable=True)
    ai_narrative_hint = Column(Text, nullable=True)
    
    # OCR (documentos)
    ocr_text          = Column(Text, nullable=True)
    
    # Segurança
    is_safe           = Column(Boolean, default=True)
    checksum_md5      = Column(String(32), nullable=True)
    
    # Metadados completos em bruto
    raw_exif          = Column(JSON, nullable=True)
    
    # Estado
    status            = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING)
    error_message     = Column(Text, nullable=True)
    
    # Timestamps
    created_at        = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at        = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
