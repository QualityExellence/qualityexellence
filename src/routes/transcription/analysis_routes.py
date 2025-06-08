from flask import Blueprint, request, jsonify
import os
import json
import numpy as np
from src.models.transcription import db, Transcription, TranscriptionSegment, Keyword
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Criar blueprint
analysis_bp = Blueprint('analysis', __name__)

@analysis_bp.route('/sentiment/<int:transcription_id>', methods=['GET'])
@jwt_required()
def get_sentiment_analysis(transcription_id):
    """
    Retorna análise de sentimento de uma transcrição
    
    Args:
        transcription_id (int): ID da transcrição
        
    Returns:
        JSON: Análise de sentimento ou mensagem de erro
    """
    try:
        # Obter usuário atual
        current_user_id = get_jwt_identity()
        
        # Buscar transcrição no banco de dados
        transcription = Transcription.query.get(transcription_id)
        
        if not transcription:
            return jsonify({'error': 'Transcrição não encontrada'}), 404
        
        # Verificar se o usuário tem permissão para acessar esta transcrição
        if transcription.user_id != current_user_id:
            return jsonify({'error': 'Sem permissão para acessar esta transcrição'}), 403
        
        # Buscar segmentos
        segments = TranscriptionSegment.query.filter_by(transcription_id=transcription_id).order_by(TranscriptionSegment.start_time).all()
        
        # Extrair sentimentos dos segmentos
        sentiments = [segment.sentiment for segment in segments if segment.sentiment is not None]
        
        # Calcular estatísticas
        if sentiments:
            avg_sentiment = sum(sentiments) / len(sentiments)
            min_sentiment = min(sentiments)
            max_sentiment = max(sentiments)
            
            # Calcular distribuição de sentimento
            positive = sum(1 for s in sentiments if s >= 0.3)
            neutral = sum(1 for s in sentiments if s > -0.3 and s < 0.3)
            negative = sum(1 for s in sentiments if s <= -0.3)
            
            # Calcular momentos críticos (segmentos com sentimento muito negativo)
            critical_moments = []
            for segment in segments:
                if segment.sentiment and segment.sentiment <= -0.5:
                    critical_moments.append({
                        'start_time': segment.start_time,
                        'end_time': segment.end_time,
                        'text': segment.text,
                        'sentiment': segment.sentiment,
                        'speaker': segment.speaker
                    })
            
            # Construir resposta
            result = {
                'average_sentiment': avg_sentiment,
                'min_sentiment': min_sentiment,
                'max_sentiment': max_sentiment,
                'distribution': {
                    'positive': positive,
                    'neutral': neutral,
                    'negative': negative,
                    'total': len(sentiments)
                },
                'critical_moments': critical_moments
            }
            
            return jsonify(result), 200
        else:
            return jsonify({'error': 'Não há dados de sentimento disponíveis'}), 404
        
    except Exception as e:
        logger.error(f"Erro ao analisar sentimento da transcrição {transcription_id}: {str(e)}")
        return jsonify({'error': f'Erro ao analisar sentimento: {str(e)}'}), 500


@analysis_bp.route('/keywords/<int:transcription_id>', methods=['GET'])
@jwt_required()
def get_keywords_analysis(transcription_id):
    """
    Retorna análise de palavras-chave de uma transcrição
    
    Args:
        transcription_id (int): ID da transcrição
        
    Returns:
        JSON: Análise de palavras-chave ou mensagem de erro
    """
    try:
        # Obter usuário atual
        current_user_id = get_jwt_identity()
        
        # Buscar transcrição no banco de dados
        transcription = Transcription.query.get(transcription_id)
        
        if not transcription:
            return jsonify({'error': 'Transcrição não encontrada'}), 404
        
        # Verificar se o usuário tem permissão para acessar esta transcrição
        if transcription.user_id != current_user_id:
            return jsonify({'error': 'Sem permissão para acessar esta transcrição'}), 403
        
        # Buscar palavras-chave
        keywords = Keyword.query.filter_by(transcription_id=transcription_id).order_by(Keyword.count.desc()).all()
        
        if keywords:
            # Converter para JSON
            keywords_list = [{
                'text': keyword.text,
                'count': keyword.count,
                'relevance': keyword.relevance
            } for keyword in keywords]
            
            # Calcular estatísticas
            total_words = sum(k.count for k in keywords)
            
            # Construir resposta
            result = {
                'keywords': keywords_list,
                'total_words': total_words,
                'unique_keywords': len(keywords_list)
            }
            
            return jsonify(result), 200
        else:
            return jsonify({'error': 'Não há palavras-chave disponíveis'}), 404
        
    except Exception as e:
        logger.error(f"Erro ao analisar palavras-chave da transcrição {transcription_id}: {str(e)}")
        return jsonify({'error': f'Erro ao analisar palavras-chave: {str(e)}'}), 500


@analysis_bp.route('/tma/<int:transcription_id>', methods=['GET'])
@jwt_required()
def get_tma_analysis(transcription_id):
    """
    Retorna análise de TMA (Tempo Médio de Atendimento) de uma transcrição
    
    Args:
        transcription_id (int): ID da transcrição
        
    Returns:
        JSON: Análise de TMA ou mensagem de erro
    """
    try:
        # Obter usuário atual
        current_user_id = get_jwt_identity()
        
        # Buscar transcrição no banco de dados
        transcription = Transcription.query.get(transcription_id)
        
        if not transcription:
            return jsonify({'error': 'Transcrição não encontrada'}), 404
        
        # Verificar se o usuário tem permissão para acessar esta transcrição
        if transcription.user_id != current_user_id:
            return jsonify({'error': 'Sem permissão para acessar esta transcrição'}), 403
        
        # Buscar segmentos
        segments = TranscriptionSegment.query.filter_by(transcription_id=transcription_id).order_by(TranscriptionSegment.start_time).all()
        
        if segments:
            # Calcular TMA
            tma = transcription.duration
            
            # Calcular tempo de fala por falante
            speaker_times = {}
            for segment in segments:
                speaker = segment.speaker or 'Desconhecido'
                duration = segment.end_time - segment.start_time
                
                if speaker in speaker_times:
                    speaker_times[speaker] += duration
                else:
                    speaker_times[speaker] = duration
            
            # Calcular pausas (períodos sem fala)
            pauses = []
            for i in range(1, len(segments)):
                prev_end = segments[i-1].end_time
                curr_start = segments[i].start_time
                
                if curr_start - prev_end > 2.0:  # Pausas maiores que 2 segundos
                    pauses.append({
                        'start_time': prev_end,
                        'end_time': curr_start,
                        'duration': curr_start - prev_end
                    })
            
            # Construir resposta
            result = {
                'tma': tma,
                'speaker_times': speaker_times,
                'pauses': pauses,
                'total_pauses_duration': sum(p['duration'] for p in pauses),
                'average_pause_duration': sum(p['duration'] for p in pauses) / len(pauses) if pauses else 0
            }
            
            return jsonify(result), 200
        else:
            return jsonify({'error': 'Não há segmentos disponíveis'}), 404
        
    except Exception as e:
        logger.error(f"Erro ao analisar TMA da transcrição {transcription_id}: {str(e)}")
        return jsonify({'error': f'Erro ao analisar TMA: {str(e)}'}), 500
