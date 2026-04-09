from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    username      = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)

    entries  = relationship("Entry", back_populates="owner", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    id      = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token   = Column(String, nullable=False, unique=True)

    user = relationship("User", back_populates="sessions")


class Entry(Base):
    __tablename__ = "entries"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    owner_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    title       = Column(String, nullable=False)
    description = Column(String, nullable=True)
    time        = Column(String, nullable=True)
    year        = Column(Integer, nullable=False)
    season      = Column(Integer, nullable=False)
    month       = Column(Integer, nullable=False)
    week        = Column(Integer, nullable=False)
    day         = Column(String, nullable=False)

    owner  = relationship("User", back_populates="entries")
    shares = relationship("Share", back_populates="entry", cascade="all, delete-orphan")


class Share(Base):
    __tablename__ = "shares"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    entry_id            = Column(Integer, ForeignKey("entries.id"), nullable=False)
    shared_with_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint("entry_id", "shared_with_user_id", name="uq_entry_user"),
    )

    entry       = relationship("Entry", back_populates="shares")
    shared_with = relationship("User", foreign_keys=[shared_with_user_id])