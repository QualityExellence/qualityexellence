from flask import Blueprint, request, jsonify, current_app, render_template
import os
import json
from datetime import datetime
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
from weasyprint import HTML, CSS
import csv
from io import StringIO

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Criar blueprint
export_bp = Blueprint('export', __name__)

@export_bp.route('/pdf/<int:transcription_id>', methods=['GET'])
@jwt_required()
def export_pdf(transcription_id):
    """
    Exporta uma transcrição para PDF
    
    Args:
        transcription_id (int): ID da transcrição
        
    Returns:
        PDF: Arquivo PDF da transcrição
    """
    try:
        # Obter usuário atual
        current_user_id = get_jwt_identity()
        
        # Buscar transcrição no banco de dados
        from src.models.transcription import Transcription, TranscriptionSegment, Keyword, Recording
        transcription = Transcription.query.get(transcription_id)
        
        if not transcription:
            return jsonify({'error': 'Transcrição não encontrada'}), 404
        
        # Verificar se o usuário tem permissão para acessar esta transcrição
        if transcription.user_id != current_user_id:
            return jsonify({'error': 'Sem permissão para acessar esta transcrição'}), 403
        
        # Buscar gravação associada
        recording = Recording.query.get(transcription.recording_id)
        
        # Buscar segmentos
        segments = TranscriptionSegment.query.filter_by(transcription_id=transcription_id).order_by(TranscriptionSegment.start_time).all()
        
        # Buscar palavras-chave
        keywords = Keyword.query.filter_by(transcription_id=transcription_id).order_by(Keyword.count.desc()).all()
        
        # Preparar dados para o template
        data = {
            'transcription': transcription,
            'recording': recording,
            'segments': segments,
            'keywords': keywords,
            'title': recording.title if recording else f'Transcrição {transcription.id}',
            'date': transcription.created_at.strftime('%d/%m/%Y'),
            'time': transcription.created_at.strftime('%H:%M'),
            'duration': format_duration(transcription.duration),
            'sentiment': get_sentiment_text(transcription.sentiment_score)
        }
        
        # Renderizar template HTML
        html_content = render_template('pdf_template.html', **data)
        
        # Criar PDF
        pdf = HTML(string=html_content).write_pdf()
        
        # Retornar PDF
        from flask import send_file
        from io import BytesIO
        
        pdf_io = BytesIO(pdf)
        pdf_io.seek(0)
        
        return send_file(
            pdf_io,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"transcricao_{transcription_id}.pdf"
        )
        
    except Exception as e:
        logger.error(f"Erro ao exportar transcrição {transcription_id} para PDF: {str(e)}")
        return jsonify({'error': f'Erro ao exportar para PDF: {str(e)}'}), 500


@export_bp.route('/csv/<int:transcription_id>', methods=['GET'])
@jwt_required()
def export_csv(transcription_id):
    """
    Exporta uma transcrição para CSV
    
    Args:
        transcription_id (int): ID da transcrição
        
    Returns:
        CSV: Arquivo CSV da transcrição
    """
    try:
        # Obter usuário atual
        current_user_id = get_jwt_identity()
        
        # Buscar transcrição no banco de dados
        from src.models.transcription import Transcription, TranscriptionSegment, Recording
        transcription = Transcription.query.get(transcription_id)
        
        if not transcription:
            return jsonify({'error': 'Transcrição não encontrada'}), 404
        
        # Verificar se o usuário tem permissão para acessar esta transcrição
        if transcription.user_id != current_user_id:
            return jsonify({'error': 'Sem permissão para acessar esta transcrição'}), 403
        
        # Buscar gravação associada
        recording = Recording.query.get(transcription.recording_id)
        
        # Buscar segmentos
        segments = TranscriptionSegment.query.filter_by(transcription_id=transcription_id).order_by(TranscriptionSegment.start_time).all()
        
        # Criar CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Cabeçalho
        writer.writerow(['Início', 'Fim', 'Falante', 'Texto', 'Sentimento'])
        
        # Linhas
        for segment in segments:
            writer.writerow([
                format_timestamp(segment.start_time),
                format_timestamp(segment.end_time),
                segment.speaker,
                segment.text,
                get_sentiment_text(segment.sentiment)
            ])
        
        # Retornar CSV
        from flask import Response
        
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=transcricao_{transcription_id}.csv'
            }
        )
        
    except Exception as e:
        logger.error(f"Erro ao exportar transcrição {transcription_id} para CSV: {str(e)}")
        return jsonify({'error': f'Erro ao exportar para CSV: {str(e)}'}), 500


