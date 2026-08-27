import os
import time

# Load environment variables from .env manually to ensure correctness in standalone mode
if os.path.exists('.env'):
    with open('.env') as f:
        for line in f:
            line_str = line.strip()
            if line_str and not line_str.startswith('#'):
                if line_str.startswith('export '):
                    line_str = line_str[7:]
                if '=' in line_str:
                    key, val = line_str.split('=', 1)
                    val = val.strip('"\'')
                    os.environ[key] = val

# Force the scheduler to start even if deactivated elsewhere (e.g. in multi-worker configurations)
os.environ['START_SCHEDULER'] = 'true'

from app import create_app

if __name__ == '__main__':
    print("Initializing Flask Application context...")
    app = create_app()
    print("Background scheduler initialized and started successfully.")
    print("All tasks (SLA checks, weather sync) are scheduled in local timezone.")
    print("Press Ctrl+C to exit.")
    
    try:
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        print("Shutting down background scheduler...")
        if hasattr(app, 'scheduler'):
            app.scheduler.shutdown()
        print("Scheduler stopped.")
