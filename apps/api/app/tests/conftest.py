from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.main import app
from app.db import session as session_module


@pytest.fixture()
def db_session(tmp_path) -> Session:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite+pysqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    with TestingSessionLocal() as db:
        yield db


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    def _get_db_override():
        yield db_session

    app.dependency_overrides[session_module.get_db] = _get_db_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

