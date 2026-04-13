from typing import List, Optional

from sqlalchemy.orm import Session

from .db_orm import ChatMessage, get_session


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
