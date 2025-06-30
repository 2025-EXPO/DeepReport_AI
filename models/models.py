from sqlalchemy import Column, Integer, String
from database.database import Base

class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    news_title = Column(String)
    news_content = Column(String)
    current_index = Column(Integer)
    tag = Column(String)
    base_url = Column(String)
