from pydantic import BaseModel
from typing import Optional

class RagRequest(BaseModel):
    question: str
    org_id: Optional[str] = None
    jobinstance_id: Optional[str] = None
    attachment_id: Optional[str] = None
    min_score_threshold: Optional[int] = None