# models.py

from sqlalchemy import Column, Integer, String
from database import Base

class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    short_summary = Column(String)
    medium_summary = Column(String)
    current_index = Column(Integer)
    tag = Column(String)
