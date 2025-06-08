from src.models.user import db
from datetime import datetime
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class Recording(db.Model):
    """Modelo para gravações de áudio/vídeo"""
    __tablename__ = 'recordings'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    title = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)  # mp3, mp4, wav, webm
    duration = db.Column(db.Float)  # duração em segundos
    language = db.Column(db.String(10))
    source = db.Column(db.String(20), nullable=False, default='upload')
    status = db.Column(db.String(20), default='pending')  # pending, processing, completed, error
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    external_id = db.Column(db.String(100), nullable=True)  # ID externo (ex: 4COM)

class Transcription(db.Model):
    """Modelo para transcrições de áudio"""
    __tablename__ = 'transcriptions'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    recording_id = db.Column(db.String(36), db.ForeignKey('recordings.id'), nullable=False)
    full_text = db.Column(db.Text)
    summary = db.Column(db.Text)
    sentiment_score = db.Column(db.Float)  # pontuação de sentimento (-1 a 1)
    average_talk_time = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

class TranscriptionSegment(db.Model):
    """Modelo para segmentos de transcrição (trechos com timestamps)"""
    __tablename__ = 'transcription_segments'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    transcription_id = db.Column(db.String(36), db.ForeignKey('transcriptions.id'), nullable=False)
    start_time = db.Column(db.Float, nullable=False)  # tempo de início em segundos
    end_time = db.Column(db.Float, nullable=False)  # tempo de fim em segundos
    text = db.Column(db.Text, nullable=False)
    speaker = db.Column(db.String(50))  # identificação do falante
    sentiment = db.Column(db.String(20))
    is_critical = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Keyword(db.Model):
    """Modelo para palavras-chave extraídas da transcrição"""
    __tablename__ = 'keywords'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    transcription_id = db.Column(db.String(36), db.ForeignKey('transcriptions.id'), nullable=False)
    word = db.Column(db.String(100), nullable=False)
    count = db.Column(db.Integer, nullable=False, default=1)  # número de ocorrências
    frequency = db.Column(db.Float)  # frequência relativa
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
