from database.db import SessionLocal
from database.models import Trend

def save_trends(trend_list):
    db = SessionLocal()
    for t in trend_list:
        entry = Trend(
            keyword=t["keyword"],
            source=t["source"],
            score=t["score"]
        )
        db.add(entry)
    db.commit()
    db.close()

