from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Premium subscription fields
    is_premium = db.Column(db.Boolean, default=False)
    premium_expires_at = db.Column(db.DateTime, nullable=True)
    stripe_customer_id = db.Column(db.String(255), nullable=True)
    stripe_subscription_id = db.Column(db.String(255), nullable=True)
    
    # Relacje z CV
    cv_uploads = db.relationship('CVUpload', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    def is_premium_active(self):
        """Check if user has active premium subscription"""
        if self.username == 'developer':  # Developer account always has premium
            return True
        if not self.is_premium or not self.premium_expires_at:
            return False
        return datetime.utcnow() < self.premium_expires_at
    
    def activate_premium(self, months=1):
        """Activate premium subscription for specified number of months"""
        from datetime import timedelta
        self.is_premium = True
        if self.premium_expires_at and self.premium_expires_at > datetime.utcnow():
            # Extend existing subscription
            self.premium_expires_at = self.premium_expires_at + timedelta(days=months*30)
        else:
            # New subscription
            self.premium_expires_at = datetime.utcnow() + timedelta(days=months*30)
    
    def deactivate_premium(self):
        """Deactivate premium subscription"""
        self.is_premium = False
        self.premium_expires_at = None
        self.stripe_subscription_id = None
    
    def __repr__(self):
        return f'<User {self.username}>'

class CVUpload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_text = db.Column(db.Text, nullable=False)
    job_title = db.Column(db.String(200), nullable=True)
    job_description = db.Column(db.Text, nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Wyniki analizy
    analysis_results = db.relationship('AnalysisResult', backref='cv_upload', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<CVUpload {self.filename}>'

class AnalysisResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cv_upload_id = db.Column(db.Integer, db.ForeignKey('cv_upload.id'), nullable=False)
    analysis_type = db.Column(db.String(50), nullable=False)  # 'optimize', 'feedback', 'cover_letter', etc.
    result_data = db.Column(db.Text, nullable=False)  # JSON string z wynikami
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AnalysisResult {self.analysis_type}>'

class UserSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_data = db.Column(db.Text)  # JSON data for user preferences
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserSession {self.user_id}>'