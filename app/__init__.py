from flask import Flask
from flask_admin import Admin
from flask_login import LoginManager
from .models import db, User, CronJob, ErrorLog
from .views import AdminIndexView, CronJobModelView, ErrorLogModelView
from .api import api_bp
from flask_migrate import Migrate

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'gizli-anahtar-buraya'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:password@db:5432/crondb'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    migrate = Migrate(app, db)

    # Veritabanı tablolarını oluştur
    with app.app_context():
        db.create_all()
        
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    admin = Admin(app, name='Cron Yönetimi', template_mode='bootstrap4', index_view=AdminIndexView())
    admin.add_view(CronJobModelView(CronJob, db.session))
    admin.add_view(ErrorLogModelView(ErrorLog, db.session))

    app.register_blueprint(api_bp)

    return app 