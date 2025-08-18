from sqlalchemy import Column, String, Integer, Boolean, DateTime
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    college = Column(String, nullable=False)
    branch = Column(String, nullable=False)
    year = Column(String, nullable=False)
    token = Column(String(6), unique=True, nullable=False)
    is_verified = Column(Boolean, default=False)
    token_created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) 