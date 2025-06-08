import os
import requests
import random
import uuid
import logging
from datetime import datetime, timedelta

# Configurar logger
logger = logging.getLogger(__name__)

def import_recordings(start_date, end_date, operator=None):
    """
    Importa gravações da API 4COM ou gera dados simulados
    """
    try:
        # SEMPRE usar dados simulados para desenvolvimento
        logger.info("Usando dados simulados para importação da 4COM")
        recordings = _get_mock_recordings(start_date, end_date, operator)

        # Salvar no banco de dados
        _save_recordings_to_db(recordings)

        return recordings
    except Exception as e:
        logger.error(f"Erro ao importar gravações da API 4COM: {str(e)}")
        raise

def _get_mock_recordings(start_date, end_date, operator=None):
    """
    Gera dados simulados de gravações
    """
    # Converter strings de data para objetos datetime
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')

    # Gerar gravações simuladas
    recordings = []

    # Operadores simulados
    operators = ['João Silva', 'Maria Oliveira', 'Carlos Santos']
    if operator and operator != 'Todos':
        operators = [operator]

    # Tipos de arquivo
    file_types = ['mp3', 'mp4', 'wav']

    # Gerar entre 5 e 15 gravações aleatórias
    num_recordings = random.randint(5, 15)

    for i in range(num_recordings):
        # Data aleatória entre start_date e end_date
        days_diff = (end - start).days
        random_days = random.randint(0, max(0, days_diff))
        recording_date = start + timedelta(days=random_days)

        # Hora aleatória
        hour = random.randint(8, 17)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        recording_time = recording_date.replace(hour=hour, minute=minute, second=second)

        # Operador aleatório
        recording_operator = random.choice(operators)

        # Duração aleatória entre 1 e 15 minutos
        duration = random.randint(60, 900)

        # Tipo de arquivo aleatório
        file_type = random.choice(file_types)

        # Criar gravação simulada
        recording = {
            'id': str(uuid.uuid4()),
            'title': f"Atendimento Cliente {i+1}",
            'date': recording_time.strftime('%Y-%m-%d %H:%M:%S'),
            'operator': recording_operator,
            'duration': duration,
            'file_type': file_type,
            'url': f"https://api.4com.com/recordings/{uuid.uuid4( )}.{file_type}"
        }

        recordings.append(recording)

    return recordings

def _save_recordings_to_db(recordings):
    """
    Salva as gravações no banco de dados
    """
    try:
        from src.models.transcription import Recording
        from src.models.user import db, User

        # Obter o primeiro usuário disponível (para desenvolvimento)
        user = User.query.first()

        if not user:
            logger.error("Nenhum usuário encontrado para associar às gravações")
            return

        for rec in recordings:
            # Verificar se a gravação já existe
            existing = Recording.query.filter_by(external_id=rec['id']).first()
            if not existing:
                # Criar nova gravação
                recording = Recording(
                    external_id=rec['id'],
                    title=rec['title'],
                    date=datetime.strptime(rec['date'], '%Y-%m-%d %H:%M:%S'),
                    operator=rec['operator'],
                    duration=rec['duration'],
                    file_type=rec['file_type'],
                    url=rec['url'],
                    user_id=user.id  # Associar ao primeiro usuário
                )
                db.session.add(recording)

        db.session.commit()
        logger.info(f"Salvas {len(recordings)} gravações no banco de dados")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao salvar gravações no banco de dados: {str(e)}")
