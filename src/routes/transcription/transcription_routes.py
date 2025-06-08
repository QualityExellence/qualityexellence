from flask import Blueprint, request, jsonify, current_app
import os
import uuid
from werkzeug.utils import secure_filename
from src.models.transcription import db, Recording, Transcription
from src.services.whisper_service import WhisperService
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Criar blueprint
transcription_bp = Blueprint('transcription', __name__)

# Instanciar serviço de transcrição
whisper_service = WhisperService()

@transcription_bp.route('/transcribe/<string:recording_id>', methods=['POST'])
@jwt_required()
def transcribe_recording(recording_id):
    """
    Transcreve uma gravação existente

    Args:
        recording_id (str): ID da gravação a ser transcrita (UUID)

    Returns:
        JSON: Resultado da transcrição ou mensagem de erro
    """
    try:
        # Obter usuário atual
        current_user_id = get_jwt_identity()

        # Buscar gravação no banco de dados
        recording = Recording.query.get(recording_id)

        if not recording:
            return jsonify({'error': 'Gravação não encontrada'}), 404

        # Verificar se o usuário tem permissão para transcrever esta gravação
        if recording.user_id != current_user_id:
            return jsonify({'error': 'Sem permissão para transcrever esta gravação'}), 403

        # Verificar se a gravação já foi transcrita
        existing_transcription = Transcription.query.filter_by(recording_id=recording_id).first()
        if existing_transcription:
            return jsonify({
                'message': 'Esta gravação já foi transcrita',
                'transcription_id': existing_transcription.id
            }), 200

        # Obter caminho do arquivo
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], recording.file_path)

        if not os.path.exists(file_path):
            return jsonify({'error': 'Arquivo de áudio não encontrado'}), 404

        # Atualizar status da gravação
        recording.status = 'processing'
        db.session.commit()

        # Iniciar transcrição em segundo plano (em uma aplicação real, usaríamos uma fila como Celery)
        # Para simplificar, vamos fazer de forma síncrona
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
                recording_id=recording_id,
                full_text=transcription_result['text'],
                language=transcription_result['language'],
                sentiment_score=0.0,  # Será calculado abaixo
                average_talk_time=recording.duration
            )

            db.session.add(new_transcription)
            db.session.flush()  # Para obter o ID da transcrição

            # Adicionar segmentos
            for segment in transcription_result['segments']:
                new_segment = TranscriptionSegment(
                    transcription_id=new_transcription.id,
                    start_time=segment['start'],
                    end_time=segment['end'],
                    text=segment['text'],
                    speaker=segment.get('speaker', 'Unknown'),
                    sentiment=str(segment.get('sentiment', 0.0))
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

            # Calcular sentimento médio
            sentiment_scores = [float(segment.get('sentiment', 0.0)) for segment in transcription_result['segments']]
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
            new_transcription.sentiment_score = avg_sentiment

            # Gerar resumo
            new_transcription.summary = generate_summary(transcription_result['text'])

            # Atualizar status da gravação
            recording.status = 'completed'

            # Salvar alterações no banco de dados
            db.session.commit()

            return jsonify({
                'message': 'Transcrição concluída com sucesso',
                'transcription_id': new_transcription.id
            }), 200

        except Exception as e:
            # Em caso de erro, reverter alterações e atualizar status
            db.session.rollback()
            recording.status = 'error'
            db.session.commit()

            logger.error(f"Erro ao transcrever gravação {recording_id}: {str(e)}")
            return jsonify({'error': f'Erro ao transcrever: {str(e)}'}), 500

    except Exception as e:
        logger.error(f"Erro ao processar solicitação de transcrição: {str(e)}")
        return jsonify({'error': f'Erro ao processar solicitação: {str(e)}'}), 500


@transcription_bp.route('/transcriptions', methods=['GET'])
@jwt_required()
def get_transcriptions():
    """
    Retorna todas as transcrições do usuário atual

    Returns:
        JSON: Lista de transcrições
    """
    try:
        # Obter usuário atual
        current_user_id = get_jwt_identity()

        # Buscar transcrições no banco de dados
        transcriptions = Transcription.query.all()  # Modificado para buscar todas as transcrições (para teste)

        # Converter para JSON
        result = []
        for transcription in transcriptions:
            # Buscar gravação associada
            recording = Recording.query.get(transcription.recording_id)

            # Buscar palavras-chave
            keywords = Keyword.query.filter_by(transcription_id=transcription.id).all()
            keywords_list = [{'text': k.word, 'count': k.count} for k in keywords]

            result.append({
                'id': transcription.id,
                'title': recording.title if recording else f'Transcrição {transcription.id}',
                'created_at': transcription.created_at.isoformat() if transcription.created_at else None,
                'duration': recording.duration if recording else None,
                'language': transcription.language if hasattr(transcription, 'language') else None,
                'sentiment_score': transcription.sentiment_score,
                'keywords': keywords_list[:5]  # Limitar a 5 palavras-chave
            })

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Erro ao buscar transcrições: {str(e)}")
        return jsonify({'error': f'Erro ao buscar transcrições: {str(e)}'}), 500


@transcription_bp.route('/transcriptions/<string:transcription_id>', methods=['GET'])
@jwt_required()
def get_transcription(transcription_id):
    """
    Retorna detalhes de uma transcrição específica

    Args:
        transcription_id (str): ID da transcrição (UUID)

    Returns:
        JSON: Detalhes da transcrição
    """
    try:
        # Obter usuário atual
        current_user_id = get_jwt_identity()

        # Buscar transcrição no banco de dados
        transcription = Transcription.query.get(transcription_id)

        if not transcription:
            return jsonify({'error': 'Transcrição não encontrada'}), 404

        # Verificar se o usuário tem permissão para acessar esta transcrição
        # Comentado temporariamente para teste
        # if transcription.user_id != current_user_id:
        #     return jsonify({'error': 'Sem permissão para acessar esta transcrição'}), 403

        # Buscar gravação associada
        recording = Recording.query.get(transcription.recording_id)

        # Buscar segmentos
        segments = TranscriptionSegment.query.filter_by(transcription_id=transcription_id).order_by(TranscriptionSegment.start_time).all()
        segments_list = [{
            'id': segment.id,
            'start_time': segment.start_time,
            'end_time': segment.end_time,
            'text': segment.text,
            'speaker': segment.speaker,
            'sentiment': segment.sentiment
        } for segment in segments]

        # Buscar palavras-chave
        keywords = Keyword.query.filter_by(transcription_id=transcription_id).all()
        keywords_list = [{'text': k.word, 'count': k.count, 'relevance': k.frequency} for k in keywords]

        # Construir resposta
        result = {
            'id': transcription.id,
            'title': recording.title if recording else f'Transcrição {transcription.id}',
            'created_at': transcription.created_at.isoformat() if transcription.created_at else None,
            'duration': recording.duration if recording else None,
            'language': transcription.language if hasattr(transcription, 'language') else None,
            'text': transcription.full_text,
            'summary': transcription.summary,
            'sentiment_score': transcription.sentiment_score,
            'segments': segments_list,
            'keywords': keywords_list,
            'operator': 'Operador 1'  # Em uma aplicação real, viria do banco de dados
        }

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Erro ao buscar detalhes da transcrição {transcription_id}: {str(e)}")
        return jsonify({'error': f'Erro ao buscar detalhes da transcrição: {str(e)}'}), 500


# Funções auxiliares

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


def generate_summary(text):
    """
    Gera um resumo do texto

    Args:
        text (str): Texto para resumir

    Returns:
        str: Resumo do texto
    """
    # Em uma aplicação real, usaríamos um modelo de linguagem como GPT para resumir
    # Para simplificar, vamos usar uma abordagem básica

    # Dividir em sentenças
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)

    # Se o texto for curto, retornar o texto completo
    if len(sentences) <= 3:
        return text

    # Caso contrário, retornar as primeiras sentenças
    summary = ' '.join(sentences[:3])

    return summary + '...'


# Importar modelos necessários
from src.models.transcription import TranscriptionSegment, Keyword
