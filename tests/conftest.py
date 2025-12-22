"""
Test configuration and fixtures.
"""
import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base, get_db
from app.core.security import get_password_hash, create_access_token
from app.models.user import User
from app.models.gym import Gym, GradingSystemType
from app.models.grade import Grade
from app.models.session import Session
from app.models.ascent import Ascent, AscentStatus


# Test database - in-memory SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for tests."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override the dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def db():
    """Create fresh database tables for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Test client with fresh database."""
    return TestClient(app)


@pytest.fixture
def test_user(db):
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=get_password_hash("testpass123")
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """Get authorization headers for test user."""
    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_gym(db):
    """Create a test gym."""
    gym = Gym(
        name="Test Climbing Gym",
        location="Test City",
        grading_system_type=GradingSystemType.COLORS
    )
    db.add(gym)
    db.commit()
    db.refresh(gym)
    return gym


@pytest.fixture
def test_grades(db, test_gym):
    """Create test grades for the gym."""
    grades = [
        Grade(gym_id=test_gym.id, label="Verde", color_hex="#00FF00", relative_difficulty=2, order=1),
        Grade(gym_id=test_gym.id, label="Azul", color_hex="#0000FF", relative_difficulty=4, order=2),
        Grade(gym_id=test_gym.id, label="Rojo", color_hex="#FF0000", relative_difficulty=6, order=3),
        Grade(gym_id=test_gym.id, label="Negro", color_hex="#000000", relative_difficulty=8, order=4),
    ]
    db.add_all(grades)
    db.commit()
    for g in grades:
        db.refresh(g)
    return grades


@pytest.fixture
def test_session(db, test_user, test_gym):
    """Create a test climbing session."""
    session = Session(
        user_id=test_user.id,
        gym_id=test_gym.id,
        date=date.today()
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@pytest.fixture
def test_ascents(db, test_session, test_grades):
    """Create test ascents for a session."""
    ascents = [
        Ascent(session_id=test_session.id, grade_id=test_grades[0].id, status=AscentStatus.FLASH),
        Ascent(session_id=test_session.id, grade_id=test_grades[1].id, status=AscentStatus.SEND),
        Ascent(session_id=test_session.id, grade_id=test_grades[1].id, status=AscentStatus.SEND),
        Ascent(session_id=test_session.id, grade_id=test_grades[2].id, status=AscentStatus.PROJECT),
    ]
    db.add_all(ascents)
    db.commit()
    for a in ascents:
        db.refresh(a)
    return ascents
