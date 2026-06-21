import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from api.main import app
from db.session import get_session


@pytest.fixture(name="session")
def session_fixture():
    """An isolated in-memory SQLite DB, fresh for every test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session):
    """A TestClient whose requests share the test `session` fixture, so
    data seeded directly via `session` is visible to requests and vice
    versa. Does not trigger the app's real startup event (no TestClient
    context manager), so the real vinyl_library.db file is never touched.
    """

    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    yield TestClient(app)
    app.dependency_overrides.clear()
