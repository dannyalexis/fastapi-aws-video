from datetime import datetime
from sqlalchemy import Column,  Integer, String
from db import Base, engine


class Video(Base):
    __tablename__ = 'video'
    id = Column(Integer, primary_key=True, autoincrement=True)
    video_title = Column(String(150))
    video_url=Column(String(150))
    

Base.metadata.create_all(bind=engine)