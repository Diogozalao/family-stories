from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from backend.models.narrative import StoryStatus

class GenerateRequest(BaseModel):
    title:      str
    event_type: str  = "default"
    query:      Optional[str] = None
    person_ids: List[int] = []
    project_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "title":      "As férias da família Silva no Algarve",
                "event_type": "viagem",
                "query":      "férias praia verão",
                "person_ids": []
            }
        }

class StoryResponse(BaseModel):
    id:            int
    title:         str
    event_type:    str
    narrative:     str
    template_used: Optional[str]
    llm_backend:   Optional[str]
    facts_used:    int
    status:        StoryStatus
    project_id:    Optional[int] = None
    created_at:    datetime

    class Config:
        from_attributes = True
