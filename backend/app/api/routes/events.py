from fastapi import APIRouter, Request, Depends, HTTPException, status
import geohash
from app.crud import get_all_events, get_event_detail
from sqlalchemy.orm import Session
from app.api.dependecies import get_db
from app.model import Event
from app.schemas import EventBase, EventDetails
router=APIRouter()


#1. endpoint for gettign all markers (no sorting initially by geohashing)
#2. getting detailed info about the event through the eventid
#3. 

@router.get("/get-all-events", response_model=list[EventBase])
async def retrieve_all_events(session:Session=Depends(get_db)):
    payload=get_all_events(session)#type:ignore
    return payload

@router.get("/get-event-details/{event_id}", response_model=EventDetails)
async def retrieve_event_detail(event_id:int, session:Session=Depends(get_db) ):
    payload=get_event_detail(session=session, event_id=event_id)
    
    if not payload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The event does not exist")
    return payload