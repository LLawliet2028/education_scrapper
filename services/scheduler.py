from apscheduler.schedulers.background import BackgroundScheduler
from fetch.google_trends import fetch_google_trends
from fetch.reddit_trends import fetch_reddit_trends
# from fetch.youtube_trends import fetch_youtube_trends   # Disabled for now
from database.db import SessionLocal
from database.models import Trend

def save_to_db(items):
    db = SessionLocal()
    for item in items:
        trend = Trend(
            keyword=item["keyword"],
            source=item["source"],
            score=item["score"]
        )
        db.add(trend)
    db.commit()
    db.close()

def scheduled_job():
    print("✅ Scheduler running…")

    google = fetch_google_trends()
    reddit = fetch_reddit_trends()

    save_to_db(google)
    save_to_db(reddit)

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_job, "interval", seconds=30)
    scheduler.start()
