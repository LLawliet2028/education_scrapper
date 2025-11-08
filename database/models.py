from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from database.db import Base

class Trend(Base):
    __tablename__ = "trends"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, index=True)
    source = Column(String)
    score = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
