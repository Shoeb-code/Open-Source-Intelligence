from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.config import settings

# Handle dialect-specific connection arguments (e.g., SQLite multi-threading)
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency generator that yields a database session and closes it cleanly."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_person_enrichment_columns(target_engine=engine):
    """Idempotently adds LinkedIn enrichment columns to existing persons tables."""
    inspector = inspect(target_engine)
    if "persons" not in inspector.get_table_names():
        return

    existing_cols = {col["name"] for col in inspector.get_columns("persons")}
    dialect = target_engine.dialect.name
    json_type = "JSON" if dialect != "postgresql" else "JSONB"
    ts_type = "DATETIME" if dialect == "sqlite" else "TIMESTAMP"

    migrations = {
        "headline": "VARCHAR(512)",
        "occupation": "VARCHAR(255)",
        "location": "VARCHAR(255)",
        "profile_pic_url": "VARCHAR(1024)",
        "follower_count": "INTEGER",
        "connections": "INTEGER",
        "summary": "TEXT",
        "experiences": json_type,
        "education": json_type,
        "projects": json_type,
        "activities": json_type,
        "skills": json_type,
        "certifications": json_type,
        "profile_enriched_at": ts_type,
        "enrichment_status": "VARCHAR(50) DEFAULT 'NOT_ENRICHED'",
    }

    with target_engine.begin() as conn:
        for col_name, col_type in migrations.items():
            if col_name not in existing_cols:
                conn.execute(text(f"ALTER TABLE persons ADD COLUMN {col_name} {col_type}"))


def init_db():
    """Creates all database tables defined in models and runs additive column migrations."""
    from backend.database import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    ensure_person_enrichment_columns(engine)

