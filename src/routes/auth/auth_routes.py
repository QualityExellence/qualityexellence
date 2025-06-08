from flask import Blueprint, request, jsonify, current_app
from src.models.user import db, User
import uuid
import logging
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import re
import os

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Criar blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Validação de email
def is_valid_email(email):
    """Verifica se o email é válido"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# Validação de senha
def is_valid_password(password):
    """Verifica se a senha atende aos requisitos mínimos"""
    if len(password) < 8:
        return False, "A senha deve ter pelo menos 8 caracteres"

    if not re.search(r'[A-Z]', password):
        return False, "A senha deve conter pelo menos uma letra maiúscula"

    if not re.search(r'[a-z]', password):
        return False, "A senha deve conter pelo menos uma letra minúscula"

    if not re.search(r'[0-9]', password):
        return False, "A senha deve conter pelo menos um número"

    return True, ""

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """
    Obtém o perfil do usuário atual

    Returns:
        JSON: Informações do usuário
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.filter_by(id=current_user_id).first()

        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404

        return jsonify(user.to_dict()), 200

    except Exception as e:
        logger.error(f"Erro ao obter perfil: {str(e)}")
        return jsonify({'error': f'Erro ao obter perfil: {str(e)}'}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    Realiza o logout do usuário

    Returns:
        JSON: Status do logout
    """
    response = jsonify({'message': 'Logout realizado com sucesso'})
    response.delete_cookie('access_token_cookie')
    return response, 200

@auth_bp.route('/register', methods=['POST', 'GET'])
def register():
    """
    Registra um novo usuário

    Request body:
        name (str): Nome do usuário
        email (str): Email do usuário
        password (str): Senha do usuário
        organization_name (str, optional): Nome da organização (se for criar uma nova)

    Returns:
        JSON: Status do registro
    """
    # Para requisições GET, apenas retornar status OK
    if request.method == 'GET':
        return jsonify({'message': 'Endpoint de registro disponível'}), 200

    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400

        # Validar campos obrigatórios
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        organization_name = data.get('organization_name')

        if not name:
            return jsonify({'error': 'Nome é obrigatório'}), 400

        if not email:
            return jsonify({'error': 'Email é obrigatório'}), 400

        if not password:
            return jsonify({'error': 'Senha é obrigatória'}), 400

        # Validar email
        if not is_valid_email(email):
            return jsonify({'error': 'Email inválido'}), 400

        # Validar senha
        is_valid, password_error = is_valid_password(password)
        if not is_valid:
            return jsonify({'error': password_error}), 400

        # Verificar se o email já está em uso
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'error': 'Email já cadastrado'}), 400

        # Criar usuário
        new_user = User(
            id=str(uuid.uuid4()),
            name=name,
            email=email,
            role='admin' if organization_name else 'operator',  # Admin se criar organização, operador se for convidado
            organization_id=str(uuid.uuid4()) if organization_name else None  # Gerar ID de organização se fornecido nome
        )

        # Definir senha
        new_user.set_password(password)

        # Adicionar ao banco de dados
        db.session.add(new_user)

        # Se for criar organização, adicionar nome
        if organization_name:
            # Em um cenário real, você teria um modelo Organization
            # Por simplicidade, vamos apenas simular isso
            logger.info(f"Criando organização: {organization_name} com ID: {new_user.organization_id}")

        db.session.commit()

        return jsonify({
            'message': 'Usuário registrado com sucesso',
            'user_id': new_user.id
        }), 201

    except Exception as e:
        logger.error(f"Erro ao registrar usuário: {str(e)}")
        db.session.rollback()
        return jsonify({'error': f'Erro ao registrar usuário: {str(e)}'}), 500

@auth_bp.route('/login', methods=['POST', 'GET'])
def login():
    """
    Autentica um usuário

    Request body:
        email (str): Email do usuário
        password (str): Senha do usuário

    Returns:
        JSON: Token de acesso e informações do usuário
    """
    # Para requisições GET, apenas retornar status OK
    if request.method == 'GET':
        return jsonify({'message': 'Endpoint de login disponível'}), 200

    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400

        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'error': 'Email e senha são obrigatórios'}), 400

        # Buscar usuário pelo email
        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            return jsonify({'error': 'Email ou senha inválidos'}), 401

        # Atualizar último login
        user.last_login = datetime.utcnow()
        db.session.commit()

        # Criar token JWT
        access_token = create_access_token(
            identity=user.id,  # O ID do usuário será armazenado no token
            expires_delta=timedelta(hours=24)  # Token válido por 24 horas
        )

        # Opcionalmente, definir o token como cookie
        response = jsonify({
            'access_token': access_token,
            'user': user.to_dict()
        })

        # Definir cookie (opcional, mas recomendado para maior compatibilidade)
        response.set_cookie(
            'access_token_cookie',
            access_token,
            httponly=True,  # Impede acesso via JavaScript (segurança )
            max_age=86400,  # 24 horas em segundos
            path='/'  # Válido para todo o site
        )

        return response, 200

    except Exception as e:
        logger.error(f"Erro ao fazer login: {str(e)}")
        return jsonify({'error': f'Erro ao fazer login: {str(e)}'}), 500

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """
    Atualiza o perfil do usuário atual

    Request body:
        name (str, optional): Novo nome do usuário
        current_password (str, optional): Senha atual (se for alterar a senha)
        new_password (str, optional): Nova senha

    Returns:
        JSON: Status da atualização
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404

        data = request.get_json()

        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400

        # Atualizar nome
        if 'name' in data:
            user.name = data['name']

        # Atualizar senha
        if 'new_password' in data:
            current_password = data.get('current_password')

            if not current_password:
                return jsonify({'error': 'Senha atual é obrigatória para alterar a senha'}), 400

            if not user.check_password(current_password):
                return jsonify({'error': 'Senha atual incorreta'}), 400

            new_password = data['new_password']

            # Validar nova senha
            is_valid, password_error = is_valid_password(new_password)
            if not is_valid:
                return jsonify({'error': password_error}), 400

            user.set_password(new_password)

        user.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'message': 'Perfil atualizado com sucesso',
            'user': user.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Erro ao atualizar perfil: {str(e)}")
        db.session.rollback()
        return jsonify({'error': f'Erro ao atualizar perfil: {str(e)}'}), 500

@auth_bp.route('/users', methods=['GET'])
@jwt_required()
def get_users():
    """
    Obtém lista de usuários da organização do usuário atual

    Returns:
        JSON: Lista de usuários
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404

        # Verificar se o usuário tem permissão (admin ou manager)
        if user.role not in ['admin', 'manager']:
            return jsonify({'error': 'Permissão negada'}), 403

        # Buscar usuários da mesma organização
        organization_users = User.query.filter_by(organization_id=user.organization_id).all()

        return jsonify([u.to_dict() for u in organization_users]), 200

    except Exception as e:
        logger.error(f"Erro ao obter usuários: {str(e)}")
        return jsonify({'error': f'Erro ao obter usuários: {str(e)}'}), 500

@auth_bp.route('/invite', methods=['POST', 'GET'])
@jwt_required()
def invite_user():
    """
    Convida um usuário para a organização

    Request body:
        email (str): Email do usuário a ser convidado
        role (str): Papel do usuário (admin, manager, operator)

    Returns:
        JSON: Status do convite
    """
    # Para requisições GET, apenas retornar status OK
    if request.method == 'GET':
        return jsonify({'message': 'Endpoint de convite disponível'}), 200

    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404

        # Verificar se o usuário tem permissão (admin)
        if user.role != 'admin':
            return jsonify({'error': 'Apenas administradores podem convidar usuários'}), 403

        data = request.get_json()

        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400

        email = data.get('email')
        role = data.get('role', 'operator')

        if not email:
            return jsonify({'error': 'Email é obrigatório'}), 400

        if role not in ['admin', 'manager', 'operator']:
            return jsonify({'error': 'Papel inválido. Deve ser admin, manager ou operator'}), 400

        # Verificar se o email já está em uso
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'error': 'Email já cadastrado'}), 400

        # Em um cenário real, você enviaria um email com um link de convite
        # Por simplicidade, vamos apenas simular isso
        invite_token = str(uuid.uuid4())

        # Em um cenário real, você salvaria o convite no banco de dados
        # Por simplicidade, vamos apenas logar
        logger.info(f"Convite enviado para {email} com token {invite_token}")

        return jsonify({
            'message': 'Convite enviado com sucesso',
            'email': email,
            'role': role,
            'invite_url': f"{request.host_url}login?invite={invite_token}"
        }), 200

    except Exception as e:
        logger.error(f"Erro ao convidar usuário: {str(e)}")
        return jsonify({'error': f'Erro ao convidar usuário: {str(e)}'}), 500

@auth_bp.route('/accept-invite/<token>', methods=['GET'])
def check_invite(token):
    """
    Verifica se um convite é válido

    Path params:
        token (str): Token do convite

    Returns:
        JSON: Informações do convite
    """
    try:
        # Em um cenário real, você verificaria o token no banco de dados
        # Por simplicidade, vamos apenas simular isso

        # Simular convite válido
        if token and len(token) > 10:
            return jsonify({
                'valid': True,
                'email': f"convidado_{token[:8]}@example.com",
                'organization': {
                    'id': str(uuid.uuid4()),
                    'name': 'Organização Exemplo'
                },
                'role': 'operator'
            }), 200
        else:
            return jsonify({
                'valid': False,
                'error': 'Convite inválido ou expirado'
            }), 400

    except Exception as e:
        logger.error(f"Erro ao verificar convite: {str(e)}")
        return jsonify({'error': f'Erro ao verificar convite: {str(e)}'}), 500

@auth_bp.route('/accept-invite', methods=['POST', 'GET'])
def accept_invite():
    """
    Aceita um convite e cria um usuário

    Request body:
        token (str): Token do convite
        name (str): Nome do usuário
        password (str): Senha do usuário

    Returns:
        JSON: Status da aceitação
    """
    # Para requisições GET, apenas retornar status OK
    if request.method == 'GET':
        return jsonify({'message': 'Endpoint de aceitação de convite disponível'}), 200

    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400

        token = data.get('token')
        name = data.get('name')
        password = data.get('password')

        if not token or not name or not password:
            return jsonify({'error': 'Token, nome e senha são obrigatórios'}), 400

        # Validar senha
        is_valid, password_error = is_valid_password(password)
        if not is_valid:
            return jsonify({'error': password_error}), 400

        # Em um cenário real, você verificaria o token no banco de dados
        # e obteria o email e a organização associados
        # Por simplicidade, vamos apenas simular isso

        # Simular convite válido
        if token and len(token) > 10:
            email = f"convidado_{token[:8]}@example.com"
            organization_id = str(uuid.uuid4())
            role = 'operator'

            # Verificar se o email já está em uso
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                return jsonify({'error': 'Email já cadastrado'}), 400

            # Criar usuário
            new_user = User(
                id=str(uuid.uuid4()),
                name=name,
                email=email,
                role=role,
                organization_id=organization_id
            )

            # Definir senha
            new_user.set_password(password)

            # Adicionar ao banco de dados
            db.session.add(new_user)
            db.session.commit()

            return jsonify({
                'message': 'Convite aceito com sucesso',
                'user_id': new_user.id
            }), 201
        else:
            return jsonify({
                'error': 'Convite inválido ou expirado'
            }), 400

    except Exception as e:
        logger.error(f"Erro ao aceitar convite: {str(e)}")
        db.session.rollback()
        return jsonify({'error': f'Erro ao aceitar convite: {str(e)}'}), 500

@auth_bp.route('/forgot-password', methods=['POST', 'GET'])
def forgot_password():
    """
    Solicita redefinição de senha

    Request body:
        email (str): Email do usuário

    Returns:
        JSON: Status da solicitação
    """
    # Para requisições GET, apenas retornar status OK
    if request.method == 'GET':
        return jsonify({'message': 'Endpoint de recuperação de senha disponível'}), 200

    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400

        email = data.get('email')

        if not email:
            return jsonify({'error': 'Email é obrigatório'}), 400

        # Buscar usuário pelo email
        user = User.query.filter_by(email=email).first()

        # Por segurança, não informamos se o email existe ou não
        if not user:
            logger.info(f"Tentativa de redefinição de senha para email não cadastrado: {email}")
            return jsonify({
                'message': 'Se o email estiver registrado, um link de redefinição de senha será enviado'
            }), 200

        # Em um cenário real, você enviaria um email com um link de redefinição
        # Por simplicidade, vamos apenas simular isso
        reset_token = str(uuid.uuid4())

        # Em um cenário real, você salvaria o token no banco de dados
        # Por simplicidade, vamos apenas logar
        logger.info(f"Token de redefinição de senha para {email}: {reset_token}")

        return jsonify({
            'message': 'Se o email estiver registrado, um link de redefinição de senha será enviado'
        }), 200

    except Exception as e:
        logger.error(f"Erro ao solicitar redefinição de senha: {str(e)}")
        return jsonify({'error': f'Erro ao solicitar redefinição de senha: {str(e)}'}), 500

@auth_bp.route('/reset-password', methods=['POST', 'GET'])
def reset_password():
    """
    Redefine a senha do usuário

    Request body:
        token (str): Token de redefinição
        password (str): Nova senha

    Returns:
        JSON: Status da redefinição
    """
    # Para requisições GET, apenas retornar status OK
    if request.method == 'GET':
        return jsonify({'message': 'Endpoint de redefinição de senha disponível'}), 200

    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400

        token = data.get('token')
        password = data.get('password')

        if not token or not password:
            return jsonify({'error': 'Token e senha são obrigatórios'}), 400

        # Validar senha
        is_valid, password_error = is_valid_password(password)
        if not is_valid:
            return jsonify({'error': password_error}), 400

        # Em um cenário real, você verificaria o token no banco de dados
        # e obteria o usuário associado
        # Por simplicidade, vamos apenas simular isso

        # Simular token válido
        if token and len(token) > 10:
            # Em um cenário real, você buscaria o usuário pelo token
            # Por simplicidade, vamos usar um usuário de teste
            user = User.query.first()

            if not user:
                return jsonify({'error': 'Usuário não encontrado'}), 404

            # Definir nova senha
            user.set_password(password)
            user.updated_at = datetime.utcnow()
            db.session.commit()

            return jsonify({
                'message': 'Senha redefinida com sucesso'
            }), 200
        else:
            return jsonify({
                'error': 'Token inválido ou expirado'
            }), 400

    except Exception as e:
        logger.error(f"Erro ao redefinir senha: {str(e)}")
        db.session.rollback()
        return jsonify({'error': f'Erro ao redefinir senha: {str(e)}'}), 500

@auth_bp.route('/confirm-email/<token>', methods=['GET'])
def confirm_email(token):
    """
    Confirma o email do usuário

    Path params:
        token (str): Token de confirmação

    Returns:
        JSON: Status da confirmação
    """
    try:
        # Em um cenário real, você verificaria o token no banco de dados
        # e obteria o usuário associado
        # Por simplicidade, vamos apenas simular isso

        # Simular token válido
        if token and len(token) > 10:
            # Em um cenário real, você buscaria o usuário pelo token
            # Por simplicidade, vamos usar um usuário de teste
            user = User.query.first()

            if not user:
                return jsonify({'error': 'Usuário não encontrado'}), 404

            # Marcar email como confirmado
            # Em um cenário real, você teria um campo email_confirmed
            # Por simplicidade, vamos apenas logar
            logger.info(f"Email confirmado para usuário {user.id}")

            return jsonify({
                'message': 'Email confirmado com sucesso'
            }), 200
        else:
            return jsonify({
                'error': 'Token inválido ou expirado'
            }), 400

    except Exception as e:
        logger.error(f"Erro ao confirmar email: {str(e)}")
        return jsonify({'error': f'Erro ao confirmar email: {str(e)}'}), 500

@auth_bp.route('/organization', methods=['GET'])
@jwt_required()
def get_organization():
    """
    Obtém informações da organização do usuário atual

    Returns:
        JSON: Informações da organização
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404

        if not user.organization_id:
            return jsonify({'error': 'Usuário não pertence a nenhuma organização'}), 404

        # Em um cenário real, você buscaria a organização no banco de dados
        # Por simplicidade, vamos apenas simular isso

        return jsonify({
            'id': user.organization_id,
            'name': 'Organização Exemplo',
            'plan': 'basic',
            'created_at': datetime.utcnow().isoformat(),
            'user_count': User.query.filter_by(organization_id=user.organization_id).count()
        }), 200

    except Exception as e:
        logger.error(f"Erro ao obter organização: {str(e)}")
        return jsonify({'error': f'Erro ao obter organização: {str(e)}'}), 500

@auth_bp.route('/organization', methods=['PUT', 'GET'])
@jwt_required()
def update_organization():
    """
    Atualiza informações da organização

    Request body:
        name (str, optional): Novo nome da organização

    Returns:
        JSON: Status da atualização
    """
    # Para requisições GET, apenas retornar status OK
    if request.method == 'GET':
        return jsonify({'message': 'Endpoint de atualização de organização disponível'}), 200

    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404

        # Verificar se o usuário tem permissão (admin)
        if user.role != 'admin':
            return jsonify({'error': 'Apenas administradores podem atualizar a organização'}), 403

        if not user.organization_id:
            return jsonify({'error': 'Usuário não pertence a nenhuma organização'}), 404

        data = request.get_json()

        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400

        name = data.get('name')

        if not name:
            return jsonify({'error': 'Nome da organização é obrigatório'}), 400

        # Em um cenário real, você atualizaria a organização no banco de dados
        # Por simplicidade, vamos apenas simular isso
        logger.info(f"Organização {user.organization_id} atualizada: nome = {name}")

        return jsonify({
            'message': 'Organização atualizada com sucesso',
            'organization': {
                'id': user.organization_id,
                'name': name,
                'plan': 'basic',
                'updated_at': datetime.utcnow().isoformat()
            }
        }), 200

    except Exception as e:
        logger.error(f"Erro ao atualizar organização: {str(e)}")
        return jsonify({'error': f'Erro ao atualizar organização: {str(e)}'}), 500
