from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from backend.models.narrative import StoryStatus

class GenerateRequest(BaseModel):
    title:            str
    event_type:       str           = "default"
    query:            Optional[str] = None
    person_ids:       List[int]     = []
    project_id:       Optional[int] = None
    # Only meaningful when ``event_type == "custom"``. Lets the user
    # supply their own tone + structure instead of one of the six
    # predefined themes.
    custom_tone:      Optional[str] = None
    custom_structure: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "title":      "As férias da família Silva no Algarve",
                "event_type": "viagem",
                "query":      "férias praia verão",
                "person_ids": []
            }
        }

class UpdateStoryRequest(BaseModel):
    """Partial update of a generated story.

    Both fields are optional — the route only writes the ones supplied so
    the client can edit just the title, just the narrative, or both.
    """
    title:     Optional[str] = None
    narrative: Optional[str] = None


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
