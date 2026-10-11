import uuid

from sqlalchemy import Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Technology(Base):
    __tablename__ = "technologies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    badge_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    max_download_mbps: Mapped[int] = mapped_column(Integer)
    max_upload_mbps: Mapped[int] = mapped_column(Integer)
