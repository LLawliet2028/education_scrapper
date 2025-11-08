import praw
import time
import random
from config import REDDIT_CLIENT_ID, REDDIT_SECRET, REDDIT_USER_AGENT

SUBREDDITS = [
    "education", "Teachers", "teaching", "EdTech", "HigherEducation", "academia",
    "college", "university", "gradschool", "PhD", "AskAcademia", "Professors",
    "Scholarships", "students", "learnpython", "learnprogramming",
    "learnmachinelearning", "languagelearning", "edX", "Coursera", "MOOCs",
    "learnmath", "learnenglish", "science", "math", "Physics", "chemistry",
    "biology", "Engineering", "computerscience", "datascience",
    "MachineLearning", "deeplearning", "ArtificialInteligence", "robotics",
    "UPSC", "JEENEETards", "JEE", "NEET", "CATprep", "GATEprep", "SSC_CGL",
    "civilservices", "IAS", "SAT", "ACT", "GMAT", "GRE", "IELTS", "TOEFL",
    "study", "studyhack", "GetStudying", "productivity", "research"
]

def fetch_reddit_trends():
    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_SECRET,
            user_agent=REDDIT_USER_AGENT
        )

        reddit.read_only = True
        results = []

        for name in SUBREDDITS:
            try:
                sub = reddit.subreddit(name)

                for post in sub.hot(limit=8):
                    results.append({
                        "keyword": post.title,
                        "score": int(post.score) if post.score else 0,
                        "source": "reddit"
                    })

                # random sleep to avoid rate limits
                time.sleep(random.uniform(0.2, 0.6))

            except Exception as e:
                print(f"⚠️ Skipping subreddit {name}: {e}")

        print(f"✅ Reddit trends fetched: {len(results)} items")
        return results

    except Exception as e:
        print("❌ Reddit API Error:", e)
        return []
