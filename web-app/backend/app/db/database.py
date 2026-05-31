"""数据库连接与会话管理"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from app.core.config import get_settings

settings = get_settings()

# 创建引擎
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    pool_pre_ping=True,
)

# SQLite 外键支持
if "sqlite" in settings.DATABASE_URL:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Session:
    """获取数据库会话（生成器，用于 FastAPI Depends）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库（创建所有表，并创建默认管理员）"""
    from app.models.user import User  # noqa
    from app.models.generation import GenerationRecord  # noqa
    Base.metadata.create_all(bind=engine)

    # 创建默认管理员账号
    db = SessionLocal()
    try:
        from app.core.security import get_password_hash
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin_user = User(
                username="admin",
                email="admin@local.system",
                hashed_password=get_password_hash("123456"),
                full_name="System Admin",
                is_active=True,
                is_superuser=True,
            )
            db.add(admin_user)
            db.commit()
            print("[INIT] Default admin created: admin / 123456")
    finally:
        db.close()
