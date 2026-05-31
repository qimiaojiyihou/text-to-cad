"""生成记录数据库模型"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.db.database import Base


class GenerationRecord(Base):
    __tablename__ = "generation_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    model_id = Column(String(16), nullable=False, index=True)
    prompt = Column(Text, nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    message = Column(Text, nullable=True)
    py_path = Column(String(500), nullable=True)
    step_path = Column(String(500), nullable=True)
    glb_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="records")
