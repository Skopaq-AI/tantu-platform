"""DB — SQLAlchemy 2.0 + Timescale stub."""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float
import os

URL = os.getenv("DATABASE_URL", "postgresql+psycopg://tantu:tantu@localhost:5432/tantu")

class Base(DeclarativeBase): pass

class DefectEventRow(Base):
    __tablename__ = "defect_events"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    station_id: Mapped[str] = mapped_column(String)
    defect_class: Mapped[str] = mapped_column(String)
    confidence: Mapped[float] = mapped_column(Float)
    latency_ms: Mapped[float] = mapped_column(Float)

# engine = create_async_engine(URL)
# Session = async_sessionmaker(engine)
