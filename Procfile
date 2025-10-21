web: cd backend && python start.py
worker: cd backend && celery -A app.celery_app worker --loglevel=info
beat: cd backend && celery -A app.celery_app beat --loglevel=info
