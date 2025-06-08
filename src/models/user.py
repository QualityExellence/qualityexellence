from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid
import secrets
import string

# Inicializar SQLAlchemy
db = SQLAlchemy()

def generate_uuid():
    return str(uuid.uuid4())

def generate_token(length=32):
    """Gera um token aleatório para confirmação de email ou redefinição de senha"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

class Organization(db.Model):
    """Modelo para organizações/empresas no sistema"""
    __tablename__ = 'organizations'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(100), nullable=False)
    domain = db.Column(db.String(100), nullable=True)  # Domínio de email da organização
    plan = db.Column(db.String(20), default='basic')  # basic, pro, enterprise
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relacionamentos
    users = db.relationship('User', backref='organization', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'domain': self.domain,
            'plan': self.plan,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class User(db.Model):
    """Modelo para usuários do sistema"""
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    role = db.Column(db.String(20), default='operator')  # admin, manager, operator
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'), nullable=True)
    email_confirmed = db.Column(db.Boolean, default=False)
    email_confirmation_token = db.Column(db.String(100), nullable=True)
    email_confirmation_sent_at = db.Column(db.DateTime, nullable=True)
    password_reset_token = db.Column(db.String(100), nullable=True)
    password_reset_expires_at = db.Column(db.DateTime, nullable=True)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        """Define a senha do usuário (hash)"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica se a senha está correta"""
        return check_password_hash(self.password_hash, password)

    def generate_email_confirmation_token(self):
        """Gera um token para confirmação de email"""
        self.email_confirmation_token = generate_token()
        self.email_confirmation_sent_at = datetime.utcnow()
        return self.email_confirmation_token

    def confirm_email(self, token):
        """Confirma o email do usuário"""
        if self.email_confirmation_token == token:
            self.email_confirmed = True
            self.email_confirmation_token = None
            return True
        return False

    def generate_password_reset_token(self, expires_in_hours=24):
        """Gera um token para redefinição de senha"""
        self.password_reset_token = generate_token()
        self.password_reset_expires_at = datetime.utcnow() + datetime.timedelta(hours=expires_in_hours)
        return self.password_reset_token

    def reset_password(self, token, new_password):
        """Redefine a senha do usuário"""
        if self.password_reset_token != token:
            return False

        if datetime.utcnow() > self.password_reset_expires_at:
            return False

        self.set_password(new_password)
        self.password_reset_token = None
        self.password_reset_expires_at = None
        return True

    def to_dict(self, include_organization=False):
        """Converte o usuário para dicionário"""
        user_dict = {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'organization_id': self.organization_id,
            'email_confirmed': self.email_confirmed,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

        if include_organization and self.organization:
            user_dict['organization'] = self.organization.to_dict()

        return user_dict

class Invitation(db.Model):
    """Modelo para convites de usuários"""
    __tablename__ = 'invitations'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    email = db.Column(db.String(120), nullable=False)
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'), nullable=False)
    role = db.Column(db.String(20), default='operator')
    token = db.Column(db.String(100), nullable=False, default=generate_token)
    invited_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    accepted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos
    organization = db.relationship('Organization', backref='invitations', lazy=True)
    inviter = db.relationship('User', backref='sent_invitations', lazy=True)

    def is_expired(self):
        """Verifica se o convite expirou"""
        return datetime.utcnow() > self.expires_at

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'organization_id': self.organization_id,
            'role': self.role,
            'invited_by': self.invited_by,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'accepted': self.accepted,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
