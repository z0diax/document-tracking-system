from apscheduler.schedulers.background import BackgroundScheduler
from app.auto_archive import archive_old_documents

def start_scheduler():
    scheduler = BackgroundScheduler()
    # Schedule job to run daily at midnight
    scheduler.add_job(archive_old_documents, 'cron', hour=0, minute=0)
    scheduler.start()

if __name__ == '__main__':
    start_scheduler()
    # Keep the script running so the scheduler can work independently
    import time
    try:
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        pass
