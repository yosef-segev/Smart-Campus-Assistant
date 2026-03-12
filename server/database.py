from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from logger import logger


DB_DIR = Path("data")
DB_DIR.mkdir(exist_ok=True)
DB_URL = f"sqlite:///{DB_DIR / 'campus.db'}"

engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False},  # required for SQLite + ASGI
    echo=False,   # set True temporarily to debug raw SQL
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # avoids lazy-load errors after session.close()
)


class Base(DeclarativeBase):
    """
    Shared base class for all ORM models.
    Inheriting from DeclarativeBase (SQLAlchemy 2.x) enables Mapped[] typing.
    """


class ExamSchedule(Base):
    """
    Stores every exam event for the current academic term.

    Unique constraint on (course_code, exam_date, start_time) prevents
    accidental duplicate seeding while allowing re-seeding to be idempotent
    via INSERT OR IGNORE semantics.
    """

    __tablename__ = "exam_schedules"
    __table_args__ = (
        UniqueConstraint("course_code", "exam_date", "start_time",
                         name="uq_exam_slot"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Course identification
    course_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    course_name: Mapped[str] = mapped_column(String(120), nullable=False)

    # Scheduling
    exam_date: Mapped[str] = mapped_column(String(10),  nullable=False)   # ISO 8601: YYYY-MM-DD
    start_time: Mapped[str] = mapped_column(String(5),  nullable=False)   # HH:MM  (24-h)
    end_time: Mapped[str]   = mapped_column(String(5),  nullable=False)   # HH:MM  (24-h)

    # Location
    building: Mapped[str]  = mapped_column(String(80),  nullable=False)
    room_number: Mapped[str] = mapped_column(String(20), nullable=False)

    # Optional metadata
    lecturer: Mapped[str | None]  = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None]     = mapped_column(Text,         nullable=True)

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<ExamSchedule id={self.id} course={self.course_code!r} "
            f"date={self.exam_date} room={self.room_number!r}>"
        )



class ReceptionHours(Base):
    """
    Office / reception availability for departments and staff members.

    One row = one recurring weekly slot, e.g.:
        department="Registrar", day_of_week="Sunday", open="09:00", close="13:00"

    Using day_of_week as a plain string (locale-neutral English name) keeps
    the data human-readable and easy for the AI prompt to consume directly.
    """

    __tablename__ = "reception_hours"
    __table_args__ = (
        UniqueConstraint("department", "contact_person", "day_of_week", "open_time",
                         name="uq_reception_slot"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Who
    department: Mapped[str]         = mapped_column(String(100), nullable=False, index=True)
    contact_person: Mapped[str | None] = mapped_column(String(100), nullable=True)
    room_number: Mapped[str | None] = mapped_column(String(20),  nullable=True)
    phone: Mapped[str | None]       = mapped_column(String(30),  nullable=True)
    email: Mapped[str | None]       = mapped_column(String(120), nullable=True)

    # When  (recurring weekly schedule)
    day_of_week: Mapped[str] = mapped_column(String(10), nullable=False)   # e.g. "Sunday"
    open_time: Mapped[str]   = mapped_column(String(5),  nullable=False)   # HH:MM
    close_time: Mapped[str]  = mapped_column(String(5),  nullable=False)   # HH:MM

    # Special flags
    is_by_appointment: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None]       = mapped_column(Text, nullable=True)

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<ReceptionHours id={self.id} dept={self.department!r} "
            f"day={self.day_of_week} {self.open_time}-{self.close_time}>"
        )


