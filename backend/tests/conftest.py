import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from app.main import app
from app.db import get_session
from app.models import *
from app.core.security import create_access_token
from app.repos.user_repo import UserRepo
from app.core.security import hash_password

# Use in‑memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///./test.db?mode=memory&cache=shared"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})

@pytest.fixture(name="session")
def session_fixture():
    """Create a fresh database for each test."""
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Test client that overrides the session dependency."""
    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    """Create a test user and return it with an auth token."""
    repo = UserRepo()
    user = repo.create_user(session, "test@example.com", "hashedpassword")
    session.commit()
    token = create_access_token(data={"sub": user.email})
    return {"user": user, "token": token}

@pytest.fixture(name="auth_header")
def auth_header_fixture(test_user):
    """Directly return the Authorization header dict."""
    return {"Authorization": f"Bearer {test_user['token']}"}



@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    """Create a test user and return it with an auth token and raw password."""
    raw_password = "testpass123"
    hashed = hash_password(raw_password)
    repo = UserRepo()
    user = repo.create_user(session, "test@example.com", hashed)
    session.commit()
    token = create_access_token(data={"sub": user.email})
    return {
        "user": user,
        "token": token,
        "password": raw_password     
    }