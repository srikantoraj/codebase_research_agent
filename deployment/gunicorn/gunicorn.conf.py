bind = "127.0.0.1:8000"
workers = 3
timeout = 120
accesslog = "logs/gunicorn-access.log"
errorlog = "logs/gunicorn-error.log"
loglevel = "info"
