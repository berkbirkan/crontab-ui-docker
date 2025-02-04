from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class AdminUser(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    
    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)

class CronJob(db.Model):
    __tablename__ = 'cron_job'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)           # Cron için isim
    command = db.Column(db.String(256), nullable=False)         # Çalıştırılacak komut
    schedule = db.Column(db.String(64), nullable=False)         # Cron zaman ifadesi örn: "*/5 * * * *"
    description = db.Column(db.Text, nullable=True)
    active = db.Column(db.Boolean, default=True)

class CronErrorLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cron_id = db.Column(db.Integer, db.ForeignKey('cron_job.id'))
    error_message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    cron = db.relationship("CronJob", backref=db.backref('error_logs', lazy=True)) 