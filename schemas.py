from typing import Optional

from pydantic import BaseModel


class PostCreate(BaseModel):
    source_url: Optional[str] = None
    raw_content: Optional[str] = None