bind = "unix:/run/gunicorn/gunicorn.sock"

workers = 3

timeout = 300

keepalive = 5

worker_class = "sync"

max_requests = 1000

max_requests_jitter = 100

accesslog = "-"

errorlog = "-"

loglevel = "info"