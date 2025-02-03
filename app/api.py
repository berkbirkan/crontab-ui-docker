from flask import Blueprint, jsonify, request
from flask_restful import Api, Resource
from .models import db, CronJob, ErrorLog
from crontab import CronTab

api_bp = Blueprint('api', __name__)
api = Api(api_bp)

class CronJobResource(Resource):
    def get(self, job_id=None):
        if job_id:
            job = CronJob.query.get_or_404(job_id)
            return {
                'id': job.id,
                'name': job.name,
                'command': job.command,
                'schedule': job.schedule,
                'active': job.active
            }
        jobs = CronJob.query.all()
        return jsonify([{
            'id': job.id,
            'name': job.name,
            'command': job.command,
            'schedule': job.schedule,
            'active': job.active
        } for job in jobs])

    def post(self):
        data = request.get_json()
        job = CronJob(
            name=data['name'],
            command=data['command'],
            schedule=data['schedule'],
            active=data.get('active', True)
        )
        db.session.add(job)
        db.session.commit()

        system_cron = CronTab(user=True)
        cron_job = system_cron.new(command=job.command)
        cron_job.setall(job.schedule)
        system_cron.write()

        return {'message': 'Cron görevi başarıyla oluşturuldu', 'id': job.id}, 201

api.add_resource(CronJobResource, '/api/cron', '/api/cron/<int:job_id>') 