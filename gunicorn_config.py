# Gunicorn configuration file
bind = '127.0.0.1:8000'
workers = 4  # Adjust based on your CPU cores
accesslog = '-'
errorlog = '-'
