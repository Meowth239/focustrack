from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
from utils.config import DB_PATH

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    name = Column(String, nullable=True)
    weight_goal = Column(Float, default=100.0)
    current_weight = Column(Float, nullable=True)
    morning_hour = Column(Integer, default=8)
    morning_minute = Column(Integer, default=0)
    nudge_enabled = Column(Integer, default=1)
    nudge_interval = Column(Integer, default=3)
    total_points = Column(Integer, default=0)
    level = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    activities = relationship("Activity", back_populates="user")
    daily_goals = relationship("DailyGoal", back_populates="user")

    def calculate_level(self):
        """Level up every 100 points"""
        self.level = (self.total_points // 100) + 1


class Activity(Base):
    __tablename__ = 'activities'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.telegram_id'))
    activity_type = Column(String, nullable=False)  # run, gym, study
    activity_name = Column(String, nullable=True)   # e.g., "r", "quant", "chest"
    duration_mins = Column(Integer, nullable=True)
    distance_km = Column(Float, nullable=True)
    points_earned = Column(Integer, default=0)
    logged_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="activities")


class DailyGoal(Base):
    __tablename__ = 'daily_goals'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.telegram_id'))
    date = Column(String, nullable=False)  # YYYY-MM-DD
    study_goal = Column(String, nullable=True)
    exercise_goal = Column(String, nullable=True)
    study_completed = Column(Integer, default=0)
    exercise_completed = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="daily_goals")


class WeightLog(Base):
    __tablename__ = 'weight_logs'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.telegram_id'))
    weight = Column(Float, nullable=False)
    logged_at = Column(DateTime, default=datetime.utcnow)


# Create engine
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(engine)


def get_session():
    """Get a database session"""
    return SessionLocal()


def get_user(telegram_id: int) -> User:
    """Get a user and detach from session for safe access"""
    session = get_session()
    user = session.query(User).filter(User.telegram_id == telegram_id).first()
    if user:
        # Expunge removes it from session, keeping data accessible after close
        session.expunge(user)
    session.close()
    return user