class RoomLocation(Base):
    """
    Physical catalogue of every named room / space on campus.

    Includes accessibility metadata so the AI can answer questions like
    "Is room B204 wheelchair accessible?" without hallucinating.
    """

    __tablename__ = "room_locations"
    __table_args__ = (
        UniqueConstraint("building", "room_number", name="uq_room"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identity
    building: Mapped[str]     = mapped_column(String(80), nullable=False, index=True)
    room_number: Mapped[str]  = mapped_column(String(20), nullable=False)
    room_name: Mapped[str | None] = mapped_column(String(120), nullable=True)  # e.g. "Dean's Office"

    # Classification
    room_type: Mapped[str]    = mapped_column(String(40), nullable=False)
    # Allowed values (not enforced at DB level to stay SQLite-friendly):
    #   "classroom" | "lab" | "office" | "auditorium" | "library" | "cafeteria" | "other"

    floor: Mapped[int | None] = mapped_column(Integer, nullable=True)   # 0 = ground floor

    # Capacity
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Accessibility
    is_accessible: Mapped[bool]     = mapped_column(Boolean, default=False, nullable=False)
    has_elevator_access: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Free-text directions / notes shown directly to the user
    directions: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None]      = mapped_column(Text, nullable=True)

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<RoomLocation id={self.id} building={self.building!r} "
            f"room={self.room_number!r} type={self.room_type!r}>"
        )



class ExamsGradesInfo(Base):
    """
    Knowledge base for grades, appeals, exam policies, and publication times.
    
    Stores FAQs about grade appeals, passing criteria, grading scales,
    exam policies, and grade publication schedules.
    """

    __tablename__ = "exams_grades_info"
    __table_args__ = (
        UniqueConstraint("question", name="uq_exam_grade_q"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Question and answer in Hebrew
    question: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Topic tags for search
    topic: Mapped[str] = mapped_column(String(60), nullable=False)
    # Allowed values: "appeals", "grades", "policy", "registration", "publication", "cumulative"
    
    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<ExamsGradesInfo id={self.id} topic={self.topic!r} "
            f"question={self.question[:50]!r}>"
        )


class LibraryServicesInfo(Base):
    """
    Knowledge base for library hours, remote access, databases, and borrowing.
    
    Stores information about library opening hours, VPN/remote access setup,
    available databases (IEEE, etc.), book borrowing/extension policies.
    """

    __tablename__ = "library_services_info"
    __table_args__ = (
        UniqueConstraint("question", name="uq_library_q"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Question and answer in Hebrew
    question: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Topic tags for search
    topic: Mapped[str] = mapped_column(String(60), nullable=False)
    # Allowed values: "hours", "access", "databases", "borrowing", "research"
    
    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<LibraryServicesInfo id={self.id} topic={self.topic!r} "
            f"question={self.question[:50]!r}>"
        )


class StudentServicesInfo(Base):
    """
    Knowledge base for student housing, union services, clubs, and wellness.
    
    Stores information about dorm applications, student union/clubs,
    scholarships, financial aid, health & wellness services.
    """

    __tablename__ = "student_services_info"
    __table_args__ = (
        UniqueConstraint("question", name="uq_student_service_q"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Question and answer in Hebrew
    question: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Topic tags for search
    topic: Mapped[str] = mapped_column(String(60), nullable=False)
    # Allowed values: "housing", "union", "clubs", "financial", "wellness", "student_day"
    
    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<StudentServicesInfo id={self.id} topic={self.topic!r} "
            f"question={self.question[:50]!r}>"
        )


def init_db() -> None:
    """
    Create all tables that don't yet exist in campus.db.

    Safe to call multiple times — SQLAlchemy uses CREATE TABLE IF NOT EXISTS
    semantics via checkfirst=True (implicit with Base.metadata.create_all).

    Called automatically at application startup from main.py.
    """
    logger.info("Initialising database at %s", DB_URL)
    Base.metadata.create_all(bind=engine)
    logger.info(
        "Tables ready: %s",
        ", ".join(Base.metadata.tables.keys()),
    )


def get_db():
    """
    Yield a SQLAlchemy session scoped to a single HTTP request.

    Usage in a route:
        from fastapi import Depends
        from database import get_db
        from sqlalchemy.orm import Session

        @app.post("/ask")
        def ask(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
