from flask import Blueprint, request, jsonify, current_app
import os
import json
from datetime import datetime, timedelta
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
import matplotlib.pyplot as plt
import io
import base64

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Criar blueprint
dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    """
    Obtém estatísticas para o dashboard

    Returns:
        JSON: Estatísticas do dashboard
    """
    try:
        # Obter ID do usuário atual
        current_user_id = get_jwt_identity()

        # Estatísticas de gravações
        recordings_count = Recording.query.filter_by(user_id=current_user_id).count()

        # Estatísticas de transcrições - usar join com Recording para filtrar por user_id
        transcriptions_count = Transcription.query.join(
            Recording, Transcription.recording_id == Recording.id
        ).filter(
            Recording.user_id == current_user_id
        ).count()

        # Tempo médio de atendimento (TMA)
        recordings = Recording.query.filter_by(user_id=current_user_id).all()
        total_duration = sum(r.duration or 0 for r in recordings)
        avg_duration = total_duration / recordings_count if recordings_count > 0 else 0

        # Estatísticas por operador
        operators = db.session.query(Recording.operator, func.count(Recording.id), func.avg(Recording.duration)).\
            filter(Recording.user_id == current_user_id).\
            group_by(Recording.operator).all()

        operator_stats = [
            {
                'name': op[0] or 'Desconhecido',
                'count': op[1],
                'avg_duration': op[2] or 0
            }
            for op in operators
        ]

        return jsonify({
            'recordings_count': recordings_count,
            'transcriptions_count': transcriptions_count,
            'avg_duration': avg_duration,
            'operators': operator_stats
        }), 200

    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas do dashboard: {str(e)}")
        return jsonify({'error': 'Erro ao buscar estatísticas'}), 500



@dashboard_bp.route('/recent-transcriptions', methods=['GET'])
@jwt_required()
def get_recent_transcriptions():
    """
    Retorna as transcrições mais recentes para o dashboard

    Returns:
        JSON: Lista de transcrições recentes
    """
    try:
        # Obter usuário atual
        current_user_id = get_jwt_identity()

        # Buscar transcrições no banco de dados
        from src.models.transcription import Transcription, Recording

        # Limitar a 5 transcrições mais recentes
        transcriptions = Transcription.query.filter_by(user_id=current_user_id).order_by(
            Transcription.created_at.desc()
        ).limit(5).all()

        # Converter para JSON
        result = []
        for transcription in transcriptions:
            # Buscar gravação associada
            recording = Recording.query.get(transcription.recording_id)

            result.append({
                'id': transcription.id,
                'title': recording.title if recording else f'Transcrição {transcription.id}',
                'operator': 'Operador 1',  # Em uma aplicação real, viria do banco de dados
                'created_at': transcription.created_at.isoformat(),
                'duration': transcription.duration,
                'sentiment_score': transcription.sentiment_score
            })

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Erro ao buscar transcrições recentes: {str(e)}")
        return jsonify({'error': f'Erro ao buscar transcrições recentes: {str(e)}'}), 500


@dashboard_bp.route('/chart/<chart_type>', methods=['GET'])
@jwt_required()
def get_chart(chart_type):
    """
    Gera um gráfico para o dashboard

    Args:
        chart_type (str): Tipo de gráfico (calls, sentiment, keywords, operators)

    Query params:
        start_date (str, optional): Data inicial no formato YYYY-MM-DD
        end_date (str, optional): Data final no formato YYYY-MM-DD
        operator (str, optional): ID do operador para filtrar
        sentiment (str, optional): Sentimento para filtrar (positive, neutral, negative)

    Returns:
        Image: Imagem do gráfico em formato PNG
    """
    try:
        # Obter usuário atual
        current_user_id = get_jwt_identity()

        # Obter parâmetros da requisição
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        operator = request.args.get('operator')
        sentiment = request.args.get('sentiment')

        # Buscar dados do dashboard
        dashboard_data = get_dashboard_stats()[0].json

        # Criar figura
        plt.figure(figsize=(10, 6))

        if chart_type == 'calls':
            # Gráfico de chamadas por dia
            dates = [item['date'] for item in dashboard_data['calls_by_day']]
            counts = [item['count'] for item in dashboard_data['calls_by_day']]

            plt.plot(dates, counts, marker='o', linewidth=2, color='#4361ee')
            plt.fill_between(dates, counts, alpha=0.2, color='#4361ee')
            plt.title('Chamadas por Dia')
            plt.xlabel('Data')
            plt.ylabel('Número de Chamadas')
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.tight_layout()

        elif chart_type == 'sentiment':
            # Gráfico de distribuição de sentimento
            labels = ['Positivo', 'Neutro', 'Negativo']
            values = [
                dashboard_data['sentiment_distribution']['positive'],
                dashboard_data['sentiment_distribution']['neutral'],
                dashboard_data['sentiment_distribution']['negative']
            ]
            colors = ['#4cc9f0', '#f8961e', '#f94144']

            plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
            plt.title('Distribuição de Sentimento')
            plt.axis('equal')

        elif chart_type == 'keywords':
            # Gráfico de palavras-chave
            keywords = [item['text'] for item in dashboard_data['top_keywords']]
            counts = [item['count'] for item in dashboard_data['top_keywords']]

            # Inverter para exibir em ordem crescente
            keywords.reverse()
            counts.reverse()

            plt.barh(keywords, counts, color='#4361ee')
            plt.title('Top 10 Palavras-chave')
            plt.xlabel('Frequência')
            plt.tight_layout()

        elif chart_type == 'operators':
            # Gráfico de desempenho por operador
            operators = [item['name'] for item in dashboard_data['operators_performance']]
            calls = [item['calls'] for item in dashboard_data['operators_performance']]
            sentiment = [item['sentiment'] for item in dashboard_data['operators_performance']]

            x = range(len(operators))
            width = 0.35

            plt.bar([i - width/2 for i in x], calls, width, label='Chamadas', color='#4361ee')
            plt.bar([i + width/2 for i in x], sentiment, width, label='Sentimento Médio', color='#4cc9f0')

            plt.xlabel('Operador')
            plt.ylabel('Valor')
            plt.title('Desempenho por Operador')
            plt.xticks(x, operators)
            plt.legend()
            plt.tight_layout()

        else:
            return jsonify({'error': 'Tipo de gráfico inválido'}), 400

        # Salvar gráfico em buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)

        # Converter para base64
        img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

        # Retornar imagem
        return jsonify({
            'image': f'data:image/png;base64,{img_base64}'
        }), 200

    except Exception as e:
        logger.error(f"Erro ao gerar gráfico {chart_type}: {str(e)}")
        return jsonify({'error': f'Erro ao gerar gráfico: {str(e)}'}), 500
