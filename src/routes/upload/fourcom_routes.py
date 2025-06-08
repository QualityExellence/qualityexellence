from flask import Blueprint, request, jsonify, current_app
import os
import requests
import logging
from datetime import datetime, timedelta
import json
from flask_jwt_extended import jwt_required, get_jwt_identity
import uuid

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Criar blueprint
fourcom_bp = Blueprint('fourcom', __name__, url_prefix='/api/fourcom')

# Configurações da API 4COM
FOURCOM_API_URL = os.getenv('FOURCOM_API_URL', 'https://api.4com.com/v1')
FOURCOM_API_KEY = os.getenv('FOURCOM_API_KEY', '')

def get_4com_headers():
    """Retorna os headers para a API 4COM"""
    return {
        'Authorization': f'Bearer {FOURCOM_API_KEY}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

def is_api_configured():
    """Verifica se a API 4COM está configurada"""
    return FOURCOM_API_KEY and FOURCOM_API_URL

@fourcom_bp.route('/status', methods=['GET'])
@jwt_required()
def api_status():
    """
    Verifica o status da conexão com a API 4COM

    Returns:
        JSON: Status da conexão
    """
    try:
        if not is_api_configured():
            return jsonify({
                'status': 'not_configured',
                'message': 'API 4COM não configurada. Configure as variáveis de ambiente FOURCOM_API_URL e FOURCOM_API_KEY.'
            }), 200

        # Tentar fazer uma requisição simples para verificar a conexão
        response = requests.get(
            f"{FOURCOM_API_URL}/status",
            headers=get_4com_headers(),
            timeout=5
        )

        if response.status_code == 200:
            return jsonify({
                'status': 'connected',
                'message': 'Conexão com a API 4COM estabelecida com sucesso.'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': f'Erro ao conectar com a API 4COM. Status code: {response.status_code}'
            }), 200

    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao verificar status da API 4COM: {str(e)}")

        return jsonify({
            'status': 'error',
            'message': f'Erro ao conectar com a API 4COM: {str(e)}'
        }), 200
    except Exception as e:
        logger.error(f"Erro inesperado ao verificar status da API 4COM: {str(e)}")

        return jsonify({
            'status': 'error',
            'message': f'Erro inesperado ao verificar status da API 4COM: {str(e)}'
        }), 200

@fourcom_bp.route('/import', methods=['GET', 'POST'])
@jwt_required()
def import_recordings():
    """
    Importa gravações da API 4COM

    Query params:
        start_date (str): Data inicial no formato YYYY-MM-DD
        end_date (str): Data final no formato YYYY-MM-DD

    Returns:
        JSON: Lista de gravações importadas
    """
    try:
        current_user_id = get_jwt_identity()

        # Obter parâmetros
        if request.method == 'GET':
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
        else:  # POST
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Dados não fornecidos'}), 400
            start_date = data.get('start_date')
            end_date = data.get('end_date')

        # Validar parâmetros
        if not start_date:
            return jsonify({'error': 'Data inicial é obrigatória'}), 422

        if not end_date:
            return jsonify({'error': 'Data final é obrigatória'}), 422

        # Validar formato das datas
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Formato de data inválido. Use YYYY-MM-DD'}), 422

        # Verificar se a data inicial é menor que a data final
        if start_date_obj > end_date_obj:
            return jsonify({'error': 'Data inicial deve ser menor ou igual à data final'}), 422

        # Verificar se o período é de no máximo 31 dias
        if (end_date_obj - start_date_obj).days > 31:
            return jsonify({'error': 'O período máximo para importação é de 31 dias'}), 422

        # Verificar se a API está configurada
        if not is_api_configured():
            logger.warning("API 4COM não configurada. Usando dados simulados.")

            # Simular importação
            recordings = simulate_recordings(start_date_obj, end_date_obj)

            return jsonify({
                'message': 'Importação simulada concluída com sucesso',
                'recordings': recordings,
                'count': len(recordings),
                'simulated': True
            }), 200

        # Tentar importar da API real
        try:
            # Formatar datas para o formato esperado pela API
            start_date_formatted = start_date_obj.strftime('%Y-%m-%d')
            end_date_formatted = end_date_obj.strftime('%Y-%m-%d')

            # Fazer requisição para a API 4COM
            response = requests.get(
                f"{FOURCOM_API_URL}/recordings",
                headers=get_4com_headers(),
                params={
                    'start_date': start_date_formatted,
                    'end_date': end_date_formatted
                },
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"Erro ao importar gravações da API 4COM. Status code: {response.status_code}")
                logger.error(f"Resposta: {response.text}")

                # Fallback para simulação
                recordings = simulate_recordings(start_date_obj, end_date_obj)

                return jsonify({
                    'message': 'Erro ao importar gravações da API 4COM. Usando dados simulados.',
                    'recordings': recordings,
                    'count': len(recordings),
                    'simulated': True,
                    'api_error': f"Status code: {response.status_code}"
                }), 200

            # Processar resposta
            data = response.json()
            recordings = data.get('recordings', [])

            # Se não houver gravações, usar simulação
            if not recordings:
                logger.info("Nenhuma gravação encontrada na API 4COM. Usando dados simulados.")
                recordings = simulate_recordings(start_date_obj, end_date_obj)

                return jsonify({
                    'message': 'Nenhuma gravação encontrada na API 4COM. Usando dados simulados.',
                    'recordings': recordings,
                    'count': len(recordings),
                    'simulated': True
                }), 200

            return jsonify({
                'message': 'Importação concluída com sucesso',
                'recordings': recordings,
                'count': len(recordings),
                'simulated': False
            }), 200

        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao importar gravações da API 4COM: {str(e)}")

            # Fallback para simulação
            recordings = simulate_recordings(start_date_obj, end_date_obj)

            return jsonify({
                'message': f'Erro ao importar gravações da API 4COM: {str(e)}. Usando dados simulados.',
                'recordings': recordings,
                'count': len(recordings),
                'simulated': True,
                'api_error': str(e)
            }), 200

    except Exception as e:
        logger.error(f"Erro inesperado ao importar gravações: {str(e)}")
        return jsonify({'error': f'Erro inesperado ao importar gravações: {str(e)}'}), 500

def simulate_recordings(start_date, end_date):
    """
    Simula gravações para um período

    Args:
        start_date (datetime): Data inicial
        end_date (datetime): Data final

    Returns:
        list: Lista de gravações simuladas
    """
    recordings = []
    current_date = start_date

    # Gerar gravações para cada dia no período
    while current_date <= end_date:
        # Número aleatório de gravações por dia (1-5)
        num_recordings = min(5, (hash(current_date.strftime('%Y-%m-%d')) % 5) + 1)

        for i in range(num_recordings):
            # Gerar horário aleatório
            hour = (hash(f"{current_date.strftime('%Y-%m-%d')}-{i}") % 12) + 8  # 8h-20h
            minute = (hash(f"{current_date.strftime('%Y-%m-%d')}-{i}-minute") % 60)

            # Duração aleatória (1-15 minutos)
            duration = (hash(f"{current_date.strftime('%Y-%m-%d')}-{i}-duration") % 15) + 1

            # Tipo aleatório
            file_type = "mp3" if (hash(f"{current_date.strftime('%Y-%m-%d')}-{i}-type") % 2) == 0 else "mp4"

            # Gerar título
            client_id = (hash(f"{current_date.strftime('%Y-%m-%d')}-{i}-client") % 100) + 1
            title = f"Atendimento Cliente {client_id}"

            # Gerar ID único
            recording_id = str(uuid.uuid4())

            recordings.append({
                'id': recording_id,
                'title': title,
                'date': current_date.strftime('%Y-%m-%d'),
                'time': f"{hour:02d}:{minute:02d}",
                'duration': duration * 60,  # em segundos
                'type': file_type,
                'url': f"https://api.4com.com/v1/recordings/{recording_id}.{file_type}",
                'operator': f"Operador {(hash(f'{current_date.strftime('%Y-%m-%d')}-{i}-operator') % 10) + 1}",
                'client': f"Cliente {client_id}",
                'status': "completed"
            })

        current_date += timedelta(days=1)

    return recordings

@fourcom_bp.route('/download/<recording_id>', methods=['GET'])
@jwt_required()
def download_recording(recording_id):
    """
    Baixa uma gravação da API 4COM

    Path params:
        recording_id (str): ID da gravação

    Returns:
        JSON: URL para download da gravação
    """
    try:
        # Verificar se a API está configurada
        if not is_api_configured():
            logger.warning("API 4COM não configurada. Usando URL simulada.")

            # Simular URL de download
            file_type = "mp3" if (hash(recording_id) % 2) == 0 else "mp4"
            download_url = f"https://api.4com.com/v1/recordings/{recording_id}.{file_type}"

            return jsonify({
                'message': 'URL de download simulada gerada com sucesso',
                'download_url': download_url,
                'simulated': True
            }), 200

        # Tentar obter URL de download da API real
        try:
            response = requests.get(
                f"{FOURCOM_API_URL}/recordings/{recording_id}/download",
                headers=get_4com_headers(),
                timeout=10
            )

            if response.status_code != 200:
                logger.error(f"Erro ao obter URL de download. Status code: {response.status_code}")
                logger.error(f"Resposta: {response.text}")

                # Fallback para URL simulada
                file_type = "mp3" if (hash(recording_id) % 2) == 0 else "mp4"
                download_url = f"https://api.4com.com/v1/recordings/{recording_id}.{file_type}"

                return jsonify({
                    'message': 'Erro ao obter URL de download. Usando URL simulada.',
                    'download_url': download_url,
                    'simulated': True,
                    'api_error': f"Status code: {response.status_code}"
                }), 200

            # Processar resposta
            data = response.json()
            download_url = data.get('download_url')

            if not download_url:
                logger.error("URL de download não encontrada na resposta da API")

                # Fallback para URL simulada
                file_type = "mp3" if (hash(recording_id) % 2) == 0 else "mp4"
                download_url = f"https://api.4com.com/v1/recordings/{recording_id}.{file_type}"

                return jsonify({
                    'message': 'URL de download não encontrada na resposta da API. Usando URL simulada.',
                    'download_url': download_url,
                    'simulated': True
                }), 200

            return jsonify({
                'message': 'URL de download obtida com sucesso',
                'download_url': download_url,
                'simulated': False
            }), 200

        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao obter URL de download: {str(e)}")

            # Fallback para URL simulada
            file_type = "mp3" if (hash(recording_id) % 2) == 0 else "mp4"
            download_url = f"https://api.4com.com/v1/recordings/{recording_id}.{file_type}"

            return jsonify({
                'message': f'Erro ao obter URL de download: {str(e)}. Usando URL simulada.',
                'download_url': download_url,
                'simulated': True,
                'api_error': str(e)
            }), 200

    except Exception as e:
        logger.error(f"Erro inesperado ao obter URL de download: {str(e)}")
        return jsonify({'error': f'Erro inesperado ao obter URL de download: {str(e)}'}), 500
