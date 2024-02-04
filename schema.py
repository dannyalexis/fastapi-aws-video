from pydantic import BaseModel

class VideoModel(BaseModel):
    id: int
    video_title: str
    video_url: str