import logging
logging.basicConfig(level=logging.DEBUG)  # Enable debug logging

from waitress import serve
from app import create_app  # Use the factory method

app = create_app()  # Create app instance

if __name__ == '__main__':
    print("Starting Waitress on 0.0.0.0:80")
    serve(app, listen='0.0.0.0:80')
