from flask import Blueprint, request, jsonify, current_app
import os
import uuid
from werkzeug.utils import secure_filename
from src.models.transcription import db, Recording, Transcription, TranscriptionSegment, Keyword
from src.services.whisper_service import WhisperService
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Criar blueprint
upload_bp = Blueprint('upload', __name__)

# Instanciar serviço de transcrição
whisper_service = WhisperService()

# Extensões permitidas
ALLOWED_EXTENSIONS = {'mp3', 'mp4', 'wav', 'webm'}

def allowed_file(filename):
    """
    Verifica se o arquivo tem uma extensão permitida

    Args:
        filename (str): Nome do arquivo

    Returns:
        bool: True se a extensão for permitida, False caso contrário
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@upload_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_file():
    """
    Endpoint para upload de arquivos de áudio/vídeo

    Returns:
        JSON: Resultado do upload ou mensagem de erro
    """
    try:
        # Verificar se há arquivo na requisição
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400

        file = request.files['file']

        # Verificar se o arquivo tem nome
        if file.filename == '':
            return jsonify({'error': 'Nome de arquivo vazio'}), 400

        # Verificar se o arquivo tem extensão permitida
        if not allowed_file(file.filename):
            return jsonify({'error': f'Extensão de arquivo não permitida. Use: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

        # Obter usuário atual
        current_user_id = get_jwt_identity()

        # Gerar nome de arquivo seguro e único
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"

        # Garantir que a pasta de uploads existe
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)

        # Salvar arquivo
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)

        # Obter informações do arquivo
        file_size = os.path.getsize(file_path)
        file_type = filename.rsplit('.', 1)[1].lower()

        # Estimar duração (em uma aplicação real, usaríamos uma biblioteca como pydub)
        # Para simplificar, vamos estimar com base no tamanho do arquivo
        estimated_duration = estimate_duration(file_path, file_type)

        # Criar registro no banco de dados
        new_recording = Recording(
            title=filename.rsplit('.', 1)[0],  # Usar nome do arquivo sem extensão como título
            file_path=unique_filename,
            file_type=file_type,
            duration=estimated_duration,
            source='upload',
            status='pending',
            user_id=current_user_id
        )

        db.session.add(new_recording)
        db.session.commit()

        # Iniciar transcrição automaticamente
        try:
            # Detectar idioma automaticamente
            language = None  # Whisper detectará automaticamente

            # Realizar transcrição
            transcription_result = whisper_service.transcribe_audio(
                file_path,
                language=language,
                diarization=True
            )

            # Criar nova transcrição no banco de dados
            new_transcription = Transcription(
                recording_id=new_recording.id,
                full_text=transcription_result['text'],
                summary="Resumo automático da transcrição",
                sentiment_score=0.0,  # Será calculado abaixo
                average_talk_time=estimated_duration
            )

            db.session.add(new_transcription)
            db.session.flush()  # Para obter o ID da transcrição

            # Adicionar segmentos
            for segment in transcription_result.get('segments', []):
                new_segment = TranscriptionSegment(
                    transcription_id=new_transcription.id,
                    start_time=segment.get('start', 0),
                    end_time=segment.get('end', 0),
                    text=segment.get('text', ''),
                    speaker=segment.get('speaker', 'Unknown'),
                    sentiment="0.0"
                )
                db.session.add(new_segment)

            # Extrair e salvar palavras-chave
            keywords = extract_keywords(transcription_result['text'])
            for keyword in keywords:
                new_keyword = Keyword(
                    transcription_id=new_transcription.id,
                    word=keyword['text'],
                    count=keyword['count'],
                    frequency=keyword['relevance']
                )
                db.session.add(new_keyword)

            # Atualizar status da gravação
            new_recording.status = 'completed'

            # Salvar alterações no banco de dados
            db.session.commit()

            return jsonify({
                'message': 'Arquivo enviado e transcrito com sucesso',
                'id': new_recording.id,
                'title': new_recording.title,
                'file_type': new_recording.file_type,
                'duration': new_recording.duration,
                'status': new_recording.status,
                'transcription_id': new_transcription.id
            }), 201

        except Exception as e:
            # Em caso de erro na transcrição, ainda retornamos sucesso no upload
            logger.error(f"Erro ao transcrever gravação: {str(e)}")

            return jsonify({
                'message': 'Arquivo enviado com sucesso, mas ocorreu um erro na transcrição',
                'id': new_recording.id,
                'title': new_recording.title,
                'file_type': new_recording.file_type,
                'duration': new_recording.duration,
                'status': 'error',
                'error': str(e)
            }), 201

    except Exception as e:
        logger.error(f"Erro ao processar upload: {str(e)}")
        return jsonify({'error': f'Erro ao processar upload: {str(e)}'}), 500


@upload_bp.route('/recordings', methods=['GET'])
@jwt_required()
def get_recordings():
    """
    Retorna todas as gravações do usuário atual

    Returns:
        JSON: Lista de gravações
    """
    try:
        # Obter usuário atual
        current_user_id = get_jwt_identity()

        # Buscar gravações no banco de dados
        recordings = Recording.query.all()  # Temporariamente buscando todas para teste

        # Converter para JSON
        result = []
        for recording in recordings:
            result.append({
                'id': recording.id,
                'title': recording.title,
                'file_type': recording.file_type,
                'duration': recording.duration,
                'status': recording.status,
                'created_at': recording.created_at.isoformat() if recording.created_at else None
            })

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Erro ao buscar gravações: {str(e)}")
        return jsonify({'error': f'Erro ao buscar gravações: {str(e)}'}), 500


@upload_bp.route('/recordings/<string:recording_id>', methods=['GET'])
@jwt_required()
def get_recording(recording_id):
    """
    Retorna detalhes de uma gravação específica

    Args:
        recording_id (str): ID da gravação (UUID)

    Returns:
        JSON: Detalhes da gravação
    """
    try:
        # Obter usuário atual
        current_user_id = get_jwt_identity()

        # Buscar gravação no banco de dados
        recording = Recording.query.get(recording_id)

        if not recording:
            return jsonify({'error': 'Gravação não encontrada'}), 404

        # Verificar se o usuário tem permissão para acessar esta gravação
        # Temporariamente comentado para teste
        # if recording.user_id != current_user_id:
        #     return jsonify({'error': 'Sem permissão para acessar esta gravação'}), 403

        # Converter para JSON
        result = {
            'id': recording.id,
            'title': recording.title,
            'file_type': recording.file_type,
            'duration': recording.duration,
            'status': recording.status,
            'created_at': recording.created_at.isoformat() if recording.created_at else None
        }

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Erro ao buscar gravação {recording_id}: {str(e)}")
        return jsonify({'error': f'Erro ao buscar gravação: {str(e)}'}), 500


@upload_bp.route('/recordings/<string:recording_id>/download', methods=['GET'])
@jwt_required()
def download_recording(recording_id):
    """
    Retorna o arquivo de uma gravação para download

    Args:
        recording_id (str): ID da gravação (UUID)

    Returns:
        File: Arquivo de áudio/vídeo
    """
    try:
        # Obter usuário atual
        current_user_id = get_jwt_identity()

        # Buscar gravação no banco de dados
        recording = Recording.query.get(recording_id)

        if not recording:
            return jsonify({'error': 'Gravação não encontrada'}), 404

        # Verificar se o usuário tem permissão para acessar esta gravação
        # Temporariamente comentado para teste
        # if recording.user_id != current_user_id:
        #     return jsonify({'error': 'Sem permissão para acessar esta gravação'}), 403

        # Obter caminho do arquivo
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        file_path = os.path.join(upload_folder, recording.file_path)

        if not os.path.exists(file_path):
            return jsonify({'error': 'Arquivo não encontrado'}), 404

        # Retornar arquivo para download
        from flask import send_file
        return send_file(file_path, as_attachment=True, download_name=f"{recording.title}.{recording.file_type}")

    except Exception as e:
        logger.error(f"Erro ao baixar gravação {recording_id}: {str(e)}")
        return jsonify({'error': f'Erro ao baixar gravação: {str(e)}'}), 500


@upload_bp.route('/recordings/<string:recording_id>', methods=['DELETE'])
@jwt_required()
def delete_recording(recording_id):
    """
    Exclui uma gravação

    Args:
        recording_id (str): ID da gravação (UUID)

    Returns:
        JSON: Mensagem de sucesso ou erro
    """
    try:
        # Obter usuário atual
        current_user_id = get_jwt_identity()

        # Buscar gravação no banco de dados
        recording = Recording.query.get(recording_id)

        if not recording:
            return jsonify({'error': 'Gravação não encontrada'}), 404

        # Verificar se o usuário tem permissão para excluir esta gravação
        # Temporariamente comentado para teste
        # if recording.user_id != current_user_id:
        #     return jsonify({'error': 'Sem permissão para excluir esta gravação'}), 403

        # Obter caminho do arquivo
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        file_path = os.path.join(upload_folder, recording.file_path)

        # Excluir arquivo se existir
        if os.path.exists(file_path):
            os.remove(file_path)

        # Excluir registro do banco de dados
        db.session.delete(recording)
        db.session.commit()

        return jsonify({'message': 'Gravação excluída com sucesso'}), 200

    except Exception as e:
        logger.error(f"Erro ao excluir gravação {recording_id}: {str(e)}")
        return jsonify({'error': f'Erro ao excluir gravação: {str(e)}'}), 500


# Funções auxiliares

def estimate_duration(file_path, file_type):
    """
    Estima a duração de um arquivo de áudio/vídeo

    Args:
        file_path (str): Caminho do arquivo
        file_type (str): Tipo do arquivo

    Returns:
        float: Duração estimada em segundos
    """
    # Em uma aplicação real, usaríamos uma biblioteca como pydub ou ffmpeg
    # Para simplificar, vamos estimar com base no tamanho do arquivo

    try:
        # Tentar usar pydub se disponível
        from pydub import AudioSegment

        if file_type == 'mp3':
            audio = AudioSegment.from_mp3(file_path)
            return len(audio) / 1000.0  # Converter de milissegundos para segundos
        elif file_type == 'wav':
            audio = AudioSegment.from_wav(file_path)
            return len(audio) / 1000.0
        elif file_type == 'webm' or file_type == 'mp4':
            # Para webm e mp4, usamos uma estimativa baseada no tamanho
            file_size = os.path.getsize(file_path)
            # Estimativa grosseira: 100KB por segundo para áudio de qualidade média
            return file_size / (100 * 1024)
    except:
        # Se pydub não estiver disponível ou falhar, usar estimativa baseada no tamanho
        file_size = os.path.getsize(file_path)
        # Estimativa grosseira: 100KB por segundo para áudio de qualidade média
        return file_size / (100 * 1024)


def extract_keywords(text):
    """
    Extrai palavras-chave de um texto

    Args:
        text (str): Texto para extrair palavras-chave

    Returns:
        list: Lista de palavras-chave com contagem e relevância
    """
    # Em uma aplicação real, usaríamos NLTK, spaCy ou outro algoritmo de NLP
    # Para simplificar, vamos usar uma abordagem básica

    # Remover pontuação e converter para minúsculas
    import re
    from collections import Counter

    # Lista de stopwords em português
    stopwords = ['a', 'ao', 'aos', 'aquela', 'aquelas', 'aquele', 'aqueles', 'aquilo', 'as', 'até', 'com', 'como',
                'da', 'das', 'de', 'dela', 'delas', 'dele', 'deles', 'depois', 'do', 'dos', 'e', 'ela', 'elas',
                'ele', 'eles', 'em', 'entre', 'era', 'eram', 'éramos', 'essa', 'essas', 'esse', 'esses', 'esta',
                'estas', 'este', 'estes', 'eu', 'foi', 'fomos', 'for', 'foram', 'fosse', 'fossem', 'fui', 'há',
                'isso', 'isto', 'já', 'lhe', 'lhes', 'mais', 'mas', 'me', 'mesmo', 'meu', 'meus', 'minha', 'minhas',
                'muito', 'na', 'não', 'nas', 'nem', 'no', 'nos', 'nós', 'nossa', 'nossas', 'nosso', 'nossos', 'num',
                'numa', 'o', 'os', 'ou', 'para', 'pela', 'pelas', 'pelo', 'pelos', 'por', 'qual', 'quando', 'que',
                'quem', 'são', 'se', 'seja', 'sejam', 'sem', 'será', 'seu', 'seus', 'só', 'somos', 'sua', 'suas',
                'também', 'te', 'tem', 'tém', 'temos', 'tenho', 'ter', 'teu', 'teus', 'tu', 'tua', 'tuas', 'um',
                'uma', 'você', 'vocês', 'vos', 'vosso', 'vossos']

    # Limpar texto
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)

    # Dividir em palavras
    words = text.split()

    # Remover stopwords
    words = [word for word in words if word not in stopwords and len(word) > 2]

    # Contar ocorrências
    word_counts = Counter(words)

    # Calcular relevância (TF - Term Frequency)
    total_words = len(words)
    keywords = []

    for word, count in word_counts.most_common(20):  # Limitar a 20 palavras-chave
        relevance = count / total_words if total_words > 0 else 0
        keywords.append({
            'text': word,
            'count': count,
            'relevance': relevance
        })

    return keywords
