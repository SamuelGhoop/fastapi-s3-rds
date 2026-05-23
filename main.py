from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, DateTime, text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
import os

# --- Configuración ---
DB_HOST = os.getenv("DB_HOST", "taller-so-db.ccj4u488skun.us-east-1.rds.amazonaws.com")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASS = os.getenv("DB_PASS", "Hola1234*")
DB_NAME = os.getenv("DB_NAME", "taller_so")
DB_PORT = os.getenv("DB_PORT", "3306")
S3_BUCKET = os.getenv("S3_BUCKET", "user-1038868860-ueia-so")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# --- Modelo ---
class Image(Base):
    __tablename__ = "images"
    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario = Column(String(255), nullable=False)
    s3_path = Column(String(500), nullable=False)
    filename = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# --- Crear DB y tabla ---
def init_db():
    temp_engine = create_engine(
        f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/"
    )
    with temp_engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}"))
    Base.metadata.create_all(engine)

init_db()

# --- App ---
app = FastAPI(title="FastAPI S3 + RDS")
s3 = boto3.client("s3", region_name=AWS_REGION)

ALLOWED_TYPES = ["image/png", "image/jpeg", "image/jpg"]

@app.post("/upload")
async def upload_image(usuario: str = Form(...), file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Formato no permitido: {file.content_type}. Solo PNG y JPG/JPEG."
        )

    s3_key = f"{usuario}/{file.filename}"

    try:
        s3.upload_fileobj(file.file, S3_BUCKET, s3_key)
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"Error subiendo a S3: {str(e)}")

    db = SessionLocal()
    try:
        img = Image(usuario=usuario, s3_path=s3_key, filename=file.filename)
        db.add(img)
        db.commit()
        db.refresh(img)
    finally:
        db.close()

    return {
        "message": "Imagen subida exitosamente",
        "id": img.id,
        "usuario": img.usuario,
        "s3_path": img.s3_path,
        "created_at": str(img.created_at)
    }

@app.get("/image/{usuario}/{filename}")
def get_image(usuario: str, filename: str):
    db = SessionLocal()
    try:
        img = db.query(Image).filter(
            Image.usuario == usuario,
            Image.filename == filename
        ).first()
    finally:
        db.close()

    if not img:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró la imagen '{filename}' para el usuario '{usuario}'"
        )

    try:
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": img.s3_path},
            ExpiresIn=3600
        )
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"Error generando URL: {str(e)}")

    return {
        "usuario": img.usuario,
        "filename": img.filename,
        "s3_path": img.s3_path,
        "presigned_url": url,
        "created_at": str(img.created_at)
    }

# --- Handler para Lambda ---
from mangum import Mangum
handler = Mangum(app)
