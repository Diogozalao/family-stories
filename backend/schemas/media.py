from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from backend.models.media import MediaType, ProcessingStatus

class MediaFileResponse(BaseModel):
    id: int
    original_filename: str
    media_type: MediaType
    file_size: Optional[int]
    status: ProcessingStatus
    
    # EXIF
    date_taken: Optional[datetime]
    latitude: Optional[float]
    longitude: Optional[float]
    location_name: Optional[str]
    camera_make: Optional[str]
    camera_model: Optional[str]
    
    # IA
    ai_description: Optional[str]
    ai_people_count: Optional[int]
    ai_setting: Optional[str]
    ai_emotion: Optional[str]
    ai_tags: Optional[List[str]]
    ai_narrative_hint: Optional[str]
    
    # OCR
    ocr_text: Optional[str]

    # People tagged in the photo (ids from the family tree)
    person_ids: Optional[List[int]] = []

    created_at: datetime

    class Config:
        from_attributes = True

class UploadResponse(BaseModel):
    message: str
    file_id: int
    filename: str
    media_type: MediaType
    status: ProcessingStatus
