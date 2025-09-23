from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func
from app.model import Event, Keyword
from app.schemas import EventBase, EventDetails

def get_all_events(session:Session)->list[EventBase]:
    """Get all events with their keywords"""
    result=session.execute(select(Event.id, Event.latitude,  Event.longitude)).mappings().all()
    return [EventBase(**row) for row in result]
    

def get_event_detail(session: Session, event_id:int):
    result = session.execute(
    select(
        Event.id,
        Event.title,
        Event.description,
        Event.start_date,
        Event.end_date,
        Event.latitude,
        Event.longitude,
        Event.author,
        Event.source,
        func.array_agg(Keyword.name).label('keyword_names')
    )
    .outerjoin(Event.keywords)
    .where(Event.id==event_id)
    .group_by(
        Event.id, Event.title, Event.description, Event.start_date,
        Event.end_date, Event.latitude, Event.longitude, Event.author, Event.source
    ).order_by(Event.id)
).mappings().first()
    
    if result is None:
        return None
    return EventDetails(**(result))

def get_filtered_events(session: Session, keyword_filter: str = "festival"):
    """Get events filtered by keyword"""
    result = session.execute(
        select(Event)
        .join(Event.keywords)
        .filter(Keyword.name == keyword_filter)
        .options(joinedload(Event.keywords))
    )
    return result.scalars().unique().all()
