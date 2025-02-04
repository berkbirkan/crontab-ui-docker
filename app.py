from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import subprocess

# Uygulama ve konfigürasyon ayarları
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelleri içe aktar
from models import AdminUser, CronJob, CronErrorLog

# Flask-Login ayarları
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return AdminUser.query.get(int(user_id))

# Özel Flask-Admin view'larıyla yönetim paneline giriş kontrolü ekliyoruz
class MyModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated
    
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login', next=request.url))

class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
         return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
         return redirect(url_for('login', next=request.url))

# Admin panel ayarları
admin = Admin(app, index_view=MyAdminIndexView(), template_mode='bootstrap3')
admin.add_view(MyModelView(CronJob, db.session))
admin.add_view(MyModelView(AdminUser, db.session))
admin.add_view(MyModelView(CronErrorLog, db.session))

# APScheduler kurulumu (cron işlemlerinin zamanlanması için)
scheduler = BackgroundScheduler()

def execute_cron(cron_id):
    """Planlanan cron görevinin çalıştırılması ve hata durumunda log tutulması"""
    with app.app_context():
        cron = CronJob.query.get(cron_id)
        if not cron or not cron.active:
            return
        try:
            # Komutu çalıştır; shell=True kullanılarak sistem komutu çalıştırıyoruz.
            subprocess.run(cron.command, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            error_log = CronErrorLog(cron_id=cron.id, error_message=str(e))
            db.session.add(error_log)
            db.session.commit()

def schedule_cron_job(cron):
    """Veritabanındaki cron job objesine ait APScheduler job'unu planla"""
    parts = cron.schedule.split()
    if len(parts) != 5:
        print(f"Cron job {cron.id} için geçersiz schedule: {cron.schedule}")
        return
    try:
        trigger = CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4]
        )
        scheduler.add_job(
            func=execute_cron,
            args=[cron.id],
            trigger=trigger,
            id=f"cron_{cron.id}",
            replace_existing=True
        )
    except Exception as e:
        print(f"Cron job {cron.id} planlanırken hata oluştu: {e}")

def reschedule_all_crons():
    """Tüm aktif cron job'ları için APScheduler planlamasını güncelle"""
    scheduler.remove_all_jobs()
    for cron in CronJob.query.filter_by(active=True).all():
        schedule_cron_job(cron)

# REST API uç noktaları
@app.route('/api/cronjobs', methods=['GET'])
def get_cronjobs():
    crons = CronJob.query.all()
    data = []
    for cron in crons:
        data.append({
            'id': cron.id,
            'name': cron.name,
            'command': cron.command,
            'schedule': cron.schedule,
            'description': cron.description,
            'active': cron.active
        })
    return jsonify(data)

@app.route('/api/cronjobs', methods=['POST'])
def add_cronjob():
    data = request.get_json()
    cron = CronJob(
        name=data.get('name'),
        command=data.get('command'),
        schedule=data.get('schedule'),
        description=data.get('description'),
        active=data.get('active', True)
    )
    db.session.add(cron)
    db.session.commit()
    reschedule_all_crons()
    return jsonify({'message': 'Cron job eklendi', 'id': cron.id}), 201

@app.route('/api/cronjobs/<int:cron_id>', methods=['PUT'])
def update_cronjob(cron_id):
    cron = CronJob.query.get_or_404(cron_id)
    data = request.get_json()
    cron.name = data.get('name', cron.name)
    cron.command = data.get('command', cron.command)
    cron.schedule = data.get('schedule', cron.schedule)
    cron.description = data.get('description', cron.description)
    cron.active = data.get('active', cron.active)
    db.session.commit()
    reschedule_all_crons()
    return jsonify({'message': 'Cron job güncellendi'})

@app.route('/api/cronjobs/<int:cron_id>', methods=['DELETE'])
def delete_cronjob(cron_id):
    cron = CronJob.query.get_or_404(cron_id)
    db.session.delete(cron)
    db.session.commit()
    reschedule_all_crons()
    return jsonify({'message': 'Cron job silindi'})

# Giriş (login) fonksiyonları
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = AdminUser.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next') or url_for('admin.index')
            return redirect(next_page)
        else:
            flash("Kullanıcı adı veya şifre hatalı", "error")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Uygulama ilk çalıştığında veritabanı ve scheduler ayarlarının yapılması için
@app.before_first_request
def initialize():
    db.create_all()
    # Varsayılan admin kullanıcı oluştur (örn: username: admin, password: admin123)
    if not AdminUser.query.filter_by(username='admin').first():
        from werkzeug.security import generate_password_hash
        default_user = AdminUser(username='admin', password_hash=generate_password_hash('admin123'))
        db.session.add(default_user)
        db.session.commit()
    reschedule_all_crons()
    if not scheduler.running:
        scheduler.start()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0') 