import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from flight_tracker.models.orm import Base


@pytest.fixture
def db_session():
    engine = create_engine("sqlite://", poolclass=None)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