@export_bp.route('/dashboard/csv', methods=['GET'])
@jwt_required()
def export_dashboard_csv():
    """
    Exporta dados do dashboard para CSV
    
    Query params:
        start_date (str, optional): Data inicial no formato YYYY-MM-DD
        end_date (str, optional): Data final no formato YYYY-MM-DD
        operator (str, optional): ID do operador para filtrar
        sentiment (str, optional): Sentimento para filtrar (positive, neutral, negative)
        
    Returns:
        CSV: Arquivo CSV com dados do dashboard
    """
    try:
        # Obter usuário atual
        current_user_id = get_jwt_identity()
        
        # Obter parâmetros da requisição
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        operator = request.args.get('operator')
        sentiment = request.args.get('sentiment')
        
        # Buscar transcrições no banco de dados com filtros
        from src.models.transcription import Transcription, Recording
        from sqlalchemy import and_, or_
        
        query = Transcription.query.filter_by(user_id=current_user_id)
        
        # Aplicar filtros
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(Transcription.created_at >= start_date_obj)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                query = query.filter(Transcription.created_at <= end_date_obj)
            except ValueError:
                pass
        
        if sentiment:
            if sentiment == 'positive':
                query = query.filter(Transcription.sentiment_score >= 0.3)
            elif sentiment == 'negative':
                query = query.filter(Transcription.sentiment_score <= -0.3)
            elif sentiment == 'neutral':
                query = query.filter(and_(Transcription.sentiment_score > -0.3, Transcription.sentiment_score < 0.3))
        
        # Buscar transcrições
        transcriptions = query.all()
        
        # Criar CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Cabeçalho
        writer.writerow(['ID', 'Título', 'Data', 'Duração', 'Sentimento', 'Resumo'])
        
        # Linhas
        for transcription in transcriptions:
            # Buscar gravação associada
            recording = Recording.query.get(transcription.recording_id)
            
            writer.writerow([
                transcription.id,
                recording.title if recording else f'Transcrição {transcription.id}',
                transcription.created_at.strftime('%d/%m/%Y %H:%M'),
                format_duration(transcription.duration),
                get_sentiment_text(transcription.sentiment_score),
                transcription.summary[:100] + '...' if transcription.summary and len(transcription.summary) > 100 else transcription.summary
            ])
        
        # Retornar CSV
        from flask import Response
        
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'attachment; filename=dashboard_export.csv'
            }
        )
        
    except Exception as e:
        logger.error(f"Erro ao exportar dashboard para CSV: {str(e)}")
        return jsonify({'error': f'Erro ao exportar dashboard: {str(e)}'}), 500


# Funções auxiliares

def format_timestamp(seconds):
    """
    Formata um timestamp em segundos para MM:SS
    
    Args:
        seconds (float): Tempo em segundos
        
    Returns:
        str: Tempo formatado
    """
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    return f"{minutes:02d}:{remaining_seconds:02d}"


def format_duration(seconds):
    """
    Formata uma duração em segundos para MM:SS
    
    Args:
        seconds (float): Duração em segundos
        
    Returns:
        str: Duração formatada
    """
    if not seconds:
        return "00:00"
    return format_timestamp(seconds)


def get_sentiment_text(sentiment):
    """
    Retorna o texto correspondente a um valor de sentimento
    
    Args:
        sentiment (float): Valor de sentimento entre -1 e 1
        
    Returns:
        str: Texto do sentimento
    """
    if sentiment >= 0.3:
        return "Positivo"
    elif sentiment <= -0.3:
        return "Negativo"
    else:
        return "Neutro"
