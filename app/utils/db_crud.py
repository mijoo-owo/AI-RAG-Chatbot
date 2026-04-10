from typing import List, Optional

from sqlalchemy.orm import Session

from .db_orm import ChatMessage, Incident, get_session

# =========================Incident=========================


def list_incidents(session: Session = get_session()) -> List[Incident]:
    return session.query(Incident).all()


def get_incident_by_id(incident_id: str,
                       session: Session = get_session()) -> Optional[Incident]:
    return session.query(Incident).filter(Incident.id == incident_id).one_or_none()


def create_incident(name: str,
                    description: str,
                    email: str,
                    log: Optional[str] = None,
                    sla_no_of_hours: float = 1.0,
                    session: Session = get_session()) -> Incident:
    incident = Incident(
        name=name,
        description=description,
        email=email,
        log=log,
        sla_no_of_hours=sla_no_of_hours,
    )
    session.add(incident)
    session.commit()
    session.refresh(incident)
    return incident


def resolve_incident(incident_id: str,
                     solution: str,
                     session: Session = get_session()) -> Optional[Incident]:
    incident = get_incident_by_id(incident_id, session)
    if incident is None:
        return None
    incident.status = "resolved"
    incident.solution = solution
    session.commit()
    session.refresh(incident)
    return incident


def delete_incident(incident_id: str,
                    session: Session = get_session()) -> bool:
    incident = get_incident_by_id(incident_id, session)
    if incident is None:
        return False
    session.delete(incident)
    session.commit()
    return True


def is_incident_overdue(incident_id: str,
                        session: Session = get_session()) -> bool:
    incident = get_incident_by_id(incident_id, session)
    if incident is None:
        return False
    return (
        incident.status == "open" and
        incident.notified == False
    )


def mark_incident_notified(incident_id: str,
                           session: Session = get_session()) -> Optional[Incident]:
    incident = get_incident_by_id(incident_id, session)
    if incident is None:
        return None
    incident.notified = True
    session.commit()
    session.refresh(incident)
    return incident


# =========================ChatMessage=========================


def log_chat_message(username: str,
                     is_human: bool,
                     message: str,
                     images_json: Optional[str] = None,
                     session: Session = get_session()) -> ChatMessage:
    chat_message = ChatMessage(
        username=username,
        is_human=is_human,
        message=message,
        images_json=images_json,
    )
    session.add(chat_message)
    session.commit()
    session.refresh(chat_message)
    return chat_message


def get_user_last_n_messages(username: str,
                             n: int = 40,
                             session: Session = get_session()) -> List[ChatMessage]:
    """Get last N chat messages for a specific user"""
    messages = session.query(ChatMessage).filter(
        ChatMessage.username == username
    ).order_by(
        ChatMessage.timestamp.desc(),  # latest messages first
        ChatMessage.is_human.asc()  # AI message, then human message if same timestamp
    ).limit(n).all()
    return list(reversed(messages))  # return in chronological order


def clear_user_chat_history(username: str,
                            session: Session = get_session()) -> int:
    """Delete all chat messages for a specific user"""
    deleted = session.query(ChatMessage).filter(
        ChatMessage.username == username
    ).delete()
    session.commit()
    return deleted
