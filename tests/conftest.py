"""
Test configuration and fixtures.
"""
import pytest
import secrets
from datetime import date, datetime, timedelta
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
from app.models.push_subscription import PushSubscription
from app.models.invitation import Invitation


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
def create_user(db):
    """Factory fixture to create additional users."""
    created_users = []
    
    def _create_user(username: str, email: str, password: str, home_gym_id: int = None):
        user = User(
            username=username,
            email=email,
            password_hash=get_password_hash(password),
            home_gym_id=home_gym_id
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        created_users.append(user)
        return user
    
    return _create_user


@pytest.fixture
def auth_headers(test_user):
    """Get authorization headers for test user."""
    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_invitation(db, test_user):
    """Create a valid test invitation."""
    invitation = Invitation(
        token=secrets.token_urlsafe(32),
        created_by_user_id=test_user.id,
        expires_at=datetime.utcnow() + timedelta(hours=24),
        used=False
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return invitation


@pytest.fixture
def create_invitation(db):
    """Factory fixture to create invitations."""
    def _create_invitation(created_by_user_id: int, used: bool = False, expired: bool = False):
        expires_at = datetime.utcnow() - timedelta(hours=1) if expired else datetime.utcnow() + timedelta(hours=24)
        invitation = Invitation(
            token=secrets.token_urlsafe(32),
            created_by_user_id=created_by_user_id,
            expires_at=expires_at,
            used=used
        )
        db.add(invitation)
        db.commit()
        db.refresh(invitation)
        return invitation
    
    return _create_invitation


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
def create_gym(db):
    """Factory fixture to create additional gyms."""
    def _create_gym(name: str, location: str):
        gym = Gym(
            name=name,
            location=location,
            grading_system_type=GradingSystemType.COLORS
        )
        db.add(gym)
        db.commit()
        db.refresh(gym)
        return gym
    
    return _create_gym


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
