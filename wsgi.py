import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from app import create_app

application = create_app()  
application.debug = True 

if __name__ == "__main__":
    application.run(host=application.config['HOST'], port=application.config['PORT'])