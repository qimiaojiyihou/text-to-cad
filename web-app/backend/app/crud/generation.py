"""生成记录 CRUD 操作"""

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.generation import GenerationRecord
from app.schemas.generation import GenerationRecordCreate, GenerationRecordUpdate


def get_record(db: Session, record_id: int) -> GenerationRecord | None:
    return db.query(GenerationRecord).filter(GenerationRecord.id == record_id).first()


def get_record_by_model_id(db: Session, model_id: str, user_id: int | None = None) -> GenerationRecord | None:
    q = db.query(GenerationRecord).filter(GenerationRecord.model_id == model_id)
    if user_id is not None:
        q = q.filter(GenerationRecord.user_id == user_id)
    return q.first()


def create_record(db: Session, record_in: GenerationRecordCreate) -> GenerationRecord:
    db_record = GenerationRecord(**record_in.model_dump())
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record


def update_record(db: Session, db_record: GenerationRecord, record_in: GenerationRecordUpdate) -> GenerationRecord:
    update_data = record_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_record, field, value)
    db.commit()
    db.refresh(db_record)
    return db_record


def get_records_by_user(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    status: str | None = None,
) -> tuple[list[GenerationRecord], int]:
    q = db.query(GenerationRecord).filter(GenerationRecord.user_id == user_id)
    if status:
        q = q.filter(GenerationRecord.status == status)
    total = q.count()
    records = q.order_by(desc(GenerationRecord.created_at)).offset(skip).limit(limit).all()
    return records, total


def get_all_records(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    user_id: int | None = None,
    status: str | None = None,
    search: str | None = None,
) -> tuple[list[GenerationRecord], int]:
    q = db.query(GenerationRecord)
    if user_id:
        q = q.filter(GenerationRecord.user_id == user_id)
    if status:
        q = q.filter(GenerationRecord.status == status)
    if search:
        pattern = f"%{search}%"
        q = q.filter(GenerationRecord.prompt.ilike(pattern))
    total = q.count()
    records = q.order_by(desc(GenerationRecord.created_at)).offset(skip).limit(limit).all()
    return records, total


def delete_record(db: Session, record_id: int) -> bool:
    record = get_record(db, record_id)
    if not record:
        return False
    db.delete(record)
    db.commit()
    return True
