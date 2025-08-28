export SLIDETAP_DBURI=sqlite:////mnt/c/temp/slidetap/db.sqlite
export SLIDETAP_BROKER_URL=amqp://user:password@localhost:5672
export  SLIDETAP_STORAGE=/mnt/c/temp/slidetap/storage

uv run celery -A slidetap.apps.example.task_app:task_app worker