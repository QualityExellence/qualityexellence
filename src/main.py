import os
from flask import Flask, render_template, jsonify

from flask_cors import CORS
from dotenv import load_dotenv
import logging
import shutil
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, verify_jwt_in_request
from datetime import timedelta

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()

# Inicializar aplicação Flask
app = Flask(__name__,
            static_url_path='',
            static_folder=os.path.join(os.path.dirname(__file__), 'static'),
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'))

# Configurar CORS
CORS(app)

# Configurar JWT
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'sua_chave_secreta_aqui')  # Você já tem esta linha
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)  # Define o tempo de expiração do token
app.config['JWT_TOKEN_LOCATION'] = ['headers', 'cookies']  # Permite receber o token tanto do cabeçalho quanto de cookies
app.config['JWT_COOKIE_CSRF_PROTECT'] = False  # Desabilita proteção CSRF para simplificar

jwt = JWTManager(app)

# Configurar banco de dados
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///transcall.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configurar pasta de uploads
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads'))
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Importar e inicializar modelos
from src.models.user import db, User, Organization, Invitation
db.init_app(app)

# Verificar se o arquivo index.html está na pasta templates
def ensure_index_html_in_templates():
    static_index = os.path.join(app.static_folder, 'index.html')
    template_index = os.path.join(app.template_folder, 'index.html')

    # Criar pasta templates se não existir
    os.makedirs(app.template_folder, exist_ok=True)

    # Se index.html existe em static mas não em templates, copiar
    if os.path.exists(static_index) and not os.path.exists(template_index):
        shutil.copy2(static_index, template_index)
        logger.info(f"Copiado index.html de {static_index} para {template_index}")

# Registrar blueprints
from src.routes.auth.auth_routes import auth_bp
app.register_blueprint(auth_bp, url_prefix='/api/auth')

from src.routes.upload.upload_routes import upload_bp
app.register_blueprint(upload_bp, url_prefix='/api/upload')

from src.routes.upload.fourcom_routes import fourcom_bp
app.register_blueprint(fourcom_bp, url_prefix='/api/fourcom')

from src.routes.transcription.transcription_routes import transcription_bp
app.register_blueprint(transcription_bp, url_prefix='/api/transcription')

from src.routes.transcription.analysis_routes import analysis_bp
app.register_blueprint(analysis_bp, url_prefix='/api/analysis')

from src.routes.dashboard.dashboard_routes import dashboard_bp
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')

from src.routes.dashboard.export_routes import export_bp
app.register_blueprint(export_bp, url_prefix='/api/export')

# Registrar blueprint principal para rotas de páginas
from src.routes.main_routes import main_bp
app.register_blueprint(main_bp, url_prefix='/')

# Rota principal - redirecionada para o blueprint principal
@app.route('/')
def index():
    try:
        # Verificar o token JWT (opcional para não lançar exceção)
        verify_jwt_in_request(optional=True)
        current_user = get_jwt_identity()

        # Se tiver um usuário autenticado, mostrar a página principal
        if current_user:
            return render_template('index.html')
        else:
            # Se não tiver usuário, redirecionar para login
            return redirect('/login')
    except Exception as e:
        # Em caso de erro, redirecionar para login
        logger.error(f"Erro ao verificar token: {str(e)}")
        return redirect('/login')

# Criar tabelas do banco de dados
with app.app_context():
    ensure_index_html_in_templates()
    db.create_all()

    # Verificar se existe um usuário admin
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        # Criar organização padrão
        default_org = Organization(
            name='TransCall Admin',
            plan='enterprise',
            active=True
        )
        db.session.add(default_org)
        db.session.flush()

        # Criar usuário admin
        admin = User(
            name='Administrador',
            email=os.getenv('ADMIN_EMAIL', 'admin@transcall.com'),
            role='admin',
            organization_id=default_org.id,
            email_confirmed=True,
            active=True
        )
        admin.set_password(os.getenv('ADMIN_PASSWORD', 'admin123'))
        db.session.add(admin)
        db.session.commit()
        logger.info(f"Usuário admin criado: {admin.email}")

# Iniciar aplicação
if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'True').lower() in ('true', '1', 't')

    app.run(host=host, port=port, debug=debug)
