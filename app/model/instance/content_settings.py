from typing import Optional
from pydantic import BaseModel, Field


class ContentSettings(BaseModel):
    drones: Optional[bool] = Field(None)
    emoji: Optional[bool] = Field(None)
    pedestals: Optional[bool] = Field(None)
    prints: Optional[bool] = Field(None)
    stickers: Optional[bool] = Field(None)
    props: Optional[bool] = Field(None)
