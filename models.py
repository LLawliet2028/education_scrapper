from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Trend(Base):
    __tablename__ = "trends"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String)
    source = Column(String)
    score = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

