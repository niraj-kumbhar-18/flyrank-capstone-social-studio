from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class PostCreate(BaseModel):
    source_url: Optional[str] = None
    raw_content: Optional[str] = None
    
class VariantCreate(BaseModel):
    platform: str
    content: str

class ScheduleCreate(BaseModel):
    scheduled_for: datetime