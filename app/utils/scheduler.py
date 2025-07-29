from apscheduler.schedulers.background import BackgroundScheduler
from app.controllers.notification_controller import check_and_send_scheduled_notifications
from app.utils.subscription_utils import check_subscriptions

scheduler = BackgroundScheduler()

def start():
    scheduler.add_job(
        check_and_send_scheduled_notifications,
        trigger='cron',
        hour=0,
        minute=0,
        id='daily_notifications',
        replace_existing=True
    )
    scheduler.add_job(
        check_subscriptions,
        trigger='cron',
        hour=0,
        minute=5,  
        id='daily_subscription_check',
        replace_existing=True
    )
    scheduler.start()
    print("Scheduler started with all jobs.")
