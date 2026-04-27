from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import uuid

from . import models, schemas, database
# Temporarily comment out AI imports until they are installed
# from ai_services.vision import VisionClassifier 
# from ai_services.audio import AudioTranscriber
# from ai_services.text import TextAnalyzer

# Create tables in the database
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="FixMyHyd Enterprise API", version="2.0")

@app.get("/")
def read_root():
    return {"message": "FixMyHyd API is running asynchronously!"}

# --- USER ENDPOINTS ---
@app.post("/users", response_model=schemas.UserResponse)
def get_or_create_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.telegram_user_id == user.telegram_user_id).first()
    if db_user:
        return db_user
    new_user = models.User(**user.dict())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# --- COMPLAINT ENDPOINTS ---
@app.post("/complaints", response_model=schemas.ComplaintResponse)
def create_complaint(complaint: schemas.ComplaintCreate, db: Session = Depends(database.get_db)):
    # Generate a dummy GHMC ID for now
    ghmc_id = f"GHMC-{str(uuid.uuid4())[:8].upper()}"
    
    new_complaint = models.Complaint(
        **complaint.dict(),
        ghmc_id=ghmc_id,
        status="Pending"
    )
    db.add(new_complaint)
    db.commit()
    db.refresh(new_complaint)
    return new_complaint

@app.get("/complaints", response_model=list[schemas.ComplaintResponse])
def get_complaints(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    return db.query(models.Complaint).offset(skip).limit(limit).all()
