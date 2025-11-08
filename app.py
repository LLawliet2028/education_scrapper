from flask import Flask, jsonify
from database.db import SessionLocal, Base, engine
from database.models import Trend
from services.scheduler import start_scheduler

# ✅ Create database tables automatically
Base.metadata.create_all(bind=engine)

app = Flask(__name__)
start_scheduler()  # automatic background fetching

@app.route("/")
def home():
    return "Trending Keyword Aggregator API Running ✅"

@app.route("/api/trends")
def get_trends():
    db = SessionLocal()
    trends = db.query(Trend).order_by(Trend.timestamp.desc()).limit(50).all()

    data = [
        {
            "keyword": t.keyword,
            "source": t.source,
            "score": t.score,
            "timestamp": t.timestamp.isoformat()
        }
        for t in trends
    ]

    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True)
