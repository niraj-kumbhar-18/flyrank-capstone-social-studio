from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey,  Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


DATABASE_URL = "sqlite:///./social_studio.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    source_url = Column(String, nullable=True)
    raw_content = Column(Text, nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

class Variant(Base):
    __tablename__ = "variants"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    platform = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String, default="draft")
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )


class ScheduleSlot(Base):
    __tablename__ = "schedule_slots"

    id = Column(Integer, primary_key=True, index=True)
    variant_id = Column(
        Integer,
        ForeignKey("variants.id"),
        nullable=False
    )
    scheduled_for = Column(DateTime, nullable=False)
    idempotency_key = Column(String, unique=True, nullable=False)


class PublishAttempt(Base):
    __tablename__ = "publish_attempts"

    id = Column(Integer, primary_key=True, index=True)
    schedule_slot_id = Column(
        Integer,
        ForeignKey("schedule_slots.id"),
        nullable=False
    )
    attempted_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )
    success = Column(Integer, nullable=False)
    detail = Column(Text, nullable=False)
    external_post_id = Column(String, nullable=True)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


Base.metadata.create_all(bind=engine)
