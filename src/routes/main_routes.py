from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from functools import wraps

# Criar blueprint
main_bp = Blueprint('main', __name__)

def jwt_optional(fn):
    """Decorator para tornar JWT opcional"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request(optional=True)
        except:
            pass
        return fn(*args, **kwargs)
    return wrapper

@main_bp.route('/')
@jwt_optional
def index():
    """Página inicial"""
    # Verificar se está logado
    try:
        verify_jwt_in_request()
        # Se não lançar exceção, está logado
        return render_template('index.html')
    except:
        # Se não estiver logado, redirecionar para login
        return redirect(url_for('main.login_page'))

@main_bp.route('/login')
def login_page():
    """Página de login"""
    # Verificar se já está logado
    try:
        verify_jwt_in_request()
        # Se não lançar exceção, está logado
        return redirect(url_for('main.index'))
    except:
        # Se lançar exceção, não está logado
        return render_template('login.html')

@main_bp.route('/import')
@jwt_required()
def import_page():
    """Página de importação"""
    return render_template('import.html')

@main_bp.route('/transcriptions')
@jwt_required()
def transcriptions_page():
    """Página de transcrições"""
    return render_template('index.html')

@main_bp.route('/dashboard')
@jwt_required()
def dashboard_page():
    """Página de dashboard"""
    return render_template('index.html')

@main_bp.route('/profile')
@jwt_required()
def profile_page():
    """Página de perfil"""
    return render_template('index.html')

@main_bp.route('/users')
@jwt_required()
def users_page():
    """Página de usuários"""
    return render_template('index.html')

@main_bp.route('/logout')
def logout_page():
    """Página de logout"""
    return render_template('login.html')
