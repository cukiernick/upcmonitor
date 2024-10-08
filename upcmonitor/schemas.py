from datetime import datetime

from pydantic import BaseModel
from typing_extensions import Literal


class EntryData(BaseModel):
    timestamp: datetime

    class Config:
        orm_mode = True


class ChannelDataDown(BaseModel):
    receiver_id: int
    channel_id: int
    lock_status: Literal["Locked", "Unlocked"]
    frequency: int
    modulation: str
    symbol_rate: int
    snr: float
    power: float

    class Config:
        orm_mode = True


class ChannelDataUp(BaseModel):
    transmitter_id: int
    channel_id: int
    lock_status: Literal["Locked", "Unlocked"]
    frequency: int
    modulation: str
    symbol_rate: int
    channel_type: str
    power: float

    class Config:
        orm_mode = True
