from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional, List
from backend.models.narrative import StoryStatus

class GenerateRequest(BaseModel):
    title:            str
    event_type:       str           = "default"
    query:            Optional[str] = None
    person_ids:       List[int]     = []
    # Optional explicit photo selection. When non-empty, ONLY these media
    # rows feed the narrative (and therefore the video); empty = use every
    # available photo (the previous behaviour). Lets the user pick exactly
    # which photos/documents go into a story.
    media_ids:        List[int]     = []
    project_id:       Optional[int] = None
    # Only meaningful when ``event_type == "custom"``. Lets the user
    # supply their own tone + structure instead of one of the six
    # predefined themes.
    custom_tone:      Optional[str] = None
    custom_structure: Optional[str] = None
    # Output language for the narrative ("pt" or "en"). Stored on the
    # Story so the M4 TTS later picks the matching voice.
    language:         str           = "pt"
    # Narrator voice for the documentary: "male" or "female". Stored on the
    # Story; M4 resolves it to a neural voice per language. None → default.
    voice:            Optional[str] = None
    # Whether to include a narration subtitle track. Default on.
    subtitles:        bool          = True
    # Subtitle size in the player: "small" / "medium" / "large".
    subtitle_size:    str           = "medium"
    # Narrative length: "short" (~1 min) / "medium" (~2-3) / "long" (~4-5) /
    # "epic" (~6-8). Steers the paragraph count and spoken duration.
    length:           str           = "medium"

    class Config:
        json_schema_extra = {
            "example": {
                "title":      "As férias da família Silva no Algarve",
                "event_type": "viagem",
                "query":      "férias praia verão",
                "person_ids": []
            }
        }

class Scene(BaseModel):
    """One scene of a scene-segmented narrative.

    ``text`` is the prose for this beat; ``photo_ids`` are the media rows
    that illustrate it (shown, in M4, exactly while ``text`` is narrated);
    ``caption`` is a short date/place label burned as a lower-third.
    """
    text:      str
    photo_ids: List[int] = []
    caption:   Optional[str] = None


class UpdateStoryRequest(BaseModel):
    """Partial update of a generated story.

    Both fields are optional — the route only writes the ones supplied so
    the client can edit just the title, just the narrative, or both.
    """
    title:     Optional[str] = None
    narrative: Optional[str] = None
    favorite:  Optional[bool] = None


class RegenerateRequest(BaseModel):
    """Re-run a story's narrative, steering it with a free-text note
    (e.g. "make it shorter", "focus on grandpa João")."""
    feedback: str = ""


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
    language:      str           = "pt"
    scenes:        Optional[List[Scene]] = None
    favorite:      bool          = False
    # Metadata for the UI (counts of photos/people the story drew on).
    person_ids:    List[int]     = []
    media_ids:     List[int]     = []
    created_at:    datetime

    # Older stories predate these columns and store NULL — coerce to safe
    # defaults so serialization never fails on legacy rows.
    @field_validator("person_ids", "media_ids", mode="before")
    @classmethod
    def _none_to_empty_list(cls, v):
        return v or []

    @field_validator("favorite", mode="before")
    @classmethod
    def _none_to_false(cls, v):
        return bool(v)

    class Config:
        from_attributes = True
