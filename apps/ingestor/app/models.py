from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    source_type: Mapped[str] = mapped_column(String(40))
    base_url: Mapped[str] = mapped_column(Text)
    rss_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    crawl_mode: Mapped[str] = mapped_column(String(40), default="k2web_rss")
    list_url_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail_url_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    encoding_hint: Mapped[str | None] = mapped_column(String(40), nullable=True)
    normalized_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Notice(Base):
    __tablename__ = "notices"
    __table_args__ = (UniqueConstraint("source_id", "external_id", name="uq_notice_source_external"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(Text)
    link: Mapped[str] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(120), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    cached_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    source: Mapped[Source] = relationship()
    attachments: Mapped[list["Attachment"]] = relationship(back_populates="notice")
    images: Mapped[list["NoticeImage"]] = relationship(back_populates="notice")


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    notice_id: Mapped[int] = mapped_column(ForeignKey("notices.id"), index=True)
    filename: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text)
    local_path: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64), index=True)

    notice: Mapped[Notice] = relationship(back_populates="attachments")


class NoticeImage(Base):
    __tablename__ = "notice_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    notice_id: Mapped[int] = mapped_column(ForeignKey("notices.id"), index=True)
    source_url: Mapped[str] = mapped_column(Text)
    local_path: Mapped[str] = mapped_column(Text)

    notice: Mapped[Notice] = relationship(back_populates="images")


class Meal(Base):
    __tablename__ = "meals"
    __table_args__ = (
        UniqueConstraint("meal_date", "cafeteria_key", "meal_type", name="uq_meals_date_cafeteria_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campus: Mapped[str] = mapped_column(String(120), default="PNU")
    cafeteria_key: Mapped[str] = mapped_column(String(80), default="default", index=True)
    cafeteria_name: Mapped[str] = mapped_column(String(120), default="기본 식당")
    meal_date: Mapped[date] = mapped_column(Date, index=True)
    meal_type: Mapped[str] = mapped_column(String(20))  # breakfast/lunch/dinner
    menu: Mapped[str] = mapped_column(Text)


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(40), index=True)
    start_date: Mapped[date] = mapped_column(Date, index=True)
    end_date: Mapped[date] = mapped_column(Date, index=True)


class SyncJob(Base):
    __tablename__ = "sync_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="queued")
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RagChunk(Base):
    __tablename__ = "rag_chunks"
    __table_args__ = (UniqueConstraint("source_key", "chunk_index", name="uq_rag_sourcekey_chunk"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    notice_id: Mapped[int | None] = mapped_column(ForeignKey("notices.id"), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(40), default="notice_body", index=True)
    source_key: Mapped[str] = mapped_column(String(255), default="", index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    notice: Mapped[Notice | None] = relationship()
