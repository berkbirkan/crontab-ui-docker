from flask_admin import AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user, login_required
from flask import redirect, url_for
from .models import CronJob, ErrorLog
from crontab import CronTab

class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('auth.login'))

class CronJobModelView(SecureModelView):
    column_list = ('name', 'command', 'schedule', 'active', 'created_at', 'updated_at')
    form_columns = ('name', 'command', 'schedule', 'active')

    def after_model_change(self, form, model, is_created):
        system_cron = CronTab(user=True)
        if is_created:
            job = system_cron.new(command=model.command)
            job.setall(model.schedule)
        system_cron.write()

class ErrorLogModelView(SecureModelView):
    column_list = ('cron_job', 'error_message', 'timestamp')
    can_create = False
    can_edit = False 