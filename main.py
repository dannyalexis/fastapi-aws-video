import boto3
from fastapi import FastAPI, UploadFile, Depends, status,HTTPException, FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import uvicorn
from models import Video
from schema import VideoModel
from db import SessionLocal
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import os
from uuid import uuid4
from typing import List
import mimetypes

load_dotenv()

S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')

app = FastAPI(debug=True)


if os.getenv("ENVIRONMENT") == "development":
    print("Development environment")
    app.docs_url = "/docs"
    app.redoc_url = "/redoc"
else:
    print("Production environment")
    app.docs_url = None
    app.redoc_url = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://react-fastapi-mr8r.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Configura las credenciales de AWS
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
AWS_REGION = os.getenv('AWS_REGION')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
S3_FOLDER_NAME = os.getenv('S3_FOLDER_NAME')  


s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)


async def is_valid_file_type(file):
    allowed_types = {"video/mp4", "video/avi", "video/mkv"}
    file_type, encoding = mimetypes.guess_type(file.filename)
    return file_type in allowed_types

def validate_file_size(file, max_size):
    if file.size > max_size:
        raise HTTPException(status_code=400, detail=f"Tamaño de archivo excede el límite máximo ({max_size / (1024 * 1024)}MB)")

@app.get("/")
async def check_status():
    return "Hello World!"


@app.post("/videos", response_description="Create Video",  status_code=status.HTTP_201_CREATED)
async def create_upload_file(file: UploadFile = File(...),db: Session = Depends(get_db)):
    try:
        # Validar el tipo de archivo
        if not await is_valid_file_type(file):
            raise HTTPException(status_code=400, detail="Tipo de archivo no permitido")
        
        #Validar el peso máximo del archivo (20MB)
        # Validar el peso máximo del archivo
        max_file_size = 20 * 1024 * 1024  # 5MB en bytes
        validate_file_size(file, max_file_size)
        
        
        # Generar un nombre único para el archivo
        unique_filename = str(uuid4()) + "." + file.filename.split(".")[-1]
        
        # Concatena la carpeta al nombre del archivo
        #s3_key = f"{S3_FOLDER_NAME}/{file.filename}"
        s3_key = f"{S3_FOLDER_NAME}/{unique_filename}"
        
        # Subir archivo a S3 en la carpeta especificada
        s3_client.upload_fileobj(file.file, S3_BUCKET_NAME, s3_key)
        
        
        # URL del archivo en S3
        file_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
        #dataVideo=Video(video_title=file.filename, video_url=file_url)
        data_video = Video(video_title=unique_filename, video_url=file_url)
        db.add(data_video)
        db.commit()
        db.refresh(data_video)
        return {"message": "Archivo subido correctamente", "file_url": file_url}
    except ClientError as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    
    
    
@app.get("/videos", response_model=List[VideoModel])
async def get_videos(db: Session = Depends(get_db)):
    videos = db.query(Video).order_by(Video.id.desc()).all()
    formatted_videos = [
        VideoModel(id=video.id, video_title=video.video_title, video_url=video.video_url)
        for video in videos
    ]
    return formatted_videos   
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
