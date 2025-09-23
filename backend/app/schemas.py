from pydantic import BaseModel, ConfigDict
from datetime import datetime


class EventBase(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    
    id:int
    latitude:float
    longitude:float

class EventDetails(EventBase):
    model_config=ConfigDict(from_attributes=True)
    
    title:str
    description:str
    start_date:datetime
    end_date:datetime
    author:str
    keyword_names:list[str]
    source:str

