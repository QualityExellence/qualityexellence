import uuid
from datetime import datetime
from src.models.user import db

def generate_uuid():
    """Gera um UUID único para usar como ID"""
    return str(uuid.uuid4())

class BaseModel:
    """Modelo base com campos comuns"""
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
