"""
Celery configuration for OpenClaw Dashboard.
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('openclaw_dashboard')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat schedule
app.conf.beat_schedule = {
    'daily-job-search-8am': {
        'task': 'jobapply.tasks.run_daily_job_search',
        'schedule': crontab(hour=8, minute=0),  # 8 AM UTC (3 AM EST)
    },
    'daily-job-search-1pm': {
        'task': 'jobapply.tasks.run_daily_job_search',
        'schedule': crontab(hour=13, minute=0),  # 1 PM UTC (8 AM EST)
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
